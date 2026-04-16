import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";

export async function GET(
  _req: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    // Leads über die Junction-Tabelle holen (many-to-many)
    const junctionRows = await prisma.suchauftragUnternehmen.findMany({
      where: { suchauftragId: params.id },
      orderBy: { unternehmen: { leadScore: "desc" } },
      take: 500,
      include: {
        unternehmen: {
          select: {
            id: true,
            name: true,
            kategorie: true,
            stadt: true,
            adresse: true,
            telefon: true,
            email: true,
            webseite: true,
            bewertung: true,
            bewertungsanzahl: true,
            oeffnungszeiten: true,
            leadScore: true,
            leadTemperatur: true,
            webseiteBedarfScore: true,
            automationBedarfScore: true,
            hatWebseite: true,
            hatEmail: true,
            hatTelefon: true,
            wahrscheinlicheSchmerzpunkte: true,
            empfohleneAngebote: true,
            erstesKontaktnachricht: true,
            scoreErklaerung: true,
            crawlStatus: true,
            lastCrawledAt: true,
            erstelltAm: true,
          },
        },
      },
    });

    // Falls Junction-Tabelle leer ist (Legacy-Daten) → Fallback auf direkten Join
    let leads;
    if (junctionRows.length === 0) {
      const directLeads = await prisma.unternehmen.findMany({
        where: { suchauftragId: params.id },
        orderBy: { leadScore: "desc" },
        take: 500,
        select: {
          id: true,
          name: true,
          kategorie: true,
          stadt: true,
          adresse: true,
          telefon: true,
          email: true,
          webseite: true,
          bewertung: true,
          bewertungsanzahl: true,
          oeffnungszeiten: true,
          leadScore: true,
          leadTemperatur: true,
          webseiteBedarfScore: true,
          automationBedarfScore: true,
          hatWebseite: true,
          hatEmail: true,
          hatTelefon: true,
          wahrscheinlicheSchmerzpunkte: true,
          empfohleneAngebote: true,
          erstesKontaktnachricht: true,
          scoreErklaerung: true,
          crawlStatus: true,
          lastCrawledAt: true,
          erstelltAm: true,
        },
      });
      leads = directLeads.map((l) => ({ ...l, herkunft: "neu" as const }));
    } else {
      leads = junctionRows.map((row) => ({
        ...row.unternehmen,
        herkunft: row.herkunft,
      }));
    }

    return NextResponse.json({ leads });
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : String(e);
    return NextResponse.json({ error: msg }, { status: 500 });
  }
}
