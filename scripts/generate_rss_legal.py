#!/usr/bin/env python3
import json
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

try:
    import requests
    REQUESTS_OK = True
except ImportError:
    REQUESTS_OK = False

ROOT      = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "data" / "legislation.json"
OUT_DIR   = ROOT / "docs"
OUT_FILE  = OUT_DIR / "feed-legal.xml"

# ⚠️  Remplacez GLU765 par votre nom GitHub
GITHUB_USERNAME = "GLU765"
GITHUB_REPO     = "suva-rss"

FEED_TITLE       = "Veille Légale — Polluants de la Construction (CH)"
FEED_LINK        = f"https://{GITHUB_USERNAME}.github.io/{GITHUB_REPO}/feed-legal.xml"
FEED_DESCRIPTION = (
    "Surveillance de la législation suisse sur les polluants du bâtiment : "
    "droit fédéral (OTConst, LAA, OLED...), législation cantonale "
    "(VD, GE, VS, FR, NE, BE, JU), normes CFST/ASCA/SIA et jurisprudence TF."
)
FEED_LANGUAGE = "fr-CH"

TYPE_ICONS = {
    "Ordonnance fédérale": "⚖️",
    "Loi fédérale":        "🏛️",
    "Loi cantonale":       "🏠",
    "Règlement cantonal":  "📋",
    "Directive cantonale": "📌",
    "Directive / Norme":   "📐",
    "Flux RSS natif":      "📡",
    "Jurisprudence":       "⚖️",
}

CANTON_FLAGS = {
    "VD": "🔵 VD",
    "GE": "🟡 GE",
    "VS": "🔴 VS",
    "FR": "🟤 FR",
    "NE": "🟢 NE",
    "BE": "🟡 BE",
    "JU": "🔴 JU",
    "":   "🇨🇭",
}

def verifier_url(url):
    if not url:
        return "supprimé", ""
    if not REQUESTS_OK:
        return "inconnu", url
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        r = requests.get(url, timeout=15, allow_redirects=True, headers=headers)
        if r.status_code == 200:
            return "actif", r.url
        elif r.status_code in (301, 302, 307, 308):
            return "redirigé", r.url
        elif r.status_code == 404:
            return "inactif", url
        elif r.status_code == 403:
            return "actif*", url
        else:
            return f"inconnu ({r.status_code})", url
    except requests.exceptions.Timeout:
        return "timeout", url
    except requests.exceptions.ConnectionError:
        return "injoignable", url
    except Exception:
        return "erreur", url

def statut_label(statut):
    if statut.startswith("actif"):    return "✅ Actif"
    if statut.startswith("redirigé"): return "↪️ Redirigé"
    if statut == "inactif":           return "❌ Lien inactif"
    if statut == "supprimé":          return "🗑️ Supprimé"
    if statut == "injoignable":       return "🔌 Injoignable"
    if statut == "timeout":           return "⏱️ Timeout"
    return f"❓ {statut}"

def main():
    now_utc = datetime.now(timezone.utc)
    now_rfc = now_utc.strftime("%a, %d %b %Y %H:%M:%S +0000")
    print(f"\n⚖️  Génération flux RSS Veille Légale — {now_utc.strftime('%d.%m.%Y %H:%M UTC')}\n")

    with open(DATA_FILE, encoding="utf-8") as f:
        textes = json.load(f)
    print(f"📋 {len(textes)} textes légaux chargés\n")

    rss     = ET.Element("rss", version="2.0")
    channel = ET.SubElement(rss, "channel")
    ET.SubElement(channel, "title").text         = FEED_TITLE
    ET.SubElement(channel, "link").text          = FEED_LINK
    ET.SubElement(channel, "description").text   = FEED_DESCRIPTION
    ET.SubElement(channel, "language").text      = FEED_LANGUAGE
    ET.SubElement(channel, "lastBuildDate").text = now_rfc
    ET.SubElement(channel, "ttl").text           = "10080"

    compteurs = {}

    for t in textes:
        print(f"  🔍 {t['reference'][:30]:30s} … ", end="", flush=True)
        statut_http, url_finale = verifier_url(t.get("url", ""))
        print(statut_label(statut_http))

        niveau = t.get("niveau", "Autre")
        compteurs[niveau] = compteurs.get(niveau, 0) + 1

        icon  = TYPE_ICONS.get(t["type"], "📄")
        flag  = CANTON_FLAGS.get(t.get("canton", ""), "🇨🇭")
        polluants_str = ", ".join(t.get("polluants", [])) or "Général"

        titre = (
            f"{icon} {flag} [{t['type']}] "
            f"{t['reference']} — {t['titre']} "
            f"| {statut_label(statut_http)}"
        )

        date_affichee = t.get("date_maj", "inconnue")
        try:
            d = datetime.strptime(date_affichee, "%Y-%m-%d")
            date_affichee = d.strftime("%d.%m.%Y")
        except Exception:
            pass

        rss_info = f"Flux RSS natif : {t['url_rss']} | " if t.get("url_rss") else ""

        description = (
            f"Référence : {t['reference']} | "
            f"Type : {t['type']} | "
            f"Niveau : {t['niveau']}"
            + (f" — Canton : {t['canton']}" if t.get('canton') else "") +
            f" | Polluants : {polluants_str} | "
            f"Statut : {statut_label(statut_http)} | "
            f"Dernière mise à jour connue : {date_affichee} | "
            f"{rss_info}"
            f"{t.get('description', '')}"
        )

        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text       = titre
        ET.SubElement(item, "link").text        = url_finale or t.get("url", "")
        ET.SubElement(item, "description").text = description
        ET.SubElement(item, "category").text    = t["type"]
        ET.SubElement(item, "pubDate").text     = now_rfc
        ET.SubElement(item, "guid").text        = t["id"]

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ET.indent(rss)
    ET.ElementTree(rss).write(OUT_FILE, encoding="UTF-8", xml_declaration=True)

    print(f"\n✅ Flux légal généré : {OUT_FILE.name}")
    print(f"\n📊 Textes par niveau :")
    for niveau, nb in sorted(compteurs.items()):
        print(f"   {'⚖️' if 'Fédéral' in niveau else '🏠'} {niveau:<20} : {nb}")
    print(f"   TOTAL                  : {sum(compteurs.values())}")

if __name__ == "__main__":
    main()
