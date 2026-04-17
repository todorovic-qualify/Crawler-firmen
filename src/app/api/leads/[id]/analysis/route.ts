import { NextRequest, NextResponse } from "next/server";

const CRAWLER_API_URL = (process.env.CRAWLER_API_URL ?? "").replace(/\/$/, "");
const CRAWLER_API_KEY = process.env.CRAWLER_API_KEY ?? "";

// ── Hilfsfunktion: Crawler-API aufrufen ───────────────────────────────────────

function crawlerHeaders() {
  return { "x-api-key": CRAWLER_API_KEY, "Content-Type": "application/json" };
}

function noCrawler() {
  return NextResponse.json(
    { error: "CRAWLER_API_URL nicht konfiguriert" },
    { status: 503 }
  );
}

// ── GET /api/leads/[id]/analysis ──────────────────────────────────────────────
//
// Gibt die gespeicherte Vertriebsanalyse für diesen Lead zurück.
// 404 wenn noch keine Analyse vorhanden.

export async function GET(
  _req: NextRequest,
  { params }: { params: { id: string } }
) {
  if (!CRAWLER_API_URL) return noCrawler();

  try {
    const res = await fetch(`${CRAWLER_API_URL}/analyze-lead/${params.id}`, {
      headers: crawlerHeaders(),
      signal: AbortSignal.timeout(10_000),
    });

    const data = await res.json();

    if (res.status === 404) {
      return NextResponse.json(
        { error: "Noch keine Analyse vorhanden", analysisExists: false },
        { status: 404 }
      );
    }

    if (!res.ok) {
      return NextResponse.json(
        { error: data.detail ?? "Analyse konnte nicht geladen werden" },
        { status: res.status }
      );
    }

    return NextResponse.json({
      leadId: params.id,
      analyse: data.analyse,
      analysisExists: true,
    });
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : String(e);
    return NextResponse.json({ error: msg }, { status: 500 });
  }
}

// ── POST /api/leads/[id]/analysis ─────────────────────────────────────────────
//
// Startet eine neue KI-Vertriebsanalyse für diesen Lead.
// Optionaler Body:
//   { website?: string, googleDaten?: object }
//
// Blockierend – wartet bis Analyse + Speicherung abgeschlossen sind.
// Timeout: 120 Sekunden (tiefer Crawl + Claude-API-Aufruf).

export async function POST(
  req: NextRequest,
  { params }: { params: { id: string } }
) {
  if (!CRAWLER_API_URL) return noCrawler();

  // Optionaler Body (website / googleDaten)
  let body: Record<string, unknown> = {};
  try {
    const text = await req.text();
    if (text) body = JSON.parse(text);
  } catch {
    // Leerer oder kein Body – in Ordnung
  }

  const payload = {
    lead_id: params.id,
    website: body.website ?? null,
    google_daten: body.googleDaten ?? null,
  };

  try {
    const res = await fetch(`${CRAWLER_API_URL}/analyze-lead`, {
      method: "POST",
      headers: crawlerHeaders(),
      body: JSON.stringify(payload),
      signal: AbortSignal.timeout(120_000),
    });

    const data = await res.json();

    if (res.status === 404) {
      return NextResponse.json(
        { error: `Lead ${params.id} nicht gefunden` },
        { status: 404 }
      );
    }

    if (!res.ok) {
      return NextResponse.json(
        { error: data.detail ?? "Analyse fehlgeschlagen" },
        { status: res.status }
      );
    }

    return NextResponse.json({
      leadId: params.id,
      analyseId: data.analyse_id,
      analyse: data.analyse,
    });
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : String(e);
    const isTimeout = msg.includes("timeout") || msg.includes("abort");
    return NextResponse.json(
      { error: isTimeout ? "Analyse-Timeout (>120s)" : msg },
      { status: isTimeout ? 504 : 500 }
    );
  }
}
