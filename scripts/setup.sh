#!/usr/bin/env bash
set -e

echo "=== LeadScout Setup ==="

# .env prüfen
if [ ! -f .env ]; then
  echo "Erstelle .env aus .env.example ..."
  cp .env.example .env
  echo "WICHTIG: Bitte .env anpassen (DATABASE_URL etc.)"
fi

# Node-Abhängigkeiten
echo "Installiere Node-Abhängigkeiten ..."
npm install

# Prisma
echo "Generiere Prisma Client ..."
npx prisma generate

echo ""
echo "=== Setup abgeschlossen ==="
echo "Nächste Schritte:"
echo "  1. PostgreSQL starten (oder: docker-compose up postgres -d)"
echo "  2. npx prisma db push"
echo "  3. npm run db:seed   (optionale Demo-Daten)"
echo "  4. npm run dev"
echo ""
echo "Crawler:"
echo "  cd crawler && pip install -r requirements.txt"
echo "  python crawler.py --place 'Worms, Deutschland' --kategorien restaurant friseur --max 50"
