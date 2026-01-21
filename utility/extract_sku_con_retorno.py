"""
Script per estrarre spedizioni GLS con "CON RETORNO" negli ultimi 30 giorni
e identificare gli SKU coinvolti nei resi.

Utile per calcolare gli SKU che tornano in stock ma non sono tracciati in Shopify.
"""
import requests
from bs4 import BeautifulSoup, Comment
from datetime import datetime, timedelta
import re
from collections import defaultdict
import pandas as pd
from pathlib import Path
import json
import sys
import os

# Aggiungi il path parent per importare config
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
# from config.settings import SHOPIFY_GRAPHQL_URL, SHOPIFY_ACCESS_TOKEN  # Non più necessario


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
        
        # Headers standard del browser
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'es,en-US;q=0.9,en;q=0.8,it-IT;q=0.7,it;q=0.6',
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
        print(f"🔐 Login a GLS Extranet come {username}...")
        
        # Prima richiesta per ottenere ViewState
        response = self.session.get(self.login_url)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        viewstate = {}
        for field in ['__VIEWSTATE', '__VIEWSTATEGENERATOR', '__EVENTVALIDATION']:
            input_field = soup.find('input', {'name': field})
            if input_field:
                viewstate[field] = input_field.get('value', '')
        
        # Dati del form di login (basati sul form reale nell'HTML)
        login_data = {
            '__VIEWSTATE': viewstate.get('__VIEWSTATE', ''),
            '__VIEWSTATEGENERATOR': viewstate.get('__VIEWSTATEGENERATOR', ''),
            '__EVENTVALIDATION': viewstate.get('__EVENTVALIDATION', ''),
            'usuario': username,
            'pass': password,
            'Button1.x': '50',
            'Button1.y': '10',
        }
        
        response = self.session.post(self.login_url, data=login_data, allow_redirects=True)
        
        # Verifica che il login sia riuscito controllando la URL finale e i cookies
        if response.status_code == 200 and 'login.aspx' not in response.url.lower():
            session_id = self.session.cookies.get('ASP.NET_SessionId')
            print(f"✅ Login riuscito! Session ID: {session_id}")
            return True
        else:
            print(f"❌ Login fallito - URL finale: {response.url}")
            return False
    
    def save_cookies(self, filename='gls_cookies.json'):
        """
        Salva i cookies della sessione corrente in un file
        
        Args:
            filename: Nome del file dove salvare i cookies
        """
        cookies_dict = dict(self.session.cookies)
        
        # In Lambda, usa /tmp per salvare i cookies (filesystem scrivibile)
        if os.environ.get('AWS_LAMBDA_FUNCTION_NAME'):
            filepath = Path('/tmp') / filename
        else:
            filepath = Path(__file__).parent / filename
        
        with open(filepath, 'w') as f:
            json.dump(cookies_dict, f, indent=2)
        
        print(f"💾 Cookies salvati in: {filepath}")
    
    @staticmethod
    def load_cookies(filename='gls_cookies.json'):
        """
        Carica i cookies da un file o da variabile d'ambiente
        
        Args:
            filename: Nome del file da cui caricare i cookies
            
        Returns:
            dict: Cookies caricati
        """
        # Prova prima da variabile d'ambiente (per Lambda)
        cookies_json = os.environ.get('GLS_COOKIES_JSON')
        if cookies_json:
            try:
                cookies = json.loads(cookies_json)
                print(f"📂 Cookies caricati da variabile d'ambiente GLS_COOKIES_JSON")
                return cookies
            except json.JSONDecodeError as e:
                print(f"⚠️ Errore parsing GLS_COOKIES_JSON: {e}")
        
        # Se non c'è variabile d'ambiente, carica da file
        # In Lambda, cerca prima in /tmp, poi nel path normale
        if os.environ.get('AWS_LAMBDA_FUNCTION_NAME'):
            filepath = Path('/tmp') / filename
            if not filepath.exists():
                # Se non esiste in /tmp, prova nel path normale (per compatibilità)
                filepath = Path(__file__).parent / filename
        else:
            filepath = Path(__file__).parent / filename
        
        if not filepath.exists():
            print(f"⚠️ File {filepath} non trovato")
            return {}
        
        with open(filepath, 'r') as f:
            cookies = json.load(f)
        
        print(f"📂 Cookies caricati da: {filepath}")
        return cookies
    
    def _get_viewstate(self):
        """
        Ottiene ViewState e EventValidation dalla pagina (necessari per ASP.NET)
        
        Returns:
            Dict con __VIEWSTATE, __VIEWSTATEGENERATOR, __EVENTVALIDATION
        """
        print("🔄 Caricamento pagina per ottenere ViewState...")
        response = self.session.get(self.search_url)
        
        # Controlla se siamo stati reindirizzati alla pagina di login
        if 'login.aspx' in response.url or 'Login' in response.text:
            print("🔐 Sessione scaduta, rifaccio login...")
            
            # Credenziali GLS (da variabili ambiente o default)
            username = os.environ.get("GLS_USERNAME", "586-4073")
            password = os.environ.get("GLS_PASSWORD", "Leneis586?!")
            
            if self.login(username, password):
                # Salva i nuovi cookies dopo il login
                self.save_cookies()
                # Riprova a caricare la pagina dopo il login
                response = self.session.get(self.search_url)
            else:
                raise Exception("Login GLS fallito")
        
        if response.status_code != 200:
            raise Exception(f"Errore caricamento pagina: {response.status_code}")
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        viewstate = {}
        for field in ['__VIEWSTATE', '__VIEWSTATEGENERATOR', '__EVENTVALIDATION']:
            input_field = soup.find('input', {'name': field})
            if input_field:
                viewstate[field] = input_field.get('value', '')
        
        print(f"✅ ViewState ottenuto")
        return viewstate
    
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
        # Ottieni ViewState
        viewstate = self._get_viewstate()
        
        # Prepara i dati del form (come nel tuo curl)
        # IMPORTANTE: per ImageButton non usare __EVENTTARGET, solo le coordinate .x e .y
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
            'entregadas': '',
            'noentregadas': '',
            'reembolso': '',
            'incidencias': '',
            'condac': '',
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
            # Salva response per debug anche in caso di errore
            if os.environ.get('AWS_LAMBDA_FUNCTION_NAME'):
                error_path = Path('/tmp') / 'extranet_response_error.html'
            else:
                error_path = Path('extranet_response_error.html')
            
            with open(error_path, 'w', encoding='utf-8') as f:
                f.write(response.text)
            print(f"💾 Response errore salvata in {error_path}")
            raise Exception(f"Errore ricerca: {response.status_code}")
        
        # Response in memoria - no salvataggio su file per velocità
        # with open('extranet_response.html', 'w', encoding='utf-8') as f:
        #     f.write(response.text)
        # print(f"💾 Response salvata in extranet_response.html")
        
        return response.text
    
    def parse_shipments(self, html_content):
        """
        Estrae le spedizioni dalla pagina HTML - versione ottimizzata
        Pre-filtra l'HTML per parsare solo righe con "CON RETORNO"
        
        Args:
            html_content: HTML della risposta
            
        Returns:
            pandas DataFrame con info spedizioni
        """
        import re
        
        # OTTIMIZZAZIONE: Estrai headers con regex (no BeautifulSoup)
        header_pattern = re.compile(r'<tr[^>]*class=["\']gv-header["\'][^>]*>(.*?)</tr>', re.DOTALL | re.IGNORECASE)
        header_match = header_pattern.search(html_content)
        
        if not header_match:
            print("⚠️ Header non trovato")
            return pd.DataFrame()
        
        # Estrai i nomi delle colonne dai <th>
        th_pattern = re.compile(r'<th[^>]*>(.*?)</th>', re.DOTALL | re.IGNORECASE)
        headers = []
        for th_match in th_pattern.finditer(header_match.group(1)):
            # Rimuovi tag HTML interni e strip
            header_text = re.sub(r'<[^>]+>', '', th_match.group(1)).strip()
            headers.append(header_text)
        
        print(f"✅ Headers trovati con regex: {len(headers)} colonne")
        
        # OTTIMIZZAZIONE: Pre-filtra righe HTML con "CON RETORNO" usando regex
        filtered_rows = []
        tr_pattern = re.compile(r'<tr[^>]*class=["\'](?:gv-row|gv-alternating)["\'][^>]*>.*?</tr>', re.DOTALL | re.IGNORECASE)
        
        for match in tr_pattern.finditer(html_content):
            row_html = match.group(0)
            if 'CON RETORNO' in row_html.upper():
                filtered_rows.append(row_html)
        
        print(f"🔍 Pre-filtro: {len(filtered_rows)} righe con 'CON RETORNO' (vs 723 totali)")
        
        if not filtered_rows:
            return pd.DataFrame()
        
        # OTTIMIZZAZIONE: Parsa SOLO le righe filtrate (no parsing completo)
        print(f"⏱️ Parsing {len(filtered_rows)} righe filtrate (no full HTML parse)")
        shipments = []
        
        for row_html in filtered_rows:
            try:
                # Pattern per estrarre celle <td>
                td_pattern = re.compile(r'<td[^>]*>(.*?)</td>', re.DOTALL | re.IGNORECASE)
                cells = []
                
                for td_match in td_pattern.finditer(row_html):
                    # Rimuovi tag HTML interni e strip
                    cell_text = re.sub(r'<[^>]+>', '', td_match.group(1)).strip()
                    cells.append(cell_text)
                
                if len(cells) != len(headers):
                    continue
                
                shipment = {}
                for i, cell in enumerate(cells):
                    shipment[headers[i]] = cell
                
                shipments.append(shipment)
            except:
                continue
        
        print(f"✅ Estratte {len(shipments)} spedizioni (parsing regex puro)")
        
        # Crea DataFrame
        df = pd.DataFrame(shipments)
        
        return df


def parse_sku_from_text(text):
    """
    Estrae gli SKU dal testo (Referencia, Destinatario, etc.)
    
    Args:
        text: Testo da analizzare
        
    Returns:
        List di tuple (sku, quantità)
    """
    if not text:
        return []
    
    skus = []
    
    # Pattern per SKU: MODELLO.TAGLIA.COLORE (es. SLIP.XS.BE, PER.L.BE)
    sku_pattern = r'(SLIP|PER)\.(XS|S|M|L|XL|XXL|XXXL)\.(BE|BL)'
    
    matches = re.findall(sku_pattern, text.upper())
    
    for match in matches:
        modelo, talla, color = match
        sku = f"{modelo}.{talla}.{color}"
        skus.append((sku, 1))  # Assume quantità 1 per SKU trovato
    
    return skus



def extract_sku_from_returns(df):
    """
    Estrae SKU dalle spedizioni con "CON RETORNO" direttamente dalla colonna 'observacion'
    
    Args:
        df: DataFrame delle spedizioni
        
    Returns:
        Dict con SKU e quantità totali
    """
    sku_totals = defaultdict(int)
    
    # Filtra spedizioni con "CON RETORNO"
    returns_df = df[df['retorno'].str.upper().str.contains('CON RETORNO', na=False)].copy()
    
    for idx, row in returns_df.iterrows():
        observacion = str(row.get('observacion', '')).strip()
        
        if not observacion:
            print(f"  ⚠️ Nessuna osservazione per spedizione {row.get('Expedicion', idx)}")
            continue
        
        # Parse SKU dalla osservazione
        skus_in_shipment = parse_skus_from_observacion(observacion)
        
        for sku, qty in skus_in_shipment.items():
            if sku:
                sku_totals[sku] += qty
    
    return dict(sku_totals)


def parse_skus_from_observacion(observacion):
    """
    Parse SKU e quantità dalla stringa osservacion
    
    Formati supportati:
    - "SLIP.S.BLx1" -> SKU: "SLIP.S.BL", QTY: 1
    - "SLIP.S.BLx2, SLIP.M.BLx1" -> multiple
    - "SLIP M .BE" -> SKU: "SLIP M .BE", QTY: 1 (senza x)
    
    Args:
        osservacion: Stringa con gli SKU
        
    Returns:
        Dict con SKU: quantità
    """
    skus = defaultdict(int)
    
    # Split per virgola
    items = [item.strip() for item in observacion.split(',') if item.strip()]
    
    for item in items:
        item = item.strip()
        
        # Cerca 'x' per separare SKU da quantità
        if 'x' in item.lower():
            # Trova l'ultimo 'x' (per casi come "SLIP.XL.BLx1")
            parts = item.lower().rsplit('x', 1)
            if len(parts) == 2:
                sku_part = parts[0].strip()
                qty_part = parts[1].strip()
                
                # Prova a convertire qty in int
                try:
                    qty = int(qty_part)
                except ValueError:
                    qty = 1
                
                # Pulisci SKU (rimuovi spazi extra, etc.)
                sku = sku_part.upper().replace(' ', '')
                
                # Normalizza SKU (corregge errori comuni)
                sku = normalize_sku(sku)
                
                # Valida SKU
                if is_valid_sku(sku):
                    skus[sku] = qty
        else:
            # Nessun 'x', assume qty=1
            sku = item.upper().replace(' ', '')
            # Normalizza SKU (corregge errori comuni)
            sku = normalize_sku(sku)
            # Valida SKU
            if is_valid_sku(sku):
                skus[sku] = 1
    
    return dict(skus)


def normalize_sku(sku):
    """
    Normalizza SKU correggendo errori comuni
    
    Args:
        sku: SKU da normalizzare
        
    Returns:
        str: SKU normalizzato
    """
    if not sku:
        return sku
    
    # Correggi pattern SLIPM -> SLIP.M, SLIPS -> SLIP.S, ecc.
    import re
    
    # Pattern: SLIP seguito direttamente da taglia (senza punto)
    # Es: SLIPM.BE -> SLIP.M.BE, SLIPXL.BL -> SLIP.XL.BL
    sizes = ['XS', 'S', 'M', 'L', 'XL', 'XXL', 'XXXL']
    for size in sizes:
        # Pattern: SLIP + taglia senza punto prima
        pattern = f'SLIP{size}\\.'
        if re.search(pattern, sku):
            sku = re.sub(pattern, f'SLIP.{size}.', sku)
            break
    
    # Stesso per PER
    for size in sizes:
        pattern = f'PER{size}\\.'
        if re.search(pattern, sku):
            sku = re.sub(pattern, f'PER.{size}.', sku)
            break
    
    return sku


def is_valid_sku(sku):
    """
    Valida se una stringa è un SKU valido
    
    Args:
        sku: Stringa da validare
        
    Returns:
        bool: True se valido
    """
    if not sku:
        return False
    
    # Deve contenere SLIP o PER
    if not ('SLIP' in sku or 'PER' in sku):
        return False
    
    # Non deve essere troppo lungo (max 20 caratteri)
    if len(sku) > 20:
        return False
    
    # Non deve contenere caratteri strani
    if any(char in sku for char in ['-', ':', ';', '(', ')', '[', ']', '{', '}', '|', '\\', '/', '?', '<', '>', '!', '@', '#', '$', '%', '^', '&', '*', '+', '=']):
        return False
    
    return True


def main():
    """
    Script principale per estrarre SKU da spedizioni GLS con "CON RETORNO"
    """
    print("🚀 Estrazione SKU da spedizioni GLS con 'CON RETORNO'\n")
    
    # === CONFIGURAZIONE ===
    use_login = False  # True = login con credenziali, False = usa cookies salvati
    days_back = 30  # Giorni indietro per la ricerca spedizioni
    
    # Date: ultimi N giorni
    today = datetime.now()
    date_from = (today - timedelta(days=days_back)).strftime("%d/%m/%Y")
    date_to = today.strftime("%d/%m/%Y")
    
    print(f"📅 Periodo: {date_from} - {date_to}")
    
    if use_login:
        # Login con credenziali
        username = os.environ.get("GLS_USERNAME", "586-4073")
        password = os.environ.get("GLS_PASSWORD", "Leneis586?!")
        
        if not username or not password:
            print("❌ Imposta le variabili d'ambiente GLS_USERNAME e GLS_PASSWORD")
            print("Es: export GLS_USERNAME='tuo_username' && export GLS_PASSWORD='tua_password'")
            return
        
        client = GLSExtranetClient()
        if not client.login(username, password):
            print("❌ Impossibile procedere senza login")
            return
        
        # Salva cookies per uso futuro
        client.save_cookies()
    
    else:
        # Prova a caricare cookies salvati
        cookies = GLSExtranetClient.load_cookies()
        
        if cookies:
            client = GLSExtranetClient(cookies)
        else:
            print("❌ Nessun cookie salvato trovato")
            print("💡 Esegui prima con use_login=True per salvare i cookies")
            return
    
    try:
        # Cerca spedizioni
        html = client.search_shipments(date_from, date_to)
        
        # Parse spedizioni
        df = client.parse_shipments(html)
        
        if df.empty:
            print("\n⚠️ Nessuna spedizione trovata")
            return
        
        print(f"\n✅ Trovate {len(df)} spedizioni totali")
        
        # Estrai SKU da spedizioni con "CON RETORNO"
        sku_returns = extract_sku_from_returns(df)
        
        if sku_returns:
            for sku, qty in sorted(sku_returns.items(), key=lambda x: x[1], reverse=True):
                print(f"{sku}: {qty}")
            
        else:
            print("\n⚠️ Nessun SKU trovato in spedizioni con 'CON RETORNO'")
    
    except Exception as e:
        print(f"\n❌ Errore: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()