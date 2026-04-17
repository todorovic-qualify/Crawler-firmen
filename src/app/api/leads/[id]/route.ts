import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";

// ── GET /api/leads/[id] ───────────────────────────────────────────────────────
//
// Gibt den vollständigen Lead zurück inkl. WebseitenAnalyse, VertriebsAnalyse
// und den letzten Suchaufträgen.
//
// Query-Parameter:
//   includeAnalysis=false  – VertriebsAnalyse weglassen (schneller, Standard: true)

export async function GET(
  req: NextRequest,
  { params }: { params: { id: string } }
) {
  const includeAnalysis = req.nextUrl.searchParams.get("includeAnalysis") !== "false";

  try {
    const lead = await prisma.unternehmen.findUnique({
      where: { id: params.id },
      include: {
        webseitenAnalyse: true,
        // vertriebsAnalyse ist nach `prisma generate` direkt verfügbar;
        // bis dahin wird der Fallback über den Crawler-API-Proxy genutzt.
        ...(includeAnalysis && { vertriebsAnalyse: true }),
        suchauftraege: {
          include: {
            suchauftrag: {
              select: { id: true, ort: true, erstelltAm: true },
            },
          },
          orderBy: { erstelltAm: "desc" },
          take: 10,
        },
      },
    });

    if (!lead) {
      return NextResponse.json({ error: "Lead nicht gefunden" }, { status: 404 });
    }

    // vertriebsAnalyse: JSON-Felder client-seitig deserialisieren
    let vertriebsAnalyse = (lead as Record<string, unknown>).vertriebsAnalyse ?? null;
    if (vertriebsAnalyse && typeof vertriebsAnalyse === "object") {
      vertriebsAnalyse = _deserialisiereAnalyse(vertriebsAnalyse as Record<string, unknown>);
    }

    return NextResponse.json({
      lead: { ...lead, vertriebsAnalyse },
      analysisExists: vertriebsAnalyse !== null,
    });
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : String(e);
    return NextResponse.json({ error: msg }, { status: 500 });
  }
}

// JSON-Strings in der DB wieder zu Objekten machen
function _deserialisiereAnalyse(
  a: Record<string, unknown>
): Record<string, unknown> {
  const jsonFelder = ["painpoints", "loesungen", "verkaufsansaetze", "hooks", "analyseJson"];
  const result = { ...a };
  for (const feld of jsonFelder) {
    const val = result[feld];
    if (typeof val === "string") {
      try {
        result[feld] = JSON.parse(val);
      } catch {
        // Feld bleibt als String wenn Parse fehlschlägt
      }
    }
  }
  return result;
}
