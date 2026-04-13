"""
OpenStreetMap / Overpass-API Quelladapter.
Gecoded via Nominatim → Overpass-Abfrage → strukturierte Unternehmensdaten.

Hinweis: Nominatim und Overpass sind kostenlos nutzbar, aber
polites Crawling (Rate-Limiting, User-Agent) ist Pflicht.
"""
from __future__ import annotations

import time
from typing import Optional

from loguru import logger

from crawler.models import Unternehmen
from crawler.utils.http_utils import get_json

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# Mapping: unser internes Kategorie-Kürzel → OSM-Tags
KATEGORIE_OSM_MAP: dict[str, list[str]] = {
    "restaurant":           ["amenity=restaurant"],
    "cafe":                 ["amenity=cafe"],
    "bar":                  ["amenity=bar", "amenity=pub"],
    "friseur":              ["shop=hairdresser"],
    "schoenheitssalon":     ["shop=beauty"],
    "nagelstudio":          ["shop=nail_salon", "shop=beauty"],
    "barber":               ["shop=barber"],
    "zahnarzt":             ["amenity=dentist"],
    "arzt":                 ["amenity=doctors", "amenity=clinic"],
    "physiotherapeut":      ["amenity=physiotherapist", "healthcare=physiotherapist"],
    "fitnessstudio":        ["leisure=fitness_centre", "sport=fitness"],
    "hotel":                ["tourism=hotel", "tourism=guest_house"],
    "immobilien":           ["office=estate_agent"],
    "handwerker":           ["craft=*"],
    "elektriker":           ["craft=electrician"],
    "klempner":             ["craft=plumber"],
    "dachdecker":           ["craft=roofer"],
    "solar":                ["craft=solar_panel_installer", "craft=solar_energy"],
    "heizung":              ["craft=hvac", "craft=heating_engineer"],
    "autowerkstatt":        ["shop=car_repair"],
    "anwalt":               ["office=lawyer"],
    "steuerberater":        ["office=tax_advisor"],
    "unternehmensberater":  ["office=consultant"],
    "einzelhandel":         ["shop=*"],
}


def geocodiere(ort: str) -> Optional[tuple[float, float]]:
    """
    Gibt (lat, lon) für einen Ortsnamen zurück (via Nominatim).
    Wartet 1 Sekunde zwischen Anfragen (Nominatim-Policy).
    """
    time.sleep(1.0)
    daten = get_json(
        NOMINATIM_URL,
        params={"q": ort, "format": "json", "limit": 1},
        timeout=15.0,
    )
    if not daten:
        logger.error(f"Geocodierung fehlgeschlagen für: {ort}")
        return None
    if not isinstance(daten, list) or len(daten) == 0:
        logger.error(f"Kein Ergebnis für: {ort}")
        return None
    lat = float(daten[0]["lat"])
    lon = float(daten[0]["lon"])
    logger.info(f"Geocodiert: {ort} → {lat:.4f}, {lon:.4f}")
    return lat, lon


def _baue_overpass_abfrage(lat: float, lon: float, radius_m: int, osm_tags: list[str]) -> str:
    """Erstellt eine Overpass QL Abfrage für mehrere OSM-Tag-Kombinationen."""
    teile = []
    for tag in osm_tags:
        if "=" in tag:
            schlüssel, wert = tag.split("=", 1)
            if wert == "*":
                filter_str = f'["{schlüssel}"]'
            else:
                filter_str = f'["{schlüssel}"="{wert}"]'
        else:
            filter_str = f'["{tag}"]'

        for typ in ("node", "way", "relation"):
            teile.append(f'{typ}{filter_str}(around:{radius_m},{lat},{lon});')

    return f"""
[out:json][timeout:60];
(
  {chr(10).join("  " + t for t in teile)}
);
out center tags;
"""


def _osm_element_zu_unternehmen(element: dict, kategorie: str) -> Optional[Unternehmen]:
    """Konvertiert ein OSM-Element in ein Unternehmen-Objekt."""
    tags = element.get("tags", {})
    name = tags.get("name")
    if not name:
        return None

    # Koordinaten (node direkt, way/relation via center)
    if element["type"] == "node":
        lat = element.get("lat")
        lon = element.get("lon")
    else:
        center = element.get("center", {})
        lat = center.get("lat")
        lon = center.get("lon")

    quelle_url = (
        f"https://www.openstreetmap.org/{element['type']}/{element['id']}"
    )

    # Adresse zusammenbauen
    strasse = tags.get("addr:street", "")
    hausnummer = tags.get("addr:housenumber", "")
    adresse = f"{strasse} {hausnummer}".strip() or None
    stadt = tags.get("addr:city") or tags.get("addr:town") or tags.get("addr:village")
    postleitzahl = tags.get("addr:postcode")

    # Öffnungszeiten
    oeffnungszeiten = tags.get("opening_hours")

    # Telefon
    telefon = (
        tags.get("phone")
        or tags.get("contact:phone")
        or tags.get("telephone")
    )

    # Webseite
    webseite = (
        tags.get("website")
        or tags.get("contact:website")
        or tags.get("url")
    )
    if webseite and not webseite.startswith("http"):
        webseite = "https://" + webseite

    # Email
    email = tags.get("email") or tags.get("contact:email")

    # Bewertungen (in OSM selten, aber vorhanden bei manchen Elementen)
    bewertung = None
    try:
        if "stars" in tags:
            bewertung = float(tags["stars"])
    except (ValueError, TypeError):
        pass

    # Beschreibung
    beschreibung = tags.get("description") or tags.get("note")

    # OSM-Kategorie-Label bestimmen
    osm_kategorie = (
        tags.get("amenity")
        or tags.get("shop")
        or tags.get("craft")
        or tags.get("office")
        or tags.get("leisure")
        or tags.get("tourism")
        or tags.get("healthcare")
        or kategorie
    )

    return Unternehmen(
        name=name,
        kategorie=kategorie,
        beschreibung=beschreibung,
        adresse=adresse,
        stadt=stadt,
        postleitzahl=postleitzahl,
        telefon=_bereinige_telefon(telefon),
        email=email.lower() if email else None,
        webseite=webseite,
        quelle_url=quelle_url,
        oeffnungszeiten=oeffnungszeiten,
        bewertung=bewertung,
        hat_webseite=bool(webseite),
        hat_email=bool(email),
        hat_telefon=bool(telefon),
    )


def _bereinige_telefon(nummer: Optional[str]) -> Optional[str]:
    if not nummer:
        return None
    return nummer.strip().replace("–", "-")


def suche_unternehmen(
    ort: str,
    radius_km: int = 10,
    kategorien: Optional[list[str]] = None,
    max_ergebnisse: int = 100,
) -> list[Unternehmen]:
    """
    Hauptfunktion: Sucht Unternehmen via Overpass API.

    Args:
        ort: Ortsname (z.B. "Worms, Deutschland")
        radius_km: Suchradius in Kilometern
        kategorien: Liste von Kategorie-Kürzeln (siehe KATEGORIE_OSM_MAP)
        max_ergebnisse: Maximale Gesamtanzahl

    Returns:
        Liste von Unternehmen-Objekten
    """
    if kategorien is None:
        kategorien = list(KATEGORIE_OSM_MAP.keys())

    coords = geocodiere(ort)
    if coords is None:
        return []

    lat, lon = coords
    radius_m = radius_km * 1000

    alle: list[Unternehmen] = []
    gesehene_ids: set[int] = set()

    for kategorie in kategorien:
        if len(alle) >= max_ergebnisse:
            break

        osm_tags = KATEGORIE_OSM_MAP.get(kategorie)
        if not osm_tags:
            logger.warning(f"Unbekannte Kategorie: {kategorie}")
            continue

        abfrage = _baue_overpass_abfrage(lat, lon, radius_m, osm_tags)
        logger.info(f"Overpass-Abfrage für Kategorie: {kategorie}")

        daten = get_json(OVERPASS_URL, params={"data": abfrage}, timeout=60.0)
        if not daten or "elements" not in daten:
            logger.warning(f"Keine Ergebnisse für Kategorie: {kategorie}")
            continue

        elemente = daten["elements"]
        logger.info(f"  → {len(elemente)} Elemente gefunden für {kategorie}")

        for el in elemente:
            if len(alle) >= max_ergebnisse:
                break
            el_id = el.get("id")
            if el_id in gesehene_ids:
                continue
            gesehene_ids.add(el_id)

            u = _osm_element_zu_unternehmen(el, kategorie)
            if u:
                alle.append(u)

        # Höfliche Pause zwischen Kategorien
        time.sleep(1.5)

    logger.info(f"Gesamt gefunden: {len(alle)} Unternehmen in '{ort}'")
    return alle
