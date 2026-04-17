import { NextRequest, NextResponse } from "next/server";

const CRAWLER_API_URL = (process.env.CRAWLER_API_URL ?? "").replace(/\/$/, "");
const CRAWLER_API_KEY = process.env.CRAWLER_API_KEY ?? "";

export async function POST(
  _req: NextRequest,
  { params }: { params: { id: string } }
) {
  if (!CRAWLER_API_URL) {
    return NextResponse.json({ error: "CRAWLER_API_URL nicht konfiguriert" }, { status: 503 });
  }

  try {
    const res = await fetch(`${CRAWLER_API_URL}/recrawl/${params.id}`, {
      method: "POST",
      headers: { "x-api-key": CRAWLER_API_KEY },
      signal: AbortSignal.timeout(90_000), // 90s Timeout für Enrichment
    });

    const data = await res.json();

    if (!res.ok) {
      return NextResponse.json(
        { error: data.detail ?? "Recrawl fehlgeschlagen" },
        { status: res.status }
      );
    }

    return NextResponse.json(data);
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : String(e);
    return NextResponse.json({ error: msg }, { status: 500 });
  }
}
