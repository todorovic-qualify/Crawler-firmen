"""
Scoring-Engine: Bewertet Unternehmen als Verkaufschancen (0–100).
Trennt klar zwischen extrahierten Fakten und Heuristiken.
"""
from __future__ import annotations

from typing import Optional

from crawler.models import Unternehmen

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


def bewerte(unternehmen: Unternehmen) -> Unternehmen:
    """
    Berechnet Lead-Score, Temperatur und alle Verkaufsfelder.
    Gibt das aktualisierte Unternehmen zurück.
    """
    profil = _hole_profil(unternehmen.kategorie)
    analyse = unternehmen.webseiten_analyse
    befund = unternehmen.anreicherungs_befund
    # Signalquelle: WebseitenAnalyse bevorzugt, AnreicherungsBefund als Fallback
    _sig = analyse or befund

    punkte = 0
    erklaerung_teile: list[str] = []
    schmerzpunkte: list[str] = []
    angebote: list[str] = []

    # ── Webseiten-Faktoren ─────────────────────────────────────────────────────
    if not unternehmen.hat_webseite:
        punkte += 30
        erklaerung_teile.append("Kein Website (+30)")
        schmerzpunkte.append("Kein Online-Auftritt – potenzielle Kunden finden das Unternehmen nicht online")
        angebote.append("Neue professionelle Webseite")
    else:
        website_qualitaet = unternehmen.webseite_qualitaet_score

        if website_qualitaet < 30:
            punkte += 18
            erklaerung_teile.append("Website sehr schwach/veraltet (+18)")
            schmerzpunkte.append("Website ist veraltet und verliert täglich potenzielle Kunden")
            angebote.append("Website-Relaunch / Modernisierung")
        elif website_qualitaet < 50:
            punkte += 12
            erklaerung_teile.append("Website ausbaufähig (+12)")
            schmerzpunkte.append("Website hat keine klare Conversion-Optimierung")
            angebote.append("Website-Optimierung mit CTA und Conversion-Elementen")

        if _sig:
            if not _sig.cta_gefunden:
                punkte += 10
                erklaerung_teile.append("Kein CTA gefunden (+10)")
                schmerzpunkte.append("Keine klare Handlungsaufforderung auf der Website")

            # Buchungs-/Kontaktoptimierung als kombinierter Faktor
            if not _sig.kontaktformular_gefunden and not _sig.buchungs_signal_gefunden:
                punkte += 10
                erklaerung_teile.append("Keine Buchungs-/Kontaktoptimierung (+10)")
                angebote.append("Online-Buchungs- oder Anfrage-System")
            elif not _sig.buchungs_signal_gefunden:
                punkte += 5
                erklaerung_teile.append("Kein Buchungssystem (+5)")
                angebote.append("Online-Buchungs- oder Anfrage-System")

            if _sig.sieht_veraltet_aus:
                punkte += 5
                erklaerung_teile.append("Veraltete Indikatoren im HTML (+5)")

            # Gute Website → Abzug
            if website_qualitaet >= 70 and _sig.cta_gefunden and _sig.kontaktformular_gefunden:
                punkte -= 15
                erklaerung_teile.append("Moderner starker Auftritt (-15)")

    # ── Kontaktdaten ──────────────────────────────────────────────────────────
    if not unternehmen.hat_email:
        punkte += 8
        erklaerung_teile.append("Keine E-Mail gefunden (+8)")
        schmerzpunkte.append("Kein direkter E-Mail-Kontakt – schwer erreichbar")

    # ── Kategorie-spezifische Faktoren ────────────────────────────────────────
    if profil["telefon_intensiv"]:
        punkte += 12
        erklaerung_teile.append("Telefon-intensives Segment (+12)")
        if profil["ki_telefon"]:
            angebote.append("KI-Telefonagent")
            schmerzpunkte.append("Hohe Telefonlast – Anrufe werden außerhalb der Öffnungszeiten verpasst")

    if profil["buchung_intensiv"]:
        punkte += 10
        erklaerung_teile.append("Buchungs-intensives Segment (+10)")
        if profil["booking"]:
            angebote.append("Buchungsautomatisierung")
            schmerzpunkte.append("Buchungen laufen noch manuell per Telefon")

    # Lead-Reaktions-abhängige Branchen: langsame Antwort = verlorener Auftrag
    if (unternehmen.kategorie or "").lower() in _LEAD_ABHAENGIGE_KATEGORIEN:
        punkte += 10
        erklaerung_teile.append("Lead-Reaktions-abhängiges Segment (+10)")
        schmerzpunkte.append("Langsame Reaktion auf Anfragen kostet Aufträge an Mitbewerber")

    if profil["whatsapp"]:
        angebote.append("WhatsApp-Automation")
        if _sig and not _sig.whatsapp_gefunden:
            punkte += 5
            erklaerung_teile.append("WhatsApp-Potential nicht genutzt (+5)")

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

    if punkte >= 75:
        unternehmen.lead_temperatur = "HEISS"
    elif punkte >= 45:
        unternehmen.lead_temperatur = "WARM"
    else:
        unternehmen.lead_temperatur = "KALT"

    # Erklärungsfelder
    unternehmen.score_erklaerung = " | ".join(erklaerung_teile) + f" = {punkte} Punkte"
    unternehmen.wahrscheinliche_schmerzpunkte = "; ".join(schmerzpunkte) if schmerzpunkte else "Keine spezifischen Schwächen identifiziert"
    unternehmen.empfohlene_angebote = ", ".join(dict.fromkeys(angebote)) if angebote else profil["hauptangebot"]
    unternehmen.verkaufs_winkel = profil["pitch"]

    if unternehmen.lead_temperatur == "HEISS":
        unternehmen.heiss_lead_grund = _erstelle_heiss_grund(unternehmen, profil)
    elif unternehmen.lead_temperatur == "WARM":
        unternehmen.heiss_lead_grund = f"Gute Verkaufschance: {', '.join(angebote[:2]) if angebote else profil['hauptangebot']}"

    # Erstansprache generieren
    unternehmen.erstes_kontaktnachricht = _erstelle_kontaktnachricht(unternehmen, profil)
    unternehmen.pitch_winkel = profil["pitch"]

    return unternehmen


def _erstelle_heiss_grund(u: Unternehmen, profil: dict) -> str:
    gründe = []
    if not u.hat_webseite:
        gründe.append("kein Online-Auftritt")
    elif u.webseite_qualitaet_score < 30:
        gründe.append("sehr schwache Website")
    if profil["ki_telefon"] and profil["telefon_intensiv"]:
        gründe.append("hohes KI-Telefonpotenzial")
    if profil["buchung_intensiv"]:
        gründe.append("Buchungsautomatisierung sofort einsetzbar")
    if not u.hat_email:
        gründe.append("digital schwer erreichbar")
    return f"Heißer Lead: {', '.join(gründe)}" if gründe else "Hoher Automatisierungsbedarf in diesem Segment"


def _erstelle_kontaktnachricht(u: Unternehmen, profil: dict) -> str:
    name = u.name
    anrede = f"Hallo, ich habe Ihr Unternehmen {name} gefunden"

    if not u.hat_webseite:
        return (
            f"{anrede} und gesehen, dass Sie noch keine eigene Webseite haben. "
            f"Ich helfe lokalen Unternehmen dabei, online sichtbar zu werden und mehr Kunden zu gewinnen. "
            f"Darf ich Ihnen kurz zeigen, was für Sie möglich wäre?"
        )
    elif u.lead_temperatur == "HEISS":
        return (
            f"{anrede} und Ihre Webseite analysiert. "
            f"Ich sehe konkretes Potenzial: {profil['pitch']} "
            f"Hätten Sie kurz Zeit für ein Gespräch?"
        )
    else:
        return (
            f"{anrede}. "
            f"{profil['pitch']} "
            f"Ich würde Ihnen gerne zeigen wie das für Ihr Unternehmen aussehen könnte. "
            f"Wann passt es Ihnen für ein kurzes Gespräch?"
        )
