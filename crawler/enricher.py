"""
Webseiten-Anreicherungs-Pipeline.

Für jedes Unternehmen mit Website:
  1. Startseite laden + analysieren
  2. Unterseiten entdecken + gezielt crawlen
  3. Befund erstellen (Fakten / Signale / Heuristiken)
  4. Fehlende Stammdaten ergänzen
  5. Qualitätsscore berechnen

Konvention im Code:
  # [FAKT]      direkt aus HTML
  # [SIGNAL]    durch Muster-Matching
  # [HEURISTIK] indirekte Schlussfolgerung
"""
from __future__ import annotations

import re
from typing import Optional
from urllib.parse import urljoin, urlparse

from loguru import logger

from crawler.models import Unternehmen, AnreicherungsBefund, WebseitenAnalyse
from crawler.utils.http_utils import get, erstelle_client
from crawler.utils.parse_utils import (
    bereinige_text,
    extrahiere_emails,
    extrahiere_entscheidungstraeger,
    extrahiere_haupttext,
    extrahiere_interne_links,
    extrahiere_leistungen_liste,
    extrahiere_meta,
    extrahiere_rechtlicher_name,
    extrahiere_social_links,
    extrahiere_technologie_stack,
    extrahiere_telefon,
    fehlt_mobile_viewport,
    hat_buchungssignal,
    hat_chat_widget,
    hat_cta,
    hat_kontaktformular,
    hat_newsletter,
    hat_whatsapp,
    ist_baukastenseite,
    hat_schwache_struktur,
    parse_html,
    sieht_veraltet_aus,
)

# Gezielte Pfade die wir immer versuchen
PRIORITAETS_PFADE = [
    "/impressum",
    "/kontakt",
    "/contact",
    "/about",
    "/ueber-uns",
    "/team",
    "/leistungen",
    "/services",
]

# Pfad → Typ-Mapping für inhaltliche Zuordnung
PFAD_TYP = {
    "impressum":    "impressum",
    "legal":        "impressum",
    "kontakt":      "kontakt",
    "contact":      "kontakt",
    "about":        "ueber_uns",
    "ueber":        "ueber_uns",
    "über":         "ueber_uns",
    "team":         "ueber_uns",
    "leistung":     "leistungen",
    "service":      "leistungen",
    "angebot":      "leistungen",
    "referenz":     "leistungen",
}


# ── Öffentliche Hauptfunktion ─────────────────────────────────────────────────

def reichere_an(unternehmen: Unternehmen) -> Unternehmen:
    """
    Crawlt die Website und füllt `anreicherungs_befund` sowie
    `webseiten_analyse` am Unternehmen-Objekt.
    Gibt das angereicherte Objekt zurück (Mutation + Return).
    """
    if not unternehmen.webseite:
        return unternehmen

    basis_url = _normalisiere_url(unternehmen.webseite)
    logger.info(f"Anreicherung: {unternehmen.name} → {basis_url}")

    befund = AnreicherungsBefund()
    soup_start = None          # wird innerhalb des with-Blocks gesetzt, danach weiterverwendet
    startseite_html: str = ""  # für Phase 4 außerhalb des with-Blocks erreichbar

    # [HEURISTIK] SSL-Check
    befund.fehlt_ssl = not basis_url.startswith("https://")

    with erstelle_client() as client:
        # ── Phase 1: Startseite ───────────────────────────────────────────────
        startseite_html = _lade_seite(basis_url, client)
        if not startseite_html:
            logger.warning(f"Startseite nicht erreichbar: {basis_url}")
            return unternehmen

        befund.gecrawlte_seiten.append(basis_url)
        soup_start = parse_html(startseite_html)

        # [FAKT] Meta
        title, meta_desc = extrahiere_meta(soup_start)
        befund.startseite_title = title
        befund.meta_beschreibung = meta_desc

        # [FAKT] Technologie
        befund.technologie_stack = extrahiere_technologie_stack(startseite_html)

        # [SIGNAL] Startseiten-Signale
        befund.kontaktformular_gefunden = hat_kontaktformular(startseite_html)
        befund.cta_gefunden = hat_cta(soup_start)
        befund.buchungs_signal_gefunden = hat_buchungssignal(startseite_html, soup_start)
        befund.whatsapp_gefunden = hat_whatsapp(startseite_html)
        befund.chat_widget_gefunden = hat_chat_widget(startseite_html)
        befund.newsletter_gefunden = hat_newsletter(startseite_html, soup_start)

        # [HEURISTIK] Seitenqualität
        befund.sieht_veraltet_aus = sieht_veraltet_aus(startseite_html)
        befund.fehlt_mobile_viewport = fehlt_mobile_viewport(startseite_html)
        befund.baukastenseite = ist_baukastenseite(befund.technologie_stack)

        # [FAKT] Social Links
        befund.social_links = extrahiere_social_links(startseite_html)

        # [FAKT] Kontaktdaten von Startseite ergänzen
        _ergaenze_kontaktdaten(unternehmen, befund, startseite_html, soup_start)

        # ── Phase 2: Unterseiten entdecken ────────────────────────────────────
        interne_links = extrahiere_interne_links(soup_start, basis_url)

        # Prioritätspfade immer versuchen
        alle_ziele: list[str] = list(interne_links)
        for pfad in PRIORITAETS_PFADE:
            kandidat = urljoin(basis_url, pfad)
            if kandidat not in alle_ziele:
                alle_ziele.append(kandidat)

        # ── Phase 3: Unterseiten crawlen ──────────────────────────────────────
        gecrawlt_typen: set[str] = set()

        for url in alle_ziele[:12]:  # max. 12 Unterseiten
            if url == basis_url or url in befund.gecrawlte_seiten:
                continue

            seiten_typ = _erkenne_seiten_typ(url)
            # Jeden Typ nur einmal crawlen (z.B. nur eine "leistungen"-Seite)
            if seiten_typ and seiten_typ in gecrawlt_typen:
                continue

            html = _lade_seite(url, client)
            if not html:
                continue

            befund.gecrawlte_seiten.append(url)
            if seiten_typ:
                gecrawlt_typen.add(seiten_typ)

            soup = parse_html(html)

            # Signale auf Unterseiten nachholen
            if not befund.kontaktformular_gefunden:
                befund.kontaktformular_gefunden = hat_kontaktformular(html)
            if not befund.cta_gefunden:
                befund.cta_gefunden = hat_cta(soup)
            if not befund.buchungs_signal_gefunden:
                befund.buchungs_signal_gefunden = hat_buchungssignal(html, soup)
            if not befund.whatsapp_gefunden:
                befund.whatsapp_gefunden = hat_whatsapp(html)
            if not befund.chat_widget_gefunden:
                befund.chat_widget_gefunden = hat_chat_widget(html)

            # Kontaktdaten ergänzen
            _ergaenze_kontaktdaten(unternehmen, befund, html, soup)

            # Typ-spezifische Extraktion
            if seiten_typ == "impressum":
                _verarbeite_impressum(html, soup, befund, unternehmen)

            elif seiten_typ == "ueber_uns":
                text = extrahiere_haupttext(html) or bereinige_text(
                    soup.get_text(" ", strip=True), 800
                )
                if text:
                    befund.ueber_uns_text = text

            elif seiten_typ == "leistungen":
                text = extrahiere_haupttext(html) or bereinige_text(
                    soup.get_text(" ", strip=True), 800
                )
                if text:
                    befund.leistungen_text = text
                leistungen_liste = extrahiere_leistungen_liste(soup)
                if leistungen_liste:
                    befund.extraktion_leistungen = ", ".join(leistungen_liste)

    # ── Phase 4: Fehlende Stammdaten aus Befund übernehmen ───────────────────
    _uebernehme_in_unternehmen(unternehmen, befund)

    # [HEURISTIK] Schwache Struktur – soup_start wurde im with-Block gesetzt
    if soup_start is not None:
        befund.schwache_struktur = hat_schwache_struktur(
            soup_start, len(befund.gecrawlte_seiten)
        )

    # [HEURISTIK] KI/Automation-Signal
    befund.kein_ai_automation_signal = not (
        befund.chat_widget_gefunden
        or befund.buchungs_signal_gefunden
        or befund.whatsapp_gefunden
    )

    # ── Phase 5: Qualitätsscore ───────────────────────────────────────────────
    befund.webseite_qualitaet_score, befund.qualitaet_erklaerung = _berechne_qualitaet(befund)

    # Befund ans Unternehmen hängen
    unternehmen.anreicherungs_befund = befund
    unternehmen.webseite_qualitaet_score = befund.webseite_qualitaet_score

    # DB-kompatible WebseitenAnalyse bauen
    unternehmen.webseiten_analyse = _befund_zu_db_analyse(befund)

    logger.info(
        f"  ✓ {unternehmen.name}: {len(befund.gecrawlte_seiten)} Seiten, "
        f"Qualität={befund.webseite_qualitaet_score}, "
        f"veraltet={befund.sieht_veraltet_aus}, "
        f"CTA={befund.cta_gefunden}"
    )
    return unternehmen


# ── Interne Hilfsfunktionen ───────────────────────────────────────────────────

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


def _normalisiere_url(url: str) -> str:
    if not url.startswith("http"):
        return "https://" + url
    return url.rstrip("/")


def _erkenne_seiten_typ(url: str) -> Optional[str]:
    """Ordnet eine URL einem inhaltlichen Typ zu."""
    pfad = urlparse(url).path.lower().strip("/")
    for schluessel, typ in PFAD_TYP.items():
        if schluessel in pfad:
            return typ
    return None


def _ergaenze_kontaktdaten(
    u: Unternehmen,
    befund: AnreicherungsBefund,
    html: str,
    soup,
) -> None:
    """[FAKT] Ergänzt fehlende Kontaktdaten am Unternehmen."""
    if not u.email:
        emails = extrahiere_emails(html)
        # Gefundene E-Mails im Befund merken
        for e in emails:
            if e not in befund.gefundene_emails:
                befund.gefundene_emails.append(e)
        if emails:
            u.email = emails[0]
            u.hat_email = True

    if not u.telefon:
        tel = extrahiere_telefon(soup.get_text(" ", strip=True))
        if tel:
            befund.gefundene_telefone.append(tel)
            u.telefon = tel
            u.hat_telefon = True


def _verarbeite_impressum(html: str, soup, befund: AnreicherungsBefund, u: Unternehmen) -> None:
    """[FAKT] Extrahiert Impressum-Daten: Rechtsform, Entscheidungsträger, E-Mail."""
    # Rohtextblock für Regex-Matching
    text = soup.get_text(" ", strip=True)
    befund.impressum_text = bereinige_text(text, 1200)

    # [FAKT] Rechtlicher Name
    rechtlicher_name = extrahiere_rechtlicher_name(text)
    if rechtlicher_name and not u.rechtlicher_name:
        u.rechtlicher_name = rechtlicher_name
        befund.rechtlicher_name = rechtlicher_name

    # [FAKT] Entscheidungsträger
    et = extrahiere_entscheidungstraeger(text)
    if et and not u.entscheidungstraeger_name:
        u.entscheidungstraeger_name = et
        befund.entscheidungstraeger = et

    # [FAKT] E-Mail aus Impressum (oft der direkteste Kontakt)
    emails = extrahiere_emails(html)
    for e in emails:
        if e not in befund.gefundene_emails:
            befund.gefundene_emails.append(e)
    if emails and not u.email:
        u.email = emails[0]
        u.hat_email = True


def _uebernehme_in_unternehmen(u: Unternehmen, befund: AnreicherungsBefund) -> None:
    """Überträgt Befund-Ergebnisse in Felder des Unternehmen-Objekts."""
    # Social Media
    social = befund.social_links
    if social.get("instagram") and not u.instagram:
        u.instagram = social["instagram"]
    if social.get("facebook") and not u.facebook:
        u.facebook = social["facebook"]
    if social.get("linkedin") and not u.linkedin:
        u.linkedin = social["linkedin"]
    if social.get("whatsapp") and not u.whatsapp:
        u.whatsapp = social.get("whatsapp")

    # Zusammenfassung (priorisiert: Über-uns > Meta-Beschreibung)
    if not u.zusammenfassung:
        if befund.ueber_uns_text:
            u.zusammenfassung = bereinige_text(befund.ueber_uns_text, 300)
        elif befund.meta_beschreibung:
            u.zusammenfassung = bereinige_text(befund.meta_beschreibung, 300)

    # Leistungen
    if not u.leistungen:
        if befund.extraktion_leistungen:
            u.leistungen = befund.extraktion_leistungen
        elif befund.leistungen_text:
            u.leistungen = bereinige_text(befund.leistungen_text, 300)


def _berechne_qualitaet(befund: AnreicherungsBefund) -> tuple[int, list[str]]:
    """
    [HEURISTIK] Webseiten-Qualitätsscore 0–100.
    Hoher Score = starke Website (weniger Verkaufspotenzial für Neugestaltung).
    Jeder Punkt wird begründet.
    """
    punkte = 20  # Basiswert: Website existiert überhaupt
    erklaerung = ["Website vorhanden (+20)"]

    if befund.cta_gefunden:
        punkte += 20
        erklaerung.append("CTA vorhanden (+20)")
    else:
        erklaerung.append("Kein CTA gefunden (-0)")

    if befund.kontaktformular_gefunden:
        punkte += 15
        erklaerung.append("Kontaktformular vorhanden (+15)")

    if befund.buchungs_signal_gefunden:
        punkte += 20
        erklaerung.append("Buchungssystem integriert (+20)")

    if befund.whatsapp_gefunden:
        punkte += 5
        erklaerung.append("WhatsApp-Link vorhanden (+5)")

    if befund.chat_widget_gefunden:
        punkte += 5
        erklaerung.append("Chat-Widget vorhanden (+5)")

    if len(befund.social_links) >= 2:
        punkte += 5
        erklaerung.append("Social-Media-Links vorhanden (+5)")

    if len(befund.gecrawlte_seiten) >= 4:
        punkte += 5
        erklaerung.append("Mehrere Unterseiten vorhanden (+5)")

    # Negative Faktoren
    if befund.sieht_veraltet_aus:
        punkte -= 25
        erklaerung.append("Veraltete Indikatoren (-25)")

    if befund.fehlt_mobile_viewport:
        punkte -= 15
        erklaerung.append("Kein Mobile-Viewport (-15)")

    if befund.fehlt_ssl:
        punkte -= 10
        erklaerung.append("Kein HTTPS (-10)")

    if befund.baukastenseite:
        punkte -= 10
        erklaerung.append("Baukastenseite (Wix/Jimdo etc.) (-10)")

    if befund.schwache_struktur:
        punkte -= 10
        erklaerung.append("Schwache Seitenstruktur (-10)")

    return max(0, min(100, punkte)), erklaerung


def _befund_zu_db_analyse(befund: AnreicherungsBefund) -> WebseitenAnalyse:
    """Konvertiert AnreicherungsBefund → WebseitenAnalyse (DB-Modell)."""
    # Mobile-Signale als lesbarer Text
    mobil_teile = []
    if befund.fehlt_mobile_viewport:
        mobil_teile.append("Kein Viewport-Meta-Tag")
    if not befund.fehlt_mobile_viewport:
        mobil_teile.append("Viewport vorhanden")
    if befund.fehlt_ssl:
        mobil_teile.append("HTTP (kein SSL)")
    mobil_signale = "; ".join(mobil_teile) or None

    return WebseitenAnalyse(
        startseite_title=befund.startseite_title,
        meta_beschreibung=befund.meta_beschreibung,
        gecrawlte_seiten=befund.gecrawlte_seiten,
        kontaktformular_gefunden=befund.kontaktformular_gefunden,
        cta_gefunden=befund.cta_gefunden,
        buchungs_signal_gefunden=befund.buchungs_signal_gefunden,
        whatsapp_gefunden=befund.whatsapp_gefunden,
        social_links_gefunden=list(befund.social_links.values()),
        sieht_veraltet_aus=befund.sieht_veraltet_aus,
        mobil_signale=mobil_signale,
        technologie_stack=befund.technologie_stack,
        impressum_text=befund.impressum_text,
        ueber_uns_text=befund.ueber_uns_text,
        leistungen_text=befund.leistungen_text,
        webseite_qualitaet_score=befund.webseite_qualitaet_score,
    )
