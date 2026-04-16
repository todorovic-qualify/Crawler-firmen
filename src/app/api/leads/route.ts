import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";
import { Prisma } from "@prisma/client";

export async function GET(req: NextRequest) {
  try {
    const { searchParams } = req.nextUrl;

    // ── Filter-Parameter ──────────────────────────────────────────────────────
    const q             = searchParams.get("q") ?? "";
    const stadt         = searchParams.get("stadt") ?? "";
    const kategorie     = searchParams.get("kategorie") ?? "";
    const temperatur    = searchParams.get("temperatur") ?? "";
    const crawlStatus   = searchParams.get("crawlStatus") ?? "";
    const suchauftragId = searchParams.get("suchauftragId") ?? "";
    const minScore      = parseInt(searchParams.get("minScore") ?? "0");
    const nurWebseite   = searchParams.get("nurWebseite") === "true";
    const nurEmail      = searchParams.get("nurEmail") === "true";
    const nurTelefon    = searchParams.get("nurTelefon") === "true";
    const maxTage       = parseInt(searchParams.get("maxTage") ?? "0");
    const minWebseiteBedarf = parseInt(searchParams.get("minWebseiteBedarf") ?? "0");
    const minAutomation = parseInt(searchParams.get("minAutomation") ?? "0");

    // ── Sortierung ────────────────────────────────────────────────────────────
    const sortBy  = searchParams.get("sortBy") ?? "leadScore";
    const sortDir = (searchParams.get("sortDir") ?? "desc") as "asc" | "desc";

    // ── Pagination ────────────────────────────────────────────────────────────
    const page = Math.max(1, parseInt(searchParams.get("page") ?? "1"));
    const pageSize = Math.min(200, Math.max(1, parseInt(searchParams.get("pageSize") ?? "50")));
    const skip = (page - 1) * pageSize;

    // ── where-Klausel aufbauen ────────────────────────────────────────────────
    const where: Prisma.UnternehmenWhereInput = {};

    if (q) {
      where.OR = [
        { name: { contains: q, mode: "insensitive" } },
        { stadt: { contains: q, mode: "insensitive" } },
        { email: { contains: q, mode: "insensitive" } },
        { adresse: { contains: q, mode: "insensitive" } },
      ];
    }

    if (stadt) {
      where.stadt = { contains: stadt, mode: "insensitive" };
    }

    if (kategorie) {
      where.kategorie = { contains: kategorie, mode: "insensitive" };
    }

    if (temperatur && ["HEISS", "WARM", "KALT"].includes(temperatur)) {
      where.leadTemperatur = temperatur as "HEISS" | "WARM" | "KALT";
    }

    if (crawlStatus && ["neu", "wiederverwendet", "aktualisiert"].includes(crawlStatus)) {
      where.crawlStatus = crawlStatus;
    }

    if (suchauftragId) {
      // Filter auf Leads die in diesem Suchauftrag vorkommen (via junction)
      where.suchauftraege = { some: { suchauftragId } };
    }

    if (minScore > 0) {
      where.leadScore = { gte: minScore };
    }

    if (nurWebseite) where.hatWebseite = true;
    if (nurEmail)    where.hatEmail    = true;
    if (nurTelefon)  where.hatTelefon  = true;

    if (maxTage > 0) {
      const grenze = new Date(Date.now() - maxTage * 24 * 60 * 60 * 1000);
      where.lastCrawledAt = { gte: grenze };
    }

    if (minWebseiteBedarf > 0) {
      where.webseiteBedarfScore = { gte: minWebseiteBedarf };
    }

    if (minAutomation > 0) {
      where.automationBedarfScore = { gte: minAutomation };
    }

    // ── Sortier-Map ───────────────────────────────────────────────────────────
    const orderByMap: Record<string, Prisma.UnternehmenOrderByWithRelationInput> = {
      leadScore:    { leadScore: sortDir },
      name:         { name: sortDir },
      stadt:        { stadt: sortDir },
      erstelltAm:   { erstelltAm: sortDir },
      lastCrawledAt: { lastCrawledAt: sortDir },
      aktualisiertAm: { aktualisiertAm: sortDir },
    };
    const orderBy = orderByMap[sortBy] ?? { leadScore: "desc" };

    // ── Queries parallel ausführen ────────────────────────────────────────────
    const [total, leads] = await Promise.all([
      prisma.unternehmen.count({ where }),
      prisma.unternehmen.findMany({
        where,
        orderBy,
        skip,
        take: pageSize,
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
          crawlStatus: true,
          lastCrawledAt: true,
          quelle: true,
          erstelltAm: true,
          aktualisiertAm: true,
          suchauftragId: true,
        },
      }),
    ]);

    return NextResponse.json({
      leads,
      pagination: {
        total,
        page,
        pageSize,
        totalPages: Math.ceil(total / pageSize),
      },
    });
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : String(e);
    return NextResponse.json({ error: msg }, { status: 500 });
  }
}
