"""
FastAPI-Service: Stellt HTTP-Endpunkte für die Next.js-Frontend-Integration bereit.
Läuft als separater Prozess auf Port 8000.
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

app = FastAPI(
    title="LeadScout Crawler API",
    description="Interner Crawler-Service für die LeadScout-Plattform",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", os.environ.get("NEXTAUTH_URL", "")],
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


# ── Auth-Helper ────────────────────────────────────────────────────────────────

def prüfe_api_key(x_api_key: Optional[str] = Header(None)) -> None:
    if API_KEY and x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Ungültiger API-Key")


# ── Hintergrund-Crawler ────────────────────────────────────────────────────────

def _starte_crawler_job(request: CrawlerStartRequest, auftrag_id: str) -> None:
    """Läuft in einem separaten Thread."""
    from crawler.sources.overpass import suche_unternehmen, KATEGORIE_OSM_MAP
    from crawler.enricher import reichere_an
    from crawler.scorer import bewerte
    from crawler.db_writer import verbinde, speichere_unternehmen, aktualisiere_suchauftrag
    from crawler.utils.http_utils import rate_limiter_setzen

    _laufende_jobs[auftrag_id] = {"status": "laeuft", "gefunden": 0, "verarbeitet": 0}

    # ── Crawler-Konfig aus Frontend anwenden ──────────────────────────────────
    if request.crawler_config:
        delay = request.crawler_config.get("delay_seconds")
        if isinstance(delay, (int, float)) and delay > 0:
            rate_limiter_setzen(float(delay))
            logger.info(f"[Job {auftrag_id}] Rate-Limiter: {delay}s Verzögerung")

    kategorien = request.kategorien or list(KATEGORIE_OSM_MAP.keys())

    try:
        # Phase 1: Suche
        logger.info(f"[Job {auftrag_id}] Starte Suche: {request.ort}")
        unternehmen_liste = suche_unternehmen(
            ort=request.ort,
            radius_km=request.radius_km,
            kategorien=kategorien,
            max_ergebnisse=request.max_ergebnisse,
        )
        _laufende_jobs[auftrag_id]["gefunden"] = len(unternehmen_liste)
        logger.info(f"[Job {auftrag_id}] Gefunden: {len(unternehmen_liste)}")

        # Phase 2: Enrichment
        if request.enrichment:
            for u in unternehmen_liste:
                if u.hat_webseite:
                    try:
                        reichere_an(u)
                    except Exception as e:
                        logger.warning(f"Enrichment fehlgeschlagen {u.name}: {e}")

        # Phase 3: Scoring (mit optionaler Frontend-Konfig)
        for u in unternehmen_liste:
            bewerte(u, konfig=request.scoring_config)

        # Phase 4: DB speichern
        conn = verbinde()
        gespeichert = 0
        for u in unternehmen_liste:
            try:
                speichere_unternehmen(conn, u, auftrag_id)
                gespeichert += 1
                _laufende_jobs[auftrag_id]["verarbeitet"] = gespeichert
            except Exception as e:
                logger.error(f"DB-Fehler für {u.name}: {e}")

        aktualisiere_suchauftrag(
            conn, auftrag_id, "abgeschlossen",
            len(unternehmen_liste), gespeichert,
        )
        conn.close()

        _laufende_jobs[auftrag_id]["status"] = "abgeschlossen"
        logger.info(f"[Job {auftrag_id}] Abgeschlossen: {gespeichert} gespeichert")

    except Exception as e:
        logger.error(f"[Job {auftrag_id}] Fehler: {e}")
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
    return {"status": "ok", "service": "LeadScout Crawler"}


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

    return JobStatus(
        auftrag_id=auftrag_id,
        status="laeuft",
    )


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
        )

    # Dann DB
    try:
        from crawler.db_writer import verbinde
        conn = verbinde()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT status, gesamt_gefunden, gesamt_verarbeitet, fehler_meldung FROM suchauftrag WHERE id=%s",
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
