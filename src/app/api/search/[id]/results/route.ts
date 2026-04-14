import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";

export async function GET(
  _req: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const leads = await prisma.unternehmen.findMany({
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
        erstelltAm: true,
      },
    });

    return NextResponse.json({ leads });
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : String(e);
    return NextResponse.json({ error: msg }, { status: 500 });
  }
}
