"""
Lambda function per evasione ordini con GLS e Shopify.
Crea spedizione GLS (SOAP) e marca ordine Shopify come fulfilled.

Nome Lambda: adibodyes_fulfill_order
Endpoint: /orders/fulfill
"""
import os
import json
import requests
import urllib3
import time
import traceback
from datetime import datetime
from typing import Dict, Any
import xml.etree.ElementTree as ET

# ============================================================================
# CONFIGURAZIONE
# ============================================================================
GLS_SOAP_ENDPOINT = "https://wsclientes.asmred.com/b2b.asmx"
GLS_UID = os.getenv("GLS_UID")

SHOPIFY_ACCESS_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN")
SHOPIFY_SHOP_DOMAIN = os.getenv("SHOPIFY_SHOP_DOMAIN", "db806d-07.myshopify.com")
SHOPIFY_API_VERSION = os.getenv("SHOPIFY_API_VERSION", "2024-04")
SHOPIFY_GRAPHQL_URL = f"https://{SHOPIFY_SHOP_DOMAIN}/admin/api/{SHOPIFY_API_VERSION}/graphql.json"

SHOPIFY_HEADERS = {
    'X-Shopify-Access-Token': SHOPIFY_ACCESS_TOKEN,
    'Content-Type': 'application/json',
    'Accept': 'application/json'
}


# ============================================================================
# GLS SERVICE - CREAZIONE SPEDIZIONE
# ============================================================================
def create_gls_shipment(order_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Crea spedizione GLS tramite SOAP API.
    
    Args:
        order_data: {
            orderId, orderName, customerName, 
            shippingAddress: {address1, address2, city, zip, country, phone},
            items: [{sku, quantity, title}],
            totalPrice, financialStatus, email,
            customObservations (optional)
        }
    
    Returns:
        {success: bool, trackingNumber: str, error: str}
    """
    try:
        # Determina reembolso basato su financial status
        is_paid = order_data.get('financialStatus', '').lower() == 'paid'
        reembolso = '0' if is_paid else str(order_data.get('totalPrice', '0'))
        
        # Observations: usa custom o genera da SKU
        custom_obs = order_data.get('customObservations', '')
        if custom_obs:
            observaciones = custom_obs
        else:
            items = order_data.get('items', [])
            observaciones = ', '.join([
                f"{item['sku']}x{item['quantity']}" 
                for item in items if item.get('sku')
            ])
        
        # Estrai albaran dal nome ordine (es: #ES9162 -> 9162)
        order_name = order_data.get('orderName', '')
        albaran = order_name.replace('#ES', '').replace('#', '')
        
        # Dati indirizzo
        shipping = order_data.get('shippingAddress', {})
        address_line = f"{shipping.get('address1', '')} {shipping.get('address2', '')}".strip()
        
        # Data spedizione (oggi in formato DD/MM/YYYY)
        fecha = datetime.now().strftime('%d/%m/%Y')
        
        # Build SOAP XML
        soap_xml = f"""<?xml version="1.0" encoding="utf-8"?>
<soap12:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                 xmlns:xsd="http://www.w3.org/2001/XMLSchema"
                 xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">
  <soap12:Body>
    <GrabaServicios xmlns="http://www.asmred.com/">
      <docIn>
        <Servicios uidcliente="{GLS_UID}" xmlns="http://www.asmred.com/">
          <Envio>
            <Fecha>{fecha}</Fecha>
            <Servicio>96</Servicio>
            <Horario>18</Horario>
            <Bultos>1</Bultos>
            <Peso>1</Peso>
            <Portes>P</Portes>
            <Remite>
              <Nombre>AdiBody ES</Nombre>
              <Direccion>Calle Pino Siberia 28 (ENVIALIA)</Direccion>
              <Poblacion>Sevilla</Poblacion>
              <Pais>34</Pais>
              <CP>41016</CP>
              <Telefono>954981710</Telefono>
            </Remite>
            <Destinatario>
              <Nombre>{order_data.get('customerName', '')}</Nombre>
              <Direccion>{address_line}</Direccion>
              <Poblacion>{shipping.get('city', '')}</Poblacion>
              <Pais>34</Pais>
              <CP>{shipping.get('zip', '')}</CP>
              <Telefono>{shipping.get('phone', '')}</Telefono>
              <Email>{order_data.get('email', '')}</Email>
            </Destinatario>
            <Referencias>
              <Referencia tipo="C">{order_name}</Referencia>
            </Referencias>
            <Albaran>{albaran}</Albaran>
            <Observaciones>{observaciones}</Observaciones>
            <Importe>{order_data.get('totalPrice', '0')}</Importe>
            <Reembolso>{reembolso}</Reembolso>
            <Retorno>0</Retorno>
          </Envio>
        </Servicios>
      </docIn>
    </GrabaServicios>
  </soap12:Body>
</soap12:Envelope>"""

        print(f"🚚 Creazione spedizione GLS per ordine: {order_name}")
        print(f"📦 Cliente: {order_data.get('customerName')}")
        print(f"💰 Importo: {order_data.get('totalPrice')} - Reembolso: {reembolso}")
        
        # Chiamata SOAP a GLS
        response = requests.post(
            GLS_SOAP_ENDPOINT,
            data=soap_xml.encode('utf-8'),
            headers={
                'Content-Type': 'text/xml; charset=UTF-8',
                'SOAPAction': 'http://www.asmred.com/GrabaServicios'
            },
            timeout=30
        )
        
        if not response.ok:
            return {
                'success': False,
                'error': f"GLS HTTP error: {response.status_code}"
            }
        
        # Parse XML response
        response_text = response.text
        print(f"📨 GLS Response: {response_text[:500]}")
        
        try:
            root = ET.fromstring(response_text)
            
            # Trova elementi nella response (gestisce namespace)
            # Cerca codbarras (tracking number)
            codbarras_elem = root.find('.//{http://www.asmred.com/}Envio[@codbarras]')
            if codbarras_elem is not None:
                tracking_number = codbarras_elem.get('codbarras')
            else:
                # Fallback: cerca in modo case-insensitive
                codbarras_elem = root.find('.//Envio[@codbarras]')
                tracking_number = codbarras_elem.get('codbarras') if codbarras_elem is not None else None
            
            # Verifica errori nella response
            resultado = root.find('.//{http://www.asmred.com/}Resultado[@return]')
            if resultado is not None:
                return_code = resultado.get('return')
                if return_code != '0':
                    error_msg = resultado.text or f"GLS error code: {return_code}"
                    return {
                        'success': False,
                        'error': error_msg
                    }
            
            if not tracking_number:
                return {
                    'success': False,
                    'error': 'GLS non ha restituito tracking number'
                }
            
            print(f"✅ GLS Tracking Number: {tracking_number}")
            
            return {
                'success': True,
                'trackingNumber': tracking_number
            }
            
        except ET.ParseError as e:
            return {
                'success': False,
                'error': f"Errore parsing XML GLS: {str(e)}"
            }
        
    except requests.RequestException as e:
        return {
            'success': False,
            'error': f"Errore chiamata GLS: {str(e)}"
        }
    except Exception as e:
        return {
            'success': False,
            'error': f"Errore GLS: {str(e)}"
        }


# ============================================================================
# SHOPIFY SERVICE - FULFILLMENT (GraphQL)
# ============================================================================
def get_open_fulfillment_order(order_id: str) -> Dict[str, Any]:
    """
    Verifica se l'ordine ha un fulfillment order OPEN.
    Questa funzione viene chiamata PRIMA di creare la spedizione GLS.
    
    Args:
        order_id: gid://shopify/Order/7250120638805 o ID numerico
    
    Returns:
        {success: bool, fulfillmentOrderId: str, error: str}
    """
    try:
        # Estrai ID numerico da GID se necessario
        if order_id.startswith('gid://'):
            numeric_id = order_id.split('/')[-1]
        else:
            numeric_id = str(order_id)
        
        order_gid = f"gid://shopify/Order/{numeric_id}"
        
        print(f"📦 VERIFICA PRELIMINARE: Controllo FO per ordine {numeric_id}")
        
        # Query per recuperare fulfillment orders
        get_fo_query = """
        query getFulfillmentOrders($orderId: ID!) {
          order(id: $orderId) {
            id
            fulfillmentOrders(first: 10) {
              edges {
                node {
                  id
                  status
                }
              }
            }
          }
        }
        """
        
        get_fo_variables = {
            "orderId": order_gid
        }
        
        fo_response = requests.post(
            SHOPIFY_GRAPHQL_URL,
            json={"query": get_fo_query, "variables": get_fo_variables},
            headers=SHOPIFY_HEADERS,
            timeout=30
        )
        
        if not fo_response.ok:
            return {
                'success': False,
                'error': f"GraphQL getFulfillmentOrders failed: HTTP {fo_response.status_code}"
            }
        
        fo_data = fo_response.json()
        
        if 'errors' in fo_data:
            return {
                'success': False,
                'error': f"GraphQL errors: {fo_data['errors']}"
            }
        
        # Estrai fulfillment orders
        order_data = fo_data.get('data', {}).get('order', {})
        if not order_data:
            return {
                'success': False,
                'error': f"Ordine {order_gid} non trovato"
            }
        
        fo_edges = order_data.get('fulfillmentOrders', {}).get('edges', [])
        
        if not fo_edges:
            return {
                'success': False,
                'error': 'Nessun fulfillment order trovato per questo ordine'
            }
        
        # Cerca il fulfillment order con status OPEN
        fo_node = None
        for edge in fo_edges:
            if edge['node']['status'] == 'OPEN':
                fo_node = edge['node']
                break
        
        if not fo_node:
            # Mostra gli status disponibili per debug
            available_statuses = [edge['node']['status'] for edge in fo_edges]
            return {
                'success': False,
                'error': f'Nessun fulfillment order con status OPEN. Status disponibili: {available_statuses}'
            }
        
        fo_id = fo_node['id']
        
        print(f"✅ Fulfillment Order OPEN trovato: {fo_id}")
        
        return {
            'success': True,
            'fulfillmentOrderId': fo_id
        }
        
    except requests.RequestException as e:
        return {
            'success': False,
            'error': f"Errore chiamata Shopify: {str(e)}"
        }
    except Exception as e:
        return {
            'success': False,
            'error': f"Errore: {str(e)}\n{traceback.format_exc()}"
        }


def create_shopify_fulfillment(
    fulfillment_order_id: str,
    tracking_number: str,
    zip_code: str,
    notify_customer: bool = False
) -> Dict[str, Any]:
    """
    Crea fulfillment su Shopify con tracking info.
    Questa funzione viene chiamata DOPO aver verificato il FO e creato la spedizione GLS.
    
    Args:
        fulfillment_order_id: ID del FO già verificato come OPEN
        tracking_number: 61586276012345
        zip_code: 28004
        notify_customer: Invia email al cliente
    
    Returns:
        {success: bool, error: str}
    """
    try:
        tracking_url = f"https://mygls.gls-spain.es/e/{tracking_number}/{zip_code}"
        
        print(f"📦 Creo fulfillment per FO: {fulfillment_order_id}")
        print(f"🚚 Tracking: {tracking_number}")
        
        fulfill_mutation = """
        mutation FulfillOrder($fulfillment: FulfillmentInput!) {
          fulfillmentCreate(fulfillment: $fulfillment) {
            fulfillment {
              id
              status
              trackingInfo(first: 5) {
                company
                number
                url
              }
            }
            userErrors {
              field
              message
            }
          }
        }
        """
        
        fulfill_variables = {
            "fulfillment": {
                "notifyCustomer": notify_customer,
                "trackingInfo": {
                    "company": "GLS Spain, S.A.",
                    "number": tracking_number,
                    "url": tracking_url
                },
                "lineItemsByFulfillmentOrder": [
                    {
                        "fulfillmentOrderId": fulfillment_order_id
                    }
                ]
            }
        }
        
        print(f"📝 Variables: {json.dumps(fulfill_variables, indent=2)}")
        
        fulfill_response = requests.post(
            SHOPIFY_GRAPHQL_URL,
            json={"query": fulfill_mutation, "variables": fulfill_variables},
            headers=SHOPIFY_HEADERS,
            timeout=30
        )
        
        if not fulfill_response.ok:
            return {
                'success': False,
                'error': f"GraphQL fulfillmentCreate failed: HTTP {fulfill_response.status_code}"
            }
        
        fulfill_data = fulfill_response.json()
        
        if 'errors' in fulfill_data:
            return {
                'success': False,
                'error': f"GraphQL errors: {fulfill_data['errors']}"
            }
        
        result = fulfill_data.get('data', {}).get('fulfillmentCreate', {})
        
        # Verifica userErrors
        user_errors = result.get('userErrors', [])
        if user_errors:
            error_messages = [f"{e.get('field', 'unknown')}: {e.get('message', 'unknown error')}" for e in user_errors]
            return {
                'success': False,
                'error': f"Fulfillment errors: {'; '.join(error_messages)}"
            }
        
        fulfillment = result.get('fulfillment')
        if not fulfillment:
            return {
                'success': False,
                'error': 'Nessun fulfillment creato nella response'
            }
        
        print(f"✅ Fulfillment creato con successo: {fulfillment['id']}")
        print(f"📊 Status: {fulfillment.get('status')}")
        
        return {'success': True}
        
    except requests.RequestException as e:
        return {
            'success': False,
            'error': f"Errore chiamata Shopify: {str(e)}"
        }
    except Exception as e:
        return {
            'success': False,
            'error': f"Errore Shopify: {str(e)}\n{traceback.format_exc()}"
        }


# ============================================================================
# LAMBDA HANDLER
# ============================================================================
def lambda_handler(event, context):
    """
    Handler Lambda per fulfill-order.
    
    Input (POST /orders/fulfill):
    {
        "orderId": "gid://shopify/Order/7248415818069",
        "orderName": "#ES9162",
        "customerName": "Maria Rossi",
        "shippingAddress": {
            "address1": "Via Roma 123",
            "address2": "",
            "city": "Madrid",
            "zip": "28004",
            "country": "Spain",
            "phone": "666777888"
        },
        "items": [
            {"sku": "SLIP.L.BL", "quantity": 1, "title": "Slip L Blue"}
        ],
        "totalPrice": "29.9",
        "financialStatus": "PAID",
        "email": "cliente@email.com",
        "customObservations": "",  // optional
        "notifyCustomer": false    // optional
    }
    
    Output:
    {
        "success": true,
        "trackingNumber": "61586276012345",
        "message": "Ordine evaso con successo"
    }
    """
    print(f"📥 Event: {json.dumps(event)}")
    
    try:
        # Parse body
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event.get('body', event)
        
        # Validazione campi obbligatori
        required_fields = ['orderId', 'orderName', 'customerName', 'shippingAddress', 
                          'items', 'totalPrice', 'financialStatus']
        missing = [f for f in required_fields if not body.get(f)]
        if missing:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'POST, OPTIONS',
                    'Access-Control-Allow-Headers': 'Content-Type'
                },
                'body': json.dumps({
                    'success': False,
                    'error': f"Campi mancanti: {', '.join(missing)}"
                })
            }
        
        # Step 1: Verifica che esista un FO OPEN su Shopify
        print("\n" + "="*60)
        print("STEP 1: VERIFICA SHOPIFY")
        print("="*60)
        
        fo_check = get_open_fulfillment_order(body['orderId'])
        
        if not fo_check['success']:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'POST, OPTIONS',
                    'Access-Control-Allow-Headers': 'Content-Type'
                },
                'body': json.dumps({
                    'success': False,
                    'error': f"Shopify: {fo_check['error']}"
                })
            }
        
        fulfillment_order_id = fo_check['fulfillmentOrderId']
        print(f"✅ FO OPEN verificato: {fulfillment_order_id}")
        
        # Step 2: Crea spedizione GLS
        print("\n" + "="*60)
        print("STEP 2: CREAZIONE SPEDIZIONE GLS")
        print("="*60)
        
        gls_result = create_gls_shipment(body)
        
        if not gls_result['success']:
            return {
                'statusCode': 500,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'POST, OPTIONS',
                    'Access-Control-Allow-Headers': 'Content-Type'
                },
                'body': json.dumps({
                    'success': False,
                    'error': f"GLS: {gls_result['error']}"
                })
            }
        
        tracking_number = gls_result['trackingNumber']
        print(f"✅ Tracking GLS ottenuto: {tracking_number}")
        
        # Step 3: Crea fulfillment su Shopify
        print("\n" + "="*60)
        print("STEP 3: CREAZIONE FULFILLMENT SHOPIFY")
        print("="*60)
        
        notify_customer = body.get('notifyCustomer', False)
        zip_code = body['shippingAddress'].get('zip', '')
        
        shopify_result = create_shopify_fulfillment(
            fulfillment_order_id,
            tracking_number,
            zip_code,
            notify_customer
        )
        
        if not shopify_result['success']:
            # GLS creato ma Shopify fallito
            return {
                'statusCode': 500,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'POST, OPTIONS',
                    'Access-Control-Allow-Headers': 'Content-Type'
                },
                'body': json.dumps({
                    'success': False,
                    'trackingNumber': tracking_number,
                    'error': f"Spedizione GLS creata ma Shopify fallito: {shopify_result['error']}"
                })
            }
        
        # Tutto OK
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type'
            },
            'body': json.dumps({
                'success': True,
                'trackingNumber': tracking_number,
                'message': f"Ordine {body['orderName']} evaso con successo"
            })
        }
        
    except json.JSONDecodeError as e:
        return {
            'statusCode': 400,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type'
            },
            'body': json.dumps({
                'success': False,
                'error': f"JSON non valido: {str(e)}"
            })
        }
    except Exception as e:
        print(f"❌ Errore: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type'
            },
            'body': json.dumps({
                'success': False,
                'error': str(e)
            })
        }


# ============================================================================
# TEST LOCALE
# ============================================================================
if __name__ == "__main__":
    print("🧪 TEST MODE - MODALITÀ PRODUZIONE")
    print("⚠️  ATTENZIONE: GLS è ABILITATO - verrà creata una spedizione reale!")
    print("📋 Ordine di test: ES9186")
    print("="*60)
    
    # INSERISCI QUI L'ID NUMERICO DELL'ORDINE ES9186
    # Puoi trovarlo nella URL dell'ordine su Shopify Admin
    # Es: https://db806d-07.myshopify.com/admin/orders/7252353253717
    ORDER_ID = "7252353253717"  # ⚠️ SOSTITUISCI CON L'ID REALE DI ES9186
    
    test_event = {
        "orderId": ORDER_ID,
        "orderName": "#ES9186",
        "customerName": "Test Cliente",
        "shippingAddress": {
            "address1": "Calle Test 123",
            "address2": "",
            "city": "Madrid",
            "zip": "28004",
            "country": "Spain",
            "phone": "666777888"
        },
        "items": [
            {"sku": "BODY.M.BE", "quantity": 1, "title": "Body Moldeador"}
        ],
        "totalPrice": "39.90",
        "financialStatus": "PAID",
        "email": "test@adibody.es",
        "customObservations": "TEST - No enviare",
        "notifyCustomer": False
    }
    
    result = lambda_handler(test_event, None)
    print(f"\n📤 Result: {json.dumps(json.loads(result['body']), indent=2)}")
