/**
 * Seed-Skript: Befüllt die Datenbank mit Beispiel-Leads
 * Ausführen: npm run db:seed
 */
import { PrismaClient, LeadTemperatur, LeadStatus } from "@prisma/client";

const prisma = new PrismaClient();

const demoUnternehmen = [
  {
    name: "Pizzeria Bella Italia",
    kategorie: "restaurant",
    beschreibung: "Familiäres italienisches Restaurant im Stadtzentrum",
    adresse: "Hauptstraße 12",
    stadt: "Worms",
    postleitzahl: "67547",
    telefon: "06241 123456",
    email: null,
    webseite: null,
    bewertung: 4.2,
    bewertungsanzahl: 87,
    leadScore: 82,
    leadTemperatur: "HEISS" as LeadTemperatur,
    webseiteBedarfScore: 85,
    automationBedarfScore: 75,
    webseiteQualitaetScore: 0,
    hatWebseite: false,
    hatEmail: false,
    hatTelefon: true,
    wahrscheinlicheSchmerzpunkte:
      "Kein Online-Auftritt, keine Reservierungsmöglichkeit, komplett telefonabhängig",
    empfohleneAngebote:
      "Neue Webseite mit Reservierungssystem, WhatsApp-Buchungsbot, KI-Telefonagent",
    verkaufswinkel:
      "Sie verlieren täglich Reservierungen, weil Kunden abends keinen erreichen. Wir bauen ein System, das 24/7 Tische bucht – ohne Personalaufwand.",
    heissLeadGrund:
      "Kein Website, hohe Bewertungen → starkes Wachstumspotenzial, sofort ansprechbar",
    scoreErklaerung:
      "Kein Website (+30), kein E-Mail (+8), buchungsintensiv (+10), telefon-intensiv (+12), gute Automatisierungspassung (+15) = 75+ Punkte",
    zusammenfassung:
      "Beliebtes lokales Restaurant ohne digitale Präsenz. Hohe Bewertungszahl zeigt aktive Kundschaft.",
    leistungen: "Mittagsmenü, Abendessen, Catering",
    status: "NEU" as LeadStatus,
    notizen: null,
    erstesKontaktnachricht:
      "Hallo! Ich habe gesehen, dass Sie bei Google sehr gut bewertet sind – aber noch keine eigene Webseite haben. Ich helfe lokalen Restaurants dabei, mehr Reservierungen online zu bekommen, ohne Mehraufwand. Darf ich Ihnen kurz zeigen, wie das aussehen würde?",
    pitchWinkel:
      "Fokus auf verlorene Reservierungen und den 24/7-Vorteil ohne Personalkosten.",
  },
  {
    name: "Friseursalon Schnittkunst",
    kategorie: "friseur",
    beschreibung: "Moderner Friseursalon mit Terminbuchung per Telefon",
    adresse: "Kirchstraße 5",
    stadt: "Worms",
    postleitzahl: "67549",
    telefon: "06241 654321",
    email: "info@schnittkunst-worms.de",
    webseite: "https://schnittkunst-worms.de",
    bewertung: 4.6,
    bewertungsanzahl: 134,
    leadScore: 68,
    leadTemperatur: "WARM" as LeadTemperatur,
    webseiteBedarfScore: 55,
    automationBedarfScore: 80,
    webseiteQualitaetScore: 35,
    hatWebseite: true,
    hatEmail: true,
    hatTelefon: true,
    wahrscheinlicheSchmerzpunkte:
      "Webseite veraltet, keine Online-Buchung, hohe No-Show-Rate möglich",
    empfohleneAngebote:
      "Online-Buchungssystem, automatische Terminerinnerungen per WhatsApp, Umbuchungs-Bot",
    verkaufswinkel:
      "Jeder nicht erschienene Termin kostet Sie Geld. Wir bauen ein System, das automatisch erinnert und Umbuchungen selbst abwickelt.",
    heissLeadGrund:
      "Website veraltet, starker Buchungsbedarf, hohe Kundenzahl",
    scoreErklaerung:
      "Website veraltet (+18), buchungsintensiv (+10), Automatisierungspassung (+15) = 68 Punkte",
    zusammenfassung:
      "Gutbewerteter Friseursalon mit bestehender Webseite, die aber erneuert werden sollte.",
    leistungen: "Haarschnitt, Färben, Styling, Hochzeitsservice",
    status: "NEU" as LeadStatus,
    notizen: null,
    erstesKontaktnachricht:
      "Guten Tag! Ihr Salon hat fantastische Bewertungen. Ich habe mir Ihre Webseite angeschaut und sehe großes Potenzial: Mit einem integrierten Online-Buchungssystem könnten Sie No-Shows um bis zu 40% reduzieren. Hätten Sie kurz Zeit für ein Gespräch?",
    pitchWinkel: "No-Show-Kosten und automatische Erinnerungen als Einstieg.",
    entscheidungstraegerName: "Sandra Koch",
  },
  {
    name: "Elektro Müller GmbH",
    kategorie: "elektriker",
    beschreibung: "Elektriker und Installationsbetrieb",
    adresse: "Industriestraße 22",
    stadt: "Worms",
    postleitzahl: "67550",
    telefon: "06241 789012",
    email: "kontakt@elektro-mueller-worms.de",
    webseite: "https://elektro-mueller-worms.de",
    bewertung: 3.8,
    bewertungsanzahl: 23,
    leadScore: 71,
    leadTemperatur: "WARM" as LeadTemperatur,
    webseiteBedarfScore: 65,
    automationBedarfScore: 70,
    webseiteQualitaetScore: 30,
    hatWebseite: true,
    hatEmail: true,
    hatTelefon: true,
    wahrscheinlicheSchmerzpunkte:
      "Verpasste Anfragen, kein Qualifizierungssystem, manuelle Angebotserstellung",
    empfohleneAngebote:
      "Lead-Qualifizierungsbot, automatisches Angebotssystem, KI-Telefonagent für Erstanfragen",
    verkaufswinkel:
      "Handwerker verlieren täglich Aufträge, weil sie nicht schnell genug antworten. Wir qualifizieren Anfragen automatisch.",
    heissLeadGrund:
      "Handwerker mit starker Abhängigkeit von manueller Lead-Bearbeitung",
    scoreErklaerung:
      "Website veraltet (+18), Automatisierungspassung (+15), service-basiert (+10), Lead-Qualifizierung-Bedarf (+10) = 71 Punkte",
    zusammenfassung:
      "Lokaler Elektrobetrieb ohne digitales Anfragemanagementsystem.",
    leistungen: "Elektroinstallation, Photovoltaik, Reparatur, Notdienst",
    status: "NEU" as LeadStatus,
    notizen: null,
    erstesKontaktnachricht:
      "Hallo Herr Müller, viele Handwerksbetriebe verlieren Aufträge, weil Anfragen zu spät beantwortet werden. Wir haben ein System entwickelt, das Anfragen automatisch qualifiziert – 24/7. Darf ich Ihnen das kurz vorstellen?",
    pitchWinkel:
      "Verlorene Aufträge durch langsame Reaktionszeit als Einstiegsthema.",
    entscheidungstraegerName: "Thomas Müller",
    rechtlicherName: "Elektro Müller GmbH",
  },
  {
    name: "Zahnarztpraxis Dr. Hofmann",
    kategorie: "zahnarzt",
    beschreibung: "Allgemeine Zahnheilkunde und ästhetische Behandlungen",
    adresse: "Bismarckstraße 44",
    stadt: "Ludwigshafen",
    postleitzahl: "67059",
    telefon: "0621 445566",
    email: "praxis@dr-hofmann-zahn.de",
    webseite: "https://dr-hofmann-zahn.de",
    bewertung: 4.4,
    bewertungsanzahl: 61,
    leadScore: 75,
    leadTemperatur: "HEISS" as LeadTemperatur,
    webseiteBedarfScore: 40,
    automationBedarfScore: 90,
    webseiteQualitaetScore: 55,
    hatWebseite: true,
    hatEmail: true,
    hatTelefon: true,
    wahrscheinlicheSchmerzpunkte:
      "Telefonleitungen überlastet, Patienten können keine Termine online buchen, hohe Wartezeiten am Telefon",
    empfohleneAngebote:
      "KI-Telefonagent für Terminbuchungen, Online-Terminkalender, automatische Erinnerungen",
    verkaufswinkel:
      "Ihre Sprechstundenhilfe verbringt Stunden am Telefon für Terminanfragen. Unser KI-Agent bucht Termine automatisch und filtert Notfälle heraus.",
    heissLeadGrund:
      "Zahnarztpraxis mit hohem Anrufvolumen – perfekt für KI-Telefon und Buchungsautomatisierung",
    scoreErklaerung:
      "Buchungsintensiv (+10), KI-Telefonpassung (+15), telefon-intensiv (+12), Automatisierungspassung (+15) = 75 Punkte",
    zusammenfassung:
      "Gutbesuchte Zahnarztpraxis mit Webseite, aber ohne Onlinebuchung und mit hohem Telefonaufkommen.",
    leistungen: "Zahnreinigung, Füllungen, Implantate, Ästhetische Zahnheilkunde",
    status: "NEU" as LeadStatus,
    notizen: null,
    erstesKontaktnachricht:
      "Guten Tag, Frau/Herr Dr. Hofmann. Viele Zahnarztpraxen verlieren täglich Zeit und Patienten durch überlastete Telefonleitungen. Unser KI-Telefonassistent bucht Termine automatisch, erinnert Patienten und filtert Notfälle heraus – Ihre Mitarbeiter werden sofort entlastet. Wäre ein kurzes Gespräch möglich?",
    pitchWinkel:
      "Entlastung des Praxispersonals durch automatisierte Telefonbuchungen.",
    entscheidungstraegerName: "Dr. Michael Hofmann",
    rechtlicherName: "Zahnarztpraxis Dr. Michael Hofmann",
  },
  {
    name: "Café Sonnenschein",
    kategorie: "cafe",
    beschreibung: "Gemütliches Café mit Frühstück und Mittagstisch",
    adresse: "Marktplatz 3",
    stadt: "Speyer",
    postleitzahl: "67346",
    telefon: null,
    email: null,
    webseite: null,
    bewertung: 4.7,
    bewertungsanzahl: 203,
    leadScore: 78,
    leadTemperatur: "HEISS" as LeadTemperatur,
    webseiteBedarfScore: 90,
    automationBedarfScore: 60,
    webseiteQualitaetScore: 0,
    hatWebseite: false,
    hatEmail: false,
    hatTelefon: false,
    wahrscheinlicheSchmerzpunkte:
      "Kein Online-Auftritt, keine Kontaktmöglichkeit außer persönlichem Besuch, viele potenzielle Neukunden finden sie nicht",
    empfohleneAngebote:
      "Neue Webseite mit Speisekarte, Google-Präsenz-Optimierung, Instagram-Integration",
    verkaufswinkel:
      "203 Bewertungen bei Google – aber keine Webseite. Kunden suchen online und finden Sie nicht. Wir ändern das.",
    heissLeadGrund:
      "Sehr gute Bewertungen, aber komplett ohne Online-Präsenz – maximale Wachstumschance",
    scoreErklaerung:
      "Kein Website (+30), kein E-Mail (+8), kein Telefon (+8), Website-Relaunch-Potential (+15) = 78 Punkte",
    zusammenfassung:
      "Sehr beliebtes Café mit hervorragenden Bewertungen aber null digitaler Präsenz.",
    leistungen: "Frühstück, Mittagstisch, Kuchen, Kaffeespezialitäten",
    status: "NEU" as LeadStatus,
    notizen: null,
    erstesKontaktnachricht:
      "Hallo! Ihr Café hat über 200 Google-Bewertungen mit 4,7 Sternen – das ist beeindruckend! Aber ich konnte keine Webseite oder Kontaktmöglichkeit finden. Neue Kunden, die online suchen, finden Sie nicht. Ich würde Ihnen gerne zeigen, wie wir das schnell und günstig ändern können.",
    pitchWinkel:
      "Kontrast zwischen starker Kundenzufriedenheit und fehlender digitaler Erreichbarkeit.",
  },
  {
    name: "Immobilien Schmidt & Partner",
    kategorie: "immobilien",
    beschreibung: "Immobilienmakler für Kauf und Vermietung in der Region",
    adresse: "Rathausstraße 18",
    stadt: "Worms",
    postleitzahl: "67547",
    telefon: "06241 333444",
    email: "info@schmidt-immobilien.de",
    webseite: "https://schmidt-immobilien.de",
    bewertung: 4.1,
    bewertungsanzahl: 38,
    leadScore: 73,
    leadTemperatur: "WARM" as LeadTemperatur,
    webseiteBedarfScore: 50,
    automationBedarfScore: 85,
    webseiteQualitaetScore: 42,
    hatWebseite: true,
    hatEmail: true,
    hatTelefon: true,
    wahrscheinlicheSchmerzpunkte:
      "Lead-Qualifizierung manuell, Follow-up-Prozess ineffizient, Interessenten warten zu lange auf Antwort",
    empfohleneAngebote:
      "Lead-Qualifizierungsbot, automatisches Follow-up-System, KI-Erstgespräch für Kaufinteressenten",
    verkaufswinkel:
      "Immobilienmakler verlieren Deals, weil Interessenten zu lange auf Rückmeldung warten. Unser System qualifiziert und folgt automatisch nach.",
    heissLeadGrund:
      "Hoher manueller Aufwand bei Lead-Qualifizierung und Follow-up",
    scoreErklaerung:
      "Service-Business (+10), Automatisierungspassung (+15), Lead-Qualifizierungs-Bedarf (+10), Website ausbaufähig (+18) = 73 Punkte",
    zusammenfassung:
      "Regionaler Immobilienmakler mit Webseite aber ohne CRM-Automatisierung.",
    leistungen: "Wohnungsverkauf, Hausvermittlung, Vermietung, Bewertungen",
    status: "KONTAKTIERT" as LeadStatus,
    notizen:
      "Erstkontakt per E-Mail am 10.04. – Antwort ausstehend. Nächster Schritt: Anruf.",
    erstesKontaktnachricht:
      "Hallo! Ich habe Ihre Webseite gesehen und frage mich: Wie viele Interessenten-Anfragen gehen bei Ihnen täglich ein – und wie lange dauert die manuelle Bearbeitung? Wir haben ein System, das das automatisch übernimmt und Ihre Abschlussrate deutlich erhöht. Kurzes Gespräch möglich?",
    pitchWinkel:
      "Automatisierte Lead-Qualifizierung als Wettbewerbsvorteil bei schnelllebigem Immobilienmarkt.",
    entscheidungstraegerName: "Klaus Schmidt",
    rechtlicherName: "Schmidt & Partner Immobilien GbR",
  },
];

async function main() {
  console.log("Seeding Datenbank …");

  // Alte Demo-Daten löschen (idempotent)
  await prisma.webseitenAnalyse.deleteMany({});
  await prisma.unternehmen.deleteMany({});
  await prisma.suchauftrag.deleteMany({});

  // Demo-Suchauftrag
  const auftrag = await prisma.suchauftrag.create({
    data: {
      ort: "Worms, Deutschland",
      radiusKm: 20,
      kategorien: ["restaurant", "cafe", "friseur", "elektriker", "zahnarzt", "immobilien"],
      maxErgebnisse: 50,
      status: "abgeschlossen",
      gesamtGefunden: demoUnternehmen.length,
      gesamtVerarbeitet: demoUnternehmen.length,
    },
  });

  // Demo-Unternehmen erstellen
  for (const u of demoUnternehmen) {
    const unternehmen = await prisma.unternehmen.create({
      data: { ...u, suchauftragId: auftrag.id },
    });

    // Demo-Webseitenanalyse für Unternehmen mit Website
    if (u.hatWebseite && u.webseite) {
      await prisma.webseitenAnalyse.create({
        data: {
          unternehmenId: unternehmen.id,
          startseiteTitle: `${u.name} – Offizielle Webseite`,
          metaBeschreibung: u.beschreibung,
          gecrawlteSeiten: [u.webseite, `${u.webseite}/kontakt`, `${u.webseite}/impressum`],
          kontaktformularGefunden: u.leadScore < 70,
          ctaGefunden: u.leadScore < 65,
          buchungsSignalGefunden: false,
          whatsappGefunden: false,
          socialLinksGefunden: u.instagram ? [u.instagram] : [],
          siehtVeraltetAus: u.webseiteBedarfScore > 50,
          webseiteQualitaetScore: u.webseiteQualitaetScore,
          leistungenText: u.leistungen,
        },
      });
    }
  }

  console.log(`✓ ${demoUnternehmen.length} Demo-Unternehmen erstellt`);
  console.log("✓ Seeding abgeschlossen");
}

main()
  .catch((e) => {
    console.error(e);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
