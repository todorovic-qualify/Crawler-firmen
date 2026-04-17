"""
KI Vertriebs-Research-Agent für B2B.

Input:  Website-URL + Google-Daten
Output: strukturierte JSON-Analyse (6-Schritte-Framework)

Nutzt Claude API für die KI-Analyse.
Fallback auf regel-basierte Analyse wenn kein API-Key vorhanden.
"""
from __future__ import annotations

import json
import os
import re
from typing import Optional
from urllib.parse import urljoin, quote_plus

from loguru import logger

from crawler.utils.http_utils import get, erstelle_client

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = "claude-sonnet-4-6"

# Unterseiten die zusätzlich gecrawlt werden (Priorität absteigend)
_CRAWL_PFADE = [
    "/impressum", "/kontakt", "/contact",
    "/about", "/ueber-uns", "/team",
    "/leistungen", "/services", "/angebot", "/preise",
]

# Pfade die nie gecrawlt werden sollen
_IGNORE_TEILE = [
    "wp-content", "wp-admin", ".jpg", ".png", ".pdf", ".svg",
    "#", "javascript:", "mailto:", "tel:", "datenschutz", "agb",
    "sitemap", "feed", "rss", "login", "cart", "shop/",
]


# ── Öffentliche Hauptfunktion ─────────────────────────────────────────────────

def analysiere(
    website: Optional[str],
    google_daten: Optional[dict],
    lead_kontext: Optional[dict] = None,
) -> dict:
    """
    Führt die vollständige KI-Verkaufsanalyse durch.

    Args:
        website:       URL der Unternehmenswebsite (oder None)
        google_daten:  Dict mit Google-Bewertungsdaten (oder None)
        lead_kontext:  Optionale Lead-Stammdaten aus der DB (name, kategorie, stadt, …)

    Returns:
        Strukturiertes JSON-Dict mit 6-Schritte-Analyse
    """
    lead_kontext = lead_kontext or {}
    google_daten = google_daten or {}

    # ── Schritt 1: Website deep crawlen ──────────────────────────────────────
    website_inhalte: dict[str, str] = {}
    if website:
        website_inhalte = _deep_crawl(website)
        logger.info(f"Deep Crawl abgeschlossen: {len(website_inhalte)} Seiten")

    # ── Schritt 2: Google-Bewertungen abrufen (falls nicht übergeben) ─────────
    if not google_daten and lead_kontext.get("name"):
        google_daten = _scrape_google_bewertungen(
            name=lead_kontext.get("name", ""),
            stadt=lead_kontext.get("stadt", ""),
        )

    # ── Schritt 3: Kontext kompilieren ────────────────────────────────────────
    kontext = _baue_kontext(lead_kontext, website_inhalte, google_daten)

    # ── Schritt 4: KI-Analyse ─────────────────────────────────────────────────
    if ANTHROPIC_API_KEY:
        ergebnis = _claude_analyse(kontext, lead_kontext)
    else:
        logger.warning("ANTHROPIC_API_KEY nicht gesetzt – Fallback-Analyse")
        ergebnis = _fallback_analyse(lead_kontext, website_inhalte)

    # Metadaten anhängen
    ergebnis["_gecrawlte_seiten"] = list(website_inhalte.keys())
    ergebnis["_google_daten_vorhanden"] = bool(google_daten)

    return ergebnis


# ── Website Deep Crawl ────────────────────────────────────────────────────────

def _deep_crawl(url: str) -> dict[str, str]:
    """Crawlt Website (Startseite + bis zu 8 Unterseiten) und gibt Texte zurück."""
    if not url.startswith("http"):
        url = "https://" + url
    basis = url.rstrip("/")

    seiten: dict[str, str] = {}
    gecrawlt: set[str] = set()

    with erstelle_client() as client:
        # Startseite
        html = _lade_seite(basis, client)
        if not html:
            return seiten

        seiten["startseite"] = _html_zu_text(html)
        gecrawlt.add(basis)

        # Prioritätspfade
        for pfad in _CRAWL_PFADE:
            if len(gecrawlt) >= 9:
                break
            ziel = urljoin(basis, pfad)
            if ziel in gecrawlt:
                continue
            sub_html = _lade_seite(ziel, client)
            if sub_html:
                key = pfad.strip("/").replace("-", "_")
                seiten[key] = _html_zu_text(sub_html)
                gecrawlt.add(ziel)

        # Weitere interne Links von Startseite
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        for a in soup.find_all("a", href=True):
            if len(gecrawlt) >= 12:
                break
            href = a["href"]
            if not href.startswith("/") or len(href) < 2:
                continue
            if any(t in href.lower() for t in _IGNORE_TEILE):
                continue
            ziel = urljoin(basis, href)
            if ziel in gecrawlt:
                continue
            sub_html = _lade_seite(ziel, client)
            if sub_html:
                key = href.strip("/").replace("/", "_")[:25]
                seiten[key] = _html_zu_text(sub_html)
                gecrawlt.add(ziel)

    return seiten


# ── Google-Bewertungen scrapen ────────────────────────────────────────────────

def _scrape_google_bewertungen(name: str, stadt: str) -> dict:
    """
    Scrapt Google-Suchergebnisse für Bewertungs-Snippets.
    Best-effort – kein API-Key nötig.
    """
    suchbegriff = f"{name} {stadt} Bewertungen".strip()
    url = f"https://www.google.com/search?q={quote_plus(suchbegriff)}&hl=de"

    try:
        with erstelle_client() as client:
            resp = client.get(
                url,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/124.0.0.0 Safari/537.36"
                    ),
                    "Accept-Language": "de-DE,de;q=0.9",
                },
                follow_redirects=True,
                timeout=10,
            )
        if resp.status_code != 200:
            return {}

        text = _html_zu_text(resp.text)

        rating: Optional[float] = None
        count: Optional[int] = None

        m = re.search(r"(\d[,\.]\d)\s*(?:★|Sterne?|von 5)", text)
        if m:
            rating = float(m.group(1).replace(",", "."))

        m2 = re.search(r"(\d[\d.]+)\s*(?:Bewertungen|Rezensionen|Google-Rezensionen)", text)
        if m2:
            count = int(m2.group(1).replace(".", ""))

        return {
            "bewertung": rating,
            "anzahl": count,
            "kontext_text": text[:3000],
        }

    except Exception as e:
        logger.debug(f"Google-Scraping fehlgeschlagen: {e}")
        return {}


# ── Kontext-Builder ───────────────────────────────────────────────────────────

def _baue_kontext(lead: dict, seiten: dict, google: dict) -> str:
    """Kompiliert alle Datenquellen zu einem strukturierten Kontext-String."""
    teile: list[str] = []

    # Stammdaten
    if lead:
        teile.append("=== UNTERNEHMEN ===")
        teile.append(f"Name: {lead.get('name', '—')}")
        teile.append(f"Branche/Kategorie: {lead.get('kategorie', '—')}")
        teile.append(f"Stadt: {lead.get('stadt', '—')}")
        teile.append(f"Webseite: {lead.get('webseite', 'keine')}")
        teile.append(f"Telefon vorhanden: {'ja' if lead.get('hat_telefon') else 'nein'}")
        teile.append(f"E-Mail vorhanden: {'ja' if lead.get('hat_email') else 'nein'}")
        if lead.get("webseite_qualitaet_score") is not None:
            teile.append(f"Website-Qualitätsscore: {lead['webseite_qualitaet_score']}/100")
        for flag, label in [
            ("cta_gefunden", "CTA vorhanden"),
            ("kontaktformular_gefunden", "Kontaktformular"),
            ("buchungs_signal_gefunden", "Buchungssystem"),
            ("whatsapp_gefunden", "WhatsApp-Link"),
            ("sieht_veraltet_aus", "Sieht veraltet aus"),
        ]:
            if flag in lead:
                teile.append(f"{label}: {'ja' if lead[flag] else 'nein'}")

    # Google-Bewertungen
    if google:
        teile.append("\n=== GOOGLE-BEWERTUNGEN ===")
        if google.get("bewertung"):
            teile.append(f"Durchschnitt: {google['bewertung']}/5")
        if google.get("anzahl"):
            teile.append(f"Anzahl: {google['anzahl']} Bewertungen")
        if google.get("kontext_text"):
            teile.append(f"Google-Kontext (Ausschnitt):\n{google['kontext_text'][:2000]}")

    # Website-Inhalte
    if seiten:
        teile.append("\n=== WEBSITE-INHALTE ===")
        for name, text in list(seiten.items())[:6]:
            if text and len(text) > 40:
                teile.append(f"\n--- {name} ---")
                teile.append(text[:1500])

    return "\n".join(teile)


# ── Claude KI-Analyse ─────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """\
Du bist ein Elite-Vertriebler und B2B-Sales-Coach für Qualify AI.

Qualify AI bietet folgende Leistungen an:
- KI Telefonassistent (24/7 Anrufe annehmen, qualifizieren, Termine buchen)
- Automatisierte Leadqualifizierung
- Webseiten & Landingpages
- Angebots- & Rechnungserstellung (automatisiert)
- CRM / Prozessautomatisierung
- Follow-Up & Nachfass-Automationen
- WhatsApp / E-Mail Automatisierung

Antworte IMMER auf Deutsch und IMMER als valides JSON mit exakt dieser Struktur:
{
  "zusammenfassung": "4-5 prägnante Sätze über das Unternehmen",
  "painpoints": {
    "marketing_leadgewinnung": ["konkreter Painpoint", "..."],
    "vertrieb_abschluss": ["..."],
    "prozesse_zeitfresser": ["..."],
    "digitalisierung_automatisierung": ["..."],
    "kundenkommunikation": ["..."]
  },
  "passende_loesungen": [
    {"leistung": "Name der Leistung", "begruendung": "Warum genau diese Leistung"}
  ],
  "verkaufsansaetze": [
    {
      "problem": "konkretes emotionales Problem",
      "folge": "was das kostet / anrichtet",
      "loesung": "wie unsere Leistung hilft"
    }
  ],
  "hooks": ["kurzer personalisierter Einstieg für Cold Call / Nachricht"],
  "google_bewertungen_analyse": "Muster in Bewertungen (z.B. häufige Kritik/Lob) oder null",
  "umsatzpotenzial": "HOCH|MITTEL|NIEDRIG",
  "top_einstiegsangebot": "Das eine konkrete Angebot mit dem du anfangen würdest"
}

REGELN:
- Keine generischen Aussagen – alles muss konkret auf diese Branche passen
- Denke: Was verliert dieses Unternehmen täglich an Geld/Kunden?
- Painpoints sollen sich anfühlen als kämen sie von jemandem der das Unternehmen kennt
- 3-5 Verkaufsansätze, 2 Hooks
- Antwort NUR als JSON, kein Text drumherum
"""


def _claude_analyse(kontext: str, lead: dict) -> dict:
    """Ruft Claude API auf und gibt geparste JSON-Analyse zurück."""
    import anthropic

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    user_msg = (
        f"Analysiere dieses Unternehmen vollständig:\n\n{kontext}\n\n"
        "Erstelle jetzt die strukturierte JSON-Analyse. "
        "Sei konkret und branchenspezifisch – keine Floskeln."
    )

    try:
        message = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=4096,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_msg}],
        )
        raw = message.content[0].text

        # JSON aus Antwort extrahieren (robust gegen Markdown-Blöcke)
        m = re.search(r"\{[\s\S]*\}", raw)
        if m:
            return json.loads(m.group())
        return json.loads(raw)

    except json.JSONDecodeError as e:
        logger.warning(f"Claude-Antwort kein valides JSON: {e}")
        return {"fehler": "JSON-Parsing fehlgeschlagen", "raw_antwort": raw[:500]}
    except Exception as e:
        logger.error(f"Claude API Fehler: {e}")
        return {"fehler": str(e)}


# ── Regel-basierter Fallback ──────────────────────────────────────────────────

def _fallback_analyse(lead: dict, seiten: dict) -> dict:
    """Einfache regel-basierte Analyse wenn kein ANTHROPIC_API_KEY gesetzt ist."""
    name = lead.get("name", "Dieses Unternehmen")
    kategorie = lead.get("kategorie", "")
    hat_website = bool(lead.get("webseite") or seiten)
    qualitaet = lead.get("webseite_qualitaet_score", 0)

    painpoints: dict[str, list[str]] = {
        "marketing_leadgewinnung": [],
        "vertrieb_abschluss": [],
        "prozesse_zeitfresser": [],
        "digitalisierung_automatisierung": [],
        "kundenkommunikation": [],
    }
    loesungen: list[dict] = []
    ansaetze: list[dict] = []

    if not hat_website:
        painpoints["marketing_leadgewinnung"].append(
            "Kein Online-Auftritt – potenzielle Kunden finden das Unternehmen nicht"
        )
        painpoints["digitalisierung_automatisierung"].append(
            "Komplett offline – kein digitaler Vertriebskanal vorhanden"
        )
        loesungen.append({
            "leistung": "Webseite & Landingpage",
            "begruendung": "Ohne Webseite ist das Unternehmen für Suchende unsichtbar",
        })
    elif qualitaet < 40:
        painpoints["marketing_leadgewinnung"].append(
            "Veraltete Website schreckt Besucher ab bevor sie Kontakt aufnehmen"
        )
        loesungen.append({
            "leistung": "Website-Relaunch",
            "begruendung": f"Website-Qualitätsscore von {qualitaet}/100 zeigt klaren Handlungsbedarf",
        })

    if not lead.get("cta_gefunden"):
        painpoints["vertrieb_abschluss"].append(
            "Kein klarer Call-to-Action – Besucher wissen nicht wie sie anfragen sollen"
        )

    if not lead.get("buchungs_signal_gefunden") and not lead.get("kontaktformular_gefunden"):
        painpoints["prozesse_zeitfresser"].append(
            "Buchungen laufen manuell über Telefon – zeitaufwendig und fehleranfällig"
        )
        loesungen.append({
            "leistung": "Online-Buchungssystem / CRM-Automatisierung",
            "begruendung": "Manuelle Terminvergabe bindet täglich mehrere Stunden",
        })

    if not lead.get("whatsapp_gefunden"):
        painpoints["kundenkommunikation"].append(
            "WhatsApp nicht genutzt – Kunden bevorzugen Messaging für schnelle Rückfragen"
        )
        loesungen.append({
            "leistung": "WhatsApp-Automatisierung",
            "begruendung": "WhatsApp-Kanal erschließt den bevorzugten Kommunikationsweg vieler Kunden",
        })

    loesungen.append({
        "leistung": "KI Telefonassistent",
        "begruendung": "Verpasste Anrufe = verlorene Aufträge – 24/7 Erreichbarkeit ohne Personalaufwand",
    })

    ansaetze.append({
        "problem": "Anrufe die niemand entgegennimmt werden direkt zur Konkurrenz weitergeleitet",
        "folge": "Jeden Monat gehen so mehrere Aufträge verloren ohne dass es auffällt",
        "loesung": "Unser KI-Telefonassistent nimmt jeden Anruf sofort entgegen und qualifiziert automatisch",
    })
    ansaetze.append({
        "problem": "Anfragen die per E-Mail oder Formular kommen werden oft stundenlang nicht beantwortet",
        "folge": "Studien zeigen: wer nicht in 5 Minuten antwortet verliert 80% der Interessenten",
        "loesung": "Automatisches Follow-Up antwortet sofort und hält den Lead warm bis der Vertrieb übernimmt",
    })

    return {
        "zusammenfassung": (
            f"{name} ist ein Unternehmen im Bereich {kategorie or 'lokale Dienstleistungen'}. "
            f"Basierend auf den vorliegenden Daten gibt es mehrere konkrete Optimierungspotenziale "
            f"in den Bereichen digitale Präsenz, Lead-Reaktion und Prozessautomatisierung. "
            f"Mit gezielten Maßnahmen lässt sich der Umsatz messbar steigern."
        ),
        "painpoints": painpoints,
        "passende_loesungen": loesungen,
        "verkaufsansaetze": ansaetze,
        "hooks": [
            f"Ich hab Ihre Website kurz angeschaut – da ist eine konkrete Sache die {name} "
            f"wahrscheinlich täglich Anfragen kostet. Darf ich kurz zeigen was ich meine?",
            f"Viele {kategorie or 'Unternehmen'} in Ihrer Lage verlieren gerade Aufträge weil "
            f"Anrufe nicht sofort bearbeitet werden – haben Sie das auch schon bemerkt?",
        ],
        "google_bewertungen_analyse": None,
        "umsatzpotenzial": "MITTEL",
        "top_einstiegsangebot": loesungen[0]["leistung"] if loesungen else "KI Telefonassistent",
        "_fallback": True,
    }


# ── HTML-Hilfsfunktionen ──────────────────────────────────────────────────────

def _lade_seite(url: str, client=None) -> Optional[str]:
    """Lädt eine Seite; gibt None zurück bei Fehler."""
    try:
        resp = get(url, client=client)
        if resp and resp.status_code == 200:
            ct = resp.headers.get("content-type", "")
            if "text/html" in ct or "text/plain" in ct:
                return resp.text
    except Exception as e:
        logger.debug(f"Seitenabruf fehlgeschlagen {url}: {e}")
    return None


def _html_zu_text(html: str) -> str:
    """Extrahiert lesbaren Fließtext aus HTML."""
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "head", "noscript"]):
            tag.decompose()
        text = soup.get_text(" ", strip=True)
        return re.sub(r"\s{2,}", " ", text)
    except Exception:
        return ""
