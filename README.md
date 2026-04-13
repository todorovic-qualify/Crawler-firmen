# LeadScout – Lokale Unternehmens-Leadgenerierung

> Finde lokale Unternehmen, bewerte sie als Verkaufschancen und bereite professionelle Erstansprachen vor.

**Einsatzbereich:** Verkauf von Webseiten, KI-Automatisierungen, KI-Telefonagenten, WhatsApp-Bots, Buchungssystemen und Lead-Follow-up-Systemen an lokale Unternehmen.

---

## Was macht LeadScout?

1. **Suche** – Findet lokale Unternehmen in einem Ort oder Umkreis (via OpenStreetMap / Overpass API)
2. **Anreicherung** – Crawlt Webseiten, extrahiert Kontaktdaten, Leistungen, Entscheidungsträger
3. **Scoring** – Bewertet jeden Lead automatisch (0–100) als Heiß / Warm / Kalt
4. **Dashboard** – Filtere, sortiere und analysiere alle Leads in einer modernen Web-UI
5. **Export** – Download als CSV oder JSON

---

## Tech-Stack

| Bereich | Technologie |
|---|---|
| Frontend | Next.js 14, TypeScript, Tailwind CSS, shadcn/ui |
| Backend | Next.js API Routes |
| Datenbank | PostgreSQL + Prisma ORM |
| Crawler | Python 3.12, httpx, BeautifulSoup4, trafilatura |
| Crawler-API | FastAPI |
| Deployment | Docker + docker-compose |

---

## Schnellstart (lokal)

### Voraussetzungen
- Node.js 20+
- Python 3.12+
- PostgreSQL 16+ (oder Docker)

### 1. Repository klonen & einrichten

```bash
git clone https://github.com/todorovic-qualify/crawler-firmen.git
cd crawler-firmen
bash scripts/setup.sh
```

### 2. Datenbank starten

```bash
# Option A: Docker (empfohlen)
docker-compose up postgres -d

# Option B: Lokale PostgreSQL-Instanz
# DATABASE_URL in .env anpassen
```

### 3. Datenbank-Schema erstellen

```bash
npx prisma db push
npm run db:seed   # Optional: Demo-Daten laden
```

### 4. Frontend starten

```bash
npm run dev
# → http://localhost:3000
```

### 5. Crawler starten

```bash
cd crawler
pip install -r requirements.txt

# Als FastAPI-Service (für die Web-UI)
uvicorn api:app --reload --port 8000

# Oder als CLI
python crawler.py --place "Worms, Deutschland" \
  --radius-km 20 \
  --kategorien restaurant friseur elektriker klempner zahnarzt \
  --max 100 \
  --output leads.csv
```

---

## Vollständig mit Docker

```bash
cp .env.example .env
# .env anpassen
docker-compose up --build
```

- Web-UI: http://localhost:3000
- Crawler-API: http://localhost:8000

---

## Projektstruktur

```
leadscout/
├── src/
│   ├── app/                   # Next.js App Router
│   │   ├── page.tsx           # Startseite / Suche
│   │   ├── leads/             # Leads-Tabelle + Detailseite
│   │   ├── auftraege/         # Suchauftrags-Übersicht
│   │   ├── einstellungen/     # Einstellungen
│   │   └── api/               # API-Routen
│   ├── components/            # React-Komponenten
│   ├── lib/                   # Prisma, Utilities
│   └── types/                 # TypeScript-Typen
├── crawler/
│   ├── crawler.py             # Haupt-CLI
│   ├── enricher.py            # Webseiten-Anreicherung
│   ├── scorer.py              # Scoring-Engine
│   ├── api.py                 # FastAPI-Endpunkte
│   ├── sources/
│   │   └── overpass.py        # OpenStreetMap / Overpass
│   └── utils/
│       ├── http_utils.py      # HTTP mit Retry, Rate-Limiting
│       └── parse_utils.py     # HTML-Parsing-Helfer
├── prisma/
│   └── schema.prisma          # Datenbank-Schema
├── scripts/
│   ├── seed.ts                # Demo-Daten
│   └── setup.sh               # Einrichtungs-Skript
├── docker-compose.yml
├── Dockerfile
└── .env.example
```

---

## Scoring-System

| Faktor | Punkte |
|---|---|
| Kein Website | +30 |
| Website veraltet | +18 |
| Kein E-Mail | +8 |
| Kein CTA | +10 |
| Keine Buchungs-/Kontaktoptimierung | +10 |
| Telefon-intensives Niche | +12 |
| Buchungs-intensives Niche | +10 |
| Service-Betrieb mit Lead-Abhängigkeit | +10 |
| Gute Automatisierungspassung | +15 |
| Starker Website-Relaunch-Bedarf | +15 |
| Moderner starker Auftritt | -15 |
| Corporate / Franchise | -10 |
| Schwache Datenlage | -5 |

**Temperatur:**
- 75+ Punkte → **Heiß**
- 45–74 Punkte → **Warm**
- 0–44 Punkte → **Kalt**

---

## Export

- **CSV:** Dashboard → Leads → „CSV exportieren"
- **JSON:** `/api/export?format=json`
- **Gefiltert:** Filter im Dashboard anwenden, dann exportieren

---

## Crawler CLI

```bash
python crawler.py \
  --place "München, Deutschland" \
  --radius-km 15 \
  --kategorien restaurant cafe friseur zahnarzt physiotherapeut \
  --max 200 \
  --output ergebnisse.csv \
  --db  # Direkt in Datenbank speichern
```

---

## Rechtlicher Hinweis

LeadScout verwendet ausschließlich **öffentlich zugängliche Daten** aus OpenStreetMap und öffentlichen Webseiten. Die Nutzer sind selbst verantwortlich für die Einhaltung der geltenden Datenschutz- und Wettbewerbsrechtgesetze (DSGVO, UWG) in ihrer jeweiligen Jurisdiktion.

- Keine Umgehung von Authentifizierung oder Paywalls
- robots.txt wird respektiert
- Rate-Limiting und höfliches Crawling sind standardmäßig aktiviert
- Extrahierte Fakten werden klar von Heuristiken getrennt

---

## Lizenz

MIT – Eigenverantwortlicher Einsatz.
