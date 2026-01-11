"""
Lambda per aggiungere tag RIFIUTO a ordini Shopify
Supporta tagging singolo e bulk con modalità preview
Endpoint POST con order_id(s) e preview nel body
"""

import json
import requests
import os

# CONFIGURAZIONE
SHOPIFY_ACCESS_TOKEN = os.environ.get('SHOPIFY_ACCESS_TOKEN')
SHOP_NAME = os.environ.get("SHOPIFY_SHOP_NAME", "db806d-07")
SHOPIFY_API_VERSION = "2024-04"
SHOPIFY_GRAPHQL_URL = f"https://{SHOP_NAME}.myshopify.com/admin/api/{SHOPIFY_API_VERSION}/graphql.json"


def add_tag_to_order(order_id, tag):
    """
    Aggiunge un tag a un ordine Shopify
    
    Args:
        order_id: ID Shopify dell'ordine (formato gid://shopify/Order/...)
        tag: Tag da aggiungere
        
    Returns:
        bool: True se successo
    """
    headers = {
        'X-Shopify-Access-Token': SHOPIFY_ACCESS_TOKEN,
        'Content-Type': 'application/json'
    }
    
    mutation = f"""
    mutation {{
      tagsAdd(id: "{order_id}", tags: ["{tag}"]) {{
        node {{
          id
        }}
        userErrors {{
          field
          message
        }}
      }}
    }}
    """
    
    try:
        response = requests.post(SHOPIFY_GRAPHQL_URL, headers=headers, json={"query": mutation})
        data = response.json()
        
        if 'errors' in data:
            print(f"⚠️ Errore aggiunta tag: {data['errors']}")
            return False, f"GraphQL errors: {data['errors']}"
        
        user_errors = data.get('data', {}).get('tagsAdd', {}).get('userErrors', [])
        if user_errors:
            print(f"⚠️ User errors: {user_errors}")
            return False, f"User errors: {user_errors}"
        
        return True, "Tag aggiunto con successo"
    except Exception as e:
        print(f"⚠️ Errore aggiunta tag: {e}")
        return False, str(e)


def lambda_handler(event, context):
    """Handler Lambda - supporta singolo e bulk con preview"""
    try:
        print("🏷️  Inizio tagging RIFIUTO...")
        
        # Parse body
        body = json.loads(event.get('body', '{}'))
        order_id = body.get('order_id')  # Singolo ordine
        order_ids = body.get('order_ids', [])  # Lista ordini per bulk
        preview = body.get('preview', False)  # Modalità preview
        
        # Determina se bulk o singolo
        if order_ids:
            is_bulk = True
            target_orders = order_ids
            print(f"📦 Bulk tagging: {len(target_orders)} ordini")
        elif order_id:
            is_bulk = False
            target_orders = [order_id]
            print(f"📦 Singolo ordine: {order_id}")
        else:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'error': 'order_id o order_ids è obbligatorio'})
            }
        
        if preview:
            print("👀 Modalità PREVIEW - nessun tag verrà aggiunto")
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'preview': True,
                    'orders_to_tag': target_orders,
                    'count': len(target_orders),
                    'message': f"Preview: {len(target_orders)} ordini verrebbero taggati con 'RIFIUTO'"
                })
            }
        
        # Esegui tagging effettivo
        results = []
        success_count = 0
        error_count = 0
        
        for i, oid in enumerate(target_orders):
            print(f"🏷️  [{i+1}/{len(target_orders)}] Tagging ordine {oid}...")
            
            success, message = add_tag_to_order(oid, 'RIFIUTO')
            
            result = {
                'order_id': oid,
                'success': success,
                'message': message
            }
            results.append(result)
            
            if success:
                success_count += 1
                print(f"✅ Tag aggiunto")
            else:
                error_count += 1
                print(f"❌ Errore: {message}")
        
        print(f"📊 Risultati: {success_count} successi, {error_count} errori")
        
        return {
            'statusCode': 200 if error_count == 0 else 207,  # 207 = Multi-Status
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'success': error_count == 0,
                'total': len(target_orders),
                'success_count': success_count,
                'error_count': error_count,
                'results': results,
                'message': f"Taggati {success_count}/{len(target_orders)} ordini con 'RIFIUTO'"
            })
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
