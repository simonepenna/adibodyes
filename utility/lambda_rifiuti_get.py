"""
Lambda per recupero rientri (devoluciones) da GLS Extranet
Arricchisce con info Shopify (stato pagamento, tag RIFIUTO) senza modificare nulla
"""

import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import os
import time

# CONFIGURAZIONE - Variabili d'ambiente per Lambda
SHOPIFY_ACCESS_TOKEN = os.environ.get('SHOPIFY_ACCESS_TOKEN')
SHOP_NAME = os.environ.get("SHOPIFY_SHOP_NAME", "db806d-07")
SHOPIFY_API_VERSION = "2024-04"
SHOPIFY_GRAPHQL_URL = f"https://{SHOP_NAME}.myshopify.com/admin/api/{SHOPIFY_API_VERSION}/graphql.json"

# Credenziali GLS (da variabili ambiente)
GLS_USERNAME = os.environ.get('GLS_USERNAME')
GLS_PASSWORD = os.environ.get('GLS_PASSWORD')


class GLSExtranetClient:
    def __init__(self):
        self.session = requests.Session()
        self.base_url = "https://extranet.gls-spain.es"
        self.login_url = f"{self.base_url}/extranet/login.aspx?ReturnUrl=~/default.aspx"
        self.search_url = f"{self.base_url}/Extranet/MiraEnvios/Miraenvios.aspx"
        
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'es,en-US;q=0.9,en;q=0.8',
        })
    
    def login(self, username, password):
        """Effettua login a GLS Extranet"""
        print(f"🔐 Login GLS con utente: {username}")
        
        response = self.session.get(self.login_url)
        if response.status_code != 200:
            raise Exception(f"Errore caricamento pagina login: {response.status_code}")
        
        soup = BeautifulSoup(response.content, 'lxml')
        
        viewstate = {}
        for field in ['__VIEWSTATE', '__VIEWSTATEGENERATOR', '__EVENTVALIDATION']:
            input_field = soup.find('input', {'name': field})
            if input_field:
                viewstate[field] = input_field.get('value', '')
        
        login_data = {
            '__VIEWSTATE': viewstate.get('__VIEWSTATE', ''),
            '__VIEWSTATEGENERATOR': viewstate.get('__VIEWSTATEGENERATOR', ''),
            '__EVENTVALIDATION': viewstate.get('__EVENTVALIDATION', ''),
            'usuario': username,
            'pass': password,
            'Button1.x': '43',
            'Button1.y': '8'
        }
        
        self.session.headers.update({
            'Referer': self.login_url,
            'Origin': self.base_url,
            'Content-Type': 'application/x-www-form-urlencoded'
        })
        
        response = self.session.post(self.login_url, data=login_data, allow_redirects=True)
        
        if response.status_code == 200 and 'Login.aspx' not in response.url:
            print("✅ Login riuscito")
            return True
        
        raise Exception("Login fallito - credenziali errate o sessione scaduta")
    
    def search_shipments(self, date_from, date_to):
        """Cerca spedizioni nel range date"""
        response = self.session.get(self.search_url)
        if response.status_code != 200:
            raise Exception(f"Errore caricamento pagina ricerca: {response.status_code}")
        
        soup = BeautifulSoup(response.content, 'lxml')
        
        viewstate = {}
        for field in ['__VIEWSTATE', '__VIEWSTATEGENERATOR', '__EVENTVALIDATION']:
            input_field = soup.find('input', {'name': field})
            if input_field:
                viewstate[field] = input_field.get('value', '')
        
        form_data = {
            '__EVENTTARGET': '',
            '__EVENTARGUMENT': '',
            '__LASTFOCUS': '',
            '__VIEWSTATE': viewstate.get('__VIEWSTATE', ''),
            '__VIEWSTATEGENERATOR': viewstate.get('__VIEWSTATEGENERATOR', ''),
            '__EVENTVALIDATION': viewstate.get('__EVENTVALIDATION', ''),
            'fechadesde': date_from,
            'fechahasta': date_to,
            'cliente': '586-4073',  # Codice cliente fisso
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
        
        print(f"🔍 Ricerca spedizioni dal {date_from} al {date_to}...")
        response = self.session.post(
            self.search_url,
            data=form_data,
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )
        
        if response.status_code != 200:
            raise Exception(f"Errore ricerca: {response.status_code}")
        
        return response.text
    
    def parse_shipments(self, html_content):
        """Estrae spedizioni dalla risposta HTML"""
        soup = BeautifulSoup(html_content, 'lxml')
        envios_div = soup.find('div', id='envios')
        
        if not envios_div:
            print("⚠️ Div 'envios' non trovato")
            return []
        
        tables = envios_div.find_all('table', class_=['tb', 'atb'])
        print(f"✅ Trovate {len(tables)} spedizioni")
        
        shipments = []
        
        for table in tables:
            try:
                rows = table.find_all('tr')
                if len(rows) < 5:
                    continue
                
                shipment = {}
                
                row1_ths = rows[0].find_all(['th', 'td'])
                if len(row1_ths) >= 2:
                    shipment['expedicion'] = row1_ths[0].get_text(strip=True)
                    shipment['referencia'] = row1_ths[1].get_text(strip=True)
                if len(row1_ths) >= 4:
                    shipment['estado'] = row1_ths[2].get_text(strip=True)
                
                row2_tds = rows[1].find_all('td')
                if len(row2_tds) >= 6:
                    shipment['fecha'] = row2_tds[0].get_text(strip=True)
                    shipment['servicio'] = row2_tds[1].get_text(strip=True)
                
                if len(rows) > 2:
                    row3_tds = rows[2].find_all('td')
                    if len(row3_tds) >= 1:
                        shipment['destinatario'] = row3_tds[0].get_text(strip=True)
                
                if len(rows) > 3:
                    row4_tds = rows[3].find_all('td')
                    if len(row4_tds) >= 2:
                        shipment['localidad'] = row4_tds[1].get_text(strip=True)
                
                shipments.append(shipment)
            
            except Exception as e:
                print(f"⚠️ Errore parsing spedizione: {e}")
                continue
        
        return shipments


def fetch_shopify_orders_by_names(order_names):
    """
    Recupera ordini Shopify specifici per nome usando GraphQL con paginazione
    
    Args:
        order_names: Lista di nomi ordini (es. ['#ES7778', '#ES7779'])
        
    Returns:
        Dict con order_name come chiave e info ordine come valore
    """
    if not order_names:
        return {}
    
    headers = {
        'X-Shopify-Access-Token': SHOPIFY_ACCESS_TOKEN,
        'Content-Type': 'application/json'
    }
    
    # Dividi gli order_names in batch da 250 (limite Shopify)
    batch_size = 250
    all_orders_dict = {}
    
    for i in range(0, len(order_names), batch_size):
        batch_names = order_names[i:i + batch_size]
        
        # Query per ordini specifici nel batch corrente
        names_query = ' OR '.join([f'name:{name}' for name in batch_names])
        query = f"""
        {{
          orders(first: 250, query: "{names_query}") {{
            edges {{
              node {{
                id
                name
                tags
                displayFinancialStatus
              }}
            }}
          }}
        }}
        """
        
        try:
            response = requests.post(SHOPIFY_GRAPHQL_URL, headers=headers, json={"query": query})
            data = response.json()
            
            if 'errors' in data:
                print(f"⚠️ Errore Shopify batch {i//batch_size + 1}: {data['errors']}")
                continue
            
            edges = data.get('data', {}).get('orders', {}).get('edges', [])
            
            for edge in edges:
                order = edge['node']
                order_name = order.get('name', '')
                all_orders_dict[order_name] = {
                    'id': order.get('id', ''),
                    'financial_status': order.get('displayFinancialStatus', ''),
                    'tags': order.get('tags', [])
                }
            
            print(f"✅ Batch {i//batch_size + 1}: recuperati {len(edges)} ordini")
            
        except Exception as e:
            print(f"⚠️ Errore recupero batch {i//batch_size + 1}: {e}")
            continue
    
    print(f"✅ Recuperati {len(all_orders_dict)} ordini totali da Shopify ({len(order_names)} richiesti)")
    return all_orders_dict


def enrich_with_shopify(devoluciones):
    """Arricchisce devoluciones con info Shopify (solo ordini corrispondenti)"""
    if not devoluciones:
        return devoluciones
    
    # Raccogli tutte le referencias uniche
    referencias = [d.get('referencia', '') for d in devoluciones if d.get('referencia', '')]
    order_names = [f"#ES{ref}" for ref in referencias if ref]
    
    if not order_names:
        print("⚠️ Nessuna referencia valida trovata")
        return devoluciones
    
    print(f"🔍 Query Shopify: {len(order_names)} ordini specifici")
    
    # Chiamata Shopify solo per ordini corrispondenti
    orders_dict = fetch_shopify_orders_by_names(order_names)
    
    print(f"✅ Recuperati {len(orders_dict)}/{len(order_names)} ordini da Shopify")
    
    # Match in memoria per referencia
    match_count = 0
    
    for devolucion in devoluciones:
        referencia = devolucion.get('referencia', '')
        
        # La referencia da GLS è "7161" ma su Shopify è "#ES7161"
        order_name = f"#ES{referencia}" if referencia else None
        
        if order_name and order_name in orders_dict:
            match_count += 1
            order_info = orders_dict[order_name]
            devolucion['stato_pagamento'] = order_info['financial_status']
            
            # Tags da Shopify arriva come lista
            tags_raw = order_info['tags'] or []
            tags_list = [tag.strip().upper() for tag in tags_raw if tag and tag.strip()]
            devolucion['ha_tag_rifiuto'] = 'RIFIUTO' in tags_list
            devolucion['order_id'] = order_info['id']
        else:
            devolucion['stato_pagamento'] = None
            devolucion['ha_tag_rifiuto'] = False
            devolucion['order_id'] = None
    
    print(f"🔗 Matched {match_count}/{len(devoluciones)} devoluciones con Shopify")
    
    return devoluciones


def lambda_handler(event, context):
    """Handler Lambda"""
    try:
        start_total = time.time()
        print("🚀 Inizio recupero rientri GLS...")
        
        # Parametro query string: days_back
        params = event.get('queryStringParameters') or {}
        days_back = int(params.get('days_back', 4))  # Default 4 giorni per rientrare in 29s
        
        print(f"📅 Giorni indietro: {days_back}")
        
        # Range date
        date_to = datetime.now()
        date_from = date_to - timedelta(days=days_back)
        
        date_from_str = date_from.strftime("%d/%m/%Y")
        date_to_str = date_to.strftime("%d/%m/%Y")
        
        # Login e ricerca GLS
        start_login = time.time()
        client = GLSExtranetClient()
        client.login(GLS_USERNAME, GLS_PASSWORD)
        print(f"⏱️  Login GLS: {time.time() - start_login:.2f}s")
        
        start_search = time.time()
        html = client.search_shipments(date_from_str, date_to_str)
        print(f"⏱️  Ricerca GLS: {time.time() - start_search:.2f}s")
        
        start_parse = time.time()
        all_shipments = client.parse_shipments(html)
        print(f"⏱️  Parsing HTML: {time.time() - start_parse:.2f}s")
        print(f"✅ Trovate {len(all_shipments)} spedizioni totali")
        
        # Filtra solo DEVOLUCIONES per AdiBody ES
        start_filter = time.time()
        devoluciones = [
            s for s in all_shipments
            if (s.get('servicio', '').upper() == 'DEVOLUCION' and 
                'ADIBODY ES' in s.get('destinatario', '').upper())
        ]
        print(f"⏱️  Filtro devoluciones: {time.time() - start_filter:.2f}s")
        print(f"📦 Trovate {len(devoluciones)} devoluciones")
        
        # Arricchisci con Shopify (senza modificare tag)
        if devoluciones:
            start_shopify = time.time()
            devoluciones = enrich_with_shopify(devoluciones)
            print(f"⏱️  Arricchimento Shopify: {time.time() - start_shopify:.2f}s")
        
        # Statistiche
        totale = len(devoluciones)
        in_transito = len([d for d in devoluciones if d.get('estado') != 'ENTREGADO'])
        consegnati = len([d for d in devoluciones if d.get('estado') == 'ENTREGADO'])
        da_taggare = len([
            d for d in devoluciones
            if (d.get('estado') == 'ENTREGADO' and 
                not d.get('ha_tag_rifiuto') and 
                d.get('stato_pagamento') == 'PENDING')
        ])
        gia_taggati = len([d for d in devoluciones if d.get('ha_tag_rifiuto')])
        
        # Lista ordini da taggare
        ordini_da_taggare = [
            {
                'order_id': d.get('order_id'),
                'referenza': d.get('referencia'),
                'destinatario': d.get('destinatario'),
                'fecha': d.get('fecha'),
                'stato_pagamento': d.get('stato_pagamento')
            }
            for d in devoluciones
            if (d.get('estado') == 'ENTREGADO' and 
                not d.get('ha_tag_rifiuto') and 
                d.get('stato_pagamento') == 'PENDING' and
                d.get('order_id'))
        ]
        
        response_data = {
            'summary': {
                'totale': totale,
                'in_transito': in_transito,
                'consegnati': consegnati,
                'da_taggare': da_taggare,
                'gia_taggati': gia_taggati
            },
            'rifiuti': devoluciones,
            'ordini_da_taggare': ordini_da_taggare
        }
        
        total_time = time.time() - start_total
        print(f"\n⏱️  TEMPO TOTALE: {total_time:.2f}s")
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(response_data)
        }
        
    except Exception as e:
        print(f"❌ Errore: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'error': str(e)})
        }
