import { NextRequest, NextResponse } from "next/server";
import { readFileSync, writeFileSync, existsSync } from "fs";
import { join } from "path";

// Auf Vercel ist das Projekt-Verzeichnis read-only → /tmp nutzen (ephemeral)
// Lokal: crawler-config.json im Projekt-Root (persistent)
const CONFIG_PATH = process.env.VERCEL
  ? "/tmp/crawler-config.json"
  : join(process.cwd(), "crawler-config.json");

export const DEFAULT_CONFIG = {
  crawler: {
    max_concurrent: 3,
    delay_seconds: 2,
    proxy_url: "",
    nominatim_url: "https://nominatim.openstreetmap.org",
    overpass_url: "https://overpass-api.de/api/interpreter",
  },
  scoring: {
    heiss_schwelle: 75,
    warm_schwelle: 45,
    faktoren: {
      kein_website: 30,
      website_sehr_schwach: 18,
      website_ausbaufaehig: 12,
      kein_cta: 10,
      keine_buchung_kontakt: 10,
      kein_buchungssystem: 5,
      veraltet_indikatoren: 5,
      keine_email: 8,
      telefon_intensiv_bonus: 12,
      buchung_intensiv_bonus: 10,
      lead_reaktionsabhaengig: 10,
      whatsapp_potential: 5,
      moderner_starker_auftritt: -15,
    },
  },
  kategorien: {
    restaurant: { telefon_intensiv: true, buchung_intensiv: true, ki_telefon: true, whatsapp: true, booking: true, automation_bonus: 15, webseite_bonus: 15, hauptangebot: "Webseite + Reservierungssystem + KI-Telefonagent", pitch: "Restaurants verlieren täglich Reservierungen über nicht erreichtes Telefon. Automatisieren Sie Buchungen 24/7." },
    cafe: { telefon_intensiv: false, buchung_intensiv: false, ki_telefon: false, whatsapp: true, booking: false, automation_bonus: 8, webseite_bonus: 18, hauptangebot: "Neue Webseite mit Speisekarte + Instagram-Integration", pitch: "Ein ansprechender Online-Auftritt zieht neue Gäste an – besonders über Google-Suche und Instagram." },
    bar: { telefon_intensiv: false, buchung_intensiv: true, ki_telefon: false, whatsapp: true, booking: true, automation_bonus: 8, webseite_bonus: 15, hauptangebot: "Webseite + Event-Buchungssystem + WhatsApp-Reservierung", pitch: "Tischreservierungen und Events lassen sich einfach automatisieren – mehr Umsatz, weniger Aufwand." },
    friseur: { telefon_intensiv: true, buchung_intensiv: true, ki_telefon: true, whatsapp: true, booking: true, automation_bonus: 15, webseite_bonus: 12, hauptangebot: "Online-Buchungssystem + automatische Terminerinnerungen", pitch: "Jeder No-Show kostet Geld. Automatische Erinnerungen per WhatsApp reduzieren Ausfälle bis zu 40%." },
    schoenheitssalon: { telefon_intensiv: true, buchung_intensiv: true, ki_telefon: true, whatsapp: true, booking: true, automation_bonus: 15, webseite_bonus: 12, hauptangebot: "Online-Buchung + Erinnerungsbot + Website-Relaunch", pitch: "Schönheitssalons profitieren enorm von automatisierten Terminerinnerungen und Online-Buchung." },
    nagelstudio: { telefon_intensiv: true, buchung_intensiv: true, ki_telefon: false, whatsapp: true, booking: true, automation_bonus: 15, webseite_bonus: 12, hauptangebot: "Online-Buchung + WhatsApp-Buchungsbot", pitch: "Online-Buchung ersetzt lästige Telefonanrufe – Kunden buchen wann es ihnen passt." },
    barber: { telefon_intensiv: true, buchung_intensiv: true, ki_telefon: false, whatsapp: true, booking: true, automation_bonus: 12, webseite_bonus: 12, hauptangebot: "Online-Buchung + WhatsApp-Bot", pitch: "Viele Barbershops laufen noch komplett über Telefon und WhatsApp manuell – das kostet Zeit." },
    zahnarzt: { telefon_intensiv: true, buchung_intensiv: true, ki_telefon: true, whatsapp: false, booking: true, automation_bonus: 18, webseite_bonus: 8, hauptangebot: "KI-Telefonagent + Online-Terminbuchung", pitch: "Ihre Sprechstundenhilfe verbringt Stunden am Telefon. Unser KI-Agent bucht Termine automatisch und filtert Notfälle." },
    arzt: { telefon_intensiv: true, buchung_intensiv: true, ki_telefon: true, whatsapp: false, booking: true, automation_bonus: 18, webseite_bonus: 8, hauptangebot: "KI-Telefonagent + Online-Terminbuchung", pitch: "Arztpraxen kämpfen täglich mit überlasteten Telefonleitungen. KI-Telefon entlastet sofort." },
    physiotherapeut: { telefon_intensiv: true, buchung_intensiv: true, ki_telefon: true, whatsapp: true, booking: true, automation_bonus: 15, webseite_bonus: 10, hauptangebot: "KI-Telefonagent + Buchungsautomatisierung", pitch: "Physiopraxen verlieren täglich Patienten durch nicht erreichtes Telefon. Wir lösen das." },
    fitnessstudio: { telefon_intensiv: false, buchung_intensiv: true, ki_telefon: false, whatsapp: true, booking: true, automation_bonus: 12, webseite_bonus: 15, hauptangebot: "Lead-Follow-up-System + Mitglieder-Onboarding-Automation", pitch: "Fitnessstudios verlieren potenzielle Mitglieder, die online anfragen und nie zurückgerufen werden." },
    hotel: { telefon_intensiv: true, buchung_intensiv: true, ki_telefon: true, whatsapp: true, booking: true, automation_bonus: 12, webseite_bonus: 15, hauptangebot: "Webseite-Upgrade + Direktbuchung + WhatsApp-Concierge", pitch: "Hotels zahlen hohe Provisionen an Booking.com. Direktbuchungen über eigene Webseite sparen das." },
    immobilien: { telefon_intensiv: true, buchung_intensiv: true, ki_telefon: true, whatsapp: false, booking: true, automation_bonus: 15, webseite_bonus: 10, hauptangebot: "Lead-Qualifizierungsbot + automatisches Follow-up", pitch: "Immobilienmakler verlieren Deals durch langsame Lead-Reaktion. Automatisiertes Follow-up schließt die Lücke." },
    handwerker: { telefon_intensiv: true, buchung_intensiv: false, ki_telefon: true, whatsapp: true, booking: false, automation_bonus: 15, webseite_bonus: 15, hauptangebot: "Lead-Qualifizierungsbot + KI-Telefon + Angebots-Automatisierung", pitch: "Handwerker verlieren Aufträge, weil sie auf Baustelle nicht ans Telefon können. KI-Telefon nimmt für Sie ab." },
    elektriker: { telefon_intensiv: true, buchung_intensiv: false, ki_telefon: true, whatsapp: true, booking: false, automation_bonus: 15, webseite_bonus: 15, hauptangebot: "KI-Telefonagent + Lead-Qualifizierung", pitch: "Elektrikerbetriebe verpassen täglich Aufträge durch verpasste Anrufe." },
    klempner: { telefon_intensiv: true, buchung_intensiv: false, ki_telefon: true, whatsapp: true, booking: false, automation_bonus: 15, webseite_bonus: 15, hauptangebot: "KI-Telefonagent (Notdienst) + Lead-Qualifizierung", pitch: "Notdienstanrufe 24/7 entgegennehmen und automatisch weiterleiten – kein verpasster Auftrag." },
    dachdecker: { telefon_intensiv: true, buchung_intensiv: false, ki_telefon: true, whatsapp: false, booking: false, automation_bonus: 12, webseite_bonus: 15, hauptangebot: "Lead-Qualifizierung + Angebots-Automation", pitch: "Dachdecker bekommen viele Anfragen, aber manuelle Qualifizierung kostet Zeit." },
    solar: { telefon_intensiv: false, buchung_intensiv: true, ki_telefon: true, whatsapp: false, booking: true, automation_bonus: 18, webseite_bonus: 15, hauptangebot: "Lead-Qualifizierungsbot + automatisches Follow-up + Beratungstermin-Buchung", pitch: "Solarfirmen erhalten viele Anfragen, aber nur wenige werden schnell genug qualifiziert. Automatisieren Sie den Prozess." },
    heizung: { telefon_intensiv: true, buchung_intensiv: false, ki_telefon: true, whatsapp: false, booking: false, automation_bonus: 12, webseite_bonus: 12, hauptangebot: "KI-Telefon + Lead-Qualifizierung", pitch: "Heizungsbetriebe haben hohe Saisonspitzen – KI-Telefon fängt Anfragen automatisch ab." },
    autowerkstatt: { telefon_intensiv: true, buchung_intensiv: true, ki_telefon: true, whatsapp: true, booking: true, automation_bonus: 12, webseite_bonus: 12, hauptangebot: "KI-Telefonagent + Online-Terminbuchung + Status-Updates per WhatsApp", pitch: "Kunden wollen wissen wann ihr Auto fertig ist. Automatische Status-Updates per WhatsApp sind ein Differenzierungsmerkmal." },
    anwalt: { telefon_intensiv: true, buchung_intensiv: true, ki_telefon: true, whatsapp: false, booking: true, automation_bonus: 12, webseite_bonus: 10, hauptangebot: "Erstberatungs-Buchungssystem + Lead-Qualifizierung", pitch: "Anwälte verlieren potenzielle Mandanten, die keine Antwort auf Erstanfragen bekommen." },
    steuerberater: { telefon_intensiv: true, buchung_intensiv: true, ki_telefon: true, whatsapp: false, booking: true, automation_bonus: 10, webseite_bonus: 10, hauptangebot: "Mandanten-Onboarding-Automation + Terminbuchungssystem", pitch: "Steuerberater-Kanzleien gewinnen mit automatisiertem Mandanten-Onboarding einen klaren Wettbewerbsvorteil." },
    unternehmensberater: { telefon_intensiv: false, buchung_intensiv: true, ki_telefon: false, whatsapp: false, booking: true, automation_bonus: 10, webseite_bonus: 12, hauptangebot: "Lead-Follow-up + Erstgespräch-Buchungssystem", pitch: "Berater brauchen einen professionellen Erstgespräch-Prozess der automatisch qualifiziert." },
    einzelhandel: { telefon_intensiv: false, buchung_intensiv: false, ki_telefon: false, whatsapp: true, booking: false, automation_bonus: 8, webseite_bonus: 18, hauptangebot: "Online-Shop / Webseite + WhatsApp-Bestellkanal", pitch: "Lokale Händler brauchen einen Online-Auftritt um gegen große Plattformen zu bestehen." },
  },
} as const;

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function deepMerge(defaults: any, override: any): any {
  const result = { ...defaults };
  for (const key of Object.keys(override ?? {})) {
    if (
      typeof override[key] === "object" &&
      override[key] !== null &&
      !Array.isArray(override[key]) &&
      typeof defaults[key] === "object" &&
      defaults[key] !== null &&
      !Array.isArray(defaults[key])
    ) {
      result[key] = deepMerge(defaults[key], override[key]);
    } else {
      result[key] = override[key];
    }
  }
  return result;
}

export async function GET() {
  try {
    if (existsSync(CONFIG_PATH)) {
      const saved = JSON.parse(readFileSync(CONFIG_PATH, "utf-8"));
      return NextResponse.json(deepMerge(DEFAULT_CONFIG, saved));
    }
  } catch {
    // fall through to defaults
  }
  return NextResponse.json(DEFAULT_CONFIG);
}

export async function POST(req: NextRequest) {
  try {
    const config = await req.json();
    writeFileSync(CONFIG_PATH, JSON.stringify(config, null, 2), "utf-8");
    return NextResponse.json({ ok: true });
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : String(e);
    return NextResponse.json({ error: msg }, { status: 500 });
  }
}

export async function DELETE() {
  try {
    writeFileSync(CONFIG_PATH, JSON.stringify(DEFAULT_CONFIG, null, 2), "utf-8");
    return NextResponse.json({ ok: true });
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : String(e);
    return NextResponse.json({ error: msg }, { status: 500 });
  }
}
