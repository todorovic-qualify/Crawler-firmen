/**
 * Seed-Skript: Befüllt die Datenbank mit Beispiel-Leads
 * Ausführen: npm run db:seed
 */
import { PrismaClient } from "@prisma/client";

const prisma = new PrismaClient();

async function main() {
  console.log("Seeding Datenbank …");

  // Demo-Suchauftrag
  const auftrag = await prisma.suchauftrag.create({
    data: {
      ort: "Worms, Deutschland",
      radiusKm: 20,
      kategorien: ["restaurant", "friseur", "handwerker"],
      maxErgebnisse: 10,
      status: "abgeschlossen",
      gesamtGefunden: 3,
      gesamtVerarbeitet: 3,
    },
  });

  // Demo-Unternehmen
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
      leadTemperatur: "HEISS" as const,
      webseiteBedarfScore: 85,
      automationBedarfScore: 75,
      hatWebseite: false,
      hatEmail: false,
      hatTelefon: true,
      wahrscheinlicheSchmerzpunkte: "Kein Online-Auftritt, keine Reservierungsmöglichkeit, komplett telefonabhängig",
      empfohleneAngebote: "Neue Webseite mit Reservierungssystem, WhatsApp-Buchungsbot, KI-Telefonagent",
      verkaufswinkel: "Sie verlieren täglich Reservierungen, weil Kunden abends keinen erreichen. Wir bauen Ihnen ein System, das 24/7 Tische bucht – ohne Personalaufwand.",
      heissLeadGrund: "Kein Website, hohe Bewertungen → starkes Wachstumspotenzial, sofort ansprechbar",
      scoreErklaerung: "Kein Website (+30), kein E-Mail (+8), buchungsintensiv (+10), telefon-intensiv (+12), gute Automatisierungspassung (+15) = 75 Punkte",
      zusammenfassung: "Beliebtes lokales Restaurant ohne digitale Präsenz. Hohe Bewertungszahl zeigt aktive Kundschaft.",
      leistungen: "Mittagsmenü, Abendessen, Catering",
      status: "NEU" as const,
      erstesKontaktnachricht: "Hallo! Ich habe gesehen, dass Sie bei Google sehr gut bewertet sind – aber noch keine eigene Webseite haben. Ich helfe lokalen Restaurants dabei, mehr Reservierungen online zu bekommen, ohne Mehraufwand. Darf ich Ihnen kurz zeigen, wie das aussehen würde?",
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
      leadTemperatur: "WARM" as const,
      webseiteBedarfScore: 55,
      automationBedarfScore: 80,
      hatWebseite: true,
      hatEmail: true,
      hatTelefon: true,
      wahrscheinlicheSchmerzpunkte: "Webseite veraltet, keine Online-Buchung, hohe No-Show-Rate möglich",
      empfohleneAngebote: "Online-Buchungssystem, automatische Terminerinnerungen, WhatsApp-Bot für Umbuchungen",
      verkaufswinkel: "Jeder nicht erschienene Termin kostet Sie Geld. Wir bauen ein System das automatisch erinnert und Umbuchungen selbst abwickelt.",
      heissLeadGrund: "Website vorhanden aber veraltet, starker Buchungsbedarf, hohe Kundenzahl",
      scoreErklaerung: "Website veraltet (+18), buchungsintensiv (+10), Automatisierungspassung (+15), hat E-Mail (-0) = 68 Punkte",
      zusammenfassung: "Gutbewerteter Friseursalon mit bestehender Webseite, die aber erneuert werden sollte.",
      leistungen: "Haarschnitt, Färben, Styling, Hochzeitsservice",
      status: "NEU" as const,
      erstesKontaktnachricht: "Guten Tag! Ihr Salon hat fantastische Bewertungen. Ich habe mir Ihre Webseite angeschaut und sehe großes Potenzial: Mit einem integrierten Online-Buchungssystem könnten Sie No-Shows um bis zu 40% reduzieren. Hätten Sie kurz Zeit für ein Gespräch?",
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
      leadTemperatur: "WARM" as const,
      webseiteBedarfScore: 65,
      automationBedarfScore: 70,
      hatWebseite: true,
      hatEmail: true,
      hatTelefon: true,
      wahrscheinlicheSchmerzpunkte: "Verpasste Anfragen, kein Qualifizierungssystem, manuelle Angebotserstellung",
      empfohleneAngebote: "Lead-Qualifizierungsbot, automatisches Angebotssystem, KI-Telefonagent für Erstanfragen",
      verkaufswinkel: "Handwerker verlieren täglich Aufträge, weil sie nicht schnell genug antworten. Wir qualifizieren Anfragen automatisch – Sie konzentrieren sich nur auf die guten Jobs.",
      heissLeadGrund: "Handwerker mit starker Abhängigkeit von manueller Lead-Bearbeitung",
      scoreErklaerung: "Website veraltet (+18), Automatisierungspassung (+15), service-basiert (+10), Lead-Qualifizierung-Bedarf (+10) = 71 Punkte",
      zusammenfassung: "Lokaler Elektrobetrieb ohne digitales Anfragemanagementsystem.",
      leistungen: "Elektroinstallation, Photovoltaik, Reparatur, Notdienst",
      status: "NEU" as const,
      erstesKontaktnachricht: "Hallo Herr Müller, ich arbeite mit Handwerksbetrieben in der Region zusammen. Viele verlieren Aufträge, weil Anfragen zu spät beantwortet werden. Wir haben ein System entwickelt, das Anfragen automatisch qualifiziert und beantwortet – 24/7. Darf ich Ihnen das kurz vorstellen?",
      entscheidungstraegerName: "Thomas Müller",
      rechtlicherName: "Elektro Müller GmbH",
    },
  ];

  for (const u of demoUnternehmen) {
    await prisma.unternehmen.create({
      data: { ...u, suchauftragId: auftrag.id },
    });
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
