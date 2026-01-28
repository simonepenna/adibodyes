"""
Lambda per controllo evadibilità ordini Shopify
Categorizza ordini in: VERDE (ok), GIALLO (warnings), ROSSO (no stock)
"""

import json
import requests
from datetime import datetime, timedelta
import os
import sys

# Importazioni per Google Sheets
from google.oauth2 import service_account
from googleapiclient.discovery import build

# CONFIGURAZIONE
SHOPIFY_ACCESS_TOKEN = os.environ.get('SHOPIFY_ACCESS_TOKEN')
SHOP_NAME = os.environ.get("SHOPIFY_SHOP_NAME", "db806d-07")
SHOPIFY_API_VERSION = "2024-04"
SHOPIFY_GRAPHQL_URL = f"https://{SHOP_NAME}.myshopify.com/admin/api/{SHOPIFY_API_VERSION}/graphql.json"
GOOGLE_SHEET_ID = "1mOWYahqRDPK0mqGEOPMsC--WWdq7hsoskQyaSWrR7xY"
DAYS_BACK_DEFAULT = 4  # Default giorni di ordini da recuperare

# Mapping taglie per controllo differenza
SIZE_ORDER = {'XXS': 0, 'XS': 1, 'S': 2, 'M': 3, 'L': 4, 'XL': 5, 'XXL': 6, '3XL': 7}

def get_google_sheets_service():
    """Crea servizio Google Sheets API"""
    try:
        credentials_json = os.environ.get('GOOGLE_CREDENTIALS_JSON')
        
        if credentials_json:
            # Da variabile ambiente (per Lambda)
            credentials_info = json.loads(credentials_json)
        else:
            # Da file locale (per test)
            script_dir = os.path.dirname(os.path.abspath(__file__))
            cred_path = os.path.join(script_dir, 'shopify-lambda-integration-ff8f0760340f.json')
            with open(cred_path, 'r') as f:
                credentials_info = json.load(f)
        
        credentials = service_account.Credentials.from_service_account_info(
            credentials_info,
            scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
        )
        
        service = build('sheets', 'v4', credentials=credentials)
        return service
    except Exception as e:
        print(f"Errore Google Sheets: {e}")
        raise

def load_stock_from_sheets():
    """Carica stock da Google Sheets e ritorna dizionario {(MODELO, TALLA): quantità}"""
    service = get_google_sheets_service()
    
    # Leggi il primo foglio (Magazzino)
    result = service.spreadsheets().values().get(
        spreadsheetId=GOOGLE_SHEET_ID,
        range="Magazzino"
    ).execute()
    
    values = result.get('values', [])
    if not values:
        return {}
    
    header_row = values[0]
    data_rows = values[1:]
    
    # Trova indici colonne
    modelo_idx = talla_idx = cantidad_idx = None
    for idx, col in enumerate(header_row):
        col_upper = str(col).upper().strip()
        if col_upper == 'MODELO':
            modelo_idx = idx
        elif col_upper == 'TALLA':
            talla_idx = idx
        elif col_upper in ['CANTIDAD', 'QUANTITÀ', 'QTY']:
            cantidad_idx = idx
    
    if modelo_idx is None or talla_idx is None or cantidad_idx is None:
        raise Exception(f"Colonne non trovate. Header: {header_row}")
    
    # Crea dizionario stock
    stock_dict = {}
    for row in data_rows:
        if len(row) > max(modelo_idx, talla_idx, cantidad_idx):
            modelo = row[modelo_idx].strip() if modelo_idx < len(row) else None
            talla = row[talla_idx].strip() if talla_idx < len(row) else None
            cantidad = row[cantidad_idx] if cantidad_idx < len(row) else 0
            
            if modelo and talla:
                try:
                    cantidad_val = int(float(cantidad)) if cantidad else 0
                    stock_dict[(modelo, talla)] = cantidad_val
                except (ValueError, TypeError):
                    continue
    
    return stock_dict

def get_unfulfilled_orders_shopify(days_back=7):
    """Recupera ordini non evasi da Shopify GraphQL"""
    start_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    
    query = f"""
    {{
      orders(first: 250, query: "fulfillment_status:unfulfilled AND created_at:>={start_date}") {{
        edges {{
          node {{
            id
            name
            createdAt
            tags
            displayFinancialStatus
            note
            customer {{
              firstName
              lastName
              phone
            }}
            shippingAddress {{
              address1
              address2
              city
              zip
              phone
            }}
            totalPriceSet {{
              shopMoney {{
                amount
              }}
            }}
            lineItems(first: 100) {{
              edges {{
                node {{
                  title
                  sku
                  quantity
                }}
              }}
            }}
          }}
        }}
      }}
    }}
    """
    
    headers = {
        "X-Shopify-Access-Token": SHOPIFY_ACCESS_TOKEN,
        "Content-Type": "application/json"
    }
    
    response = requests.post(SHOPIFY_GRAPHQL_URL, json={'query': query}, headers=headers)
    response.raise_for_status()
    
    data = response.json()
    orders = []
    
    for edge in data.get('data', {}).get('orders', {}).get('edges', []):
        node = edge['node']
        
        # Salta ordini REFUNDED e VOIDED
        financial_status = node.get('displayFinancialStatus', '')
        if financial_status in ['REFUNDED', 'VOIDED']:
            continue
        
        # Estrai line items
        line_items = []
        for item_edge in node.get('lineItems', {}).get('edges', []):
            item_node = item_edge['node']
            line_items.append({
                'title': item_node.get('title', ''),
                'sku': item_node.get('sku', ''),
                'quantity': item_node.get('quantity', 0)
            })
        
        orders.append({
            'id': node['id'],
            'name': node['name'],
            'created_at': node['createdAt'],
            'tags': node.get('tags', []),
            'financial_status': financial_status,
            'note': node.get('note', ''),
            'shipping_address': node.get('shippingAddress', {}),
            'customer': node.get('customer', {}),
            'total_price': node.get('totalPriceSet', {}).get('shopMoney', {}).get('amount', '0'),
            'line_items': line_items
        })
    
    return orders

def parse_sku(sku):
    """
    Estrae MODELO e TALLA dallo SKU
    Formati SKU supportati:
    - SLIP.M.BL -> SLIP BL, M
    - PER.XS.BE -> PER BE, XS
    - SLIP_BE_XL -> SLIP BE, XL
    """
    if not sku or sku == 'N/A':
        return None, None
    
    sku = str(sku).strip()
    
    # Formato con punti: SLIP.M.BL
    if '.' in sku:
        parts = sku.split('.')
        if len(parts) >= 3:
            modelo = f"{parts[0]} {parts[2]}"  # Es: "SLIP BL"
            talla = parts[1]  # Es: "M"
            
            # Converti taglie speciali
            if talla == 'XXXL':
                talla = '3XL'
            elif talla == 'XXL':
                talla = '2XL'
            
            return modelo, talla
    
    # Formato con underscore: SLIP_BE_XL
    elif '_' in sku:
        parts = sku.split('_')
        if len(parts) >= 3:
            modelo = f"{parts[0]} {parts[1]}"  # Es: "SLIP BE"
            talla = parts[2]  # Es: "XL"
            return modelo, talla
    
    return None, None

def check_size_difference(sizes):
    """Controlla se ci sono almeno 2 taglie con differenza >= 2 (es. S + L, XS + M)"""
    if len(sizes) < 2:
        return False
    
    # Converti taglie in numeri usando SIZE_ORDER
    size_values = []
    for size in sizes:
        size_upper = size.upper().strip()
        if size_upper in SIZE_ORDER:
            size_values.append(SIZE_ORDER[size_upper])
    
    # Se abbiamo almeno 2 taglie valide, controlla differenza
    if len(size_values) < 2:
        return False
    
    size_values.sort()
    max_diff = size_values[-1] - size_values[0]
    
    return max_diff >= 2

def check_address_issues(address):
    """Verifica problemi con l'indirizzo"""
    if not address:
        return True, "Indirizzo mancante"
    
    # Verifica campi essenziali
    if not address.get('address1'):
        return True, "Via mancante"
    
    if not address.get('city'):
        return True, "Città mancante"
    
    if not address.get('zip'):
        return True, "CAP mancante"
    
    # Indirizzo OK
    return False, ""

def categorize_order(order, stock_dict):
    """
    Categorizza ordine in:
    - GREEN: Evadibile senza problemi
    - YELLOW: Evadibile ma con warnings (note, indirizzo, taglie)
    - RED: Non evadibile (stock insufficiente)
    
    Ritorna: (categoria, dettagli, items_detail)
    """
    warnings = []
    items_detail = []
    can_fulfill = True
    
    # 1. Controlla NOTE
    if order.get('note') and order['note'].strip():
        warnings.append(f"Note: {order['note']}")
    
    # 2. Controlla INDIRIZZO
    has_address_issue, address_msg = check_address_issues(order.get('shipping_address'))
    if has_address_issue:
        warnings.append(f"Indirizzo: {address_msg}")
    
    # 3. Controlla STOCK e raccogli taglie
    sizes_in_order = []
    
    for item in order['line_items']:
        sku = item['sku']
        quantity = item['quantity']
        title = item['title']
        
        # Ignora item senza SKU (es. "Pago Contra Reembolso", spese spedizione)
        if not sku:
            items_detail.append({
                'sku': sku,
                'title': title,
                'quantity': quantity,
                'modelo': 'N/A',
                'talla': 'N/A',
                'available': 'N/A',
                'sufficient': True,  # Non blocca l'ordine
                'status': 'UNKNOWN'
            })
            continue  # Salta al prossimo item senza bloccare l'ordine
        
        modelo, talla = parse_sku(sku)
        
        if not modelo or not talla:
            # SKU presente ma non parsabile - questo è un problema
            items_detail.append({
                'sku': sku,
                'title': title,
                'quantity': quantity,
                'modelo': 'N/A',
                'talla': 'N/A',
                'available': 'N/A',
                'sufficient': False,
                'status': 'UNKNOWN'
            })
            can_fulfill = False
            continue
        
        # Aggiungi taglia alla lista per controllo differenza
        sizes_in_order.append(talla)
        
        # Verifica stock
        stock_key = (modelo, talla)
        available = stock_dict.get(stock_key, 0)
        sufficient = available >= quantity
        
        items_detail.append({
            'sku': sku,
            'title': item['title'],
            'quantity': quantity,
            'modelo': modelo,
            'talla': talla,
            'available': available,
            'sufficient': sufficient,
            'status': 'OK' if sufficient else 'MISSING'
        })
        
        if not sufficient:
            can_fulfill = False
    
    # 4. Controlla TAGLIE STRANE (se almeno 2 items)
    if len(order['line_items']) >= 2:
        if check_size_difference(sizes_in_order):
            warnings.append(f"Taglie strane: {', '.join(set(sizes_in_order))}")
    
    # Determina categoria
    if not can_fulfill:
        category = 'RED'
        category_label = 'Non Evadibile'
    elif warnings:
        category = 'YELLOW'
        category_label = 'Evadibile con Warning'
    else:
        category = 'GREEN'
        category_label = 'Evadibile'
    
    return category, {
        'category': category,
        'category_label': category_label,
        'warnings': warnings,
        'can_fulfill': can_fulfill
    }, items_detail

def lambda_handler(event, context):
    """Handler principale Lambda"""
    try:
        # Leggi days_back dai query parameters, default 4 giorni
        query_params = event.get('queryStringParameters') or {}
        days_back = int(query_params.get('days', DAYS_BACK_DEFAULT))
        
        # 1. Carica stock da Google Sheets
        stock_dict = load_stock_from_sheets()
        
        # 2. Recupera ordini da Shopify
        orders = get_unfulfilled_orders_shopify(days_back)
        
        # 3. Categorizza ordini
        green_orders = []
        yellow_orders = []
        red_orders = []
        
        for order in orders:
            category, details, items = categorize_order(order, stock_dict)
            
            # Estrai nome cliente dal campo customer
            customer = order.get('customer') or {}
            first_name = customer.get('firstName', '') or customer.get('first_name', '')
            last_name = customer.get('lastName', '') or customer.get('last_name', '')
            customer_name = f"{first_name} {last_name}".strip()
            if not customer_name:
                customer_name = "N/A"
            
            order_data = {
                'id': order['id'],
                'name': order['name'],
                'created_at': order['created_at'],
                'financial_status': order['financial_status'],
                'customer_name': customer_name,
                'total_price': order['total_price'],
                'note': order.get('note', ''),
                'tags': order.get('tags', []),
                'items': items,
                'shipping_address': order.get('shipping_address', {}),
                **details
            }
            
            if category == 'GREEN':
                green_orders.append(order_data)
            elif category == 'YELLOW':
                yellow_orders.append(order_data)
            else:
                red_orders.append(order_data)
        
        # 4. Crea risposta
        response_data = {
            'summary': {
                'total': len(orders),
                'green': len(green_orders),
                'yellow': len(yellow_orders),
                'red': len(red_orders)
            },
            'orders': {
                'green': green_orders,
                'yellow': yellow_orders,
                'red': red_orders
            }
        }
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(response_data)
        }
        
    except Exception as e:
        print(f"Errore: {str(e)}")
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

# Test locale
if __name__ == '__main__':
    # Carica config locale
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from config.settings import SHOPIFY_ACCESS_TOKEN as TOKEN
    
    os.environ['SHOPIFY_ACCESS_TOKEN'] = TOKEN
    
    # Carica credenziali Google
    script_dir = os.path.dirname(os.path.abspath(__file__))
    creds_path = os.path.join(script_dir, 'shopify-lambda-integration-ff8f0760340f.json')
    with open(creds_path, 'r') as f:
        os.environ['GOOGLE_CREDENTIALS_JSON'] = f.read()
    
    result = lambda_handler({}, {})
    print(json.dumps(json.loads(result['body']), indent=2))
