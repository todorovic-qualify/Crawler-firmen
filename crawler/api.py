"""
FastAPI-Service: Stellt HTTP-Endpunkte für die Next.js-Frontend-Integration bereit.
Läuft als separater Prozess auf Port 8000.

Pipeline (4 Phasen):
  1. Rohdaten sammeln (Overpass)
  2. Duplikat-Matching gegen DB
  3. Nur neue / veraltete Leads anreichern (Enrichment)
  4. Scoring + Speichern + Suchauftrag verknüpfen
"""
from __future__ import annotations

import os
import threading
from typing import Optional, Any

import psycopg2.extras
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Header, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from pydantic import BaseModel

load_dotenv()

API_KEY = os.environ.get("CRAWLER_API_KEY", "")


# ── DB-Schema-Migration (idempotent, läuft bei jedem Start) ───────────────────

def _migriere_db() -> None:
    """
    Fügt fehlende Spalten/Tabellen hinzu (IF NOT EXISTS → sicher idempotent).
    Läuft beim App-Start, damit der Python-Service unabhängig von prisma db push
    funktioniert.
    """
    try:
        import psycopg2
        db_url = os.environ.get("DATABASE_URL")
        if not db_url:
            logger.warning("DATABASE_URL nicht gesetzt – Migration übersprungen")
            return

        conn = psycopg2.connect(db_url)
        with conn.cursor() as cur:
            # ── Neue Spalten in unternehmen ────────────────────────────────────
            cur.execute("""
                ALTER TABLE unternehmen
                  ADD COLUMN IF NOT EXISTS externe_id       TEXT,
                  ADD COLUMN IF NOT EXISTS norm_name        TEXT,
                  ADD COLUMN IF NOT EXISTS norm_domain      TEXT,
                  ADD COLUMN IF NOT EXISTS last_crawled_at  TIMESTAMPTZ,
                  ADD COLUMN IF NOT EXISTS crawl_status     TEXT DEFAULT 'neu',
                  ADD COLUMN IF NOT EXISTS quelle           TEXT DEFAULT 'overpass'
            """)

            # ── Neue Spalten in suchauftrag ────────────────────────────────────
            cur.execute("""
                ALTER TABLE suchauftrag
                  ADD COLUMN IF NOT EXISTS anzahl_neu              INTEGER DEFAULT 0,
                  ADD COLUMN IF NOT EXISTS anzahl_wiederverwendet  INTEGER DEFAULT 0,
                  ADD COLUMN IF NOT EXISTS anzahl_aktualisiert     INTEGER DEFAULT 0
            """)

            # ── Junction-Tabelle suchauftrag_unternehmen ───────────────────────
            cur.execute("""
                CREATE TABLE IF NOT EXISTS suchauftrag_unternehmen (
                  id              TEXT PRIMARY KEY,
                  suchauftrag_id  TEXT NOT NULL REFERENCES suchauftrag(id) ON DELETE CASCADE,
                  unternehmen_id  TEXT NOT NULL REFERENCES unternehmen(id) ON DELETE CASCADE,
                  herkunft        TEXT NOT NULL DEFAULT 'neu',
                  erstellt_am     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                  UNIQUE(suchauftrag_id, unternehmen_id)
                )
            """)

            # ── Indexes für Performance ────────────────────────────────────────
            cur.execute("CREATE INDEX IF NOT EXISTS idx_unt_externe_id    ON unternehmen(externe_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_unt_norm          ON unternehmen(norm_name, norm_domain)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_unt_stadt         ON unternehmen(stadt)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_unt_lead_score    ON unternehmen(lead_score)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_unt_crawl_status  ON unternehmen(crawl_status)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_sau_suchauftrag   ON suchauftrag_unternehmen(suchauftrag_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_sau_unternehmen   ON suchauftrag_unternehmen(unternehmen_id)")

        conn.commit()
        conn.close()
        logger.info("DB-Migration erfolgreich abgeschlossen")
    except Exception as e:
        logger.warning(f"DB-Migration fehlgeschlagen (nicht kritisch): {e}")

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app_instance):
    _migriere_db()
    yield

app = FastAPI(
    title="LeadScout Crawler API",
    description="Interner Crawler-Service für die LeadScout-Plattform",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", os.environ.get("NEXTAUTH_URL", ""), "https://crawler-firmen.vercel.app"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Laufende Jobs tracken (in-memory, für MVP ausreichend)
_laufende_jobs: dict[str, dict] = {}


# ── Request-Modelle ────────────────────────────────────────────────────────────

class CrawlerStartRequest(BaseModel):
    ort: str
    radius_km: int = 10
    kategorien: list[str] = []
    max_ergebnisse: int = 100
    enrichment: bool = True
    auftrag_id: Optional[str] = None
    # Optionale Konfig aus dem Frontend (Einstellungen-Seite)
    crawler_config: Optional[dict[str, Any]] = None
    scoring_config: Optional[dict[str, Any]] = None


class JobStatus(BaseModel):
    auftrag_id: str
    status: str
    gefunden: int = 0
    verarbeitet: int = 0
    fehler: Optional[str] = None
    # Statistiken (neu)
    anzahl_neu: int = 0
    anzahl_wiederverwendet: int = 0
    anzahl_aktualisiert: int = 0
    uebersprungen: int = 0


# ── Auth-Helper ────────────────────────────────────────────────────────────────

def prüfe_api_key(x_api_key: Optional[str] = Header(None)) -> None:
    if API_KEY and x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Ungültiger API-Key")


# ── Hintergrund-Crawler (4-Phasen-Pipeline) ────────────────────────────────────

def _starte_crawler_job(request: CrawlerStartRequest, auftrag_id: str) -> None:
    """
    Läuft in einem separaten Thread.

    Phase 1: Rohdaten sammeln (Overpass)
    Phase 2: Duplikat-Matching (DB-Lookup für jeden Treffer)
    Phase 3: Enrichment nur für neue/veraltete Leads
    Phase 4: Scoring + Speichern + Statistiken
    """
    from crawler.sources.overpass import suche_unternehmen, KATEGORIE_OSM_MAP
    from crawler.enricher import reichere_an
    from crawler.scorer import bewerte
    from crawler.db_writer import (
        verbinde, aktualisiere_suchauftrag,
        suche_duplikat, speichere_oder_aktualisiere_unternehmen,
        ist_crawl_frisch,
    )
    from crawler.utils.http_utils import rate_limiter_setzen

    _laufende_jobs[auftrag_id] = {
        "status": "laeuft",
        "gefunden": 0,
        "verarbeitet": 0,
        "anzahl_neu": 0,
        "anzahl_wiederverwendet": 0,
        "anzahl_aktualisiert": 0,
        "uebersprungen": 0,
    }

    # ── Crawler-Konfig aus Frontend anwenden ──────────────────────────────────
    if request.crawler_config:
        delay = request.crawler_config.get("delay_seconds")
        if isinstance(delay, (int, float)) and delay > 0:
            rate_limiter_setzen(float(delay))
            logger.info(f"[Job {auftrag_id}] Rate-Limiter: {delay}s Verzögerung")

    kategorien = request.kategorien or list(KATEGORIE_OSM_MAP.keys())

    try:
        # ── Phase 1: Rohdaten sammeln ─────────────────────────────────────────
        logger.info(f"[Job {auftrag_id}] ═══ Phase 1: Suche in '{request.ort}' ═══")
        roh_liste = suche_unternehmen(
            ort=request.ort,
            radius_km=request.radius_km,
            kategorien=kategorien,
            max_ergebnisse=request.max_ergebnisse,
        )
        _laufende_jobs[auftrag_id]["gefunden"] = len(roh_liste)
        logger.info(f"[Job {auftrag_id}] Roh-Treffer: {len(roh_liste)}")

        if not roh_liste:
            logger.warning(f"[Job {auftrag_id}] Keine Treffer gefunden – Geocodierung prüfen!")
            conn = verbinde()
            aktualisiere_suchauftrag(conn, auftrag_id, "abgeschlossen", 0, 0)
            conn.close()
            _laufende_jobs[auftrag_id]["status"] = "abgeschlossen"
            return

        # ── Phase 2: Duplikat-Matching ────────────────────────────────────────
        logger.info(f"[Job {auftrag_id}] ═══ Phase 2: Duplikat-Matching ═══")
        conn = verbinde()

        neu_liste = []       # Brauchen vollen Enrichment
        frisch_liste = []    # Werden wiederverwendet (kein Re-Crawl)
        veraltet_liste = []  # Brauchen Refresh-Enrichment

        for u in roh_liste:
            existierend = suche_duplikat(conn, u)
            if existierend is None:
                neu_liste.append(u)
            else:
                frisch = ist_crawl_frisch(
                    last_crawled_at=existierend.get("last_crawled_at"),
                    hat_webseite=existierend.get("hat_webseite", False),
                    hat_telefon=existierend.get("hat_telefon", False),
                    hat_email=existierend.get("hat_email", False),
                )
                if frisch:
                    frisch_liste.append(u)
                else:
                    veraltet_liste.append(u)

        conn.close()

        logger.info(
            f"[Job {auftrag_id}] Matching-Ergebnis: "
            f"{len(neu_liste)} neu | "
            f"{len(frisch_liste)} wiederverwendet | "
            f"{len(veraltet_liste)} zu aktualisieren"
        )

        # ── Phase 3: Enrichment ───────────────────────────────────────────────
        logger.info(f"[Job {auftrag_id}] ═══ Phase 3: Enrichment ═══")
        enrichment_liste = neu_liste + veraltet_liste  # Nur diese werden gecrawlt
        uebersprungen = len(frisch_liste)

        logger.info(
            f"[Job {auftrag_id}] Enrichment: {len(enrichment_liste)} Leads "
            f"({len(neu_liste)} neu + {len(veraltet_liste)} veraltet) | "
            f"{uebersprungen} Re-Crawls übersprungen"
        )
        _laufende_jobs[auftrag_id]["uebersprungen"] = uebersprungen

        if request.enrichment:
            for i, u in enumerate(enrichment_liste):
                if u.hat_webseite:
                    try:
                        reichere_an(u)
                        logger.debug(f"[Job {auftrag_id}] Enrichment {i+1}/{len(enrichment_liste)}: {u.name}")
                    except Exception as e:
                        logger.warning(f"[Job {auftrag_id}] Enrichment fehlgeschlagen {u.name}: {e}")

        # ── Phase 4: Scoring + Speichern ──────────────────────────────────────
        logger.info(f"[Job {auftrag_id}] ═══ Phase 4: Scoring + Speichern ═══")

        # Alle Leads (enrichment_liste + frisch_liste) bewerten und speichern
        alle_leads = enrichment_liste + frisch_liste
        conn = verbinde()

        anzahl_neu = 0
        anzahl_wiederverwendet = 0
        anzahl_aktualisiert = 0
        gespeichert = 0

        for u in alle_leads:
            try:
                bewerte(u, konfig=request.scoring_config)
                u_id, herkunft = speichere_oder_aktualisiere_unternehmen(conn, u, auftrag_id)

                gespeichert += 1
                _laufende_jobs[auftrag_id]["verarbeitet"] = gespeichert

                if herkunft == "neu":
                    anzahl_neu += 1
                elif herkunft == "wiederverwendet":
                    anzahl_wiederverwendet += 1
                elif herkunft == "aktualisiert":
                    anzahl_aktualisiert += 1

                _laufende_jobs[auftrag_id]["anzahl_neu"] = anzahl_neu
                _laufende_jobs[auftrag_id]["anzahl_wiederverwendet"] = anzahl_wiederverwendet
                _laufende_jobs[auftrag_id]["anzahl_aktualisiert"] = anzahl_aktualisiert

            except Exception as e:
                logger.error(f"[Job {auftrag_id}] DB-Fehler für {u.name}: {e}")

        aktualisiere_suchauftrag(
            conn, auftrag_id, "abgeschlossen",
            len(roh_liste), gespeichert,
            anzahl_neu=anzahl_neu,
            anzahl_wiederverwendet=anzahl_wiederverwendet,
            anzahl_aktualisiert=anzahl_aktualisiert,
        )
        conn.close()

        _laufende_jobs[auftrag_id]["status"] = "abgeschlossen"

        logger.info(
            f"[Job {auftrag_id}] ═══ Abgeschlossen ═══\n"
            f"  Roh-Treffer:      {len(roh_liste)}\n"
            f"  Neu angelegt:     {anzahl_neu}\n"
            f"  Wiederverwendet:  {anzahl_wiederverwendet}\n"
            f"  Aktualisiert:     {anzahl_aktualisiert}\n"
            f"  Re-Crawls skip:   {uebersprungen}\n"
            f"  Final gespeichert: {gespeichert}"
        )

    except Exception as e:
        logger.error(f"[Job {auftrag_id}] Fehler: {e}", exc_info=True)
        _laufende_jobs[auftrag_id]["status"] = "fehler"
        _laufende_jobs[auftrag_id]["fehler"] = str(e)
        try:
            from crawler.db_writer import verbinde, aktualisiere_suchauftrag
            conn = verbinde()
            aktualisiere_suchauftrag(conn, auftrag_id, "fehler", 0, 0, str(e))
            conn.close()
        except Exception:
            pass


# ── Endpunkte ─────────────────────────────────────────────────────────────────

@app.get("/gesundheit")
@app.get("/health")
def gesundheitscheck():
    return {"status": "ok", "service": "LeadScout Crawler v2"}


@app.post("/starten", response_model=JobStatus)
def crawler_starten(
    request: CrawlerStartRequest,
    background_tasks: BackgroundTasks,
    x_api_key: Optional[str] = Header(None),
):
    """Startet einen Crawler-Job im Hintergrund."""
    prüfe_api_key(x_api_key)

    from crawler.db_writer import verbinde, erstelle_suchauftrag
    from crawler.sources.overpass import KATEGORIE_OSM_MAP

    kategorien = request.kategorien or list(KATEGORIE_OSM_MAP.keys())

    auftrag_id = request.auftrag_id
    if not auftrag_id:
        try:
            conn = verbinde()
            auftrag_id = erstelle_suchauftrag(
                conn, request.ort, request.radius_km,
                kategorien, request.max_ergebnisse,
            )
            conn.close()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"DB-Fehler: {e}")

    # Hintergrund-Thread starten
    thread = threading.Thread(
        target=_starte_crawler_job,
        args=(request, auftrag_id),
        daemon=True,
    )
    thread.start()

    return JobStatus(auftrag_id=auftrag_id, status="laeuft")


@app.get("/status/{auftrag_id}", response_model=JobStatus)
def job_status(
    auftrag_id: str,
    x_api_key: Optional[str] = Header(None),
):
    """Gibt den Status eines laufenden Jobs zurück."""
    prüfe_api_key(x_api_key)

    # Erst in-memory prüfen
    if auftrag_id in _laufende_jobs:
        j = _laufende_jobs[auftrag_id]
        return JobStatus(
            auftrag_id=auftrag_id,
            status=j["status"],
            gefunden=j.get("gefunden", 0),
            verarbeitet=j.get("verarbeitet", 0),
            fehler=j.get("fehler"),
            anzahl_neu=j.get("anzahl_neu", 0),
            anzahl_wiederverwendet=j.get("anzahl_wiederverwendet", 0),
            anzahl_aktualisiert=j.get("anzahl_aktualisiert", 0),
            uebersprungen=j.get("uebersprungen", 0),
        )

    # Dann DB
    try:
        from crawler.db_writer import verbinde
        conn = verbinde()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """SELECT status, gesamt_gefunden, gesamt_verarbeitet, fehler_meldung,
                          anzahl_neu, anzahl_wiederverwendet, anzahl_aktualisiert
                   FROM suchauftrag WHERE id=%s""",
                (auftrag_id,),
            )
            row = cur.fetchone()
        conn.close()
        if not row:
            raise HTTPException(status_code=404, detail="Auftrag nicht gefunden")
        return JobStatus(
            auftrag_id=auftrag_id,
            status=row["status"],
            gefunden=row["gesamt_gefunden"],
            verarbeitet=row["gesamt_verarbeitet"],
            fehler=row["fehler_meldung"],
            anzahl_neu=row.get("anzahl_neu", 0) or 0,
            anzahl_wiederverwendet=row.get("anzahl_wiederverwendet", 0) or 0,
            anzahl_aktualisiert=row.get("anzahl_aktualisiert", 0) or 0,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/kategorien")
def kategorien_liste():
    """Gibt alle verfügbaren Kategorien zurück."""
    from crawler.sources.overpass import KATEGORIE_OSM_MAP
    return {"kategorien": list(KATEGORIE_OSM_MAP.keys())}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
