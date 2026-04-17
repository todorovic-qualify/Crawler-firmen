"""
Datenbankschreiber: Schreibt Crawler-Ergebnisse direkt in PostgreSQL.
Tabellen- und Spaltennamen entsprechen dem Prisma-Schema (@map-Deklarationen).

Neu: Deduplication, Freshness-Check, Junction-Table (suchauftrag_unternehmen).
"""
from __future__ import annotations

import os
import re
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional
from urllib.parse import urlparse

import psycopg2
import psycopg2.extras
from loguru import logger

from crawler.models import Unternehmen

# Leads gelten als "frisch", wenn der letzte Crawl jünger als 30 Tage ist
# UND Website + (Telefon oder E-Mail) vorhanden sind.
FRISCH_TAGE = 30


def _jetzt() -> datetime:
    return datetime.now(timezone.utc)


def _neue_id() -> str:
    """Prisma-kompatibler cuid-ähnlicher String."""
    return "c" + uuid.uuid4().hex[:23]


# ── Normalisierung ─────────────────────────────────────────────────────────────

def normalisiere_name(name: str) -> str:
    """Kleinbuchstaben, Sonderzeichen entfernen, mehrfache Leerzeichen zusammenfassen."""
    if not name:
        return ""
    n = name.lower().strip()
    # Umlaute normalisieren
    n = n.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
    # Nur Buchstaben/Zahlen/Leerzeichen behalten
    n = re.sub(r"[^a-z0-9 ]", " ", n)
    n = re.sub(r"\s+", " ", n).strip()
    return n


def normalisiere_domain(url: Optional[str]) -> Optional[str]:
    """Extrahiert und normalisiert die Domain aus einer URL."""
    if not url:
        return None
    try:
        parsed = urlparse(url if "://" in url else "https://" + url)
        domain = parsed.netloc.lower()
        # www. entfernen
        domain = re.sub(r"^www\.", "", domain)
        # Port entfernen
        domain = domain.split(":")[0]
        return domain if domain else None
    except Exception:
        return None


def ist_crawl_frisch(
    last_crawled_at: Optional[datetime],
    hat_webseite: bool,
    hat_telefon: bool,
    hat_email: bool,
) -> bool:
    """
    Gibt True zurück wenn der Lead frisch genug ist und keine Re-Anreicherung benötigt.

    Bedingungen (alle müssen erfüllt sein):
    - lastCrawledAt jünger als FRISCH_TAGE Tage
    - Website vorhanden
    - Telefon ODER E-Mail vorhanden
    """
    if not last_crawled_at:
        return False
    if not hat_webseite:
        return False
    if not (hat_telefon or hat_email):
        return False
    grenze = _jetzt() - timedelta(days=FRISCH_TAGE)
    # Sicherstellen dass last_crawled_at timezone-aware ist
    if last_crawled_at.tzinfo is None:
        last_crawled_at = last_crawled_at.replace(tzinfo=timezone.utc)
    return last_crawled_at >= grenze


# ── Verbindung ─────────────────────────────────────────────────────────────────

def verbinde() -> psycopg2.extensions.connection:
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        raise ValueError("DATABASE_URL ist nicht gesetzt")
    return psycopg2.connect(db_url)


# ── Suchauftrag ────────────────────────────────────────────────────────────────

def erstelle_suchauftrag(
    conn,
    ort: str,
    radius_km: Optional[int],
    kategorien: list[str],
    max_ergebnisse: int,
) -> str:
    auftrag_id = _neue_id()
    jetzt = _jetzt()
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO suchauftrag
              (id, ort, radius_km, kategorien, max_ergebnisse, status,
               gesamt_gefunden, gesamt_verarbeitet,
               anzahl_neu, anzahl_wiederverwendet, anzahl_aktualisiert,
               erstellt_am, aktualisiert_am)
            VALUES (%s, %s, %s, %s, %s, 'laeuft', 0, 0, 0, 0, 0, %s, %s)
            """,
            (auftrag_id, ort, radius_km, kategorien, max_ergebnisse, jetzt, jetzt),
        )
    conn.commit()
    logger.info(f"Suchauftrag erstellt: {auftrag_id}")
    return auftrag_id


def aktualisiere_suchauftrag(
    conn,
    auftrag_id: str,
    status: str,
    gesamt_gefunden: int,
    gesamt_verarbeitet: int,
    fehler: Optional[str] = None,
    anzahl_neu: int = 0,
    anzahl_wiederverwendet: int = 0,
    anzahl_aktualisiert: int = 0,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE suchauftrag
            SET status=%s, gesamt_gefunden=%s, gesamt_verarbeitet=%s,
                fehler_meldung=%s, aktualisiert_am=%s,
                anzahl_neu=%s, anzahl_wiederverwendet=%s, anzahl_aktualisiert=%s
            WHERE id=%s
            """,
            (
                status, gesamt_gefunden, gesamt_verarbeitet, fehler, _jetzt(),
                anzahl_neu, anzahl_wiederverwendet, anzahl_aktualisiert,
                auftrag_id,
            ),
        )
    conn.commit()


# ── Duplikat-Erkennung ─────────────────────────────────────────────────────────

def suche_duplikat(conn, u: Unternehmen) -> Optional[dict]:
    """
    Sucht nach einem existierenden Lead anhand folgender Priorität:
    1. Externe ID (OSM-Element-ID) – am zuverlässigsten
    2. Normalisierter Name + Domain
    3. Normalisierter Name + Stadt
    4. LOWER(name) Fallback für Legacy-Records ohne norm_name

    Gibt dict mit Feldern des gefundenen Leads zurück, oder None.
    """
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:

        # 1. Externe ID
        if u.externe_id:
            cur.execute(
                """SELECT id, name, hat_webseite, hat_telefon, hat_email,
                          last_crawled_at, crawl_status, webseite, telefon, email
                   FROM unternehmen WHERE externe_id = %s LIMIT 1""",
                (u.externe_id,),
            )
            row = cur.fetchone()
            if row:
                logger.debug(f"Duplikat via externe_id: {u.name} → {row['id']}")
                return dict(row)

        # 2. Normalisierter Name + Domain
        norm_name = normalisiere_name(u.name)
        norm_domain = normalisiere_domain(u.webseite)

        if norm_name and norm_domain:
            cur.execute(
                """SELECT id, name, hat_webseite, hat_telefon, hat_email,
                          last_crawled_at, crawl_status, webseite, telefon, email
                   FROM unternehmen
                   WHERE norm_name = %s AND norm_domain = %s LIMIT 1""",
                (norm_name, norm_domain),
            )
            row = cur.fetchone()
            if row:
                logger.debug(f"Duplikat via name+domain: {u.name} ({norm_domain}) → {row['id']}")
                return dict(row)

        # 3. Normalisierter Name + Stadt
        if norm_name and u.stadt:
            cur.execute(
                """SELECT id, name, hat_webseite, hat_telefon, hat_email,
                          last_crawled_at, crawl_status, webseite, telefon, email
                   FROM unternehmen
                   WHERE norm_name = %s AND LOWER(stadt) = LOWER(%s) LIMIT 1""",
                (norm_name, u.stadt),
            )
            row = cur.fetchone()
            if row:
                logger.debug(f"Duplikat via name+stadt: {u.name} ({u.stadt}) → {row['id']}")
                return dict(row)

        # 4. LOWER(name) Fallback für Legacy-Records ohne norm_name
        if u.name:
            name_lower = u.name.lower().strip()
            if u.stadt:
                cur.execute(
                    """SELECT id, name, hat_webseite, hat_telefon, hat_email,
                              last_crawled_at, crawl_status, webseite, telefon, email
                       FROM unternehmen
                       WHERE LOWER(TRIM(name)) = %s
                         AND LOWER(TRIM(COALESCE(stadt, ''))) = LOWER(%s)
                       LIMIT 1""",
                    (name_lower, u.stadt),
                )
            else:
                cur.execute(
                    """SELECT id, name, hat_webseite, hat_telefon, hat_email,
                              last_crawled_at, crawl_status, webseite, telefon, email
                       FROM unternehmen
                       WHERE LOWER(TRIM(name)) = %s
                         AND (stadt IS NULL OR TRIM(stadt) = '')
                       LIMIT 1""",
                    (name_lower,),
                )
            row = cur.fetchone()
            if row:
                logger.debug(f"Duplikat via LOWER(name) Fallback: {u.name} → {row['id']}")
                return dict(row)

    return None


# ── Junction-Table ─────────────────────────────────────────────────────────────

def verknuepfe_mit_suchauftrag(
    conn,
    unternehmen_id: str,
    auftrag_id: str,
    herkunft: str,
) -> None:
    """Verknüpft einen Lead mit einem Suchauftrag (many-to-many). Ignoriert Duplikate."""
    link_id = _neue_id()
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO suchauftrag_unternehmen (id, suchauftrag_id, unternehmen_id, herkunft, erstellt_am)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (suchauftrag_id, unternehmen_id) DO UPDATE
              SET herkunft = EXCLUDED.herkunft
            """,
            (link_id, auftrag_id, unternehmen_id, herkunft, _jetzt()),
        )
    # Commit wird vom Aufrufer gemacht


# ── Hauptfunktion: Speichern oder Wiederverwenden ──────────────────────────────

def speichere_oder_aktualisiere_unternehmen(
    conn,
    u: Unternehmen,
    auftrag_id: Optional[str] = None,
) -> tuple[str, str]:
    """
    Intelligentes Upsert mit Duplikat-Erkennung und Freshness-Check.

    Rückgabe: (unternehmen_id, herkunft)
    herkunft: 'neu' | 'wiederverwendet' | 'aktualisiert'
    """
    norm_name = normalisiere_name(u.name)
    norm_domain = normalisiere_domain(u.webseite)
    jetzt = _jetzt()

    # Duplikat prüfen
    existierend = suche_duplikat(conn, u)

    if existierend is None:
        # ── NEU: Einfügen ──────────────────────────────────────────────────────
        u_id = _neue_id()
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO unternehmen (
                  id, name, kategorie, beschreibung, adresse, stadt, postleitzahl,
                  telefon, email, webseite, quelle_url,
                  bewertung, bewertungs_anzahl, oeffnungszeiten,
                  instagram, facebook, linkedin, whatsapp,

                  lead_score, lead_temperatur,
                  webseite_bedarf_score, automation_bedarf_score, webseite_qualitaet_score,

                  wahrscheinliche_schmerzpunkte, empfohlene_angebote,
                  verkaufs_winkel, heiss_lead_grund, score_erklaerung,
                  erstes_kontaktnachricht, pitch_winkel,

                  entscheidungstraeger_name, rechtlicher_name,
                  zusammenfassung, leistungen,

                  hat_webseite, hat_email, hat_telefon,
                  status, notizen,

                  externe_id, norm_name, norm_domain,
                  last_crawled_at, crawl_status, quelle,

                  suchauftrag_id, erstellt_am, aktualisiert_am
                ) VALUES (
                  %s,%s,%s,%s,%s,%s,%s,
                  %s,%s,%s,%s,
                  %s,%s,%s,
                  %s,%s,%s,%s,

                  %s,%s::\"LeadTemperatur\",
                  %s,%s,%s,

                  %s,%s,
                  %s,%s,%s,
                  %s,%s,

                  %s,%s,
                  %s,%s,

                  %s,%s,%s,
                  %s::\"LeadStatus\",%s,

                  %s,%s,%s,
                  %s,%s,%s,

                  %s,%s,%s
                )
                """,
                (
                    u_id, u.name, u.kategorie, u.beschreibung, u.adresse, u.stadt, u.postleitzahl,
                    u.telefon, u.email, u.webseite, u.quelle_url,
                    u.bewertung, u.bewertungsanzahl, u.oeffnungszeiten,
                    u.instagram, u.facebook, u.linkedin, u.whatsapp,

                    u.lead_score, u.lead_temperatur,
                    u.webseite_bedarf_score, u.automation_bedarf_score, u.webseite_qualitaet_score,

                    u.wahrscheinliche_schmerzpunkte, u.empfohlene_angebote,
                    u.verkaufs_winkel, u.heiss_lead_grund, u.score_erklaerung,
                    u.erstes_kontaktnachricht, u.pitch_winkel,

                    u.entscheidungstraeger_name, u.rechtlicher_name,
                    u.zusammenfassung, u.leistungen,

                    u.hat_webseite, u.hat_email, u.hat_telefon,
                    u.status, None,

                    u.externe_id, norm_name, norm_domain,
                    jetzt, "neu", u.quelle,

                    auftrag_id, jetzt, jetzt,
                ),
            )

            # Webseitenanalyse speichern
            if u.webseiten_analyse:
                _speichere_webseiten_analyse(cur, u_id, u.webseiten_analyse, jetzt)

        conn.commit()

        if auftrag_id:
            verknuepfe_mit_suchauftrag(conn, u_id, auftrag_id, "neu")
            conn.commit()

        logger.debug(f"[NEU] {u.name} → {u_id}")
        return u_id, "neu"

    else:
        # ── WIEDERVERWENDET: Existierender Lead – Daten NIEMALS überschreiben ──
        # Nur Dedup-Felder befüllen falls noch fehlend
        u_id = existierend["id"]
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE unternehmen SET
                  externe_id = COALESCE(externe_id, %s),
                  norm_name = COALESCE(norm_name, %s),
                  norm_domain = COALESCE(norm_domain, %s),
                  crawl_status = 'wiederverwendet',
                  aktualisiert_am = %s
                WHERE id = %s
                """,
                (u.externe_id, norm_name, norm_domain, jetzt, u_id),
            )
        conn.commit()

        if auftrag_id:
            verknuepfe_mit_suchauftrag(conn, u_id, auftrag_id, "wiederverwendet")
            conn.commit()

        logger.debug(f"[WIEDERVERWENDET] {u.name} → {u_id}")
        return u_id, "wiederverwendet"


# ── Rückwärtskompatible Funktion (für crawler.py CLI) ─────────────────────────

def speichere_unternehmen(
    conn,
    u: Unternehmen,
    auftrag_id: Optional[str] = None,
) -> str:
    """Wrapper für Abwärtskompatibilität mit dem CLI-Crawler."""
    u_id, _ = speichere_oder_aktualisiere_unternehmen(conn, u, auftrag_id)
    return u_id


def aktualisiere_unternehmen(conn, u_id: str, u: Unternehmen) -> None:
    """Aktualisiert einen bestehenden Lead (wird bei Refresh aufgerufen)."""
    jetzt = _jetzt()
    norm_name = normalisiere_name(u.name)
    norm_domain = normalisiere_domain(u.webseite)

    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE unternehmen SET
              email=%s, telefon=%s, webseite=%s,
              instagram=%s, facebook=%s, linkedin=%s, whatsapp=%s,
              hat_webseite=%s, hat_email=%s, hat_telefon=%s,

              lead_score=%s, lead_temperatur=%s::\"LeadTemperatur\",
              webseite_bedarf_score=%s, automation_bedarf_score=%s,
              webseite_qualitaet_score=%s,

              wahrscheinliche_schmerzpunkte=%s, empfohlene_angebote=%s,
              verkaufs_winkel=%s, heiss_lead_grund=%s, score_erklaerung=%s,
              erstes_kontaktnachricht=%s, pitch_winkel=%s,

              entscheidungstraeger_name=%s, rechtlicher_name=%s,
              zusammenfassung=%s, leistungen=%s,

              norm_name=COALESCE(norm_name, %s),
              norm_domain=COALESCE(norm_domain, %s),
              last_crawled_at=%s,
              crawl_status='aktualisiert',
              aktualisiert_am=%s
            WHERE id=%s
            """,
            (
                u.email, u.telefon, u.webseite,
                u.instagram, u.facebook, u.linkedin, u.whatsapp,
                u.hat_webseite, u.hat_email, u.hat_telefon,

                u.lead_score, u.lead_temperatur,
                u.webseite_bedarf_score, u.automation_bedarf_score,
                u.webseite_qualitaet_score,

                u.wahrscheinliche_schmerzpunkte, u.empfohlene_angebote,
                u.verkaufs_winkel, u.heiss_lead_grund, u.score_erklaerung,
                u.erstes_kontaktnachricht, u.pitch_winkel,

                u.entscheidungstraeger_name, u.rechtlicher_name,
                u.zusammenfassung, u.leistungen,

                norm_name, norm_domain,
                jetzt, jetzt, u_id,
            ),
        )

        if u.webseiten_analyse:
            _upsert_webseiten_analyse(cur, u_id, u.webseiten_analyse, jetzt)

    conn.commit()


# ── Webseitenanalyse-Hilfsfunktionen ──────────────────────────────────────────

def _speichere_webseiten_analyse(cur, u_id: str, a, jetzt: datetime) -> None:
    """Fügt eine neue Webseitenanalyse ein (nur wenn noch nicht vorhanden)."""
    a_id = _neue_id()
    cur.execute(
        """
        INSERT INTO webseiten_analyse (
          id, unternehmen_id,
          startseite_title, meta_beschreibung, gecrawlte_seiten,
          kontaktformular_gefunden, cta_gefunden,
          buchungs_signal_gefunden, whatsapp_gefunden,
          social_links_gefunden, sieht_veraltet_aus,
          mobil_signale, technologie_stack,
          impressum_text, ueber_uns_text, leistungen_text,
          webseite_qualitaet_score, erstellt_am
        ) VALUES (
          %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s
        )
        ON CONFLICT (unternehmen_id) DO NOTHING
        """,
        (
            a_id, u_id,
            a.startseite_title, a.meta_beschreibung, a.gecrawlte_seiten,
            a.kontaktformular_gefunden, a.cta_gefunden,
            a.buchungs_signal_gefunden, a.whatsapp_gefunden,
            a.social_links_gefunden, a.sieht_veraltet_aus,
            a.mobil_signale, a.technologie_stack,
            a.impressum_text, a.ueber_uns_text, a.leistungen_text,
            a.webseite_qualitaet_score, jetzt,
        ),
    )


def _upsert_webseiten_analyse(cur, u_id: str, a, jetzt: datetime) -> None:
    """Fügt eine Webseitenanalyse ein oder aktualisiert sie."""
    a_id = _neue_id()
    cur.execute(
        """
        INSERT INTO webseiten_analyse (
          id, unternehmen_id,
          startseite_title, meta_beschreibung, gecrawlte_seiten,
          kontaktformular_gefunden, cta_gefunden,
          buchungs_signal_gefunden, whatsapp_gefunden,
          social_links_gefunden, sieht_veraltet_aus,
          mobil_signale, technologie_stack,
          impressum_text, ueber_uns_text, leistungen_text,
          webseite_qualitaet_score, erstellt_am
        ) VALUES (
          %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s
        )
        ON CONFLICT (unternehmen_id) DO UPDATE SET
          startseite_title=EXCLUDED.startseite_title,
          meta_beschreibung=EXCLUDED.meta_beschreibung,
          gecrawlte_seiten=EXCLUDED.gecrawlte_seiten,
          kontaktformular_gefunden=EXCLUDED.kontaktformular_gefunden,
          cta_gefunden=EXCLUDED.cta_gefunden,
          buchungs_signal_gefunden=EXCLUDED.buchungs_signal_gefunden,
          whatsapp_gefunden=EXCLUDED.whatsapp_gefunden,
          social_links_gefunden=EXCLUDED.social_links_gefunden,
          sieht_veraltet_aus=EXCLUDED.sieht_veraltet_aus,
          mobil_signale=EXCLUDED.mobil_signale,
          technologie_stack=EXCLUDED.technologie_stack,
          impressum_text=EXCLUDED.impressum_text,
          ueber_uns_text=EXCLUDED.ueber_uns_text,
          leistungen_text=EXCLUDED.leistungen_text,
          webseite_qualitaet_score=EXCLUDED.webseite_qualitaet_score
        """,
        (
            a_id, u_id,
            a.startseite_title, a.meta_beschreibung, a.gecrawlte_seiten,
            a.kontaktformular_gefunden, a.cta_gefunden,
            a.buchungs_signal_gefunden, a.whatsapp_gefunden,
            a.social_links_gefunden, a.sieht_veraltet_aus,
            a.mobil_signale, a.technologie_stack,
            a.impressum_text, a.ueber_uns_text, a.leistungen_text,
            a.webseite_qualitaet_score, jetzt,
        ),
    )
