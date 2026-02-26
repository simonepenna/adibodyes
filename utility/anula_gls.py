"""
Script per gestire spedizioni GLS manualmente.

Comandi:
  lookup <referenza> [GLS_UID]   Cerca spedizione per referenza ordine (es: ES10085 o #ES10085)
  <albaran>  [GLS_UID]           Annulla spedizione per numero albaran (es: 10085)

Esempi:
  .venv/bin/python anula_gls.py lookup ES10085 cbfbcd8f-xxxx-xxxx-xxxx-xxxxxxxxxxxx
  .venv/bin/python anula_gls.py 10085 cbfbcd8f-xxxx-xxxx-xxxx-xxxxxxxxxxxx
"""
import sys
import os
import requests
import urllib3
import xml.etree.ElementTree as ET

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Carica manualmente il .env se presente
env_file = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(env_file):
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

GLS_SOAP_ENDPOINT     = "https://wsclientes.asmred.com/b2b.asmx"
GLS_CUSTOMER_ENDPOINT = "https://ws-customer.gls-spain.es/b2b.asmx"


# ---------------------------------------------------------------------------
# LOOKUP — GetExpCli: cerca spedizione per referenza cliente
# ---------------------------------------------------------------------------
def lookup(referenza: str):
    GLS_UID = os.environ.get("GLS_UID")
    # normalizza: ES10085 → #ES10085
    if not referenza.startswith("#"):
        referenza = "#" + referenza

    soap_xml = f"""<?xml version="1.0" encoding="utf-8"?>
<soap12:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                 xmlns:xsd="http://www.w3.org/2001/XMLSchema"
                 xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">
  <soap12:Body>
    <GetExpCli xmlns="http://www.asmred.com/">
      <codigo>{referenza}</codigo>
      <uid>{GLS_UID}</uid>
    </GetExpCli>
  </soap12:Body>
</soap12:Envelope>"""

    print(f"🔍 Lookup referenza: {referenza}")
    response = requests.post(
        GLS_CUSTOMER_ENDPOINT,
        data=soap_xml.encode("utf-8"),
        headers={
            "Content-Type": "text/xml; charset=UTF-8",
            "SOAPAction": "http://www.asmred.com/GetExpCli"
        },
        timeout=30,
        verify=False
    )

    print(f"HTTP {response.status_code}")
    print(f"Response: {response.text[:2000]}")

    if not response.ok:
        print(f"❌ HTTP error: {response.status_code}")
        return

    try:
        root = ET.fromstring(response.text)
        ns = {"asm": "http://www.asmred.com/"}
        result_elem = root.find(".//asm:GetExpCliResult", ns)
        if result_elem is None:
            result_elem = root.find(".//GetExpCliResult")
        if result_elem is None:
            print("❌ GetExpCliResult non trovato nella risposta")
            return

        exp_elem = (
            result_elem.find(".//{http://www.asmred.com/}exp") or
            result_elem.find(".//exp")
        )
        if exp_elem is None and result_elem.text and result_elem.text.strip():
            inner = ET.fromstring(result_elem.text.strip())
            exp_elem = inner.find(".//{http://www.asmred.com/}exp") or inner.find(".//exp")

        if exp_elem is None:
            print(f"⚠️  Nessuna spedizione trovata per referenza {referenza}")
            return

        print("\n📦 Spedizione trovata:")
        for child in exp_elem:
            tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
            print(f"   {tag}: {child.text}")

        expedicion = (
            exp_elem.findtext("{http://www.asmred.com/}expedicion") or
            exp_elem.findtext("expedicion")
        )
        if expedicion:
            print(f"\n✅ Tracking (expedicion): {expedicion.strip()}")
            albaran = referenza.replace("#ES", "").replace("#", "")
            print(f"ℹ️  Per annullare usa: .venv/bin/python anula_gls.py {albaran} <GLS_UID>")

    except ET.ParseError as e:
        print(f"❌ Errore parsing XML: {e}")


# ---------------------------------------------------------------------------
# ANULA — cancella spedizione per albaran
# ---------------------------------------------------------------------------
def anula(albaran: str):
    GLS_UID = os.environ.get("GLS_UID")
    soap_xml = f"""<?xml version="1.0" encoding="utf-8"?>
<soap12:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                 xmlns:xsd="http://www.w3.org/2001/XMLSchema"
                 xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">
  <soap12:Body>
    <Anula xmlns="http://www.asmred.com/">
      <docIn>
        <Servicios uidcliente="{GLS_UID}">
          <Envio>
            <Albaran>{albaran}</Albaran>
          </Envio>
        </Servicios>
      </docIn>
    </Anula>
  </soap12:Body>
</soap12:Envelope>"""

    print(f"🗑️  Annullamento albaran: {albaran}")
    response = requests.post(
        GLS_SOAP_ENDPOINT,
        data=soap_xml.encode("utf-8"),
        headers={
            "Content-Type": "text/xml; charset=UTF-8",
            "SOAPAction": "http://www.asmred.com/Anula"
        },
        timeout=30,
        verify=False
    )

    print(f"HTTP {response.status_code}")
    print(f"Response: {response.text}")

    if not response.ok:
        print(f"❌ HTTP error: {response.status_code}")
        return

    try:
        root = ET.fromstring(response.text)
        resultado = (
            root.find(".//{http://www.asmred.com/}Resultado") or
            root.find(".//Resultado")
        )
        if resultado is not None:
            code = resultado.get("return", "0")
            msg  = resultado.text or ""
            if code == "0":
                print(f"✅ Spedizione {albaran} annullata con successo")
            elif code == "-1":
                # -1 = già cancellata o non trovata
                print(f"⚠️  GLS -1: {msg} (spedizione già cancellata o albaran non trovato)")
            else:
                print(f"❌ Errore GLS {code}: {msg}")
        else:
            print("✅ Annullamento completato (nessun tag Resultado nella risposta)")
    except ET.ParseError as e:
        print(f"❌ Errore parsing XML: {e}")


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "lookup":
        if len(sys.argv) < 3:
            print("Uso: .venv/bin/python anula_gls.py lookup <referenza> [GLS_UID]")
            sys.exit(1)
        if len(sys.argv) >= 4:
            os.environ["GLS_UID"] = sys.argv[3]
        if not os.environ.get("GLS_UID"):
            print("❌ GLS_UID mancante. Passalo come terzo argomento.")
            sys.exit(1)
        lookup(sys.argv[2])
    else:
        # cmd è il numero albaran
        albaran = cmd
        if len(sys.argv) >= 3:
            os.environ["GLS_UID"] = sys.argv[2]
        if not os.environ.get("GLS_UID"):
            print("❌ GLS_UID mancante. Passalo come secondo argomento:")
            print("   .venv/bin/python anula_gls.py <albaran> <GLS_UID>")
            sys.exit(1)
        anula(albaran)
