import { NextRequest, NextResponse } from "next/server";

const CRAWLER_URL = process.env.CRAWLER_API_URL ?? "http://localhost:8000";
const CRAWLER_KEY = process.env.CRAWLER_API_KEY ?? "";

export async function GET(
  _req: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const res = await fetch(`${CRAWLER_URL}/status/${params.id}`, {
      headers: CRAWLER_KEY ? { "x-api-key": CRAWLER_KEY } : {},
      cache: "no-store",
    });

    if (!res.ok) {
      return NextResponse.json({ error: "Status nicht verfügbar" }, { status: res.status });
    }

    const data = await res.json();
    return NextResponse.json(data);
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : String(e);
    return NextResponse.json({ error: msg }, { status: 503 });
  }
}
