"""
Datenmodelle für den Crawler (Pydantic).
Entsprechen dem Prisma-Schema, aber Python-seitig.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class WebseitenAnalyse:
    startseite_title: Optional[str] = None
    meta_beschreibung: Optional[str] = None
    gecrawlte_seiten: list[str] = field(default_factory=list)
    kontaktformular_gefunden: bool = False
    cta_gefunden: bool = False
    buchungs_signal_gefunden: bool = False
    whatsapp_gefunden: bool = False
    social_links_gefunden: list[str] = field(default_factory=list)
    sieht_veraltet_aus: bool = False
    mobil_signale: Optional[str] = None
    technologie_stack: Optional[str] = None
    impressum_text: Optional[str] = None
    ueber_uns_text: Optional[str] = None
    leistungen_text: Optional[str] = None
    webseite_qualitaet_score: int = 0


@dataclass
class Unternehmen:
    # Basisdaten
    name: str
    kategorie: Optional[str] = None
    beschreibung: Optional[str] = None
    adresse: Optional[str] = None
    stadt: Optional[str] = None
    postleitzahl: Optional[str] = None
    telefon: Optional[str] = None
    email: Optional[str] = None
    webseite: Optional[str] = None
    quelle_url: Optional[str] = None
    bewertung: Optional[float] = None
    bewertungsanzahl: Optional[int] = None
    oeffnungszeiten: Optional[str] = None

    # Social Media
    instagram: Optional[str] = None
    facebook: Optional[str] = None
    linkedin: Optional[str] = None
    whatsapp: Optional[str] = None

    # Flags
    hat_webseite: bool = False
    hat_email: bool = False
    hat_telefon: bool = False

    # Scoring (wird später befüllt)
    lead_score: int = 0
    lead_temperatur: str = "KALT"
    webseite_bedarf_score: int = 0
    automation_bedarf_score: int = 0
    webseite_qualitaet_score: int = 0
    wahrscheinliche_schmerzpunkte: Optional[str] = None
    empfohlene_angebote: Optional[str] = None
    verkaufs_winkel: Optional[str] = None
    heiss_lead_grund: Optional[str] = None
    score_erklaerung: Optional[str] = None
    erstes_kontaktnachricht: Optional[str] = None
    pitch_winkel: Optional[str] = None
    entscheidungstraeger_name: Optional[str] = None
    rechtlicher_name: Optional[str] = None
    zusammenfassung: Optional[str] = None
    leistungen: Optional[str] = None

    # Webseitenanalyse
    webseiten_analyse: Optional[WebseitenAnalyse] = None

    def to_csv_row(self) -> dict:
        """Flacht das Objekt für CSV-Export."""
        row = {
            "name": self.name,
            "kategorie": self.kategorie or "",
            "stadt": self.stadt or "",
            "postleitzahl": self.postleitzahl or "",
            "adresse": self.adresse or "",
            "telefon": self.telefon or "",
            "email": self.email or "",
            "webseite": self.webseite or "",
            "bewertung": self.bewertung or "",
            "bewertungsanzahl": self.bewertungsanzahl or "",
            "lead_score": self.lead_score,
            "lead_temperatur": self.lead_temperatur,
            "webseite_bedarf_score": self.webseite_bedarf_score,
            "automation_bedarf_score": self.automation_bedarf_score,
            "hat_webseite": self.hat_webseite,
            "hat_email": self.hat_email,
            "hat_telefon": self.hat_telefon,
            "empfohlene_angebote": self.empfohlene_angebote or "",
            "verkaufs_winkel": self.verkaufs_winkel or "",
            "wahrscheinliche_schmerzpunkte": self.wahrscheinliche_schmerzpunkte or "",
            "heiss_lead_grund": self.heiss_lead_grund or "",
            "entscheidungstraeger_name": self.entscheidungstraeger_name or "",
            "zusammenfassung": self.zusammenfassung or "",
            "leistungen": self.leistungen or "",
            "erstes_kontaktnachricht": self.erstes_kontaktnachricht or "",
            "instagram": self.instagram or "",
            "facebook": self.facebook or "",
            "quelle_url": self.quelle_url or "",
        }
        return row
