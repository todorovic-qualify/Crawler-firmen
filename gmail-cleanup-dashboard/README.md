# 📤 Gmail Cleanup Dashboard

Ein datenschutzfreundliches Dashboard zum Aufräumen deines Gmail-Postfachs.  
E-Mails werden nach Absender gruppiert, kategorisiert und **niemals automatisch verändert** — jede Aktion erfordert deine Bestätigung.

## ✨ Features

| Feature | Detail |
|---|---|
| **Gmail OAuth Login** | Sicheres Login mit deinem Google-Konto |
| **Absender-Gruppierung** | E-Mails nach Absender gebündelt |
| **7 Kategorien** | PV/Energie, KI/Automatisierung, Finanzen, Hausbau, Newsletter, Wichtig, Sonstiges |
| **Dashboard-Statistiken** | Ungelesen, Newsletter, Rechnungen, Duplikate |
| **Aktionsvorschläge** | Archivieren, Papierkorb, Als gelesen, Label hinzufügen |
| **Bestätigungs-Dialog** | Jede Aktion wird vorher zusammengefasst |
| **Gmail Labels** | PV & Energie, Qualify.ai, Rechnungen, Steuer, Hausbau, Kunden, Newsletter, Wichtig prüfen |

## 🛡️ Sicherheitsprinzipien

- ✅ Keine E-Mail-Inhalte werden gespeichert (nur Metadaten)
- ✅ Keine automatischen Aktionen — immer Bestätigung erforderlich
- ✅ Keine externen KI-APIs
- ✅ OAuth-Token bleibt beim Nutzer

## 🚀 Lokaler Start

```bash
cd gmail-cleanup-dashboard
npm install
cp .env.example .env.local
# .env.local ausfüllen
npm run dev
```

## ☁️ Vercel Deployment

1. Gehe zu https://vercel.com → "New Project"
2. Wähle das `Crawler-firmen` Repository
3. **Root Directory** auf `gmail-cleanup-dashboard` setzen
4. Environment Variables eintragen:
   - `NEXTAUTH_SECRET` (32 Zeichen, zufällig)
   - `NEXTAUTH_URL` (deine Vercel-URL)
   - `GOOGLE_CLIENT_ID`
   - `GOOGLE_CLIENT_SECRET`
5. Deploy!

## 🔧 Google OAuth einrichten

1. https://console.cloud.google.com → Neues Projekt
2. Gmail API aktivieren
3. OAuth-Zustimmungsbildschirm: Extern, deine E-Mail als Testnutzer
4. OAuth-Client-ID: Typ **Webanwendung**
5. Redirect URIs:
   - `http://localhost:3000/api/auth/callback/google`
   - `https://DEIN-PROJEKTNAME.vercel.app/api/auth/callback/google`
