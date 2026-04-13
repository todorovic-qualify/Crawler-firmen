export type LeadTemperatur = "HEISS" | "WARM" | "KALT";
export type LeadStatus = "NEU" | "KONTAKTIERT" | "INTERESSIERT" | "ABGESCHLOSSEN" | "UNGEEIGNET";

export interface Unternehmen {
  id: string;
  name: string;
  kategorie?: string | null;
  beschreibung?: string | null;
  adresse?: string | null;
  stadt?: string | null;
  postleitzahl?: string | null;
  telefon?: string | null;
  email?: string | null;
  webseite?: string | null;
  quelleUrl?: string | null;
  bewertung?: number | null;
  bewertungsanzahl?: number | null;
  oeffnungszeiten?: string | null;
  instagram?: string | null;
  facebook?: string | null;
  linkedin?: string | null;
  whatsapp?: string | null;
  leadScore: number;
  leadTemperatur: LeadTemperatur;
  webseiteBedarfScore: number;
  automationBedarfScore: number;
  wahrscheinlicheSchmerzpunkte?: string | null;
  empfohleneAngebote?: string | null;
  verkaufswinkel?: string | null;
  heissLeadGrund?: string | null;
  scoreErklaerung?: string | null;
  entscheidungstraegerName?: string | null;
  rechtlicherName?: string | null;
  zusammenfassung?: string | null;
  leistungen?: string | null;
  hatWebseite: boolean;
  hatEmail: boolean;
  hatTelefon: boolean;
  status: LeadStatus;
  notizen?: string | null;
  erstesKontaktnachricht?: string | null;
  webseitenAnalyse?: WebseitenAnalyse | null;
  suchauftragId?: string | null;
  erstelltAm: string | Date;
  aktualisiertAm: string | Date;
}

export interface WebseitenAnalyse {
  id: string;
  unternehmenId: string;
  startseiteTitle?: string | null;
  metaBeschreibung?: string | null;
  gecrawlteSeiten: string[];
  kontaktformularGefunden: boolean;
  ctaGefunden: boolean;
  buchungsSignalGefunden: boolean;
  whatsappGefunden: boolean;
  socialLinksGefunden: string[];
  siehtVeraltetAus: boolean;
  mobilSignale?: string | null;
  technologieStack?: string | null;
  impressumText?: string | null;
  ueberUnsText?: string | null;
  leistungenText?: string | null;
  webseiteQualitaetScore: number;
  erstelltAm: string | Date;
}

export interface Suchauftrag {
  id: string;
  ort: string;
  radiusKm?: number | null;
  kategorien: string[];
  maxErgebnisse: number;
  status: "ausstehend" | "laeuft" | "abgeschlossen" | "fehler";
  gesamtGefunden: number;
  gesamtVerarbeitet: number;
  fehlerMeldung?: string | null;
  unternehmen?: Unternehmen[];
  erstelltAm: string | Date;
  aktualisiertAm: string | Date;
}

export interface LeadFilter {
  stadt?: string;
  kategorien?: string[];
  minScore?: number;
  maxScore?: number;
  temperatur?: LeadTemperatur[];
  hatWebseite?: boolean;
  hatEmail?: boolean;
  hatTelefon?: boolean;
  status?: LeadStatus[];
  suche?: string;
}

export interface SuchauftragErstellen {
  ort: string;
  radiusKm?: number;
  kategorien?: string[];
  maxErgebnisse?: number;
}

export const KATEGORIEN = [
  { wert: "restaurant", label: "Restaurant" },
  { wert: "cafe", label: "Café" },
  { wert: "bar", label: "Bar" },
  { wert: "friseur", label: "Friseur" },
  { wert: "schoenheitssalon", label: "Schönheitssalon" },
  { wert: "nagelstudio", label: "Nagelstudio" },
  { wert: "barber", label: "Barbershop" },
  { wert: "zahnarzt", label: "Zahnarzt" },
  { wert: "arzt", label: "Arzt / Praxis" },
  { wert: "physiotherapeut", label: "Physiotherapeut" },
  { wert: "fitnessstudio", label: "Fitnessstudio" },
  { wert: "hotel", label: "Hotel" },
  { wert: "immobilien", label: "Immobilienmakler" },
  { wert: "handwerker", label: "Handwerker" },
  { wert: "elektriker", label: "Elektriker" },
  { wert: "klempner", label: "Klempner / Sanitär" },
  { wert: "dachdecker", label: "Dachdecker" },
  { wert: "solar", label: "Solartechnik" },
  { wert: "heizung", label: "Heizung / HLK" },
  { wert: "autowerkstatt", label: "Autowerkstatt" },
  { wert: "anwalt", label: "Anwalt / Kanzlei" },
  { wert: "steuerberater", label: "Steuerberater" },
  { wert: "unternehmensberater", label: "Unternehmensberater" },
  { wert: "einzelhandel", label: "Einzelhandel" },
] as const;

export type KategorieWert = typeof KATEGORIEN[number]["wert"];
