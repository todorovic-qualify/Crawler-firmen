import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";

export async function GET(
  _req: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const lead = await prisma.unternehmen.findUnique({
      where: { id: params.id },
      include: {
        webseitenAnalyse: true,
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

    return NextResponse.json({ lead });
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : String(e);
    return NextResponse.json({ error: msg }, { status: 500 });
  }
}
