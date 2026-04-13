"""
Webseiten-Anreicherung: Crawlt die Webseite eines Unternehmens
und extrahiert sales-relevante Informationen.
"""
from __future__ import annotations

from typing import Optional
from urllib.parse import urljoin, urlparse

from loguru import logger

from crawler.models import Unternehmen, WebseitenAnalyse
from crawler.utils.http_utils import get, erstelle_client
from crawler.utils.parse_utils import (
    bereinige_text,
    extrahiere_emails,
    extrahiere_entscheidungstraeger,
    extrahiere_interne_links,
    extrahiere_meta,
    extrahiere_social_links,
    extrahiere_technologie_stack,
    extrahiere_telefon,
    hat_buchungssignal,
    hat_cta,
    hat_kontaktformular,
    hat_whatsapp,
    parse_html,
    sieht_veraltet_aus,
)

# Unterseiten, die wir gezielt suchen
ZIEL_UNTERSEITEN = [
    "/impressum",
    "/kontakt",
    "/contact",
    "/about",
    "/ueber-uns",
    "/über-uns",
    "/team",
    "/leistungen",
    "/services",
    "/angebot",
]


def reichere_an(unternehmen: Unternehmen) -> Unternehmen:
    """
    Crawlt die Webseite des Unternehmens und füllt webseitenAnalyse + fehlende Felder.
    Gibt das angereicherte Unternehmen zurück.
    """
    if not unternehmen.webseite:
        return unternehmen

    basis_url = _normalisiere_url(unternehmen.webseite)
    logger.info(f"Anreicherung: {unternehmen.name} → {basis_url}")

    analyse = WebseitenAnalyse()
    gecrawlte_seiten: list[str] = []

    with erstelle_client() as client:
        # 1. Startseite crawlen
        startseite_html = _lade_seite(basis_url, client)
        if not startseite_html:
            logger.warning(f"Startseite nicht abrufbar: {basis_url}")
            return unternehmen

        gecrawlte_seiten.append(basis_url)
        soup_start = parse_html(startseite_html)

        # Metadaten
        title, meta_desc = extrahiere_meta(soup_start)
        analyse.startseite_title = title
        analyse.meta_beschreibung = meta_desc

        # Signale auf der Startseite
        analyse.kontaktformular_gefunden = hat_kontaktformular(startseite_html)
        analyse.cta_gefunden = hat_cta(soup_start)
        analyse.buchungs_signal_gefunden = hat_buchungssignal(soup_start)
        analyse.whatsapp_gefunden = hat_whatsapp(soup_start)
        analyse.sieht_veraltet_aus = sieht_veraltet_aus(soup_start, startseite_html)
        analyse.technologie_stack = extrahiere_technologie_stack(startseite_html)

        # Social Links
        social = extrahiere_social_links(soup_start, basis_url)
        analyse.social_links_gefunden = list(social.values())
        if social.get("instagram") and not unternehmen.instagram:
            unternehmen.instagram = social["instagram"]
        if social.get("facebook") and not unternehmen.facebook:
            unternehmen.facebook = social["facebook"]
        if social.get("linkedin") and not unternehmen.linkedin:
            unternehmen.linkedin = social["linkedin"]

        # Kontaktdaten aus Startseite
        if not unternehmen.email:
            emails = extrahiere_emails(startseite_html)
            if emails:
                unternehmen.email = emails[0]
                unternehmen.hat_email = True

        if not unternehmen.telefon:
            tel = extrahiere_telefon(soup_start.get_text())
            if tel:
                unternehmen.telefon = tel
                unternehmen.hat_telefon = True

        # Interne Links für Unterseiten
        interne_links = extrahiere_interne_links(soup_start, basis_url)

        # Bekannte Pfade hinzufügen
        für_ziele = set(interne_links)
        for pfad in ZIEL_UNTERSEITEN:
            für_ziele.add(urljoin(basis_url, pfad))

        # 2. Unterseiten crawlen
        impressum_text = ""
        ueber_uns_text = ""
        leistungen_text = ""

        for url in list(für_ziele)[:8]:  # Max 8 Unterseiten
            if url == basis_url or url in gecrawlte_seiten:
                continue

            html = _lade_seite(url, client)
            if not html:
                continue

            gecrawlte_seiten.append(url)
            soup = parse_html(html)
            text = soup.get_text(" ", strip=True)
            pfad = urlparse(url).path.lower()

            # Kontaktformular auch auf Unterseiten prüfen
            if not analyse.kontaktformular_gefunden:
                analyse.kontaktformular_gefunden = hat_kontaktformular(html)
            if not analyse.cta_gefunden:
                analyse.cta_gefunden = hat_cta(soup)
            if not analyse.buchungs_signal_gefunden:
                analyse.buchungs_signal_gefunden = hat_buchungssignal(soup)
            if not analyse.whatsapp_gefunden:
                analyse.whatsapp_gefunden = hat_whatsapp(soup)

            # E-Mail aus Unterseiten
            if not unternehmen.email:
                emails = extrahiere_emails(html)
                if emails:
                    unternehmen.email = emails[0]
                    unternehmen.hat_email = True

            # Telefon aus Unterseiten
            if not unternehmen.telefon:
                tel = extrahiere_telefon(text)
                if tel:
                    unternehmen.telefon = tel
                    unternehmen.hat_telefon = True

            # Impressum
            if any(k in pfad for k in ["impressum", "legal", "anbieterkennzeichnung"]):
                impressum_text = bereinige_text(text, 1000)
                analyse.impressum_text = impressum_text
                # Entscheidungsträger
                et = extrahiere_entscheidungstraeger(text)
                if et and not unternehmen.entscheidungstraeger_name:
                    unternehmen.entscheidungstraeger_name = et

            # Über uns / Team
            elif any(k in pfad for k in ["about", "ueber", "über", "team"]):
                ueber_uns_text = bereinige_text(text, 800)
                analyse.ueber_uns_text = ueber_uns_text
                if not unternehmen.zusammenfassung:
                    unternehmen.zusammenfassung = bereinige_text(text, 300)

            # Leistungen / Services
            elif any(k in pfad for k in ["leistung", "service", "angebot"]):
                leistungen_text = bereinige_text(text, 800)
                analyse.leistungen_text = leistungen_text
                if not unternehmen.leistungen:
                    unternehmen.leistungen = bereinige_text(text, 300)

    analyse.gecrawlte_seiten = gecrawlte_seiten

    # Webseite-Qualitätsscore berechnen
    analyse.webseite_qualitaet_score = _berechne_qualitaet(analyse)

    unternehmen.webseiten_analyse = analyse
    unternehmen.webseite_qualitaet_score = analyse.webseite_qualitaet_score

    return unternehmen


def _lade_seite(url: str, client=None) -> Optional[str]:
    """Lädt eine Seite und gibt den HTML-Content zurück."""
    try:
        resp = get(url, client=client)
        if resp and resp.status_code == 200:
            return resp.text
    except Exception as e:
        logger.debug(f"Seitenabruf fehlgeschlagen {url}: {e}")
    return None


def _normalisiere_url(url: str) -> str:
    """Stellt sicher dass die URL ein Schema hat."""
    if not url.startswith("http"):
        return "https://" + url
    return url.rstrip("/")


def _berechne_qualitaet(analyse: WebseitenAnalyse) -> int:
    """
    Berechnet einen Webseiten-Qualitätsscore 0–100.
    Hoher Score = gute Website (weniger Verkaufspotenzial für neues Design).
    """
    punkte = 20  # Basiswert: Website existiert

    if analyse.cta_gefunden:
        punkte += 20
    if analyse.kontaktformular_gefunden:
        punkte += 15
    if analyse.buchungs_signal_gefunden:
        punkte += 20
    if analyse.whatsapp_gefunden:
        punkte += 5
    if len(analyse.social_links_gefunden) > 0:
        punkte += 5
    if analyse.sieht_veraltet_aus:
        punkte -= 25
    if len(analyse.gecrawlte_seiten) > 3:
        punkte += 10  # Viele Seiten = strukturierter Auftritt
    if analyse.technologie_stack:
        if "Wix" in (analyse.technologie_stack or "") or "Jimdo" in (analyse.technologie_stack or ""):
            punkte -= 10  # Baukastenseiten gelten als ausbaufähig

    return max(0, min(100, punkte))
