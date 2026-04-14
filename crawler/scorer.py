"""
Scoring-Engine: Bewertet Unternehmen als Verkaufschancen (0–100).
Trennt klar zwischen extrahierten Fakten und Heuristiken.
"""
from __future__ import annotations

from typing import Optional, Any

from crawler.models import Unternehmen

# ── Standard-Scoring-Faktoren ─────────────────────────────────────────────────
# Diese Werte werden verwendet, wenn kein konfig-Dict übergeben wird.
# Können über die Frontend-Einstellungen überschrieben werden.

DEFAULT_FAKTOREN: dict[str, int] = {
    "kein_website": 30,
    "website_sehr_schwach": 18,
    "website_ausbaufaehig": 12,
    "kein_cta": 10,
    "keine_buchung_kontakt": 10,
    "kein_buchungssystem": 5,
    "veraltet_indikatoren": 5,
    "keine_email": 8,
    "telefon_intensiv_bonus": 12,
    "buchung_intensiv_bonus": 10,
    "lead_reaktionsabhaengig": 10,
    "whatsapp_potential": 5,
    "moderner_starker_auftritt": -15,
}

HEISS_SCHWELLE = 75
WARM_SCHWELLE = 45

# ── Kategorie-Profile ─────────────────────────────────────────────────────────

KATEGORIE_PROFILE: dict[str, dict] = {
    "restaurant": {
        "telefon_intensiv": True,
        "buchung_intensiv": True,
        "automation_bonus": 15,
        "webseite_bonus": 15,
        "ki_telefon": True,
        "whatsapp": True,
        "booking": True,
        "hauptangebot": "Webseite + Reservierungssystem + KI-Telefonagent",
        "pitch": "Restaurants verlieren täglich Reservierungen über nicht erreichtes Telefon. Automatisieren Sie Buchungen 24/7.",
    },
    "cafe": {
        "telefon_intensiv": False,
        "buchung_intensiv": False,
        "automation_bonus": 8,
        "webseite_bonus": 18,
        "ki_telefon": False,
        "whatsapp": True,
        "booking": False,
        "hauptangebot": "Neue Webseite mit Speisekarte + Instagram-Integration",
        "pitch": "Ein ansprechender Online-Auftritt zieht neue Gäste an – besonders über Google-Suche und Instagram.",
    },
    "bar": {
        "telefon_intensiv": False,
        "buchung_intensiv": True,
        "automation_bonus": 8,
        "webseite_bonus": 15,
        "ki_telefon": False,
        "whatsapp": True,
        "booking": True,
        "hauptangebot": "Webseite + Event-Buchungssystem + WhatsApp-Reservierung",
        "pitch": "Tischreservierungen und Events lassen sich einfach automatisieren – mehr Umsatz, weniger Aufwand.",
    },
    "friseur": {
        "telefon_intensiv": True,
        "buchung_intensiv": True,
        "automation_bonus": 15,
        "webseite_bonus": 12,
        "ki_telefon": True,
        "whatsapp": True,
        "booking": True,
        "hauptangebot": "Online-Buchungssystem + automatische Terminerinnerungen",
        "pitch": "Jeder No-Show kostet Geld. Automatische Erinnerungen per WhatsApp reduzieren Ausfälle bis zu 40%.",
    },
    "schoenheitssalon": {
        "telefon_intensiv": True,
        "buchung_intensiv": True,
        "automation_bonus": 15,
        "webseite_bonus": 12,
        "ki_telefon": True,
        "whatsapp": True,
        "booking": True,
        "hauptangebot": "Online-Buchung + Erinnerungsbot + Website-Relaunch",
        "pitch": "Schönheitssalons profitieren enorm von automatisierten Terminerinnerungen und Online-Buchung.",
    },
    "nagelstudio": {
        "telefon_intensiv": True,
        "buchung_intensiv": True,
        "automation_bonus": 15,
        "webseite_bonus": 12,
        "ki_telefon": False,
        "whatsapp": True,
        "booking": True,
        "hauptangebot": "Online-Buchung + WhatsApp-Buchungsbot",
        "pitch": "Online-Buchung ersetzt lästige Telefonanrufe – Kunden buchen wann es ihnen passt.",
    },
    "barber": {
        "telefon_intensiv": True,
        "buchung_intensiv": True,
        "automation_bonus": 12,
        "webseite_bonus": 12,
        "ki_telefon": False,
        "whatsapp": True,
        "booking": True,
        "hauptangebot": "Online-Buchung + WhatsApp-Bot",
        "pitch": "Viele Barbershops laufen noch komplett über Telefon und WhatsApp manuell – das kostet Zeit.",
    },
    "zahnarzt": {
        "telefon_intensiv": True,
        "buchung_intensiv": True,
        "automation_bonus": 18,
        "webseite_bonus": 8,
        "ki_telefon": True,
        "whatsapp": False,
        "booking": True,
        "hauptangebot": "KI-Telefonagent + Online-Terminbuchung",
        "pitch": "Ihre Sprechstundenhilfe verbringt Stunden am Telefon. Unser KI-Agent bucht Termine automatisch und filtert Notfälle.",
    },
    "arzt": {
        "telefon_intensiv": True,
        "buchung_intensiv": True,
        "automation_bonus": 18,
        "webseite_bonus": 8,
        "ki_telefon": True,
        "whatsapp": False,
        "booking": True,
        "hauptangebot": "KI-Telefonagent + Online-Terminbuchung",
        "pitch": "Arztpraxen kämpfen täglich mit überlasteten Telefonleitungen. KI-Telefon entlastet sofort.",
    },
    "physiotherapeut": {
        "telefon_intensiv": True,
        "buchung_intensiv": True,
        "automation_bonus": 15,
        "webseite_bonus": 10,
        "ki_telefon": True,
        "whatsapp": True,
        "booking": True,
        "hauptangebot": "KI-Telefonagent + Buchungsautomatisierung",
        "pitch": "Physiopraxen verlieren täglich Patienten durch nicht erreichtes Telefon. Wir lösen das.",
    },
    "fitnessstudio": {
        "telefon_intensiv": False,
        "buchung_intensiv": True,
        "automation_bonus": 12,
        "webseite_bonus": 15,
        "ki_telefon": False,
        "whatsapp": True,
        "booking": True,
        "hauptangebot": "Lead-Follow-up-System + Mitglieder-Onboarding-Automation",
        "pitch": "Fitnessstudios verlieren potenzielle Mitglieder, die online anfragen und nie zurückgerufen werden.",
    },
    "hotel": {
        "telefon_intensiv": True,
        "buchung_intensiv": True,
        "automation_bonus": 12,
        "webseite_bonus": 15,
        "ki_telefon": True,
        "whatsapp": True,
        "booking": True,
        "hauptangebot": "Webseite-Upgrade + Direktbuchung + WhatsApp-Concierge",
        "pitch": "Hotels zahlen hohe Provisionen an Booking.com. Direktbuchungen über eigene Webseite sparen das.",
    },
    "immobilien": {
        "telefon_intensiv": True,
        "buchung_intensiv": True,
        "automation_bonus": 15,
        "webseite_bonus": 10,
        "ki_telefon": True,
        "whatsapp": False,
        "booking": True,
        "hauptangebot": "Lead-Qualifizierungsbot + automatisches Follow-up",
        "pitch": "Immobilienmakler verlieren Deals durch langsame Lead-Reaktion. Automatisiertes Follow-up schließt die Lücke.",
    },
    "handwerker": {
        "telefon_intensiv": True,
        "buchung_intensiv": False,
        "automation_bonus": 15,
        "webseite_bonus": 15,
        "ki_telefon": True,
        "whatsapp": True,
        "booking": False,
        "hauptangebot": "Lead-Qualifizierungsbot + KI-Telefon + Angebots-Automatisierung",
        "pitch": "Handwerker verlieren Aufträge, weil sie auf Baustelle nicht ans Telefon können. KI-Telefon nimmt für Sie ab.",
    },
    "elektriker": {
        "telefon_intensiv": True,
        "buchung_intensiv": False,
        "automation_bonus": 15,
        "webseite_bonus": 15,
        "ki_telefon": True,
        "whatsapp": True,
        "booking": False,
        "hauptangebot": "KI-Telefonagent + Lead-Qualifizierung",
        "pitch": "Elektrikerbetriebe verpassen täglich Aufträge durch verpasste Anrufe.",
    },
    "klempner": {
        "telefon_intensiv": True,
        "buchung_intensiv": False,
        "automation_bonus": 15,
        "webseite_bonus": 15,
        "ki_telefon": True,
        "whatsapp": True,
        "booking": False,
        "hauptangebot": "KI-Telefonagent (Notdienst) + Lead-Qualifizierung",
        "pitch": "Notdienstanrufe 24/7 entgegennehmen und automatisch weiterleiten – kein verpasster Auftrag.",
    },
    "dachdecker": {
        "telefon_intensiv": True,
        "buchung_intensiv": False,
        "automation_bonus": 12,
        "webseite_bonus": 15,
        "ki_telefon": True,
        "whatsapp": False,
        "booking": False,
        "hauptangebot": "Lead-Qualifizierung + Angebots-Automation",
        "pitch": "Dachdecker bekommen viele Anfragen, aber manuelle Qualifizierung kostet Zeit.",
    },
    "solar": {
        "telefon_intensiv": False,
        "buchung_intensiv": True,
        "automation_bonus": 18,
        "webseite_bonus": 15,
        "ki_telefon": True,
        "whatsapp": False,
        "booking": True,
        "hauptangebot": "Lead-Qualifizierungsbot + automatisches Follow-up + Beratungstermin-Buchung",
        "pitch": "Solarfirmen erhalten viele Anfragen, aber nur wenige werden schnell genug qualifiziert. Automatisieren Sie den Prozess.",
    },
    "heizung": {
        "telefon_intensiv": True,
        "buchung_intensiv": False,
        "automation_bonus": 12,
        "webseite_bonus": 12,
        "ki_telefon": True,
        "whatsapp": False,
        "booking": False,
        "hauptangebot": "KI-Telefon + Lead-Qualifizierung",
        "pitch": "Heizungsbetriebe haben hohe Saisonspitzen – KI-Telefon fängt Anfragen automatisch ab.",
    },
    "autowerkstatt": {
        "telefon_intensiv": True,
        "buchung_intensiv": True,
        "automation_bonus": 12,
        "webseite_bonus": 12,
        "ki_telefon": True,
        "whatsapp": True,
        "booking": True,
        "hauptangebot": "KI-Telefonagent + Online-Terminbuchung + Status-Updates per WhatsApp",
        "pitch": "Kunden wollen wissen wann ihr Auto fertig ist. Automatische Status-Updates per WhatsApp sind ein Differenzierungsmerkmal.",
    },
    "anwalt": {
        "telefon_intensiv": True,
        "buchung_intensiv": True,
        "automation_bonus": 12,
        "webseite_bonus": 10,
        "ki_telefon": True,
        "whatsapp": False,
        "booking": True,
        "hauptangebot": "Erstberatungs-Buchungssystem + Lead-Qualifizierung",
        "pitch": "Anwälte verlieren potenzielle Mandanten, die keine Antwort auf Erstanfragen bekommen.",
    },
    "steuerberater": {
        "telefon_intensiv": True,
        "buchung_intensiv": True,
        "automation_bonus": 10,
        "webseite_bonus": 10,
        "ki_telefon": True,
        "whatsapp": False,
        "booking": True,
        "hauptangebot": "Mandanten-Onboarding-Automation + Terminbuchungssystem",
        "pitch": "Steuerberater-Kanzleien gewinnen mit automatisiertem Mandanten-Onboarding einen klaren Wettbewerbsvorteil.",
    },
    "unternehmensberater": {
        "telefon_intensiv": False,
        "buchung_intensiv": True,
        "automation_bonus": 10,
        "webseite_bonus": 12,
        "ki_telefon": False,
        "whatsapp": False,
        "booking": True,
        "hauptangebot": "Lead-Follow-up + Erstgespräch-Buchungssystem",
        "pitch": "Berater brauchen einen professionellen Erstgespräch-Prozess der automatisch qualifiziert.",
    },
    "einzelhandel": {
        "telefon_intensiv": False,
        "buchung_intensiv": False,
        "automation_bonus": 8,
        "webseite_bonus": 18,
        "ki_telefon": False,
        "whatsapp": True,
        "booking": False,
        "hauptangebot": "Online-Shop / Webseite + WhatsApp-Bestellkanal",
        "pitch": "Lokale Händler brauchen einen Online-Auftritt um gegen große Plattformen zu bestehen.",
    },
}

DEFAULT_PROFIL = {
    "telefon_intensiv": False,
    "buchung_intensiv": False,
    "automation_bonus": 8,
    "webseite_bonus": 10,
    "ki_telefon": False,
    "whatsapp": False,
    "booking": False,
    "hauptangebot": "Webseite + digitale Präsenz",
    "pitch": "Jedes lokale Unternehmen profitiert von einer modernen Online-Präsenz.",
}

# Kategorien, bei denen langsame Lead-Reaktion direkt Aufträge kostet
_LEAD_ABHAENGIGE_KATEGORIEN: frozenset[str] = frozenset({
    "fitnessstudio",
    "immobilien",
    "handwerker",
    "elektriker",
    "klempner",
    "dachdecker",
    "solar",
    "heizung",
    "anwalt",
    "steuerberater",
    "unternehmensberater",
})

# Keyword-Fallback für nicht exakt gematchte Kategorie-Strings
_KATEGORIE_KEYWORDS: dict[str, list[str]] = {
    "restaurant":           ["restaurant", "pizzeria", "imbiss", "gaststätte", "speise"],
    "cafe":                 ["café", "cafe", "kaffee", "bäckerei", "konditor"],
    "bar":                  ["bar", "pub", "lounge", "club", "disco"],
    "friseur":              ["friseur", "frisör", "hair", "coiffeur"],
    "schoenheitssalon":     ["beauty", "kosmetik", "wellness", "spa"],
    "nagelstudio":          ["nagel", "nail"],
    "barber":               ["barber", "barbershop", "herrenfriseur"],
    "zahnarzt":             ["zahnarzt", "zahnärztin", "dental", "orthodont"],
    "arzt":                 ["arzt", "ärztin", "praxis", "medizin", "klinik"],
    "physiotherapeut":      ["physio", "krankengymnastik", "osteopathie"],
    "fitnessstudio":        ["fitness", "gym", "sport", "training"],
    "hotel":                ["hotel", "pension", "gasthaus", "hostel"],
    "immobilien":           ["immobilien", "makler", "hausverwaltung"],
    "handwerker":           ["handwerk", "bau", "montage", "renovier"],
    "elektriker":           ["elektrik", "elektriker", "elektro"],
    "klempner":             ["klempner", "sanitär", "rohr"],
    "dachdecker":           ["dach", "dachdeck"],
    "solar":                ["solar", "photovoltaik", "pv-anlage"],
    "heizung":              ["heizung", "wärmepumpe", "hvac"],
    "autowerkstatt":        ["werkstatt", "kfz", "reifenwechsel"],
    "anwalt":               ["anwalt", "rechtsanwalt", "kanzlei"],
    "steuerberater":        ["steuer", "buchhalter"],
    "unternehmensberater":  ["unternehmensberatung", "consulting"],
    "einzelhandel":         ["laden", "boutique", "handel"],
}


def _hole_profil(kategorie: Optional[str]) -> dict:
    """
    Gibt das Kategorie-Profil zurück.
    Versucht erst Exakt-Match, dann Keyword-Fallback, dann DEFAULT_PROFIL.
    """
    if not kategorie:
        return DEFAULT_PROFIL
    key = kategorie.lower().strip()
    if key in KATEGORIE_PROFILE:
        return KATEGORIE_PROFILE[key]
    for profil_key, keywords in _KATEGORIE_KEYWORDS.items():
        if any(kw in key for kw in keywords):
            return KATEGORIE_PROFILE[profil_key]
    return DEFAULT_PROFIL


def bewerte(unternehmen: Unternehmen, konfig: Optional[dict[str, Any]] = None) -> Unternehmen:
    """
    Berechnet Lead-Score, Temperatur und alle Verkaufsfelder.
    Gibt das aktualisierte Unternehmen zurück.

    konfig: optionales Dict aus den Frontend-Einstellungen, z.B.:
        {
          "scoring": { "heiss_schwelle": 75, "warm_schwelle": 45, "faktoren": {...} },
          "kategorien": { "restaurant": { ... }, ... }
        }
    """
    # ── Konfig auflösen ───────────────────────────────────────────────────────
    sc = (konfig or {}).get("scoring") or {}
    faktoren: dict[str, int] = {**DEFAULT_FAKTOREN, **(sc.get("faktoren") or {})}
    heiss_schwelle: int = int(sc.get("heiss_schwelle", HEISS_SCHWELLE))
    warm_schwelle: int = int(sc.get("warm_schwelle", WARM_SCHWELLE))

    # Kategorie-Profil: ggf. aus Frontend-Konfig überschreiben
    kat_override = (konfig or {}).get("kategorien") or {}
    kat_key = (unternehmen.kategorie or "").lower().strip()
    if kat_key and kat_key in kat_override:
        profil = {**_hole_profil(unternehmen.kategorie), **kat_override[kat_key]}
    else:
        profil = _hole_profil(unternehmen.kategorie)

    analyse = unternehmen.webseiten_analyse
    befund = unternehmen.anreicherungs_befund
    # Signalquelle: WebseitenAnalyse bevorzugt, AnreicherungsBefund als Fallback
    _sig = analyse or befund

    punkte = 0
    erklaerung_teile: list[str] = []
    schmerzpunkte: list[str] = []
    angebote: list[str] = []

    f = faktoren  # Kurzname

    # ── Webseiten-Faktoren ─────────────────────────────────────────────────────
    if not unternehmen.hat_webseite:
        punkte += f["kein_website"]
        erklaerung_teile.append(f"Kein Website (+{f['kein_website']})")
        schmerzpunkte.append("Kein Online-Auftritt – potenzielle Kunden finden das Unternehmen nicht online")
        angebote.append("Neue professionelle Webseite")
    else:
        website_qualitaet = unternehmen.webseite_qualitaet_score

        if website_qualitaet < 30:
            punkte += f["website_sehr_schwach"]
            erklaerung_teile.append(f"Website sehr schwach/veraltet (+{f['website_sehr_schwach']})")
            schmerzpunkte.append("Website ist veraltet und verliert täglich potenzielle Kunden")
            angebote.append("Website-Relaunch / Modernisierung")
        elif website_qualitaet < 50:
            punkte += f["website_ausbaufaehig"]
            erklaerung_teile.append(f"Website ausbaufähig (+{f['website_ausbaufaehig']})")
            schmerzpunkte.append("Website hat keine klare Conversion-Optimierung")
            angebote.append("Website-Optimierung mit CTA und Conversion-Elementen")

        if _sig:
            if not _sig.cta_gefunden:
                punkte += f["kein_cta"]
                erklaerung_teile.append(f"Kein CTA gefunden (+{f['kein_cta']})")
                schmerzpunkte.append("Keine klare Handlungsaufforderung auf der Website")

            # Buchungs-/Kontaktoptimierung als kombinierter Faktor
            if not _sig.kontaktformular_gefunden and not _sig.buchungs_signal_gefunden:
                punkte += f["keine_buchung_kontakt"]
                erklaerung_teile.append(f"Keine Buchungs-/Kontaktoptimierung (+{f['keine_buchung_kontakt']})")
                angebote.append("Online-Buchungs- oder Anfrage-System")
            elif not _sig.buchungs_signal_gefunden:
                punkte += f["kein_buchungssystem"]
                erklaerung_teile.append(f"Kein Buchungssystem (+{f['kein_buchungssystem']})")
                angebote.append("Online-Buchungs- oder Anfrage-System")

            if _sig.sieht_veraltet_aus:
                punkte += f["veraltet_indikatoren"]
                erklaerung_teile.append(f"Veraltete Indikatoren im HTML (+{f['veraltet_indikatoren']})")

            # Gute Website → Abzug
            if website_qualitaet >= 70 and _sig.cta_gefunden and _sig.kontaktformular_gefunden:
                punkte += f["moderner_starker_auftritt"]  # negativer Wert
                erklaerung_teile.append(f"Moderner starker Auftritt ({f['moderner_starker_auftritt']})")

    # ── Kontaktdaten ──────────────────────────────────────────────────────────
    if not unternehmen.hat_email:
        punkte += f["keine_email"]
        erklaerung_teile.append(f"Keine E-Mail gefunden (+{f['keine_email']})")
        schmerzpunkte.append("Kein direkter E-Mail-Kontakt – schwer erreichbar")

    # ── Kategorie-spezifische Faktoren ────────────────────────────────────────
    if profil["telefon_intensiv"]:
        punkte += f["telefon_intensiv_bonus"]
        erklaerung_teile.append(f"Telefon-intensives Segment (+{f['telefon_intensiv_bonus']})")
        if profil["ki_telefon"]:
            angebote.append("KI-Telefonagent")
            schmerzpunkte.append("Hohe Telefonlast – Anrufe werden außerhalb der Öffnungszeiten verpasst")

    if profil["buchung_intensiv"]:
        punkte += f["buchung_intensiv_bonus"]
        erklaerung_teile.append(f"Buchungs-intensives Segment (+{f['buchung_intensiv_bonus']})")
        if profil["booking"]:
            angebote.append("Buchungsautomatisierung")
            schmerzpunkte.append("Buchungen laufen noch manuell per Telefon")

    # Lead-Reaktions-abhängige Branchen: langsame Antwort = verlorener Auftrag
    if (unternehmen.kategorie or "").lower() in _LEAD_ABHAENGIGE_KATEGORIEN:
        punkte += f["lead_reaktionsabhaengig"]
        erklaerung_teile.append(f"Lead-Reaktions-abhängiges Segment (+{f['lead_reaktionsabhaengig']})")
        schmerzpunkte.append("Langsame Reaktion auf Anfragen kostet Aufträge an Mitbewerber")

    if profil["whatsapp"]:
        angebote.append("WhatsApp-Automation")
        if _sig and not _sig.whatsapp_gefunden:
            punkte += f["whatsapp_potential"]
            erklaerung_teile.append(f"WhatsApp-Potential nicht genutzt (+{f['whatsapp_potential']})")

    # Automation- und Website-Bonus aus Kategorie-Profil
    punkte += profil["automation_bonus"]
    erklaerung_teile.append(f"Kategorie-Automatisierungspassung (+{profil['automation_bonus']})")

    # ── Webseite-Bedarf-Score (0–100) ─────────────────────────────────────────
    webseite_bedarf = 0
    if not unternehmen.hat_webseite:
        webseite_bedarf = 95
    elif unternehmen.webseite_qualitaet_score < 30:
        webseite_bedarf = 80
    elif unternehmen.webseite_qualitaet_score < 50:
        webseite_bedarf = 55
    elif unternehmen.webseite_qualitaet_score < 70:
        webseite_bedarf = 30
    else:
        webseite_bedarf = 10

    webseite_bedarf += profil["webseite_bonus"]
    unternehmen.webseite_bedarf_score = min(100, webseite_bedarf)

    # ── Automation-Bedarf-Score (0–100) ──────────────────────────────────────
    automation_bedarf = 20  # Basis
    if profil["ki_telefon"]:
        automation_bedarf += 30
    if profil["buchung_intensiv"]:
        automation_bedarf += 20
    if profil["whatsapp"]:
        automation_bedarf += 15
    if profil["telefon_intensiv"]:
        automation_bedarf += 15
    unternehmen.automation_bedarf_score = min(100, automation_bedarf)

    # ── Endberechnung ─────────────────────────────────────────────────────────
    punkte = max(0, min(100, punkte))
    unternehmen.lead_score = punkte

    if punkte >= heiss_schwelle:
        unternehmen.lead_temperatur = "HEISS"
    elif punkte >= warm_schwelle:
        unternehmen.lead_temperatur = "WARM"
    else:
        unternehmen.lead_temperatur = "KALT"

    # Erklärungsfelder
    unternehmen.score_erklaerung = " | ".join(erklaerung_teile) + f" = {punkte} Punkte"
    unternehmen.wahrscheinliche_schmerzpunkte = "; ".join(schmerzpunkte) if schmerzpunkte else "Keine spezifischen Schwächen identifiziert"
    unternehmen.empfohlene_angebote = ", ".join(dict.fromkeys(angebote)) if angebote else profil["hauptangebot"]
    unternehmen.verkaufs_winkel = profil["pitch"]
    unternehmen.pitch_winkel = _was_zuerst_verkaufen(unternehmen, profil, angebote)

    if unternehmen.lead_temperatur == "HEISS":
        unternehmen.heiss_lead_grund = _erstelle_heiss_grund(unternehmen, profil, schmerzpunkte)
    elif unternehmen.lead_temperatur == "WARM":
        top = list(dict.fromkeys(angebote))[:2]
        unternehmen.heiss_lead_grund = (
            f"Gute Verkaufschance: {', '.join(top)}" if top else profil["hauptangebot"]
        )

    unternehmen.erstes_kontaktnachricht = _erstelle_kontaktnachricht(unternehmen, profil, angebote)

    return unternehmen


def _was_zuerst_verkaufen(u: Unternehmen, profil: dict, angebote: list[str]) -> str:
    """Was ist das konkrete erste Angebot für diesen Lead?"""
    if not u.hat_webseite:
        return "Neue professionelle Webseite + Google-Sichtbarkeit"
    q = u.webseite_qualitaet_score
    if q < 30:
        if profil["ki_telefon"] and profil["telefon_intensiv"]:
            return "KI-Telefonagent (sofortiger ROI) + Website-Relaunch"
        return "Website-Relaunch mit CTA, Kontaktformular und Mobile-Optimierung"
    if profil["ki_telefon"] and profil["telefon_intensiv"]:
        return "KI-Telefonagent – entlastet Rezeption sofort, keine IT-Kenntnisse nötig"
    if profil["buchung_intensiv"] and profil["booking"]:
        return "Online-Buchungssystem mit automatischen WhatsApp-Erinnerungen"
    if (u.kategorie or "").lower() in _LEAD_ABHAENGIGE_KATEGORIEN:
        return "Automatisches Lead-Follow-up – antwortet in unter 5 Minuten"
    if profil["whatsapp"]:
        return "WhatsApp-Buchungsbot – Kunden buchen direkt ohne Anruf"
    if angebote:
        return angebote[0]
    return profil["hauptangebot"]


def _erstelle_heiss_grund(u: Unternehmen, profil: dict, schmerzpunkte: list[str]) -> str:
    """Konkrete Begründung warum dieser Lead heiß ist."""
    gründe = []
    if not u.hat_webseite:
        gründe.append("kein Online-Auftritt – täglich unsichtbar für suchende Kunden")
    elif u.webseite_qualitaet_score < 30:
        gründe.append(f"Website sehr schwach (Score {u.webseite_qualitaet_score}/100)")
    elif u.webseite_qualitaet_score < 50:
        gründe.append("Website ohne Conversion-Elemente – kein CTA, kein Formular")
    if profil["ki_telefon"] and profil["telefon_intensiv"]:
        gründe.append("telefon-intensive Branche ohne KI-Automatisierung")
    if profil["buchung_intensiv"] and not (
        u.anreicherungs_befund and u.anreicherungs_befund.buchungs_signal_gefunden
    ):
        gründe.append("Buchungsbetrieb ohne Online-Buchungssystem")
    if not u.hat_email:
        gründe.append("kein E-Mail-Kontakt – digital kaum erreichbar")
    if (u.kategorie or "").lower() in _LEAD_ABHAENGIGE_KATEGORIEN:
        gründe.append("Lead-Reaktionszeit entscheidend in dieser Branche")
    if gründe:
        return "Heißer Lead: " + " | ".join(gründe)
    if schmerzpunkte:
        return f"Lead-Score {u.lead_score}/100: {schmerzpunkte[0]}"
    return f"Lead-Score {u.lead_score}/100 – {profil['hauptangebot']}"


def _erstelle_kontaktnachricht(u: Unternehmen, profil: dict, angebote: list[str]) -> str:
    """Personalisierte Erstkontakt-Nachricht basierend auf echten Lead-Daten."""
    vorname = ""
    if u.entscheidungstraeger_name:
        teile = u.entscheidungstraeger_name.strip().split()
        vorname = teile[0] if teile else ""

    anrede = f"Hallo{' ' + vorname if vorname else ''},"
    ort_info = f" in {u.stadt}" if u.stadt else ""
    erstes = angebote[0] if angebote else profil["hauptangebot"]

    if not u.hat_webseite:
        return (
            f"{anrede}\n\n"
            f"ich bin auf {u.name}{ort_info} aufmerksam geworden und habe gesehen, "
            f"dass Sie noch keine eigene Webseite haben.\n\n"
            f"Viele Ihrer Mitbewerber gewinnen über Google täglich neue Kunden. "
            f"Eine professionelle Webseite würde auch Sie dort sichtbar machen – "
            f"ohne großen Aufwand Ihrerseits.\n\n"
            f"Darf ich Ihnen in einem kurzen Gespräch zeigen, was konkret möglich wäre?"
        )

    if u.webseite_qualitaet_score < 40:
        befund = u.anreicherungs_befund
        details = []
        if befund:
            if not befund.cta_gefunden:
                details.append("kein klarer Handlungsaufruf")
            if not befund.kontaktformular_gefunden and not befund.buchungs_signal_gefunden:
                details.append("kein Buchungs- oder Kontaktsystem")
            if befund.sieht_veraltet_aus:
                details.append("veraltetes Design")
            if befund.fehlt_mobile_viewport:
                details.append("nicht mobiloptimiert")
        detail_str = (", ".join(details) + " – ") if details else ""
        return (
            f"{anrede}\n\n"
            f"ich habe die Website von {u.name}{ort_info} kurz angeschaut. "
            f"Sie haben {detail_str}da ist konkretes Verbesserungspotenzial.\n\n"
            f"{profil['pitch']}\n\n"
            f"Konkret würde ich Ihnen {erstes} vorschlagen. "
            f"Hätten Sie kurz Zeit für ein Gespräch?"
        )

    return (
        f"{anrede}\n\n"
        f"ich bin auf {u.name}{ort_info} gestoßen und sehe eine passende Möglichkeit für Sie.\n\n"
        f"{profil['pitch']}\n\n"
        f"Ich würde Ihnen gerne {erstes} vorstellen – "
        f"das funktioniert bei ähnlichen Unternehmen in Ihrer Branche bereits sehr gut.\n\n"
        f"Wann passt es Ihnen für ein kurzes Gespräch?"
    )
