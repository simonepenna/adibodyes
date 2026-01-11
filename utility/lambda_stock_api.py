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
from datetime import datetime, timedelta
from google.oauth2 import service_account
from googleapiclient.discovery import build

# ==================== CONFIGURAZIONE ====================

# Shopify API
SHOP_NAME = os.environ.get("SHOPIFY_SHOP_NAME", "db806d-07")
SHOPIFY_ACCESS_TOKEN = os.environ.get("SHOPIFY_ACCESS_TOKEN")
SHOPIFY_API_VERSION = "2024-04"

# Shopify GraphQL
SHOPIFY_GRAPHQL_URL = f"https://{SHOP_NAME}.myshopify.com/admin/api/{SHOPIFY_API_VERSION}/graphql.json"
SHOPIFY_GRAPHQL_TOKEN = os.environ.get("SHOPIFY_GRAPHQL_TOKEN")

# Parametri inventario
GIORNI_TARGET_SCORTA = 40
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
    
    for order in data.get("orders", []):
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
    
    return sku_data


def fetch_backorders():
    """Recupera ordini arretrati"""
    headers = {
        'X-Shopify-Access-Token': SHOPIFY_GRAPHQL_TOKEN,
        'Content-Type': 'application/json'
    }
    
    # Ordini arretrati ultimi 30 giorni (allineato al periodo di analisi)
    start_date = (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%d")
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
    
    df["date"] = pd.to_datetime(df["created_at"], utc=True).dt.date
    
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


def build_stock_data(weighted_avg, arrivo_fornitore, magazzino_attuale, backorders):
    """Costruisce dati completi stock + ordine fornitore"""
    
    # Tutti gli SKU
    all_skus = set(arrivo_fornitore.keys()) | set(magazzino_attuale.keys())
    
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
        fabbisogno = max(0, (GIORNI_TARGET_SCORTA - row["autonomia_tra_transito"]) * vendite_previste)
        return math.ceil(fabbisogno / 10) * 10 if fabbisogno > 0 else 0
    
    df["fabbisogno"] = df.apply(calcola_fabbisogno, axis=1).astype(int)
    
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


# ==================== LAMBDA HANDLER ====================

def lambda_handler(event, context):
    """Handler Lambda - restituisce stock + ordine fornitore"""
    
    try:
        import time
        start_total = time.time()
        print("🚀 Inizio elaborazione stock...")
        
        # 1. Google Sheets
        service = get_google_sheets_service()
        if not service:
            raise Exception("Impossibile connettersi a Google Sheets")
        
        magazzino_attuale = read_sheet_data(service, SHEET_MAGAZZINO)
        
        arrivo_fornitore = read_sheet_data(service, SHEET_ARRIVO)
        
        # 2. Shopify
        sku_data = fetch_shopify_orders(days_back=GIORNI_ANALISI_VENDITE)
        
        weighted_avg = calculate_weighted_average(sku_data, days=GIORNI_ANALISI_VENDITE)
        
        backorders = {}  # Rimossi ordini arretrati per velocità
        
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
        
        total_time = time.time() - start_total
        print(f"✅ Completato: {len(stock_list)} SKU, {len(ordine_list)} da ordinare")
        print(f"⏱️  TEMPO TOTALE: {total_time:.2f}s")
        
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
            for item in data['ordine_fornitore'][:5]:
                print(f"  {item['sku']}: {item['quantita']} pz ({item['urgenza']})")
