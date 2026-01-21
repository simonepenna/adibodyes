"""
AWS Lambda function per estrarre le spedizioni GLS consegnate in Parcel Shop
(stato: ENTREGADO EN PARCELSHOP GLS)
"""
import requests
import time
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re
from collections import defaultdict
import pandas as pd
from pathlib import Path
import json
import sys
import os
import logging

# Configurazione logging per CloudWatch
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Configurazione Shopify da environment variables
SHOPIFY_ACCESS_TOKEN = os.environ.get("SHOPIFY_ACCESS_TOKEN")
SHOPIFY_GRAPHQL_URL = os.environ.get("SHOPIFY_GRAPHQL_URL")


class GLSExtranetClient:
    def __init__(self, cookies=None):
        """
        Inizializza il client con i cookies della sessione o vuoto per login

        Args:
            cookies: Dict con i cookies dalla tua sessione browser (opzionale)
        """
        self.session = requests.Session()
        self.base_url = "https://extranet.gls-spain.es"
        self.login_url = f"{self.base_url}/extranet/login.aspx?ReturnUrl=~/default.aspx"
        self.search_url = f"{self.base_url}/Extranet/MiraEnvios/Miraenvios.aspx"

        # Imposta i cookies se forniti
        if cookies:
            for name, value in cookies.items():
                self.session.cookies.set(name, value)

        # Headers esatti dal browser (curl) per performance ottimale
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'es,en-US;q=0.9,en;q=0.8,it-IT;q=0.7,it;q=0.6',
            'cache-control': 'no-cache',
            'pragma': 'no-cache',
            'priority': 'u=0, i',
            'sec-ch-ua': '"Not(A:Brand";v="8", "Chromium";v="144", "Google Chrome";v="144"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
        })

    def login(self, username, password):
        """
        Effettua il login all'extranet GLS

        Args:
            username: Username GLS
            password: Password GLS

        Returns:
            bool: True se login riuscito
        """
        logger.info(f"🔐 Login con utente: {username}")

        # 1. Ottieni la pagina di login per ViewState
        t_start = time.time()
        response = self.session.get(self.login_url)
        logger.info(f"⏱️ GET pagina login: {time.time() - t_start:.2f}s")
        if response.status_code != 200:
            logger.error(f"❌ Errore caricamento pagina login: {response.status_code}")
            return False

        soup = BeautifulSoup(response.content, 'html.parser')

        # Estrai ViewState e altri campi nascosti
        viewstate = {}
        for field in ['__VIEWSTATE', '__VIEWSTATEGENERATOR', '__EVENTVALIDATION']:
            input_field = soup.find('input', {'name': field})
            if input_field:
                viewstate[field] = input_field.get('value', '')

        # 2. Invia credenziali di login
        login_data = {
            '__VIEWSTATE': viewstate.get('__VIEWSTATE', ''),
            '__VIEWSTATEGENERATOR': viewstate.get('__VIEWSTATEGENERATOR', ''),
            '__EVENTVALIDATION': viewstate.get('__EVENTVALIDATION', ''),
            'usuario': username,
            'pass': password,
            'Button1.x': '43',
            'Button1.y': '8'
        }

        # Aggiorna headers per il POST
        self.session.headers.update({
            'Referer': self.login_url,
            'Origin': self.base_url,
            'Content-Type': 'application/x-www-form-urlencoded'
        })

        t_start = time.time()
        response = self.session.post(
            self.login_url,
            data=login_data,
            allow_redirects=True
        )
        logger.info(f"⏱️ POST login: {time.time() - t_start:.2f}s")

        # Verifica se il login è riuscito
        if response.status_code == 200:
            # Controlla se siamo stati reindirizzati alla home o se ci sono errori
            if 'Login.aspx' not in response.url and 'error' not in response.text.lower():
                logger.info(f"✅ Login riuscito! Session ID: {self.session.cookies.get('ASP.NET_SessionId')}")
                return True
            else:
                logger.error("❌ Login fallito - controlla credenziali")
                return False
        else:
            logger.error(f"❌ Errore HTTP durante login: {response.status_code}")
            return False

    def save_cookies(self, filename='gls_cookies.json'):
        """
        Salva i cookies della sessione corrente in un file

        Args:
            filename: Nome del file dove salvare i cookies
        """
        cookies_dict = dict(self.session.cookies)

        # In Lambda, usa /tmp per salvare i cookies (filesystem scrivibile)
        filepath = Path('/tmp') / filename

        with open(filepath, 'w') as f:
            json.dump(cookies_dict, f, indent=2)

        logger.info(f"💾 Cookies salvati in: {filepath}")

    @staticmethod
    def load_cookies(filename='gls_cookies.json'):
        """
        Carica i cookies da un file

        Args:
            filename: Nome del file da cui caricare i cookies

        Returns:
            dict: Cookies caricati
        """
        # In Lambda, cerca in /tmp
        filepath = Path('/tmp') / filename

        if not filepath.exists():
            logger.warning(f"⚠️ File {filepath} non trovato")
            return {}

        with open(filepath, 'r') as f:
            cookies = json.load(f)

        logger.info(f"📂 Cookies caricati da: {filepath}")
        return cookies

    def search_shipments(self, date_from, date_to, cliente="586-4073"):
        """
        Cerca spedizioni per range di date

        Args:
            date_from: Data inizio (DD/MM/YYYY)
            date_to: Data fine (DD/MM/YYYY)
            cliente: Codice cliente (default dal tuo curl)

        Returns:
            Response HTML con le spedizioni
        """
        # Ottieni ViewState con una singola richiesta GET
        t_start = time.time()
        response = self.session.get(self.search_url)
        logger.info(f"⏱️ GET ViewState: {time.time() - t_start:.2f}s")
        if response.status_code != 200:
            raise Exception(f"Errore caricamento pagina: {response.status_code}")
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        viewstate = {}
        for field in ['__VIEWSTATE', '__VIEWSTATEGENERATOR', '__EVENTVALIDATION']:
            input_field = soup.find('input', {'name': field})
            if input_field:
                viewstate[field] = input_field.get('value', '')

        # Prepara i dati del form
        form_data = {
            '__EVENTTARGET': '',
            '__EVENTARGUMENT': '',
            '__LASTFOCUS': '',
            '__VIEWSTATE': viewstate.get('__VIEWSTATE', ''),
            '__VIEWSTATEGENERATOR': viewstate.get('__VIEWSTATEGENERATOR', ''),
            '__EVENTVALIDATION': viewstate.get('__EVENTVALIDATION', ''),
            'fechadesde': date_from,
            'fechahasta': date_to,
            'cliente': cliente,
            'codplaza_dst': '-987',
            'horario': '-987',
            'servicio': '-987',
            'referencia': '',
            'dpto_org': '',
            'cpDst': '',
            'pais_dst': '-987',
            'btBuscar.x': '42',
            'btBuscar.y': '3',
        }

        logger.info(f"🔍 Ricerca spedizioni dal {date_from} al {date_to}...")
        t_start = time.time()
        response = self.session.post(
            self.search_url,
            data=form_data,
            headers={
                'Content-Type': 'application/x-www-form-urlencoded',
                'Referer': self.search_url,
                'Origin': self.base_url,
            }
        )
        logger.info(f"⏱️ POST ricerca: {time.time() - t_start:.2f}s")

        if response.status_code != 200:
            raise Exception(f"Errore ricerca: {response.status_code}")

        return response.text

    def parse_shipments(self, html_content):
        """
        Estrae le spedizioni dalla tabella nascosta nei commenti HTML
        GLS include una tabella completa con id="gr" dentro i commenti HTML
        che contiene TUTTI i campi incluso cp_dst alla colonna 32
        
        OTTIMIZZATO: usa regex per estrarre commento + filtra prima di creare dizionari
        
        Args:
            html_content: HTML della risposta
            
        Returns:
            pandas DataFrame con info spedizioni
        """
        # OTTIMIZZAZIONE 1: Usa regex per trovare il commento (molto più veloce)
        import re
        comment_match = re.search(r'<!--.*?<table[^>]*id=["\']gr["\'].*?</table>.*?-->', html_content, re.DOTALL)
        
        if not comment_match:
            logger.warning("⚠️ Tabella nascosta id='gr' non trovata nei commenti")
            return pd.DataFrame()
        
        # Estrai solo il contenuto della tabella dal commento
        comment_html = comment_match.group(0).replace('<!--', '').replace('-->', '')
        
        # Parsa SOLO il commento (non tutto l'HTML)
        soup = BeautifulSoup(comment_html, 'html.parser')
        table_gr = soup.find('table', id='gr')
        
        if not table_gr:
            logger.warning("⚠️ Tabella id='gr' non trovata")
            return pd.DataFrame()
        
        rows = table_gr.find_all('tr')
        if len(rows) < 2:
            logger.warning("⚠️ Nessuna riga dati nella tabella gr")
            return pd.DataFrame()
        
        # Estrai nomi colonne
        columns = [th.get_text(strip=True) for th in rows[0].find_all('th')]
        
        # Trova indice colonna 'estado' per filtrare subito
        try:
            estado_idx = columns.index('estado')
        except ValueError:
            logger.warning("⚠️ Colonna 'estado' non trovata")
            return pd.DataFrame()
        
        logger.info(f"📋 {len(columns)} colonne - cp_dst: {columns.index('cp_dst') if 'cp_dst' in columns else 'N/A'}")
        
        # OTTIMIZZAZIONE 2: Filtra PRIMA di creare dizionari
        shipments = []
        
        for row in rows[1:]:
            cells = row.find_all('td')
            if len(cells) != len(columns):
                continue
            
            # Controlla subito lo stato (colonna estado_idx)
            estado = cells[estado_idx].get_text(strip=True).upper()
            if 'PARCELSHOP' not in estado:
                continue  # Skip subito senza creare dizionario
            
            # Solo per PARCELSHOP: estrai testo celle
            cell_values = [cell.get_text(strip=True) for cell in cells]
            row_data = dict(zip(columns, cell_values))
            
            # Recupera telefono da Shopify
            referencia = row_data.get('Referencia', '')
            phone = self.get_phone_from_shopify(referencia) if referencia else None
            
            # Mappa campi
            shipments.append({
                'expedicion': row_data.get('Expedicion', ''),
                'referencia': referencia,
                'estado': row_data.get('estado', ''),
                'pod': row_data.get('Pod', ''),
                'fecha': row_data.get('Fecha', ''),
                'servicio': row_data.get('Servicio', ''),
                'horario': row_data.get('Horario', ''),
                'bultos': row_data.get('bultos', ''),
                'kgs': row_data.get('Kgs', ''),
                'reembolso': row_data.get('Reembolso', ''),
                'destinatario': row_data.get('Destinatario', ''),
                'phone': phone,  # ✅ TELEFONO DA SHOPIFY
                'dac': row_data.get('dac', ''),
                'retorno': row_data.get('retorno', ''),
                'direccion': row_data.get('Direccion', ''),
                'localidad': row_data.get('Localidad', ''),
                'cp_dst': row_data.get('cp_dst', ''),
                'cp_org': row_data.get('cp_org', ''),
                'nombre_org': row_data.get('nombre_org', ''),
                'localidad_org': row_data.get('localidad_org', ''),
                'fecha_actualizacion': row_data.get('fechaActualizacion', ''),
            })

        logger.info(f"✅ Trovate {len(shipments)} spedizioni PARCELSHOP con cp_dst")
        return pd.DataFrame(shipments)

    def get_phone_from_shopify(self, order_number):
        """
        Cerca telefono cliente da Shopify usando il numero ordine
        
        Args:
            order_number: Numero ordine Shopify (es: "8369")
            
        Returns:
            str: Numero telefono o None
        """
        try:
            # Shopify usa formato #ES8369
            query = f"""
            {{
              orders(first: 1, query: "name:#ES{order_number}") {{
                edges {{
                  node {{
                    phone
                    customer {{
                      phone
                    }}
                    shippingAddress {{
                      phone
                    }}
                  }}
                }}
              }}
            }}
            """
            
            headers = {
                'X-Shopify-Access-Token': SHOPIFY_ACCESS_TOKEN,
                'Content-Type': 'application/json'
            }
            
            response = requests.post(SHOPIFY_GRAPHQL_URL, headers=headers, json={"query": query}, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                edges = data.get('data', {}).get('orders', {}).get('edges', [])
                if edges:
                    node = edges[0]['node']
                    # Prova in ordine: phone ordine, phone cliente, phone indirizzo spedizione
                    phone = (node.get('phone') or 
                            (node.get('customer', {}).get('phone') if node.get('customer') else None) or
                            (node.get('shippingAddress', {}).get('phone') if node.get('shippingAddress') else None))
                    return phone
            
            return None
            
        except Exception as e:
            logger.warning(f"⚠️ Errore recupero telefono per ordine {order_number}: {e}")
            return None


def lambda_handler(event, context):
    """
    Handler principale della Lambda function

    Args:
        event: Evento Lambda (può contenere parametri custom)
        context: Contesto Lambda

    Returns:
        dict: Risposta della funzione
    """
    logger.info("🚀 Avvio estrazione spedizioni GLS consegnate in Parcel Shop")

    try:
        # === CONFIGURAZIONE ===
        # Parametri da environment variables
        username = os.environ.get("GLS_USERNAME", "586-4073")
        password = os.environ.get("GLS_PASSWORD", "Leneis586?!")
        
        # Parse del body se proviene da API Gateway
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event
        
        # Parametro days_back dall'event (default 15 giorni)
        days_back = int(body.get('days_back', 15))
        logger.info(f"📊 Parametro ricevuto: days_back={days_back}")

        if not username or not password:
            raise ValueError("GLS_USERNAME e GLS_PASSWORD sono obbligatori nelle environment variables")

        # Date: ultimi N giorni
        today = datetime.now()
        date_from = (today - timedelta(days=days_back)).strftime("%d/%m/%Y")
        date_to = today.strftime("%d/%m/%Y")

        logger.info(f"📅 Periodo: {date_from} - {date_to}")

        # Login con credenziali
        client = GLSExtranetClient()
        if not client.login(username, password):
            raise Exception("Login GLS fallito")

        # Cerca spedizioni
        html = client.search_shipments(date_from, date_to)

        # Parse spedizioni
        t_start = time.time()
        df = client.parse_shipments(html)
        logger.info(f"⏱️ Parsing HTML: {time.time() - t_start:.2f}s")

        if df.empty:
            logger.warning("⚠️ Nessuna spedizione consegnata in Parcel Shop trovata")
            return {
                'statusCode': 200,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type',
                    'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
                },
                'body': json.dumps({
                    'message': 'Nessuna spedizione consegnata in Parcel Shop trovata',
                    'total_shipments': 0,
                    'period': f"{date_from} - {date_to}"
                })
            }

        logger.info(f"✅ Trovate {len(df)} spedizioni totali")

        # Converti DataFrame a lista di dict per JSON
        shipments_list = df.to_dict('records')

        # Restituisci direttamente i dati invece di salvare su S3
        result_data = {
            'metadata': {
                'extraction_date': datetime.now().isoformat(),
                'period': f"{date_from} - {date_to}",
                'total_shipments': len(df),
                'status_filter': 'ENTREGADO EN PARCELSHOP GLS'
            },
            'shipments': shipments_list
        }

        logger.info("✅ Estrazione completata con successo")

        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
            },
            'body': json.dumps(result_data, indent=2, ensure_ascii=False)
        }

    except Exception as e:
        logger.error(f"❌ Errore durante l'estrazione: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
            },
            'body': json.dumps({
                'error': str(e),
                'message': 'Errore durante l\'estrazione delle spedizioni GLS'
            })
        }


# === TEST LOCALE ===
if __name__ == "__main__":
    import time
    
    # Per test locale, importa config se disponibile
    if not SHOPIFY_ACCESS_TOKEN or not SHOPIFY_GRAPHQL_URL:
        try:
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
            from config.settings import SHOPIFY_GRAPHQL_URL as SHOPIFY_URL_CONFIG, SHOPIFY_ACCESS_TOKEN as SHOPIFY_TOKEN_CONFIG
            SHOPIFY_ACCESS_TOKEN = SHOPIFY_TOKEN_CONFIG
            SHOPIFY_GRAPHQL_URL = SHOPIFY_URL_CONFIG
        except ImportError:
            pass
    
    print("🧪 TEST LOCALE Lambda Parcel Shop")
    print("=" * 60)
    
    # Carica credenziali da file .env se esiste, altrimenti usa variabili ambiente
    try:
        from dotenv import load_dotenv
        load_dotenv()
        print("✅ File .env caricato")
    except ImportError:
        print("⚠️ python-dotenv non installato, uso variabili ambiente")
    
    # Simula evento Lambda
    test_event = {
        'days_back': 15  # Puoi modificare questo valore
    }
    
    print(f"📅 Test con days_back={test_event['days_back']}")
    print("=" * 60)
    
    start = time.time()
    
    # Esegui handler
    result = lambda_handler(test_event, None)
    
    elapsed = time.time() - start
    
    print("\n" + "=" * 60)
    print(f"⏱️  TEMPO TOTALE: {elapsed:.2f}s")
    print("=" * 60)
    
    # Mostra risultato
    if result['statusCode'] == 200:
        data = json.loads(result['body'])
        print(f"\n✅ SUCCESS!")
        print(f"📦 Totale spedizioni: {data['metadata']['total_shipments']}")
        print(f"📅 Periodo: {data['metadata']['period']}")
        print(f"🏪 Filtro: {data['metadata']['status_filter']}")
        
        # Salva risultato per ispezione
        output_file = Path('/tmp/parcel_shop_test_result.json')
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Risultato completo salvato in: {output_file}")
        
        # Mostra prime 3 spedizioni come esempio
        if data['shipments']:
            print(f"\n📋 Prime 3 spedizioni:")
            for i, ship in enumerate(data['shipments'][:3], 1):
                print(f"\n  {i}. Expedición: {ship.get('expedicion')}")
                print(f"     Referencia: {ship.get('referencia')}")
                print(f"     Destinatario: {ship.get('destinatario')}")
                print(f"     Estado: {ship.get('estado')}")
                print(f"     Fecha: {ship.get('fecha')}")
    else:
        print(f"\n❌ ERROR: {result['statusCode']}")
        print(json.dumps(json.loads(result['body']), indent=2))