#!/usr/bin/env python3
"""
LeadScout Crawler – Haupt-CLI.

Beispiel:
  python crawler.py --place "Worms, Deutschland" --radius-km 20 \
    --kategorien restaurant friseur elektriker zahnarzt \
    --max 100 --output leads.csv

  python crawler.py --place "München" --kategorien restaurant hotel \
    --max 50 --db  # Direkt in Datenbank speichern
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger
from tqdm import tqdm

load_dotenv()

# Logging konfigurieren
logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}",
    level="INFO",
)
logger.add(
    "logs/crawler_{time}.log",
    rotation="50 MB",
    retention="7 days",
    level="DEBUG",
    encoding="utf-8",
)

Path("logs").mkdir(exist_ok=True)
Path("output").mkdir(exist_ok=True)

from crawler.sources.overpass import suche_unternehmen, KATEGORIE_OSM_MAP
from crawler.enricher import reichere_an
from crawler.scorer import bewerte
from crawler.utils.http_utils import rate_limiter_setzen


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="LeadScout – Lokale Unternehmens-Leadgenerierung",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Verfügbare Kategorien:
  """ + "  ".join(KATEGORIE_OSM_MAP.keys()),
    )
    parser.add_argument(
        "--place", "--ort",
        required=True,
        help='Ortsname, z.B. "Worms, Deutschland"',
    )
    parser.add_argument(
        "--radius-km",
        type=int,
        default=10,
        help="Suchradius in Kilometern (Standard: 10)",
    )
    parser.add_argument(
        "--kategorien", "--categories",
        nargs="+",
        default=list(KATEGORIE_OSM_MAP.keys()),
        help="Kategorien zum Durchsuchen",
    )
    parser.add_argument(
        "--max", "--max-results",
        type=int,
        default=100,
        dest="max_ergebnisse",
        help="Maximale Anzahl Ergebnisse (Standard: 100)",
    )
    parser.add_argument(
        "--output", "-o",
        default="output/leads.csv",
        help="Ausgabedatei (CSV oder JSON, Standard: output/leads.csv)",
    )
    parser.add_argument(
        "--format",
        choices=["csv", "json"],
        default=None,
        help="Ausgabeformat (automatisch aus Dateiendung erkannt)",
    )
    parser.add_argument(
        "--db",
        action="store_true",
        help="Zusätzlich in Datenbank speichern",
    )
    parser.add_argument(
        "--kein-enrichment",
        action="store_true",
        help="Webseiten-Anreicherung überspringen (schneller)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=2.0,
        help="Pause zwischen Anfragen in Sekunden (Standard: 2.0)",
    )
    parser.add_argument(
        "--auftrag-id",
        default=None,
        help="Suchauftrags-ID (für Frontend-Integration)",
    )
    return parser.parse_args()


def speichere_csv(unternehmen_liste: list, pfad: str) -> None:
    if not unternehmen_liste:
        logger.warning("Keine Daten zum Speichern")
        return
    felder = list(unternehmen_liste[0].to_csv_row().keys())
    with open(pfad, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=felder)
        writer.writeheader()
        for u in unternehmen_liste:
            writer.writerow(u.to_csv_row())
    logger.info(f"CSV gespeichert: {pfad} ({len(unternehmen_liste)} Einträge)")


def speichere_json(unternehmen_liste: list, pfad: str) -> None:
    daten = [u.__dict__ for u in unternehmen_liste]
    # webseiten_analyse als dict
    for d in daten:
        if d.get("webseiten_analyse"):
            d["webseiten_analyse"] = d["webseiten_analyse"].__dict__
    with open(pfad, "w", encoding="utf-8") as f:
        json.dump(daten, f, ensure_ascii=False, indent=2, default=str)
    logger.info(f"JSON gespeichert: {pfad} ({len(unternehmen_liste)} Einträge)")


def speichere_db(unternehmen_liste: list, auftrag_id: str) -> None:
    from crawler.db_writer import verbinde, speichere_unternehmen, aktualisiere_suchauftrag

    try:
        conn = verbinde()
        gespeichert = 0
        for u in unternehmen_liste:
            try:
                speichere_unternehmen(conn, u, auftrag_id)
                gespeichert += 1
            except Exception as e:
                logger.error(f"DB-Fehler für {u.name}: {e}")

        aktualisiere_suchauftrag(
            conn, auftrag_id, "abgeschlossen",
            len(unternehmen_liste), gespeichert,
        )
        conn.close()
        logger.info(f"Datenbank: {gespeichert} Unternehmen gespeichert")
    except Exception as e:
        logger.error(f"Datenbankverbindung fehlgeschlagen: {e}")


def main() -> None:
    args = parse_args()

    # Rate-Limiter setzen
    rate_limiter_setzen(args.delay)

    logger.info(f"=== LeadScout Crawler ===")
    logger.info(f"Ort: {args.place}")
    logger.info(f"Radius: {args.radius_km} km")
    logger.info(f"Kategorien: {', '.join(args.kategorien)}")
    logger.info(f"Max. Ergebnisse: {args.max_ergebnisse}")

    # 1. Unternehmen entdecken
    logger.info("Phase 1: Unternehmenssuche …")
    unternehmen_liste = suche_unternehmen(
        ort=args.place,
        radius_km=args.radius_km,
        kategorien=args.kategorien,
        max_ergebnisse=args.max_ergebnisse,
    )

    if not unternehmen_liste:
        logger.warning("Keine Unternehmen gefunden. Abbruch.")
        sys.exit(0)

    logger.info(f"Gefunden: {len(unternehmen_liste)} Unternehmen")

    # 2. Webseiten-Anreicherung
    if not args.kein_enrichment:
        logger.info("Phase 2: Webseiten-Anreicherung …")
        mit_webseite = [u for u in unternehmen_liste if u.hat_webseite]
        logger.info(f"  {len(mit_webseite)} Unternehmen haben eine Webseite")

        for u in tqdm(unternehmen_liste, desc="Anreicherung", unit="Unternehmen"):
            if u.hat_webseite:
                try:
                    reichere_an(u)
                except Exception as e:
                    logger.warning(f"Anreicherung fehlgeschlagen für {u.name}: {e}")
    else:
        logger.info("Phase 2: Webseiten-Anreicherung übersprungen (--kein-enrichment)")

    # 3. Scoring
    logger.info("Phase 3: Scoring …")
    for u in unternehmen_liste:
        bewerte(u)

    # Statistik
    heiss = sum(1 for u in unternehmen_liste if u.lead_temperatur == "HEISS")
    warm = sum(1 for u in unternehmen_liste if u.lead_temperatur == "WARM")
    kalt = sum(1 for u in unternehmen_liste if u.lead_temperatur == "KALT")
    logger.info(f"Scoring abgeschlossen: {heiss} heiß | {warm} warm | {kalt} kalt")

    # 4. Ausgabe
    output_pfad = args.output
    fmt = args.format
    if fmt is None:
        fmt = "json" if output_pfad.endswith(".json") else "csv"

    if fmt == "json":
        speichere_json(unternehmen_liste, output_pfad)
    else:
        speichere_csv(unternehmen_liste, output_pfad)

    # 5. Optional: Datenbank
    if args.db:
        from crawler.db_writer import verbinde, erstelle_suchauftrag

        auftrag_id = args.auftrag_id
        if not auftrag_id:
            try:
                conn = verbinde()
                auftrag_id = erstelle_suchauftrag(
                    conn, args.place, args.radius_km,
                    args.kategorien, args.max_ergebnisse,
                )
                conn.close()
            except Exception as e:
                logger.error(f"Konnte Suchauftrag nicht erstellen: {e}")
                auftrag_id = None

        if auftrag_id:
            speichere_db(unternehmen_liste, auftrag_id)

    logger.info("=== Crawling abgeschlossen ===")


if __name__ == "__main__":
    main()
