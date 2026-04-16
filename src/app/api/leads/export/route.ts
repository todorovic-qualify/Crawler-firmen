import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";
import { Prisma } from "@prisma/client";

const CSV_COLS = [
  { key: "name",                         label: "Firmenname" },
  { key: "kategorie",                    label: "Kategorie" },
  { key: "stadt",                        label: "Stadt" },
  { key: "adresse",                      label: "Adresse" },
  { key: "telefon",                      label: "Telefon" },
  { key: "email",                        label: "E-Mail" },
  { key: "webseite",                     label: "Website" },
  { key: "bewertung",                    label: "Bewertung" },
  { key: "bewertungsanzahl",             label: "Bewertungsanzahl" },
  { key: "oeffnungszeiten",             label: "Öffnungszeiten" },
  { key: "leadScore",                    label: "Lead-Score" },
  { key: "leadTemperatur",               label: "Lead-Temperatur" },
  { key: "webseiteBedarfScore",          label: "Website-Bedarf" },
  { key: "automationBedarfScore",        label: "Automations-Bedarf" },
  { key: "wahrscheinlicheSchmerzpunkte", label: "Schmerzpunkte" },
  { key: "empfohleneAngebote",           label: "Empfohlenes Angebot" },
  { key: "erstesKontaktnachricht",       label: "Erstkontakt-Nachricht" },
  { key: "quelle",                       label: "Quelle" },
  { key: "crawlStatus",                  label: "Crawl-Status" },
  { key: "suchauftragId",                label: "Suchauftrag-ID" },
  { key: "erstelltAm",                   label: "Erstellt am" },
  { key: "lastCrawledAt",                label: "Zuletzt gecrawlt am" },
] as const;

function csvEscape(val: unknown): string {
  const s = val == null ? "" : String(val);
  // Ersetze newlines durch Leerzeichen, escape quotes
  const cleaned = s.replace(/[\r\n]+/g, " ").replace(/"/g, '""');
  return `"${cleaned}"`;
}

export async function GET(req: NextRequest) {
  try {
    const { searchParams } = req.nextUrl;

    // ── Gleiche Filter wie /api/leads ─────────────────────────────────────────
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

    const where: Prisma.UnternehmenWhereInput = {};

    if (q) {
      where.OR = [
        { name: { contains: q, mode: "insensitive" } },
        { stadt: { contains: q, mode: "insensitive" } },
        { email: { contains: q, mode: "insensitive" } },
      ];
    }
    if (stadt)      where.stadt = { contains: stadt, mode: "insensitive" };
    if (kategorie)  where.kategorie = { contains: kategorie, mode: "insensitive" };
    if (temperatur && ["HEISS", "WARM", "KALT"].includes(temperatur)) {
      where.leadTemperatur = temperatur as "HEISS" | "WARM" | "KALT";
    }
    if (crawlStatus && ["neu", "wiederverwendet", "aktualisiert"].includes(crawlStatus)) {
      where.crawlStatus = crawlStatus;
    }
    if (suchauftragId) {
      where.suchauftraege = { some: { suchauftragId } };
    }
    if (minScore > 0)  where.leadScore = { gte: minScore };
    if (nurWebseite)   where.hatWebseite = true;
    if (nurEmail)      where.hatEmail    = true;
    if (nurTelefon)    where.hatTelefon  = true;

    // Max 5000 Einträge pro Export
    const leads = await prisma.unternehmen.findMany({
      where,
      orderBy: { leadScore: "desc" },
      take: 5000,
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
        wahrscheinlicheSchmerzpunkte: true,
        empfohleneAngebote: true,
        erstesKontaktnachricht: true,
        quelle: true,
        crawlStatus: true,
        suchauftragId: true,
        erstelltAm: true,
        lastCrawledAt: true,
      },
    });

    // ── CSV aufbauen ──────────────────────────────────────────────────────────
    const header = CSV_COLS.map((c) => csvEscape(c.label)).join(";");
    const rows = leads.map((lead) =>
      CSV_COLS.map((col) => {
        const val = (lead as Record<string, unknown>)[col.key];
        // Datums-Formatierung
        if (val instanceof Date) {
          return csvEscape(val.toISOString().slice(0, 19).replace("T", " "));
        }
        return csvEscape(val);
      }).join(";")
    );

    const csv = "\uFEFF" + [header, ...rows].join("\r\n");
    const dateiname = `leads_${new Date().toISOString().slice(0, 10)}.csv`;

    return new NextResponse(csv, {
      status: 200,
      headers: {
        "Content-Type": "text/csv; charset=utf-8",
        "Content-Disposition": `attachment; filename="${dateiname}"`,
      },
    });
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : String(e);
    return NextResponse.json({ error: msg }, { status: 500 });
  }
}
