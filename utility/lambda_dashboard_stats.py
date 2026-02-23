"""
Lambda function per ottenere statistiche aggregate degli ordini Shopify.
Restituisce: totali ordini, resi, cambi, rifiuti, fulfillment e payment status.

Self-contained: include tutto il codice necessario per funzionare autonomamente.
"""
import os
import json
import time
import random
import requests
from datetime import datetime, timedelta
from typing import Dict, Any, List

# ============================================================================
# CONFIGURAZIONE SHOPIFY
# ============================================================================
SHOPIFY_ACCESS_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN")
SHOPIFY_SHOP_DOMAIN = os.getenv("SHOPIFY_SHOP_DOMAIN", "db806d-07.myshopify.com")
SHOPIFY_API_VERSION = os.getenv("SHOPIFY_API_VERSION", "2024-01")
SHOPIFY_GRAPHQL_URL = f"https://{SHOPIFY_SHOP_DOMAIN}/admin/api/{SHOPIFY_API_VERSION}/graphql.json"
START_DATE_ORDERS = os.getenv("START_DATE_ORDERS", "2025-02-07")
SHOPIFY_SKIP_SSL_VERIFY = os.getenv("SHOPIFY_SKIP_SSL_VERIFY", "0") == "1"

HEADERS = {
    'X-Shopify-Access-Token': SHOPIFY_ACCESS_TOKEN,
    'Content-Type': 'application/json'
}


# ============================================================================
# FETCH ORDERS DA SHOPIFY
# ============================================================================
def fetch_all_orders(start_date: str | None = None, end_date: str | None = None, 
                     max_retries: int = 6, backoff_base: float = 1.5) -> List[Dict]:
    """
    Scarica tutti gli ordini da start_date (YYYY-MM-DD) (inclusa) e opzionale end_date (inclusa).
    Usa paginazione 250. Gestisce rate limit (THROTTLED) con backoff esponenziale.
    """
    all_orders = []
    has_next_page = True
    after_cursor = None
    start = start_date or START_DATE_ORDERS

    # Costruzione filtro query
    filter_parts = [f"created_at:>={start}"]
    if end_date:
        filter_parts.append(f"created_at:<={end_date}")
    query_filter = " ".join(filter_parts)

    while has_next_page:
        cursor_part = f', after: "{after_cursor}"' if after_cursor else ''
        query = f"""
        {{
          orders(first: 250{cursor_part}, sortKey: CREATED_AT, reverse: false, query: \"{query_filter}\") {{
            pageInfo {{ hasNextPage }}
            edges {{
              cursor
              node {{
                createdAt
                cancelledAt
                tags
                currentTotalPriceSet {{ shopMoney {{ amount }} }}
                displayFulfillmentStatus
                displayFinancialStatus
                fullyPaid
                unpaid
                refunds {{ id }}
              }}
            }}
          }}
        }}
        """
        attempt = 0
        while True:
            resp = requests.post(SHOPIFY_GRAPHQL_URL, headers=HEADERS, json={"query": query}, 
                               verify=not SHOPIFY_SKIP_SSL_VERIFY)
            data = resp.json()
            
            if 'errors' in data:
                throttled = False
                for err in data['errors']:
                    code = err.get('extensions', {}).get('code')
                    if code == 'THROTTLED':
                        throttled = True
                        break
                
                if throttled and attempt < max_retries:
                    delay = (backoff_base ** attempt) + random.uniform(0, 0.5)
                    print(f"⚠️ Rate limit Shopify (THROTTLED). Retry {attempt+1}/{max_retries} tra {delay:.2f}s...")
                    time.sleep(delay)
                    attempt += 1
                    continue
                
                if throttled:
                    print("❌ Max retry raggiunti su THROTTLED. Restituisco ordini parziali.")
                    has_next_page = False
                    break
                
                raise RuntimeError(f"Errore Shopify: {data['errors']}")
            
            batch = data['data']['orders']
            edges = batch['edges']
            all_orders.extend(edges)
            has_next_page = batch['pageInfo']['hasNextPage']
            
            if has_next_page:
                after_cursor = edges[-1]['cursor']
            break
    
    return all_orders



# ============================================================================
# LAMBDA HANDLER
# ============================================================================
def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handler principale della Lambda.
    
    Query params opzionali:
    - start_date: YYYY-MM-DD (default: ultimi 30 giorni)
    - end_date: YYYY-MM-DD (default: oggi)
    """
    try:
        # Estrai parametri dalla query string
        params = event.get('queryStringParameters', {}) or {}
        
        # Date di default: ultimi 30 giorni
        end_date = params.get('end_date')
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        start_date = params.get('start_date')
        if not start_date:
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        
        print(f"📊 Recupero statistiche ordini dal {start_date} al {end_date}")
        
        # Fetch ordini da Shopify
        orders = fetch_all_orders(start_date=start_date, end_date=end_date)
        
        # Calcola statistiche
        stats = calculate_order_stats(orders, start_date, end_date)
        
        # Aggiungi metadati
        stats['metadata'] = {
            'start_date': start_date,
            'end_date': end_date,
            'generated_at': datetime.now().isoformat(),
            'total_orders_fetched': len(orders)
        }
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Methods': 'GET,OPTIONS'
            },
            'body': json.dumps(stats, ensure_ascii=False, indent=2)
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
            'body': json.dumps({
                'error': str(e),
                'type': type(e).__name__
            })
        }


def calculate_order_stats(orders: list, start_date: str, end_date: str) -> Dict[str, Any]:
    """
    Calcola statistiche aggregate dagli ordini.
    
    Args:
        orders: Lista ordini da Shopify
        start_date: Data inizio periodo (YYYY-MM-DD)
        end_date: Data fine periodo (YYYY-MM-DD)
    
    Returns:
        Dict con statistiche complete
    """
    stats = {
        'total_orders': 0,
        'orders_by_tag': {
            'RESO': 0,
            'CAMBIO': 0,
            'RIFIUTO': 0,
            'other': 0
        },
        'fulfillment_status': {
            'FULFILLED': 0,
            'UNFULFILLED': 0,
            'PARTIALLY_FULFILLED': 0,
            'SCHEDULED': 0,
            'ON_HOLD': 0
        },
        'financial_status': {
            'PAID': 0,
            'PARTIALLY_PAID': 0,
            'PENDING': 0,
            'REFUNDED': 0,
            'VOIDED': 0,
            'AUTHORIZED': 0,
            'PARTIALLY_REFUNDED': 0
        },
        'payment_status': {
            'fully_paid': 0,
            'unpaid': 0,
            'partially_paid': 0
        },
        'cancelled_orders': 0,
        'orders_with_refunds': 0,
        'total_revenue': 0.0,
        'currency': 'EUR'
    }
    
    # Dizionario per contare ordini per data
    orders_by_date = {}
    
    for edge in orders:
        order = edge.get('node', {})

        # Escludi ordini cancellati da tutti i conteggi
        if order.get('cancelledAt'):
            stats['cancelled_orders'] += 1
            continue

        # Escludi ordini di test (tag TEST)
        order_tags = order.get('tags', [])
        if isinstance(order_tags, str):
            order_tags = [t.strip() for t in order_tags.split(',')]
        if any(t.upper() == 'TEST' for t in order_tags):
            continue

        stats['total_orders'] += 1
        
        # Estrai data creazione ordine
        created_at = order.get('createdAt', '')
        if created_at:
            order_date = created_at.split('T')[0]  # Prendi solo YYYY-MM-DD
            orders_by_date[order_date] = orders_by_date.get(order_date, 0) + 1
        
        # Analizza tags
        tags = order.get('tags', [])
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(',')]
        
        tag_found = False
        for tag in tags:
            tag_upper = tag.upper()
            if 'RESO' in tag_upper:
                stats['orders_by_tag']['RESO'] += 1
                tag_found = True
                break
            elif 'CAMBIO' in tag_upper:
                stats['orders_by_tag']['CAMBIO'] += 1
                tag_found = True
                break
            elif 'RIFIUT' in tag_upper:  # Copre RIFIUTO, RIFIUTI, etc.
                stats['orders_by_tag']['RIFIUTO'] += 1
                tag_found = True
                break
        
        if not tag_found:
            stats['orders_by_tag']['other'] += 1
        
        # Fulfillment status
        fulfillment = order.get('displayFulfillmentStatus', 'UNFULFILLED')
        if fulfillment in stats['fulfillment_status']:
            stats['fulfillment_status'][fulfillment] += 1
        
        # Financial status
        financial = order.get('displayFinancialStatus', 'PENDING')
        if financial in stats['financial_status']:
            stats['financial_status'][financial] += 1
        
        # Payment status (boolean flags)
        if order.get('fullyPaid'):
            stats['payment_status']['fully_paid'] += 1
        elif order.get('unpaid'):
            stats['payment_status']['unpaid'] += 1
        else:
            stats['payment_status']['partially_paid'] += 1
        
        # Refunds
        refunds = order.get('refunds', [])
        if refunds and len(refunds) > 0:
            stats['orders_with_refunds'] += 1
        
        # Revenue
        price_set = order.get('currentTotalPriceSet', {})
        shop_money = price_set.get('shopMoney', {})
        amount_str = shop_money.get('amount', '0')
        try:
            amount = float(amount_str)
            stats['total_revenue'] += amount
            
            # Prendi currency dal primo ordine
            if stats['currency'] == 'EUR':
                currency = shop_money.get('currencyCode', 'EUR')
                stats['currency'] = currency
        except (ValueError, TypeError):
            pass
    
    # Calcola percentuali
    total = stats['total_orders']
    fulfilled = stats['fulfillment_status'].get('FULFILLED', 0)
    
    if total > 0:
        stats['percentages'] = {
            'reso': round((stats['orders_by_tag']['RESO'] / fulfilled) * 100, 2) if fulfilled > 0 else 0,
            'cambio': round((stats['orders_by_tag']['CAMBIO'] / fulfilled) * 100, 2) if fulfilled > 0 else 0,
            'rifiuto': round((stats['orders_by_tag']['RIFIUTO'] / fulfilled) * 100, 2) if fulfilled > 0 else 0,
            'fulfilled': round((fulfilled / total) * 100, 2),
            'fully_paid': round((stats['payment_status']['fully_paid'] / total) * 100, 2),
            'cancelled': round((stats['cancelled_orders'] / total) * 100, 2),
            'with_refunds': round((stats['orders_with_refunds'] / total) * 100, 2)
        }
    else:
        stats['percentages'] = {
            'reso': 0,
            'cambio': 0,
            'rifiuto': 0,
            'fulfilled': 0,
            'fully_paid': 0,
            'cancelled': 0,
            'with_refunds': 0
        }
    
    # Calcola ordini consegnati senza problemi
    consegnati_senza_problemi = fulfilled - (stats['orders_by_tag']['RESO'] + stats['orders_by_tag']['CAMBIO'] + stats['orders_by_tag']['RIFIUTO'])
    stats['consegnati_senza_problemi'] = max(0, consegnati_senza_problemi)
    
    # Arrotonda revenue
    stats['total_revenue'] = round(stats['total_revenue'], 2)
    
    # Genera timeline ordini
    stats['orders_timeline'] = generate_timeline(orders_by_date, start_date, end_date)
    
    return stats


def generate_timeline(orders_by_date: Dict[str, int], start_date: str, end_date: str) -> List[Dict[str, Any]]:
    """
    Genera una timeline completa con tutte le date nel range, anche quelle senza ordini.
    
    Args:
        orders_by_date: Dizionario {data: count}
        start_date: Data inizio (YYYY-MM-DD)
        end_date: Data fine (YYYY-MM-DD)
    
    Returns:
        Lista di dict [{date: "YYYY-MM-DD", count: int}]
    """
    timeline = []
    current = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')
    
    while current <= end:
        date_str = current.strftime('%Y-%m-%d')
        count = orders_by_date.get(date_str, 0)
        timeline.append({
            'date': date_str,
            'count': count
        })
        current += timedelta(days=1)
    
    return timeline