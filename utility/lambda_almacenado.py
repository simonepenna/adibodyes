"""
AWS Lambda function per estrarre le spedizioni GLS in stato ALMACENADO
che non hanno "NO ACEPTA EXPEDICION" nel POD
"""
import requests
import time
import boto3
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
import numpy as np
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.adapters import HTTPAdapter

# Configurazione logging per CloudWatch
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Configurazione Shopify da environment variables
SHOPIFY_ACCESS_TOKEN = os.environ.get("SHOPIFY_ACCESS_TOKEN")
SHOPIFY_GRAPHQL_URL = os.environ.get("SHOPIFY_GRAPHQL_URL")

# S3 per tracciare i clienti già contattati
CONTACTED_S3_BUCKET = os.environ.get("CONTACTED_S3_BUCKET", "adibody-almacenado-state-bucket")
CONTACTED_S3_KEY = "almacenado/contacted.json"

# Client S3 a livello di modulo (riusato tra invocazioni Lambda - warm start)
_s3_client = None
def get_s3_client():
    global _s3_client
    if _s3_client is None:
        _s3_client = boto3.client('s3')
    return _s3_client


def load_contacted_from_s3() -> dict:
    """Carica da S3 il dizionario {expedicion: data_contatto}. Ritorna {} se non esiste."""
    try:
        s3 = get_s3_client()
        obj = s3.get_object(Bucket=CONTACTED_S3_BUCKET, Key=CONTACTED_S3_KEY)
        data = json.loads(obj['Body'].read())
        logger.info(f"📋 Caricati {len(data)} expediciones già contattati da S3")
        return data
    except Exception as e:
        logger.info(f"📋 Nessuno storico contatti trovato su S3 ({e}), parto da zero")
        return {}


class GLSExtranetClient:
    def __init__(self, cookies=None):
        """
        Inizializza il client con i cookies della sessione o vuoto per login

        Args:
            cookies: Dict con i cookies dalla tua sessione browser (opzionale)
        """
        self.session = requests.Session()
        # Pool grande per supportare le chiamate parallele (25+ thread simultanei)
        adapter = HTTPAdapter(pool_connections=50, pool_maxsize=50)
        self.session.mount('https://', adapter)
        self.session.mount('http://', adapter)
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

        soup = BeautifulSoup(response.content, 'lxml')

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
        
        soup = BeautifulSoup(response.content, 'lxml')
        
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
        comment_match = re.search(r'<!--.*?<table[^>]*id=["\']gr["\'].*?</table>.*?-->', html_content, re.DOTALL)
        
        if not comment_match:
            logger.warning("⚠️ Tabella nascosta id='gr' non trovata nei commenti")
            return pd.DataFrame()
        
        # Estrai solo il contenuto della tabella dal commento
        comment_html = comment_match.group(0).replace('<!--', '').replace('-->', '')
        
        # Parsa SOLO il commento (non tutto l'HTML)
        soup = BeautifulSoup(comment_html, 'lxml')
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
        
        # Trova indice colonna 'Pod' per controllare "NO ACEPTA EXPEDICION"
        try:
            pod_idx = columns.index('Pod')
        except ValueError:
            logger.warning("⚠️ Colonna 'Pod' non trovata")
            return pd.DataFrame()
        
        # Trova indici per tutte le colonne necessarie (micro-ottimizzazione)
        column_indices = {}
        required_columns = [
            'Expedicion', 'Referencia', 'estado', 'Pod', 'Fecha', 'Servicio', 'Horario',
            'bultos', 'Kgs', 'Reembolso', 'Destinatario', 'dac', 'retorno', 'Direccion',
            'Localidad', 'cp_dst', 'cp_org', 'nombre_org', 'localidad_org', 'fechaActualizacion'
        ]
        
        for col in required_columns:
            try:
                column_indices[col] = columns.index(col)
            except ValueError:
                logger.warning(f"⚠️ Colonna '{col}' non trovata")
                column_indices[col] = None
        
        logger.info(f"📋 {len(columns)} colonne - cp_dst: {columns.index('cp_dst') if 'cp_dst' in columns else 'N/A'}")
        
        # OTTIMIZZAZIONE 2: Filtra PRIMA di creare dizionari
        shipments = []
        
        for row in rows[1:]:
            cells = row.find_all('td')
            if len(cells) != len(columns):
                continue
            
            # Controlla subito lo stato (colonna estado_idx)
            estado = cells[estado_idx].get_text(strip=True).upper()
            if estado != 'ALMACENADO':
                continue  # Skip se non è ALMACENADO
            
            # Controlla POD (colonna pod_idx)
            pod = cells[pod_idx].get_text(strip=True).upper()
            if 'NO ACEPTA' in pod:
                continue  # Skip se contiene "NO ACEPTA" (qualsiasi variante)
            
            # MICRO-OTTIMIZZAZIONE: Estrai solo le colonne necessarie direttamente
            def get_cell_text(col_name):
                idx = column_indices[col_name]
                return cells[idx].get_text(strip=True) if idx is not None else ''
            
            # NON chiamare Shopify qui - salva solo referencia per batch
            referencia = get_cell_text('Referencia')
            
            # Mappa campi (senza phone per ora)
            shipments.append({
                'expedicion': get_cell_text('Expedicion'),
                'referencia': referencia,
                'estado': get_cell_text('estado'),
                'pod': get_cell_text('Pod'),
                'fecha': get_cell_text('Fecha'),
                'servicio': get_cell_text('Servicio'),
                'horario': get_cell_text('Horario'),
                'bultos': get_cell_text('bultos'),
                'kgs': get_cell_text('Kgs'),
                'reembolso': get_cell_text('Reembolso'),
                'destinatario': get_cell_text('Destinatario'),
                'phone': None,  # Placeholder - sarà riempito dopo con batch
                'dac': get_cell_text('dac'),
                'retorno': get_cell_text('retorno'),
                'direccion': get_cell_text('Direccion'),
                'localidad': get_cell_text('Localidad'),
                'cp_dst': get_cell_text('cp_dst'),
                'cp_org': get_cell_text('cp_org'),
                'nombre_org': get_cell_text('nombre_org'),
                'localidad_org': get_cell_text('localidad_org'),
                'fecha_actualizacion': get_cell_text('fechaActualizacion'),
                'indirizzo_agenzia': None,   # Placeholder - riempito dopo
                'telefono_agenzia': None,    # Placeholder - riempito dopo
                'orari_agenzia': None,       # Placeholder - riempito dopo
            })

        logger.info(f"✅ Trovate {len(shipments)} spedizioni ALMACENADO senza 'NO ACEPTA' nel POD")
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

    def get_codplaza_org_from_soap(self, expedicion, uid_cliente):
        """
        Chiama il WS SOAP GLS (GetExpCli) per ottenere il codplaza_org reale
        dell'agenzia di origine associata alla spedizione.

        Args:
            expedicion: Numero expedicion (es: "1250846273")
            uid_cliente: UID cliente GLS

        Returns:
            str: codplaza_org oppure None se non trovato
        """
        url = "https://ws-customer.gls-spain.es/b2b.asmx?wsdl"
        soap_xml = f'''<?xml version="1.0" encoding="utf-8"?>
<soap12:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">
  <soap12:Body>
    <GetExpCli xmlns="http://www.asmred.com/">
      <codigo>{expedicion}</codigo>
      <uid>{uid_cliente}</uid>
    </GetExpCli>
  </soap12:Body>
</soap12:Envelope>'''
        headers = {
            'Content-Type': 'text/xml; charset=UTF-8',
            'SOAPAction': 'http://www.asmred.com/GetExpCli'
        }
        try:
            resp = requests.post(url, data=soap_xml, headers=headers, verify=False, timeout=15)
            if resp.status_code != 200:
                logger.warning(f"⚠️ SOAP HTTP {resp.status_code} per expedicion {expedicion}")
                return None
            root = ET.fromstring(resp.text)
            elem = root.find('.//codplaza_org')
            if elem is not None and elem.text:
                codplaza = elem.text.strip()
                logger.info(f"✅ codplaza_org SOAP per {expedicion}: {codplaza}")
                return codplaza
            logger.warning(f"⚠️ codplaza_org non trovato nel SOAP per {expedicion}")
            return None
        except Exception as e:
            logger.warning(f"⚠️ Errore SOAP codplaza_org per {expedicion}: {e}")
            return None

    def get_agenzia_destino_details(self, codplaza_org, codexp):
        """
        Ottiene indirizzo, telefono e orari dell'agenzia di destinazione dall'extranet GLS.
        Usa la sessione già autenticata.

        Args:
            codplaza_org: Codice plaza origine della spedizione (ottenuto via SOAP)
            codexp: Numero expedicion della spedizione

        Returns:
            dict con chiavi 'indirizzo_agenzia', 'telefono_agenzia', 'orari_agenzia' oppure {}
        """
        try:
            url = f"{self.base_url}/Extranet/MiraEnvios/expedicion.aspx?codplaza_org={codplaza_org}&codexp={codexp}"
            response = self.session.get(url, verify=False, timeout=15)

            if response.status_code != 200:
                logger.warning(f"⚠️ Extranet agenzia HTTP {response.status_code} per expedicion {codexp}")
                return {}

            html = response.text
            info = {}

            indirizzo_m = re.search(r'<input name="plzDstDireccion"[^>]*value="([^"]*)"', html)
            if indirizzo_m:
                info['indirizzo_agenzia'] = indirizzo_m.group(1).strip()

            telefono_m = re.search(r'<input name="plzDstTelefono"[^>]*value="([^"]*)"', html)
            if telefono_m:
                info['telefono_agenzia'] = telefono_m.group(1).strip()

            orari_m = re.search(r'<input name="plzDstHorario"[^>]*value="([^"]*)"', html)
            if orari_m:
                info['orari_agenzia'] = orari_m.group(1).strip()

            if info:
                logger.info(f"✅ Dettagli agenzia destino per {codexp}: {info}")
            else:
                logger.warning(f"⚠️ Nessun dettaglio agenzia trovato per expedicion {codexp}")

            return info

        except Exception as e:
            logger.warning(f"⚠️ Errore recupero dettagli agenzia per {codexp}: {e}")
            return {}

    def get_phones_from_shopify_batch(self, order_numbers):
        """
        Recupera telefoni per più ordini Shopify in una sola chiamata batch
        
        Args:
            order_numbers: Lista di numeri ordine (es: ["8369", "8370"])
            
        Returns:
            dict: {order_number: phone} per ordini trovati
        """
        if not order_numbers:
            return {}
        
        try:
            # Costruisci query OR per tutti gli ordini
            query_parts = [f"name:#ES{num}" for num in order_numbers]
            query_string = " OR ".join(query_parts)
            
            query = f"""
            {{
              orders(first: {len(order_numbers)}, query: "{query_string}") {{
                edges {{
                  node {{
                    name
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
            
            response = requests.post(SHOPIFY_GRAPHQL_URL, headers=headers, json={"query": query}, timeout=15)
            
            phones = {}
            
            if response.status_code == 200:
                data = response.json()
                edges = data.get('data', {}).get('orders', {}).get('edges', [])
                
                for edge in edges:
                    node = edge['node']
                    order_name = node['name']  # es "#ES8369"
                    order_number = order_name.replace("#ES", "")
                    
                    # Prova in ordine: phone ordine, phone cliente, phone indirizzo spedizione
                    phone = (node.get('phone') or 
                            (node.get('customer', {}).get('phone') if node.get('customer') else None) or
                            (node.get('shippingAddress', {}).get('phone') if node.get('shippingAddress') else None))
                    
                    phones[order_number] = phone
            
            logger.info(f"📞 Batch Shopify: richiesti {len(order_numbers)} ordini, trovati {len(phones)} telefoni")
            return phones
            
        except Exception as e:
            logger.warning(f"⚠️ Errore batch recupero telefoni: {e}")
            return {}


def lambda_handler(event, context):
    """
    Handler principale della Lambda function

    Args:
        event: Evento Lambda (può contenere parametri custom)
        context: Contesto Lambda

    Returns:
        dict: Risposta della funzione
    """
    logger.info("🚀 Avvio estrazione spedizioni GLS in stato ALMACENADO")

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
        show_all = bool(body.get('show_all', False))  # Se True, restituisce tutti (contattati + non)
        logger.info(f"📊 Parametri: days_back={days_back}, show_all={show_all}")

        if not username or not password:
            raise ValueError("GLS_USERNAME e GLS_PASSWORD sono obbligatori nelle environment variables")

        # Date: ultimi N giorni
        today = datetime.now()
        date_from = (today - timedelta(days=days_back)).strftime("%d/%m/%Y")
        date_to = today.strftime("%d/%m/%Y")

        logger.info(f"📅 Periodo: {date_from} - {date_to}")

        # 📋 Carica storico contatti da S3 (in parallelo con il login GLS sotto)
        with ThreadPoolExecutor(max_workers=2) as _ex:
            _future_contacted = _ex.submit(load_contacted_from_s3)

            # Login con credenziali (eseguito in parallelo con il GET S3)
            client = GLSExtranetClient()
            if not client.login(username, password):
                raise Exception("Login GLS fallito")

        already_contacted = _future_contacted.result()

        # Cerca spedizioni
        html = client.search_shipments(date_from, date_to)

        # Parse spedizioni
        t_start = time.time()
        df = client.parse_shipments(html)
        logger.info(f"⏱️ Parsing HTML: {time.time() - t_start:.2f}s")

        if df.empty:
            logger.warning("⚠️ Nessuna spedizione in stato ALMACENADO senza 'NO ACEPTA EXPEDICION' trovata")
            return {
                'statusCode': 200,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type',
                    'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
                },
                'body': json.dumps({
                    'message': 'Nessuna spedizione in stato ALMACENADO senza \'NO ACEPTA EXPEDICION\' trovata',
                    'total_shipments': 0,
                    'period': f"{date_from} - {date_to}"
                })
            }

        # 🔥 OTTIMIZZAZIONE: Batch Shopify + SOAP in parallelo
        gls_uid = os.environ.get("GLS_UID_CLIENTE", "cbfbcd8f-ef6c-4986-9643-0b964e1efa20")
        order_numbers = df['referencia'].dropna().astype(str).tolist()
        first_exp = str(df.iloc[0].get('expedicion', '')).strip() if not df.empty else ''

        t_start = time.time()
        with ThreadPoolExecutor(max_workers=2) as ex:
            future_phones = ex.submit(client.get_phones_from_shopify_batch, order_numbers)
            future_codplaza = ex.submit(client.get_codplaza_org_from_soap, first_exp, gls_uid) if first_exp else None

        phones_map = future_phones.result()
        codplaza_org_comune = future_codplaza.result() if future_codplaza else None
        df['phone'] = df['referencia'].map(phones_map)
        logger.info(f"⏱️ Batch Shopify + SOAP in parallelo: {time.time() - t_start:.2f}s")
        logger.info(f"🏢 codplaza_org comune: {codplaza_org_comune}")

        # 🏢 Recupero dettagli agenzia in parallelo (tutte le extranet insieme)
        def fetch_agenzia(idx_expedicion):
            idx, expedicion = idx_expedicion
            expedicion = str(expedicion).strip()
            if not expedicion or not codplaza_org_comune:
                return idx, {}
            return idx, client.get_agenzia_destino_details(codplaza_org_comune, expedicion)

        t_start = time.time()
        expediciones = [(idx, row.get('expedicion', '')) for idx, row in df.iterrows()]
        with ThreadPoolExecutor(max_workers=min(len(expediciones), 30) or 1) as executor:
            futures = {executor.submit(fetch_agenzia, item): item for item in expediciones}
            for future in as_completed(futures):
                idx, dettagli = future.result()
                df.loc[idx, ['indirizzo_agenzia', 'telefono_agenzia', 'orari_agenzia']] = [
                    dettagli.get('indirizzo_agenzia'),
                    dettagli.get('telefono_agenzia'),
                    dettagli.get('orari_agenzia'),
                ]

        logger.info(f"⏱️ Dettagli agenzie extranet parallelo: {time.time() - t_start:.2f}s")

        logger.info(f"✅ Trovate {len(df)} spedizioni totali")

        # 📋 Marca le spedizioni già contattate
        total_before = len(df)
        df['already_contacted'] = df['expedicion'].astype(str).map(
            lambda x: already_contacted.get(x, {}).get('data') if isinstance(already_contacted.get(x), dict) else already_contacted.get(x, None)
        )
        new_df = df[df['already_contacted'].isna()]
        skipped = total_before - len(new_df)
        logger.info(f"📋 Contatti: {total_before} totali → {len(new_df)} da contattare ({skipped} già contattati)")

        # show_all=True → ritorna tutto il df (con campo already_contacted popolato)
        # show_all=False (default) → ritorna solo quelli non ancora contattati
        output_df = df if show_all else new_df
        shipments_list = output_df.to_dict('records')

        # 🔥 FIX: Gestisci valori NaN/NaT che non sono validi in JSON
        def clean_for_json(obj):
            """Converte valori NaN/NaT in None per JSON valido"""
            if isinstance(obj, dict):
                return {k: clean_for_json(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [clean_for_json(item) for item in obj]
            elif isinstance(obj, float) and (np.isnan(obj) or np.isinf(obj)):
                return None
            elif hasattr(obj, 'isnull') and obj.isnull():  # Per pandas NaT
                return None
            else:
                return obj

        # Applica pulizia a tutti i dati
        shipments_list = clean_for_json(shipments_list)

        # Restituisci direttamente i dati invece di salvare su S3
        result_data = {
            'metadata': {
                'extraction_date': datetime.now().isoformat(),
                'period': f"{date_from} - {date_to}",
                'total_shipments': len(output_df),
                'total_including_contacted': total_before,
                'already_contacted_skipped': skipped,
                'show_all': show_all,
                'status_filter': 'ALMACENADO (senza NO ACEPTA nel POD)'
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
            'body': json.dumps(result_data, ensure_ascii=False)
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
    
    print("🧪 TEST LOCALE Lambda ALMACENADO")
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
        output_file = Path('/tmp/almacenado_test_result.json')
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
                print(f"     POD: {ship.get('pod')}")
                print(f"     Fecha: {ship.get('fecha')}")
    else:
        print(f"\n❌ ERROR: {result['statusCode']}")
        print(json.dumps(json.loads(result['body']), indent=2))