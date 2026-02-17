"""
Lambda API per Dashboard Stock
Restituisce dati stock da Google Sheets + calcolo ordine fornitore

Endpoint: GET /stock
Response:
{
  "stock": [
    {
      "sku": "SLIP.XS.BE",
      "modelo": "SLIP BE",
      "talla": "XS",
      "magazzino_attuale": 150,
      "in_arrivo": 0,
      "totale_disponibile": 150,
      "ordini_arretrati": 5,
      "magazzino_netto": 145,
      "giorni_autonomia": 25,
      "urgenza": "ORDINARE"
    },
    ...
  ],
  "ordine_fornitore": [
    {
      "sku": "SLIP.XS.BE",
      "modelo": "SLIP BE",
      "talla": "XS",
      "quantita": 100,
      "urgenza": "CRITICO",
      "giorni_autonomia": 12
    },
    ...
  ],
  "summary": {
    "totale_sku": 150,
    "totale_pezzi_stock": 25000,
    "sku_critici": 5,
    "sku_da_ordinare": 15,
    "totale_pezzi_ordine": 1500
  }
}
"""

import json
import os
import requests
import pandas as pd
import math
import sys
from datetime import datetime, timedelta
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Aggiungi path per importare moduli locali
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'GLS'))

# Import GLS per SKU ritorni
from extract_sku_con_retorno import GLSExtranetClient, extract_sku_from_returns

# ==================== CONFIGURAZIONE ====================

# Abilita/disabilita controllo spedizioni GLS
ENABLE_GLS_CHECKS = os.environ.get("ENABLE_GLS_CHECKS", "True").lower() == "true"

# Shopify API
SHOP_NAME = os.environ.get("SHOPIFY_SHOP_NAME", "db806d-07")
SHOPIFY_ACCESS_TOKEN = os.environ.get("SHOPIFY_ACCESS_TOKEN")
SHOPIFY_API_VERSION = "2024-04"

# Shopify GraphQL
SHOPIFY_GRAPHQL_URL = f"https://{SHOP_NAME}.myshopify.com/admin/api/{SHOPIFY_API_VERSION}/graphql.json"
SHOPIFY_GRAPHQL_TOKEN = os.environ.get("SHOPIFY_GRAPHQL_TOKEN")

# Parametri inventario
GIORNI_TARGET_SCORTA = 45
GIORNI_TRANSITO = 21
SOGLIA_ALLARME = GIORNI_TARGET_SCORTA + GIORNI_TRANSITO
SOGLIA_CRITICA = 21
GIORNI_ANALISI_VENDITE = 10
MOLTIPLICATORE_CRESCITA_VENDITE = 1

# Tags ordini arretrati
TAGS_ORDINI_ARRETRATI = ["MANCA MODELLO", "MANCA MODELLO 2"]

# Google Sheets
GOOGLE_SHEET_ID = os.environ.get("GOOGLE_SHEET_ID", "1mOWYahqRDPK0mqGEOPMsC--WWdq7hsoskQyaSWrR7xY")
SHEET_MAGAZZINO = "Magazzino"
SHEET_ARRIVO = "InArrivo"

# Credenziali Google (da variabile ambiente o file)
GOOGLE_CREDENTIALS_JSON = os.environ.get("GOOGLE_CREDENTIALS_JSON")

# ==================== GOOGLE SHEETS ====================

def get_google_sheets_service():
    """Crea servizio Google Sheets API"""
    try:
        if GOOGLE_CREDENTIALS_JSON:
            # Da variabile ambiente (per Lambda)
            credentials_info = json.loads(GOOGLE_CREDENTIALS_JSON)
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
        
        return build('sheets', 'v4', credentials=credentials)
    except Exception as e:
        print(f"❌ Errore Google Sheets: {e}")
        return None


def read_sheet_data(service, sheet_name):
    """Legge dati da Google Sheets"""
    try:
        result = service.spreadsheets().values().get(
            spreadsheetId=GOOGLE_SHEET_ID,
            range=f"{sheet_name}!A:D"
        ).execute()
        
        values = result.get('values', [])
        if not values:
            return {}
        
        data = {}
        for row in values[1:]:  # Skip header
            if len(row) >= 4:
                sku = str(row[2]).strip()
                if sku.upper() == "TOTAL" or not sku:
                    continue
                try:
                    data[sku] = int(row[3])
                except (ValueError, IndexError):
                    continue
        
        return data
    except Exception as e:
        print(f"❌ Errore lettura {sheet_name}: {e}")
        return {}


# ==================== SHOPIFY ====================

def fetch_shopify_orders(days_back=10):
    """Scarica ordini Shopify ultimi N giorni"""
    today = datetime.utcnow()
    start_date = (today - timedelta(days=days_back)).isoformat()
    
    base_url = f"https://{SHOP_NAME}.myshopify.com/admin/api/{SHOPIFY_API_VERSION}/orders.json"
    headers = {"X-Shopify-Access-Token": SHOPIFY_ACCESS_TOKEN}
    params = {
        "status": "any",
        "created_at_min": start_date,
        "limit": 250
    }
    
    sku_data = []
    response = requests.get(base_url, headers=headers, params=params)
    
    if response.status_code != 200:
        raise Exception(f"Errore Shopify: {response.status_code}")
    
    data = response.json()
    
    def extract_data(orders):
        for order in orders:
            created_at = order.get("created_at")
            for item in order.get("line_items", []):
                sku = item.get("sku")
                qty = item.get("current_quantity")
                if sku and created_at:
                    sku_data.append({
                        "sku": sku,
                        "current_quantity": qty,
                        "created_at": created_at
                    })
    
    extract_data(data.get("orders", []))
    
    # Paginazione - continua finché ci sono altre pagine
    while 'Link' in response.headers and 'rel="next"' in response.headers['Link']:
        link_header = response.headers['Link']
        next_url = None
        for part in link_header.split(','):
            if 'rel="next"' in part:
                next_url = part.split(';')[0].strip('<> ')
                break
        
        if not next_url:
            break
        
        response = requests.get(next_url, headers=headers)
        data = response.json()
        extract_data(data.get("orders", []))
    
    return sku_data


def fetch_backorders():
    """Recupera ordini arretrati"""
    headers = {
        'X-Shopify-Access-Token': SHOPIFY_GRAPHQL_TOKEN,
        'Content-Type': 'application/json'
    }
    
    # Ordini arretrati ultimi 30 giorni (allineato al periodo di analisi)
    start_date = (datetime.utcnow() - timedelta(days=GIORNI_ANALISI_VENDITE)).strftime("%Y-%m-%d")
    all_orders = []
    has_next_page = True
    after_cursor = None
    
    while has_next_page:
        cursor_part = f', after: "{after_cursor}"' if after_cursor else ''
        query = f"""
        {{
          orders(first: 250{cursor_part}, query: "created_at:>={start_date}") {{
            pageInfo {{ hasNextPage }}
            edges {{
              cursor
              node {{
                tags
                lineItems(first: 100) {{
                  edges {{
                    node {{
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
        
        response = requests.post(SHOPIFY_GRAPHQL_URL, headers=headers, json={"query": query})
        
        if response.status_code != 200:
            break
        
        data = response.json()
        if "errors" in data:
            break
        
        orders_batch = data["data"]["orders"]["edges"]
        all_orders.extend(orders_batch)
        
        has_next_page = data["data"]["orders"]["pageInfo"]["hasNextPage"]
        if has_next_page:
            after_cursor = orders_batch[-1]["cursor"]
    
    # Filtra e somma
    sku_backorders = {}
    for edge in all_orders:
        tags = edge["node"].get("tags", [])
        if any(tag.strip() in TAGS_ORDINI_ARRETRATI for tag in tags):
            for item_edge in edge["node"]["lineItems"]["edges"]:
                item = item_edge["node"]
                sku = item["sku"]
                quantity = item["quantity"]
                if sku:
                    sku_backorders[sku] = sku_backorders.get(sku, 0) + quantity
    
    return sku_backorders


# ==================== CALCOLI ====================

def calculate_weighted_average(sku_data, days=10):
    """Calcola media pesata vendite"""
    df = pd.DataFrame(sku_data).copy()
    
    if df.empty:
        return pd.DataFrame(columns=["sku", "media_pesata"])
    
    # Unifica le date: Shopify usa "created_at" (ISO datetime), GLS usa "date" (YYYY-MM-DD)
    def extract_date(row):
        if pd.notna(row.get("created_at")):
            return pd.to_datetime(row["created_at"], utc=True).date()
        elif pd.notna(row.get("date")):
            return pd.to_datetime(row["date"]).date()
        else:
            return None
    
    df["date"] = df.apply(extract_date, axis=1)
    
    grouped = (
        df.groupby(["date", "sku"])
        .agg(total_quantity=("current_quantity", "sum"))
        .reset_index()
    )
    
    end_date = max(grouped["date"])
    start_date = end_date - timedelta(days=days - 1)
    date_range = pd.date_range(start=start_date, end=end_date).date
    
    grouped_window = grouped[(grouped["date"] >= start_date) & (grouped["date"] <= end_date)].copy()
    all_skus = grouped_window["sku"].dropna().astype(str).unique()
    
    full_index = pd.MultiIndex.from_product([date_range, all_skus], names=["date", "sku"])
    
    full_df = (
        grouped_window
        .assign(sku=lambda x: x["sku"].astype(str))
        .set_index(["date", "sku"])
        .reindex(full_index, fill_value=0)
        .reset_index()
    )
    
    full_df["weight"] = full_df["date"].apply(lambda d: (d - start_date).days + 1)
    
    weighted_avg = (
        full_df.assign(weighted_quantity=lambda x: x["total_quantity"] * x["weight"])
        .groupby("sku", as_index=False)
        .agg(
            weighted_sum=("weighted_quantity", "sum"),
            total_weight=("weight", "sum")
        )
    )
    
    weighted_avg["media_pesata"] = weighted_avg["weighted_sum"] / weighted_avg["total_weight"]
    
    return weighted_avg[["sku", "media_pesata"]]


def parse_sku(sku):
    """Estrae MODELO e TALLA da SKU (es: SLIP.XS.BE -> SLIP BE, XS)"""
    parts = sku.split('.')
    if len(parts) >= 3:
        modelo_base = parts[0]
        talla = parts[1]
        color = parts[2]
        modelo = f"{modelo_base} {color}"
        return modelo, talla
    return sku, ""


def is_valid_sku(sku):
    """Verifica se uno SKU ha il formato valido (almeno 3 parti separate da punto)"""
    if not sku or not isinstance(sku, str):
        return False
    parts = sku.split('.')
    return len(parts) >= 3 and all(part.strip() for part in parts)


def build_stock_data(weighted_avg, arrivo_fornitore, magazzino_attuale, backorders):
    """Costruisce dati completi stock + ordine fornitore"""
    
    # Tutti gli SKU validi (filtra quelli con formato non valido)
    all_skus = set()
    for sku in set(arrivo_fornitore.keys()) | set(magazzino_attuale.keys()):
        if is_valid_sku(sku):
            all_skus.add(sku)
    
    # Filtra anche i dati di input per rimuovere SKU non validi
    arrivo_fornitore = {sku: qty for sku, qty in arrivo_fornitore.items() if is_valid_sku(sku)}
    magazzino_attuale = {sku: qty for sku, qty in magazzino_attuale.items() if is_valid_sku(sku)}
    backorders = {sku: qty for sku, qty in backorders.items() if is_valid_sku(sku)}
    
    # Filtra weighted_avg per SKU validi
    if not weighted_avg.empty:
        weighted_avg = weighted_avg[weighted_avg["sku"].apply(is_valid_sku)].copy()
    
    # DataFrame base
    df = weighted_avg.copy()
    
    # Aggiungi SKU non venduti recentemente
    existing_skus = set(df["sku"])
    missing_skus = all_skus - existing_skus
    
    if missing_skus:
        new_rows = pd.DataFrame([
            {"sku": sku, "media_pesata": 0}
            for sku in missing_skus
        ])
        df = pd.concat([df, new_rows], ignore_index=True)
    
    # Aggiungi dati inventario
    df["magazzino_attuale"] = df["sku"].map(magazzino_attuale).fillna(0).astype(int)
    df["in_arrivo"] = df["sku"].map(arrivo_fornitore).fillna(0).astype(int)
    df["totale_disponibile"] = df["magazzino_attuale"] + df["in_arrivo"]
    df["ordini_arretrati"] = df["sku"].map(backorders).fillna(0).astype(int)
    df["magazzino_netto"] = df["totale_disponibile"] - df["ordini_arretrati"]
    
    # Calcola autonomia
    df["giorni_autonomia"] = df.apply(
        lambda row: row["magazzino_netto"] / row["media_pesata"] 
        if row["media_pesata"] > 0 else float('inf'), 
        axis=1
    )
    
    # Calcola fabbisogno
    df["autonomia_tra_transito"] = df["giorni_autonomia"] - GIORNI_TRANSITO
    
    def calcola_fabbisogno(row):
        if row["media_pesata"] <= 0:
            return 0
        vendite_previste = row["media_pesata"] * MOLTIPLICATORE_CRESCITA_VENDITE
        giorni_mancanti = GIORNI_TARGET_SCORTA - row["autonomia_tra_transito"]
        fabbisogno_grezzo = max(0, giorni_mancanti * vendite_previste)
        
        # Log debug per SKU con fabbisogno > 0
        if fabbisogno_grezzo > 0:
            arrotondato = max(10, math.ceil(fabbisogno_grezzo / 10) * 10)
            print(f"🔍 DEBUG {row['sku']}:")
            print(f"   Magazzino netto: {row['magazzino_netto']} | Media vendite: {row['media_pesata']:.2f}/giorno")
            print(f"   Autonomia attuale: {row['giorni_autonomia']:.1f} giorni")
            print(f"   Autonomia tra transito: {row['autonomia_tra_transito']:.1f} giorni")
            print(f"   Giorni da coprire: {giorni_mancanti:.1f}")
            print(f"   Fabbisogno grezzo: {fabbisogno_grezzo:.2f} → arrotondato: {arrotondato}")
            return arrotondato
        return 0
    
    df["fabbisogno"] = df.apply(calcola_fabbisogno, axis=1).astype(int)
    
    # Debug: riepilogo fabbisogni
    df_con_fabbisogno = df[df["fabbisogno"] > 0]
    print(f"\n📋 RIEPILOGO FABBISOGNI (Stock API):")
    print(f"   SKU da ordinare: {len(df_con_fabbisogno)}")
    print(f"   Totale pezzi: {df_con_fabbisogno['fabbisogno'].sum()}")
    print(f"\n   Dettaglio:")
    for _, row in df_con_fabbisogno.iterrows():
        print(f"   {row['sku']}: {row['fabbisogno']} pz (autonomia: {row['giorni_autonomia']:.1f}gg, media: {row['media_pesata']:.2f}/gg)")
    
    # Urgenza
    def urgenza(giorni):
        if giorni < SOGLIA_CRITICA:
            return "CRITICO"
        elif giorni < SOGLIA_ALLARME:
            return "ORDINARE"
        return "OK"
    
    df["urgenza"] = df["giorni_autonomia"].apply(urgenza)
    
    # Parse SKU
    df[["modelo", "talla"]] = df["sku"].apply(lambda x: pd.Series(parse_sku(x)))
    
    # Mantieni ordine originale del foglio Excel (Magazzino)
    sku_order = list(magazzino_attuale.keys())
    df["order"] = df["sku"].map({sku: i for i, sku in enumerate(sku_order)})
    df = df.sort_values("order", na_position='last').drop(columns=["order"])
    
    return df


def get_gls_returns_skus(days_back=7):
    """
    Recupera SKU da spedizioni GLS CON RETORNO (vendite esterne a Shopify)
    
    Args:
        days_back: Giorni indietro per la ricerca
        
    Returns:
        List di dict con formato: [{"sku": "SLIP.XL.BL", "quantity": 2, "date": "2026-01-15"}, ...]
    """
    import time
    try:
        # Carica cookies GLS
        cookies = GLSExtranetClient.load_cookies()
        if not cookies:
            print("⚠️ Cookies GLS non trovati, skip GLS sales")
            return []
        
        client = GLSExtranetClient(cookies)
        
        # Calcola date
        today = datetime.now()
        date_from = (today - timedelta(days=days_back)).strftime("%d/%m/%Y")
        date_to = today.strftime("%d/%m/%Y")
        
        # Cerca spedizioni (HTTP request)
        t_http = time.time()
        html = client.search_shipments(date_from, date_to)
        http_time = time.time() - t_http
        print(f"   ⏱️ HTTP request GLS: {http_time:.2f}s")
        
        if not html:
            return []
        
        # Parse spedizioni (CPU-intensive)
        t_parse = time.time()
        df = client.parse_shipments(html)
        parse_time = time.time() - t_parse
        print(f"   ⏱️ Parsing HTML: {parse_time:.2f}s")
        
        if df.empty:
            return []
        
        # Estrai SKU da spedizioni CON RETORNO con date
        t_extract = time.time()
        sku_sales_with_dates = extract_sku_from_returns_with_dates(df)
        extract_time = time.time() - t_extract
        print(f"   ⏱️ Elaborazione dati: {extract_time:.2f}s")
        
        return sku_sales_with_dates
        
    except Exception as e:
        print(f"⚠️ Errore recupero GLS sales: {e}")
        return []


def extract_sku_from_returns_with_dates(df):
    """
    Estrae SKU dalle spedizioni con "CON RETORNO" mantenendo la data di ogni spedizione
    
    Args:
        df: DataFrame delle spedizioni con colonna 'Fecha'
        
    Returns:
        List di dict con formato: [{"sku": "SLIP.XL.BL", "quantity": 2, "date": "2026-01-15"}, ...]
    """
    from collections import defaultdict
    
    sku_sales_list = []
    
    # Filtra spedizioni con "CON RETORNO"
    returns_df = df[df['retorno'].str.upper().str.contains('CON RETORNO', na=False)].copy()
    
    print(f"🔄 Analisi di {len(returns_df)} spedizioni con 'CON RETORNO'...\n")
    
    for idx, row in returns_df.iterrows():
        observacion = str(row.get('observacion', '')).strip()
        fecha = row.get('Fecha', '')
        
        # Converti data da formato DD/MM/YYYY a YYYY-MM-DD
        try:
            if fecha:
                date_obj = datetime.strptime(str(fecha), "%d/%m/%Y")
                date_str = date_obj.strftime("%Y-%m-%d")
            else:
                date_str = datetime.now().strftime("%Y-%m-%d")
        except:
            date_str = datetime.now().strftime("%Y-%m-%d")
        
        if not observacion:
            continue
        
        # Parse SKU dalla osservazione - crea un mini-df per la funzione esistente
        mini_df = pd.DataFrame([row])
        skus_in_shipment = extract_sku_from_returns(mini_df)
        
        for sku, qty in skus_in_shipment.items():
            if sku:
                sku_sales_list.append({
                    "sku": sku,
                    "quantity": qty,
                    "date": date_str
                })
    
    return sku_sales_list


# ==================== LAMBDA HANDLER ====================

def lambda_handler(event, context):
    """Handler Lambda - restituisce stock + ordine fornitore"""
    
    try:
        print("🚀 Inizio elaborazione stock...")
        
        # 1. Google Sheets
        service = get_google_sheets_service()
        if not service:
            raise Exception("Impossibile connettersi a Google Sheets")
        
        magazzino_attuale = read_sheet_data(service, SHEET_MAGAZZINO)
        arrivo_fornitore = read_sheet_data(service, SHEET_ARRIVO)
        
        # 2. Shopify
        sku_data = fetch_shopify_orders(days_back=GIORNI_ANALISI_VENDITE)
        
        # 2.5. Aggiungi vendite GLS esterne (se abilitato)
        if ENABLE_GLS_CHECKS:
            gls_sales_list = get_gls_returns_skus(days_back=GIORNI_ANALISI_VENDITE)
            if gls_sales_list:
                # Aggiungi le vendite GLS
                for item in gls_sales_list:
                    sku_data.append({
                        "created_at": item['date'],
                        "sku": item['sku'],
                        "current_quantity": item['quantity']
                    })
        
        # Filtra SKU non validi dai dati di vendita
        sku_data = [item for item in sku_data if is_valid_sku(item.get('sku'))]
        
        weighted_avg = calculate_weighted_average(sku_data, days=GIORNI_ANALISI_VENDITE)
        backorders = fetch_backorders()
        
        # Filtra backorders per SKU validi
        backorders = {sku: qty for sku, qty in backorders.items() if is_valid_sku(sku)}
        
        # 3. Calcola tutto
        df = build_stock_data(weighted_avg, arrivo_fornitore, magazzino_attuale, backorders)
        
        # 4. Prepara response
        stock_list = []
        for _, row in df.iterrows():
            stock_list.append({
                "sku": row["sku"],
                "modelo": row["modelo"],
                "talla": row["talla"],
                "magazzino_attuale": int(row["magazzino_attuale"]),
                "in_arrivo": int(row["in_arrivo"]),
                "totale_disponibile": int(row["totale_disponibile"]),
                "ordini_arretrati": int(row["ordini_arretrati"]),
                "magazzino_netto": int(row["magazzino_netto"]),
                "media_vendite_giornaliere": round(float(row["media_pesata"]), 2),
                "giorni_autonomia": round(float(row["giorni_autonomia"]), 1) if row["giorni_autonomia"] != float('inf') else 999,
                "urgenza": row["urgenza"]
            })
        
        # 5. Ordine fornitore (solo da ordinare) - ordinato per autonomia crescente (più critici prima)
        df_ordine = df[df["urgenza"].isin(["CRITICO", "ORDINARE"])].copy()
        df_ordine = df_ordine.sort_values("giorni_autonomia", ascending=True)
        
        ordine_list = []
        for _, row in df_ordine.iterrows():
            ordine_list.append({
                "sku": row["sku"],
                "modelo": row["modelo"],
                "talla": row["talla"],
                "quantita": int(row["fabbisogno"]),
                "urgenza": row["urgenza"],
                "giorni_autonomia": round(float(row["giorni_autonomia"]), 1)
            })
        
        # 6. Summary
        summary = {
            "totale_sku": len(df),
            "totale_pezzi_stock": int(df["totale_disponibile"].sum()),
            "totale_magazzino_attuale": int(df["magazzino_attuale"].sum()),
            "totale_in_arrivo": int(df["in_arrivo"].sum()),
            "sku_critici": int((df["urgenza"] == "CRITICO").sum()),
            "sku_da_ordinare": int((df["urgenza"] == "ORDINARE").sum()),
            "totale_pezzi_ordine": int(df_ordine["fabbisogno"].sum()) if not df_ordine.empty else 0
        }
        
        response_data = {
            "stock": stock_list,
            "ordine_fornitore": ordine_list,
            "summary": summary,
            "timestamp": datetime.now().isoformat()
        }
        
        print(f"✅ Completato: {len(stock_list)} SKU, {len(ordine_list)} da ordinare")
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Methods': 'GET,OPTIONS'
            },
            'body': json.dumps(response_data, ensure_ascii=False)
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


# ==================== TEST LOCALE ====================

if __name__ == "__main__":
    print("🧪 Test locale Lambda Stock API\n")
    result = lambda_handler({}, None)
    print(f"\nStatus: {result['statusCode']}")
    if result['statusCode'] == 200:
        data = json.loads(result['body'])
        print(f"\n📊 Summary:")
        print(json.dumps(data['summary'], indent=2))
        print(f"\n📦 Prime 5 righe stock:")
        for item in data['stock'][:5]:
            print(f"  {item['sku']}: {item['magazzino_netto']} pz, {item['giorni_autonomia']} gg")
        if data['ordine_fornitore']:
            print(f"\n🛒 Ordine fornitore ({len(data['ordine_fornitore'])} SKU):")
            for item in data['ordine_fornitore']:  # Mostra tutti, non solo i primi 5
                print(f"  {item['sku']}: {item['quantita']} pz ({item['urgenza']})")
