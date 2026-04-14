"""
Datenbankschreiber: Schreibt Crawler-Ergebnisse direkt in PostgreSQL.
Tabellen- und Spaltennamen entsprechen dem Prisma-Schema (@map-Deklarationen).
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import Optional

import psycopg2
import psycopg2.extras
from loguru import logger

from crawler.models import Unternehmen


def _jetzt() -> datetime:
    return datetime.now(timezone.utc)


def _neue_id() -> str:
    """Prisma-kompatibler cuid-ähnlicher String."""
    return "c" + uuid.uuid4().hex[:23]


def verbinde() -> psycopg2.extensions.connection:
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        raise ValueError("DATABASE_URL ist nicht gesetzt")
    return psycopg2.connect(db_url)


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
               gesamt_gefunden, gesamt_verarbeitet, erstellt_am, aktualisiert_am)
            VALUES (%s, %s, %s, %s, %s, 'laeuft', 0, 0, %s, %s)
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
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE suchauftrag
            SET status=%s, gesamt_gefunden=%s, gesamt_verarbeitet=%s,
                fehler_meldung=%s, aktualisiert_am=%s
            WHERE id=%s
            """,
            (status, gesamt_gefunden, gesamt_verarbeitet, fehler, _jetzt(), auftrag_id),
        )
    conn.commit()


def speichere_unternehmen(
    conn,
    u: Unternehmen,
    auftrag_id: Optional[str] = None,
) -> str:
    """
    Speichert ein Unternehmen + optionale Webseitenanalyse.
    Gibt die neue ID zurück.
    Doppelte Namen+Stadt werden übersprungen (ON CONFLICT DO NOTHING).
    """
    u_id = _neue_id()
    jetzt = _jetzt()

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
              %s,%s,%s
            )
            ON CONFLICT DO NOTHING
            RETURNING id
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
                auftrag_id, jetzt, jetzt,
            ),
        )
        row = cur.fetchone()
        # ON CONFLICT → row ist None, dann trotzdem u_id zurückgeben
        gespeicherte_id = row[0] if row else u_id

        # Webseitenanalyse speichern (wenn vorhanden und Unternehmen neu eingefügt)
        if u.webseiten_analyse and row:
            a = u.webseiten_analyse
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
                    a_id, gespeicherte_id,
                    a.startseite_title,
                    a.meta_beschreibung,
                    a.gecrawlte_seiten,
                    a.kontaktformular_gefunden,
                    a.cta_gefunden,
                    a.buchungs_signal_gefunden,
                    a.whatsapp_gefunden,
                    a.social_links_gefunden,
                    a.sieht_veraltet_aus,
                    a.mobil_signale,
                    a.technologie_stack,
                    a.impressum_text,
                    a.ueber_uns_text,
                    a.leistungen_text,
                    a.webseite_qualitaet_score,
                    jetzt,
                ),
            )

    conn.commit()
    return gespeicherte_id


def aktualisiere_unternehmen(
    conn,
    u_id: str,
    u: Unternehmen,
) -> None:
    """
    Aktualisiert Anreicherungs- und Scoring-Felder eines bestehenden Eintrags.
    Wird verwendet wenn ON CONFLICT ausgelöst wurde (Eintrag bereits vorhanden).
    """
    jetzt = _jetzt()
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
                jetzt,
                u_id,
            ),
        )

        # Webseitenanalyse upsert
        if u.webseiten_analyse:
            a = u.webseiten_analyse
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
                    a.startseite_title,
                    a.meta_beschreibung,
                    a.gecrawlte_seiten,
                    a.kontaktformular_gefunden,
                    a.cta_gefunden,
                    a.buchungs_signal_gefunden,
                    a.whatsapp_gefunden,
                    a.social_links_gefunden,
                    a.sieht_veraltet_aus,
                    a.mobil_signale,
                    a.technologie_stack,
                    a.impressum_text,
                    a.ueber_uns_text,
                    a.leistungen_text,
                    a.webseite_qualitaet_score,
                    jetzt,
                ),
            )
    conn.commit()
