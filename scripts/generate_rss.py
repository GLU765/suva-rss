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
DATA_FILE = ROOT / "data" / "fiches.json"
OUT_DIR   = ROOT / "docs"
OUT_FILE  = OUT_DIR / "feed.xml"

# ⚠️  Remplacez VOTRE_USERNAME par votre nom GitHub
GITHUB_USERNAME = "GLU765"
GITHUB_REPO     = "suva-rss"

FEED_TITLE       = "Veille SUVA — Polluants de la Construction"
FEED_LINK        = f"https://{GITHUB_USERNAME}.github.io/{GITHUB_REPO}/feed.xml"
FEED_DESCRIPTION = "Suivi automatique des fiches techniques SUVA : amiante, HAP, PCB, métaux lourds et laines minérales."
FEED_LANGUAGE    = "fr-CH"

ICONS = {
    "Amiante":          "🔴",
    "HAP":              "🟠",
    "PCB":              "🟠",
    "Métaux lourds":    "🟡",
    "Laines minérales": "🟡",
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
    if statut == "supprimé":          return "🗑️ Fiche supprimée"
    if statut == "injoignable":       return "🔌 Site injoignable"
    if statut == "timeout":           return "⏱️ Timeout"
    return f"❓ {statut}"

def main():
    now_utc = datetime.now(timezone.utc)
    now_rfc = now_utc.strftime("%a, %d %b %Y %H:%M:%S +0000")
    print(f"\n🚀 Génération du flux RSS — {now_utc.strftime('%d.%m.%Y %H:%M UTC')}\n")

    with open(DATA_FILE, encoding="utf-8") as f:
        fiches = json.load(f)
    print(f"📋 {len(fiches)} fiches chargées\n")

    rss     = ET.Element("rss", version="2.0")
    channel = ET.SubElement(rss, "channel")
    ET.SubElement(channel, "title").text         = FEED_TITLE
    ET.SubElement(channel, "link").text          = FEED_LINK
    ET.SubElement(channel, "description").text   = FEED_DESCRIPTION
    ET.SubElement(channel, "language").text      = FEED_LANGUAGE
    ET.SubElement(channel, "lastBuildDate").text = now_rfc
    ET.SubElement(channel, "ttl").text           = "10080"

    compteurs = {}

    for fiche in fiches:
        if fiche.get("statut") == "supprimé":
            statut_http, url_finale = "supprimé", ""
        else:
            print(f"  🔍 {fiche['numero']:12s} … ", end="", flush=True)
            statut_http, url_finale = verifier_url(fiche.get("url", ""))
            print(statut_label(statut_http))

        cat = fiche["categorie"]
        compteurs[cat] = compteurs.get(cat, 0) + 1

        icon = ICONS.get(cat, "📄")
        titre = f"{icon} [{cat}] N°{fiche['numero']} — {fiche['titre']} | {statut_label(statut_http)}"

        date_affichee = fiche.get("date_maj", "inconnue")
        try:
            d = datetime.strptime(date_affichee, "%Y-%m-%d")
            date_affichee = d.strftime("%d.%m.%Y")
        except Exception:
            pass

        description = (
            f"Numéro : {fiche['numero']} | "
            f"Catégorie : {cat} | "
            f"Statut : {statut_label(statut_http)} | "
            f"Dernière mise à jour : {date_affichee} | "
            f"{fiche.get('description', '')}"
        )

        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text       = titre
        ET.SubElement(item, "link").text        = url_finale or fiche.get("url", "")
        ET.SubElement(item, "description").text = description
        ET.SubElement(item, "category").text    = cat
        ET.SubElement(item, "pubDate").text     = now_rfc
        ET.SubElement(item, "guid").text        = fiche["id"]

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ET.indent(rss)
    ET.ElementTree(rss).write(OUT_FILE, encoding="UTF-8", xml_declaration=True)

    print(f"\n✅ Flux généré : {OUT_FILE.name}")
    print(f"\n📊 Fiches par catégorie :")
    for cat, nb in sorted(compteurs.items()):
        print(f"   {ICONS.get(cat,'📄')} {cat:<20} : {nb}")
    print(f"   TOTAL                  : {sum(compteurs.values())}")

if __name__ == "__main__":
    main()
