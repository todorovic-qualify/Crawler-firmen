"""
HTML-Parsing-Hilfsfunktionen.

Konvention in Docstrings:
  [FAKT]      = direkt aus HTML extrahiert
  [SIGNAL]    = durch Muster-Matching erkannt
  [HEURISTIK] = aus indirekten Indikatoren geschlossen
"""
from __future__ import annotations

import re
from typing import Optional
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup, Tag

# ── Regex-Muster ──────────────────────────────────────────────────────────────

EMAIL_RE = re.compile(
    r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"
)

# Telefon: deutsch + international, flexibel formatiert
TELEFON_RE = re.compile(
    r"(?:Tel(?:efon)?\.?|Fon|Phone|☎|📞)[\s:]*"
    r"((?:\+49|0049|0)[\s.\-/]?\(?\d{2,5}\)?[\s.\-/]?\d{3,}[\s.\-/]?\d{0,6})",
    re.I,
)
TELEFON_PLAIN_RE = re.compile(
    r"(?<!\d)(?:\+49|0049|\(0\))?[\s.\-]?\(?\d{2,5}\)?[\s.\-/]\d{3,}(?:[\s.\-/]\d{2,5}){0,3}(?!\d)"
)

# Matcht vollständige Social-Media-URLs direkt im HTML-Quellcode.
# Gruppe 0 = volle URL (wird zurückgegeben).
SOCIAL_DOMAIN_RE: dict[str, re.Pattern] = {
    "instagram": re.compile(
        r'https?://(?:www\.)?instagram\.com/'
        r'(?!p/|explore/|reel/|stories/|_u/)([^/?#"\'>\s]{2,})',
        re.I,
    ),
    "facebook": re.compile(
        r'https?://(?:www\.)?facebook\.com/'
        r'(?!sharer|share|dialog|plugins|tr\?)([^/?#"\'>\s]{2,})',
        re.I,
    ),
    "linkedin": re.compile(
        r'https?://(?:www\.)?linkedin\.com/(?:in|company)/([^/?#"\'>\s]{2,})',
        re.I,
    ),
    "tiktok": re.compile(
        r'https?://(?:www\.)?tiktok\.com/@([^/?#"\'>\s]{2,})',
        re.I,
    ),
    "youtube": re.compile(
        r'https?://(?:www\.)?youtube\.com/(?:channel|user|@c?)([^/?#"\'>\s]{2,})',
        re.I,
    ),
}

# [HEURISTIK] Veraltete Website-Indikatoren
VERALTET_PATTERNS = [
    re.compile(r"©\s*20(?:0\d|1[0-5])\b"),                           # Copyright 2000-2015
    re.compile(r"copyright\s+20(?:0\d|1[0-5])\b", re.I),
    re.compile(r"flash|macromedia|ms\s?frontpage|dreamweaver", re.I),
    re.compile(r"<!--\[if\s+(?:lt\s+)?IE\s*\d", re.I),               # IE-Conditionals
    re.compile(r'<meta\s+http-equiv=["\']X-UA-Compatible["\']', re.I),
    re.compile(r"table\s+width=[\"\']\d+%?[\"\']\s+cellpadding", re.I),  # Table-Layout
    re.compile(r"font\s+face=[\"\']\w+[\"\']\s+color=", re.I),        # Font-Tags
]

# [SIGNAL] CTA-Schlüsselwörter
CTA_KEYWORDS = [
    # Deutsch
    "jetzt anfragen", "jetzt buchen", "termin buchen", "termin vereinbaren",
    "termin anfragen", "kostenlos testen", "jetzt kontaktieren",
    "angebot anfordern", "jetzt anrufen", "rückruf anfordern",
    "rückruf anfragen", "kontakt aufnehmen", "jetzt bestellen",
    "kostenlose beratung", "beratung anfragen", "probetraining",
    "erstgespräch", "unverbindlich anfragen", "jetzt starten",
    # Englisch
    "book now", "get a quote", "contact us", "schedule", "appointment",
    "free consultation", "get started", "request a call",
]

# [SIGNAL] Buchungs-Schlüsselwörter und Widget-Fingerprints
BUCHUNGS_PATTERNS = [
    # Keywords
    re.compile(r"online\s*buch", re.I),
    re.compile(r"termin\s*online", re.I),
    re.compile(r"reservier", re.I),
    re.compile(r"book\s+(?:an?\s+)?appointment", re.I),
    re.compile(r"online\s+booking", re.I),
    # Widget-Fingerprints
    re.compile(r"calendly\.com", re.I),
    re.compile(r"bookingkit", re.I),
    re.compile(r"treatwell", re.I),
    re.compile(r"timify", re.I),
    re.compile(r"shore\.com|shore-booking", re.I),
    re.compile(r"appointy|setmore|acuityscheduling", re.I),
    re.compile(r"doctolib", re.I),
    re.compile(r"jameda\.de", re.I),
    re.compile(r"zocdoc", re.I),
    re.compile(r"widget.*reserv|reserv.*widget", re.I),
]

# [SIGNAL] WhatsApp-Fingerprints
WHATSAPP_PATTERNS = [
    re.compile(r"wa\.me/", re.I),
    re.compile(r"api\.whatsapp\.com/send", re.I),
    re.compile(r'href=["\'][^"\']*whatsapp', re.I),
    re.compile(r"whatsapp\s*(?:chat|button|kontakt|schreiben|uns)", re.I),
]

# [SIGNAL] Chat/KI-Widget-Fingerprints
CHAT_WIDGET_PATTERNS = [
    re.compile(r"tawk\.to|tawkto", re.I),
    re.compile(r"crisp\.chat|crispcdn", re.I),
    re.compile(r"intercom(?:\.io)?", re.I),
    re.compile(r"drift\.com|driftt\.com", re.I),
    re.compile(r"livechat(?:inc)?\.com", re.I),
    re.compile(r"zendesk(?:\.com)?.*chat|zopim", re.I),
    re.compile(r"tidio(?:\.com|cdn)", re.I),
    re.compile(r"hubspot.*chat|hs-analytics", re.I),
    re.compile(r"freshchat|freshdesk", re.I),
    re.compile(r"smartsupp", re.I),
    re.compile(r"userlike", re.I),
    re.compile(r"chatbot|chat-bot|chatwidget", re.I),
]

# [SIGNAL] Kontaktformular-Fingerprints
KONTAKTFORMULAR_PATTERNS = [
    re.compile(r'<form[^>]+(?:contact|kontakt|anfrage|message|nachricht)', re.I),
    re.compile(r'class=["\'][^"\']*(?:contact|kontakt|wpcf7|gform|ninja-form|cf7)[^"\']*["\']', re.I),
    re.compile(r'id=["\'][^"\']*(?:contact|kontakt|contactform)[^"\']*["\']', re.I),
    re.compile(r'action=["\'][^"\']*(?:contact|anfrage|formspree|formcarry)[^"\']*["\']', re.I),
]

# Geschäftsführer / Inhaber aus Impressum
ENTSCHEIDUNGSTRAEGER_RE = [
    re.compile(
        r"(?:geschäftsführer(?:in)?|inhaber(?:in)?|vorstand|ceo|"
        r"managing\s+director|vertreten\s+durch|verantwortlich|"
        r"gründer(?:in)?|founder)\s*:?\s*"
        r"([A-ZÄÖÜ][a-zäöüß\-]+(?:\s+[A-ZÄÖÜ][a-zäöüß\-]+){1,3})",
        re.I | re.MULTILINE,
    ),
    # "Inh.: Max Mustermann" oder "Inh. Max Mustermann"
    re.compile(
        r"\bInh\.?\s*:?\s*([A-ZÄÖÜ][a-zäöüß\-]+(?:\s+[A-ZÄÖÜ][a-zäöüß\-]+){1,3})",
        re.MULTILINE,
    ),
]

# Rechtlicher Firmenname
RECHTLICHER_NAME_RE = [
    re.compile(
        r"([A-ZÄÖÜ][A-Za-zäöüÄÖÜß\s&\.\-]+(?:GmbH|UG|AG|OHG|KG|GbR|e\.K\.|e\.V\.|mbH)(?:\s*&\s*Co\.?\s*KG)?)",
        re.MULTILINE,
    ),
    re.compile(
        r"Firmenname\s*:?\s*(.+?)(?:\n|<br)", re.I | re.MULTILINE
    ),
]

# Technologie-Stack-Fingerprints (HEURISTIK / FAKT hybrid)
TECHNOLOGIE_MAP = [
    ("WordPress",   [r"wp-content", r"wp-includes", r"/wp-json/"]),
    ("Shopify",     [r"shopify\.com", r"cdn\.shopify", r'"Shopify"']),
    ("Wix",         [r"wix\.com", r"wixsite\.com", r"wix-code"]),
    ("Squarespace", [r"squarespace\.com", r"sqsp\.net"]),
    ("Jimdo",       [r"jimdo\.com", r"jimdocontent"]),
    ("Weebly",      [r"weebly\.com", r"editmysite\.com"]),
    ("TYPO3",       [r"typo3", r"EXT:form"]),
    ("Joomla",      [r"/joomla", r'content="Joomla']),
    ("Drupal",      [r"drupal\.js", r'content="Drupal']),
    ("Bootstrap",   [r"bootstrap\.min\.css", r"bootstrap\.bundle"]),
    ("React",       [r"__NEXT_DATA__", r"react\.production", r'id="__next"']),
    ("Vue",         [r"vue\.min\.js", r"__VUE__"]),
    ("Webflow",     [r"webflow\.com", r"data-wf-page"]),
]


# ── Hilfsfunktionen ───────────────────────────────────────────────────────────

def parse_html(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "lxml")


# [FAKT] E-Mail-Extraktion
def extrahiere_emails(html_oder_text: str) -> list[str]:
    gefunden = EMAIL_RE.findall(html_oder_text)
    ignoriere_endungen = {".png", ".jpg", ".gif", ".svg", ".webp", ".ico", ".woff"}
    ignoriere_domains = {"example", "domain", "yourdomain", "mustermann", "ihre-domain"}
    bereinigt = []
    for e in gefunden:
        e_lower = e.lower()
        if any(e_lower.endswith(ext) for ext in ignoriere_endungen):
            continue
        domain = e_lower.split("@")[-1].split(".")[0]
        if domain in ignoriere_domains:
            continue
        bereinigt.append(e_lower)
    return list(dict.fromkeys(bereinigt))


# [FAKT] Telefon-Extraktion
def extrahiere_telefon(text: str) -> Optional[str]:
    # Erst mit Kontext-Label (Tel.: 0621 ...)
    m = TELEFON_RE.search(text)
    if m:
        nummer = m.group(1).strip()
        ziffern = re.sub(r"\D", "", nummer)
        if len(ziffern) >= 7:
            return nummer

    # Dann einfaches Muster
    treffer = TELEFON_PLAIN_RE.findall(text)
    for t in treffer:
        t = t.strip()
        ziffern = re.sub(r"\D", "", t)
        if 7 <= len(ziffern) <= 15:
            return t
    return None


# [FAKT] Social Links – matcht volle URLs direkt im Quellcode
def extrahiere_social_links(html: str) -> dict[str, str]:
    """
    Gibt {plattform: volle_url} zurück.
    Sucht direkt nach vollständigen https://…-URLs im HTML-Quelltext.
    """
    links: dict[str, str] = {}
    for plattform, pattern in SOCIAL_DOMAIN_RE.items():
        m = pattern.search(html)
        if m:
            # m.group(0) ist die vollständige URL (kein href= drum herum)
            links[plattform] = m.group(0)
    return links


# [FAKT] Meta-Informationen
def extrahiere_meta(soup: BeautifulSoup) -> tuple[Optional[str], Optional[str]]:
    title = None
    if soup.title and soup.title.string:
        title = soup.title.string.strip()

    desc = None
    meta = soup.find("meta", attrs={"name": re.compile(r"description", re.I)})
    if meta and isinstance(meta, Tag):
        desc = meta.get("content", "")
        desc = desc.strip() if desc else None

    return title or None, desc or None


# [FAKT] Technologie-Stack
def extrahiere_technologie_stack(html: str) -> Optional[str]:
    gefunden = []
    for name, muster_liste in TECHNOLOGIE_MAP:
        if any(re.search(m, html) for m in muster_liste):
            gefunden.append(name)
    return ", ".join(gefunden) if gefunden else None


# [SIGNAL] Kontaktformular
# Muster-Match auf bekannte Form-Fingerprints; Fallback: <form> mit einem
# <input type="text"> und einem <textarea> gilt als Kontaktformular.
def hat_kontaktformular(html: str) -> bool:
    html_lower = html.lower()
    if "<form" not in html_lower:
        return False
    # Explizite Fingerprints
    if any(p.search(html) for p in KONTAKTFORMULAR_PATTERNS):
        return True
    # Fallback: form + textarea + text-input = sehr wahrscheinlich Kontaktformular
    hat_textarea = "<textarea" in html_lower
    hat_input = bool(re.search(r'<input[^>]+type=["\'](?:text|email)["\']', html_lower))
    return hat_textarea and hat_input


# [SIGNAL] CTA
def hat_cta(soup: BeautifulSoup) -> bool:
    text = soup.get_text(" ", strip=True).lower()
    return any(k in text for k in CTA_KEYWORDS)


# [SIGNAL] Buchungssystem
def hat_buchungssignal(html: str, soup: BeautifulSoup) -> bool:
    text = soup.get_text(" ", strip=True)
    return any(p.search(html) or p.search(text) for p in BUCHUNGS_PATTERNS)


# [SIGNAL] WhatsApp
def hat_whatsapp(html: str) -> bool:
    return any(p.search(html) for p in WHATSAPP_PATTERNS)


# [SIGNAL] Chat-/KI-Widget
def hat_chat_widget(html: str) -> bool:
    return any(p.search(html) for p in CHAT_WIDGET_PATTERNS)


# [SIGNAL] Newsletter
def hat_newsletter(html: str, soup: BeautifulSoup) -> bool:
    text = soup.get_text(" ", strip=True).lower()
    keywords = ["newsletter", "e-mail abonnieren", "email abonnieren", "anmelden", "subscribe"]
    return any(k in text for k in keywords) and "<form" in html.lower()


# [HEURISTIK] Veraltete Website
def sieht_veraltet_aus(html: str) -> bool:
    return any(p.search(html) for p in VERALTET_PATTERNS)


# [HEURISTIK] Fehlender Mobile-Viewport
def fehlt_mobile_viewport(html: str) -> bool:
    return not bool(re.search(r'<meta[^>]+name=["\']viewport["\']', html, re.I))


# [HEURISTIK] Baukastenseite
def ist_baukastenseite(stack: Optional[str]) -> bool:
    if not stack:
        return False
    return any(b in stack for b in ["Wix", "Jimdo", "Squarespace", "Weebly"])


# [HEURISTIK] Schwache Seitenstruktur
def hat_schwache_struktur(soup: BeautifulSoup, anzahl_seiten: int) -> bool:
    nav = soup.find("nav")
    menu_links = soup.find_all("a", href=True)
    zu_wenig_seiten = anzahl_seiten <= 2
    kein_nav = nav is None
    wenig_links = len(menu_links) < 5
    return zu_wenig_seiten and (kein_nav or wenig_links)


# [FAKT] Interne Links für Unterseiten-Crawling
# Substring-Suche im Pfad – flexibler als exakter Teilstring-Match
_INTERESSANTE_PFAD_FRAGMENTE = [
    "impressum", "kontakt", "contact", "about",
    "ueber-uns", "ueber_uns", "ueber",
    "team", "leistungen", "services", "angebot",
    "leistung", "service",
]

def extrahiere_interne_links(soup: BeautifulSoup, basis_url: str) -> list[str]:
    """
    [FAKT] Gibt interne URLs zurück, deren Pfad auf eine für
    die Anreicherung relevante Unterseite hindeutet.
    """
    basis_host = urlparse(basis_url).netloc
    gefunden = []
    for a in soup.find_all("a", href=True):
        href = str(a["href"]).strip()
        if href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        absolut = urljoin(basis_url, href)
        parsed = urlparse(absolut)
        if parsed.netloc != basis_host:
            continue
        pfad = parsed.path.lower()
        if any(frag in pfad for frag in _INTERESSANTE_PFAD_FRAGMENTE):
            gefunden.append(absolut)
    return list(dict.fromkeys(gefunden))


# [FAKT] Entscheidungsträger aus Impressum
def extrahiere_entscheidungstraeger(text: str) -> Optional[str]:
    for pattern in ENTSCHEIDUNGSTRAEGER_RE:
        m = pattern.search(text)
        if m:
            name = m.group(1).strip()
            # Plausibilitätsprüfung: min. 2 Wörter, keine Zahlen
            if " " in name and not re.search(r"\d", name):
                return name
    return None


# [FAKT] Rechtlicher Firmenname aus Impressum
def extrahiere_rechtlicher_name(text: str) -> Optional[str]:
    for pattern in RECHTLICHER_NAME_RE:
        m = pattern.search(text)
        if m:
            name = m.group(1).strip()
            if 3 < len(name) < 100:
                return name
    return None


# [FAKT] Sauberer Text mit trafilatura (wenn verfügbar) oder Fallback
def extrahiere_haupttext(html: str, max_zeichen: int = 800) -> Optional[str]:
    try:
        import trafilatura
        text = trafilatura.extract(html, include_comments=False, include_tables=False)
        if text:
            return bereinige_text(text, max_zeichen)
    except ImportError:
        pass

    # Fallback: BeautifulSoup
    soup = parse_html(html)
    # Störende Elemente entfernen
    for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
        tag.decompose()
    text = soup.get_text(" ", strip=True)
    return bereinige_text(text, max_zeichen) if text else None


# [FAKT] Leistungen aus strukturiertem HTML extrahieren
def extrahiere_leistungen_liste(soup: BeautifulSoup) -> list[str]:
    """Versucht eine strukturierte Leistungsliste zu extrahieren."""
    leistungen = []

    # Aus <ul> / <li> in Leistungs-Abschnitten
    for section in soup.find_all(["section", "div", "article"]):
        text = section.get_text().lower()
        if any(k in text for k in ["leistung", "service", "angebot", "was wir"]):
            for li in section.find_all("li"):
                item = li.get_text(strip=True)
                if 3 < len(item) < 80 and not re.search(r"(cookie|datenschutz|impressum)", item, re.I):
                    leistungen.append(item)

    # Aus <h2>/<h3> Headlines als Leistungsübersicht
    if not leistungen:
        for h in soup.find_all(["h2", "h3"]):
            text = h.get_text(strip=True)
            if 3 < len(text) < 60:
                leistungen.append(text)

    # Max. 10 Einträge, dedupliziert
    gesehen = set()
    eindeutig = []
    for item in leistungen:
        key = item.lower()
        if key not in gesehen:
            gesehen.add(key)
            eindeutig.append(item)
    return eindeutig[:10]


def bereinige_text(text: str, max_zeichen: int = 500) -> str:
    bereinigt = " ".join(text.split())
    return bereinigt[:max_zeichen].rstrip() if len(bereinigt) > max_zeichen else bereinigt
