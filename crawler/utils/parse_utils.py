"""
HTML-Parsing-Hilfsfunktionen: E-Mail, Telefon, Social-Links, CTA-Signale etc.
"""
from __future__ import annotations

import re
from typing import Optional
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

# ── Regex-Muster ──────────────────────────────────────────────────────────────

EMAIL_RE = re.compile(
    r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"
)

# Deutsche + internationale Telefonnummern
TELEFON_RE = re.compile(
    r"(?:(?:\+|00)49[\s\-./]?)?(?:\(?\d{2,5}\)?[\s\-./]?)?\d{3,}[\s\-./]?\d{3,}(?:[\s\-./]?\d{1,4})?"
)

WHATSAPP_RE = re.compile(r"whatsapp|wa\.me", re.I)

SOCIAL_PATTERNS = {
    "instagram": re.compile(r"instagram\.com/(?!p/|explore/|reel/)([^/?#\"'\s]+)", re.I),
    "facebook":  re.compile(r"facebook\.com/(?!sharer|share|dialog|plugins)([^/?#\"'\s]+)", re.I),
    "linkedin":  re.compile(r"linkedin\.com/(?:in|company)/([^/?#\"'\s]+)", re.I),
    "tiktok":    re.compile(r"tiktok\.com/@([^/?#\"'\s]+)", re.I),
}

# Veraltete Website-Indikatoren
VERALTET_PATTERNS = [
    re.compile(r"copyright\s*©?\s*20(0\d|1[0-6])", re.I),
    re.compile(r"flash|macromedia|ms\s?frontpage|dreamweaver", re.I),
    re.compile(r"designed\s+by.*(?:2008|2009|2010|2011|2012|2013|2014|2015|2016)", re.I),
]

# CTA-Schlüsselwörter (Deutsch + Englisch)
CTA_KEYWORDS = [
    "jetzt anfragen", "jetzt buchen", "termin buchen", "termin vereinbaren",
    "kostenlos testen", "jetzt kontaktieren", "angebot anfordern",
    "jetzt anrufen", "rückruf anfordern", "kontakt aufnehmen",
    "book now", "get a quote", "contact us", "schedule", "appointment",
    "jetzt bestellen", "jetzt kaufen",
]

BUCHUNGS_KEYWORDS = [
    "online buchen", "termin online", "buchung", "reservierung",
    "terminkalender", "calendly", "bookingkit", "treatwell",
    "book an appointment", "online booking", "reserve",
]

KONTAKTFORMULAR_KEYWORDS = [
    '<form', 'contact-form', 'kontaktformular', 'kontakt-form',
    'cf7', 'wpcf7', 'gform', 'ninja-forms',
]

IMPRESSUM_KEYWORDS = ["impressum", "rechtliche hinweise", "legal notice", "anbieterkennzeichnung"]
GESCHAEFTSFUEHRER_RE = re.compile(
    r"(?:geschäftsführer|inhaber|vorstand|ceo|managing\s+director|"
    r"vertreten\s+durch|verantwortlich)[:\s]+([A-ZÄÖÜ][a-zäöüß]+(?:\s+[A-ZÄÖÜ][a-zäöüß]+){1,3})",
    re.I,
)


# ── Parsing-Funktionen ────────────────────────────────────────────────────────

def parse_html(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "lxml")


def extrahiere_emails(text: str) -> list[str]:
    gefunden = EMAIL_RE.findall(text)
    # Filter: keine Bild-Dateinamen, zu kurze Domains etc.
    return list({
        e.lower() for e in gefunden
        if not any(e.lower().endswith(ext) for ext in [".png", ".jpg", ".gif", ".svg"])
        and "example" not in e.lower()
        and "domain" not in e.lower()
    })


def extrahiere_telefon(text: str) -> Optional[str]:
    """Gibt die erste plausible Telefonnummer zurück."""
    treffer = TELEFON_RE.findall(text)
    for t in treffer:
        t = t.strip()
        ziffern = re.sub(r"\D", "", t)
        if len(ziffern) >= 7:
            return t
    return None


def extrahiere_social_links(soup: BeautifulSoup, basis_url: str = "") -> dict[str, str]:
    links: dict[str, str] = {}
    for a in soup.find_all("a", href=True):
        href = a["href"]
        for plattform, pattern in SOCIAL_PATTERNS.items():
            if plattform not in links and pattern.search(href):
                links[plattform] = href
    return links


def hat_kontaktformular(html: str) -> bool:
    html_lower = html.lower()
    return any(k in html_lower for k in KONTAKTFORMULAR_KEYWORDS) and "<form" in html_lower


def hat_cta(soup: BeautifulSoup) -> bool:
    text = soup.get_text(" ", strip=True).lower()
    return any(k in text for k in CTA_KEYWORDS)


def hat_buchungssignal(soup: BeautifulSoup) -> bool:
    text = soup.get_text(" ", strip=True).lower()
    html = str(soup).lower()
    return any(k in text or k in html for k in BUCHUNGS_KEYWORDS)


def hat_whatsapp(soup: BeautifulSoup) -> bool:
    return bool(WHATSAPP_RE.search(str(soup)))


def sieht_veraltet_aus(soup: BeautifulSoup, html: str) -> bool:
    text = soup.get_text(" ", strip=True)
    return any(p.search(text) or p.search(html) for p in VERALTET_PATTERNS)


def extrahiere_meta(soup: BeautifulSoup) -> tuple[Optional[str], Optional[str]]:
    """Gibt (title, meta_description) zurück."""
    title = soup.title.string.strip() if soup.title and soup.title.string else None
    meta = soup.find("meta", attrs={"name": re.compile("description", re.I)})
    beschreibung = meta.get("content", "").strip() if meta else None
    return title, beschreibung or None


def extrahiere_interne_links(soup: BeautifulSoup, basis_url: str) -> list[str]:
    """Gibt interne Links zurück, die für Unterseiten interessant sind."""
    basis_host = urlparse(basis_url).netloc
    interessant = {
        "impressum", "kontakt", "contact", "about", "ueber-uns", "über-uns",
        "team", "leistungen", "services", "angebot", "referenzen",
    }
    gefunden = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        absolut = urljoin(basis_url, href)
        parsed = urlparse(absolut)
        if parsed.netloc != basis_host:
            continue
        pfad_teile = parsed.path.lower().strip("/").split("/")
        if any(teil in interessant for teil in pfad_teile):
            gefunden.append(absolut)
    return list(dict.fromkeys(gefunden))  # Deduplizieren, Reihenfolge behalten


def extrahiere_entscheidungstraeger(text: str) -> Optional[str]:
    """Versucht Geschäftsführer / Inhaber aus Impressum-Text zu extrahieren."""
    m = GESCHAEFTSFUEHRER_RE.search(text)
    return m.group(1).strip() if m else None


def extrahiere_technologie_stack(html: str) -> Optional[str]:
    """Erkennt gängige CMS / Frameworks anhand von HTML-Fingerprints."""
    hinweise = []
    if "wp-content" in html or "wp-includes" in html:
        hinweise.append("WordPress")
    if "Shopify" in html or "shopify" in html:
        hinweise.append("Shopify")
    if "wix.com" in html or "wixsite" in html:
        hinweise.append("Wix")
    if "squarespace" in html.lower():
        hinweise.append("Squarespace")
    if "jimdo" in html.lower():
        hinweise.append("Jimdo")
    if "typo3" in html.lower():
        hinweise.append("TYPO3")
    if "joomla" in html.lower():
        hinweise.append("Joomla")
    if "bootstrap" in html.lower():
        hinweise.append("Bootstrap")
    return ", ".join(hinweise) if hinweise else None


def bereinige_text(text: str, max_zeichen: int = 500) -> str:
    """Normalisiert Whitespace und kürzt auf max_zeichen."""
    bereinigt = " ".join(text.split())
    return bereinigt[:max_zeichen] if len(bereinigt) > max_zeichen else bereinigt
