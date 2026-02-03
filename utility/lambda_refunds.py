"""
Lambda function per ottenere ordini Shopify con tag RESO e DA RIMBORSARE.
Restituisce ordini da rimborsare con note e informazioni necessarie.
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

HEADERS = {
    'X-Shopify-Access-Token': SHOPIFY_ACCESS_TOKEN,
    'Content-Type': 'application/json'
}

# ============================================================================
# FETCH ORDERS CON TAG SPECIFICI
# ============================================================================
def fetch_orders_with_tags(tags: List[str], max_retries: int = 6, backoff_base: float = 1.5) -> List[Dict]:
    """
    Scarica ordini che hanno TUTTI i tag specificati.
    Cerca in tutti gli ordini senza limitazione di data.
    Usa paginazione 250. Gestisce rate limit con backoff esponenziale.
    """
    all_orders = []
    has_next_page = True
    after_cursor = None

    # Costruzione filtro query - ordini che hanno tutti i tag richiesti
    tag_filters = []
    for tag in tags:
        # Quota i tag che contengono spazi
        if ' ' in tag:
            tag_filters.append(f"tag:'{tag}'")
        else:
            tag_filters.append(f"tag:{tag}")
    query_filter = f"{' AND '.join(tag_filters)}"

    while has_next_page:
        cursor_part = f', after: "{after_cursor}"' if after_cursor else ''
        query = f"""
        {{
          orders(first: 250{cursor_part}, sortKey: CREATED_AT, reverse: true, query: "{query_filter}") {{
            pageInfo {{ hasNextPage }}
            edges {{
              cursor
              node {{
                id
                name
                createdAt
                tags
                note
                customer {{
                  displayName
                  phone
                }}
                shippingAddress {{
                  name
                  address1
                  city
                  province
                  country
                  phone
                }}
                currentTotalPriceSet {{ shopMoney {{ amount currencyCode }} }}
                displayFulfillmentStatus
                displayFinancialStatus
                fullyPaid
                refunds {{
                  id
                  createdAt
                  note
                }}
              }}
            }}
          }}
        }}
        """

        attempt = 0
        while True:
            resp = requests.post(SHOPIFY_GRAPHQL_URL, headers=HEADERS, json={"query": query})
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

            # Successo
            orders_data = data.get('data', {}).get('orders', {})
            edges = orders_data.get('edges', [])

            for edge in edges:
                order = edge['node']
                try:
                    all_orders.append({
                        'id': order.get('id', ''),
                        'name': order.get('name', ''),
                        'created_at': order.get('createdAt', ''),
                        'tags': order.get('tags', []),
                        'note': order.get('note'),
                        'customer': order.get('customer'),
                        'shipping_address': order.get('shippingAddress'),
                        'total_price': order.get('currentTotalPriceSet', {}).get('shopMoney', {}).get('amount', '0'),
                        'currency': order.get('currentTotalPriceSet', {}).get('shopMoney', {}).get('currencyCode', 'EUR'),
                        'fulfillment_status': order.get('displayFulfillmentStatus', ''),
                        'financial_status': order.get('displayFinancialStatus', ''),
                        'fully_paid': order.get('fullyPaid', False),
                        'refunds': order.get('refunds', [])
                    })
                except Exception as e:
                    print(f"⚠️ Errore nel processamento ordine {order.get('name', 'N/A')}: {str(e)}")
                    continue

            has_next_page = orders_data.get('pageInfo', {}).get('hasNextPage', False)
            if has_next_page:
                after_cursor = edges[-1]['cursor'] if edges else None

            break  # Esci dal loop di retry

    return all_orders

# ============================================================================
# LAMBDA HANDLER
# ============================================================================
def lambda_handler(event, context):
    """
    Handler principale Lambda.
    Cerca tutti gli ordini con tag RESO e DA RIMBORSARE.
    """
    try:
        # Tag richiesti
        required_tags = ['RESO', 'DA RIMBORSARE']

        print(f"🔍 Cercando tutti gli ordini con tag {required_tags}...")

        # Scarica ordini
        orders = fetch_orders_with_tags(required_tags)

        # Prepara risposta
        response = {
            'metadata': {
                'extraction_date': datetime.now().isoformat(),
                'period_days': 'all',
                'total_orders': len(orders),
                'required_tags': required_tags
            },
            'orders': orders
        }

        print(f"✅ Trovati {len(orders)} ordini da rimborsare")

        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(response, default=str)
        }

    except Exception as e:
        print(f"❌ Errore: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': str(e),
                'metadata': {
                    'extraction_date': datetime.now().isoformat()
                }
            })
        }