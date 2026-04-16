"use client";

import { useState, useEffect, useCallback, Fragment } from "react";
import { KATEGORIEN } from "@/types";

// ── Typen ──────────────────────────────────────────────────────────────────────

interface Lead {
  id: string;
  name: string;
  kategorie?: string | null;
  stadt?: string | null;
  adresse?: string | null;
  telefon?: string | null;
  email?: string | null;
  webseite?: string | null;
  bewertung?: number | null;
  bewertungsanzahl?: number | null;
  leadScore: number;
  leadTemperatur: "HEISS" | "WARM" | "KALT";
  webseiteBedarfScore: number;
  automationBedarfScore: number;
  hatWebseite: boolean;
  hatEmail: boolean;
  hatTelefon: boolean;
  wahrscheinlicheSchmerzpunkte?: string | null;
  empfohleneAngebote?: string | null;
  erstesKontaktnachricht?: string | null;
  oeffnungszeiten?: string | null;
  crawlStatus?: string | null;
  lastCrawledAt?: string | null;
  erstelltAm?: string | null;
}

interface Pagination {
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
}

type SortField = "leadScore" | "name" | "stadt" | "erstelltAm" | "lastCrawledAt";
type SortDir = "asc" | "desc";

// ── Helfer ─────────────────────────────────────────────────────────────────────

function tempBadge(t: "HEISS" | "WARM" | "KALT") {
  const styles = {
    HEISS: "bg-red-100 text-red-700 font-bold",
    WARM: "bg-orange-100 text-orange-700 font-semibold",
    KALT: "bg-slate-100 text-slate-500",
  };
  const labels = { HEISS: "Heiß", WARM: "Warm", KALT: "Kalt" };
  return (
    <span className={`px-2 py-0.5 rounded text-xs ${styles[t]}`}>
      {labels[t]}
    </span>
  );
}

function herkunftBadge(status?: string | null) {
  if (!status) return null;
  const cfg: Record<string, { label: string; cls: string }> = {
    neu:            { label: "Neu",            cls: "bg-green-100 text-green-700" },
    wiederverwendet:{ label: "Wiederverwendet",cls: "bg-blue-100 text-blue-700" },
    aktualisiert:   { label: "Aktualisiert",   cls: "bg-yellow-100 text-yellow-700" },
  };
  const c = cfg[status];
  if (!c) return null;
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-medium ${c.cls}`}>
      {c.label}
    </span>
  );
}

function fmtDatum(iso?: string | null) {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("de-DE", { day: "2-digit", month: "2-digit", year: "numeric" });
}

async function kopiereText(text: string) {
  try { await navigator.clipboard.writeText(text); } catch {}
}

function exportCSV(params: URLSearchParams) {
  const url = `/api/leads/export?${params.toString()}`;
  const a = document.createElement("a");
  a.href = url;
  a.download = `leads_${new Date().toISOString().slice(0, 10)}.csv`;
  a.click();
}

// ── Haupt-Seite ────────────────────────────────────────────────────────────────

export default function LeadsSeite() {
  // Filter-State
  const [q, setQ]                     = useState("");
  const [stadt, setStadt]             = useState("");
  const [kategorie, setKategorie]     = useState("");
  const [temperatur, setTemperatur]   = useState("");
  const [crawlStatus, setCrawlStatus] = useState("");
  const [minScore, setMinScore]       = useState(0);
  const [nurWebseite, setNurWebseite] = useState(false);
  const [nurEmail, setNurEmail]       = useState(false);
  const [nurTelefon, setNurTelefon]   = useState(false);
  const [maxTage, setMaxTage]         = useState(0);
  const [minWebseiteBedarf, setMinWebseiteBedarf] = useState(0);
  const [minAutomation, setMinAutomation] = useState(0);

  // Sortierung
  const [sortBy, setSortBy]   = useState<SortField>("leadScore");
  const [sortDir, setSortDir] = useState<SortDir>("desc");

  // Pagination
  const [page, setPage]           = useState(1);
  const [pageSize]                = useState(50);
  const [pagination, setPagination] = useState<Pagination | null>(null);

  // Daten
  const [leads, setLeads]       = useState<Lead[]>([]);
  const [laden, setLaden]       = useState(false);
  const [fehler, setFehler]     = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  // Filterbereich ein/aus
  const [zeigeFilter, setZeigeFilter] = useState(false);

  // ── Query-Parameter bauen ────────────────────────────────────────────────────

  const baueParams = useCallback(() => {
    const p = new URLSearchParams();
    if (q)             p.set("q", q);
    if (stadt)         p.set("stadt", stadt);
    if (kategorie)     p.set("kategorie", kategorie);
    if (temperatur)    p.set("temperatur", temperatur);
    if (crawlStatus)   p.set("crawlStatus", crawlStatus);
    if (minScore > 0)  p.set("minScore", String(minScore));
    if (nurWebseite)   p.set("nurWebseite", "true");
    if (nurEmail)      p.set("nurEmail", "true");
    if (nurTelefon)    p.set("nurTelefon", "true");
    if (maxTage > 0)   p.set("maxTage", String(maxTage));
    if (minWebseiteBedarf > 0) p.set("minWebseiteBedarf", String(minWebseiteBedarf));
    if (minAutomation > 0)     p.set("minAutomation", String(minAutomation));
    p.set("sortBy", sortBy);
    p.set("sortDir", sortDir);
    p.set("page", String(page));
    p.set("pageSize", String(pageSize));
    return p;
  }, [q, stadt, kategorie, temperatur, crawlStatus, minScore, nurWebseite,
      nurEmail, nurTelefon, maxTage, minWebseiteBedarf, minAutomation,
      sortBy, sortDir, page, pageSize]);

  // ── Daten laden ──────────────────────────────────────────────────────────────

  const ladeDaten = useCallback(async () => {
    setLaden(true);
    setFehler(null);
    try {
      const params = baueParams();
      const res = await fetch(`/api/leads?${params.toString()}`);
      const data = await res.json();
      if (!res.ok) {
        setFehler(data.error ?? "Fehler beim Laden");
        return;
      }
      setLeads(data.leads ?? []);
      setPagination(data.pagination ?? null);
    } catch (e) {
      setFehler(String(e));
    } finally {
      setLaden(false);
    }
  }, [baueParams]);

  useEffect(() => {
    ladeDaten();
  }, [ladeDaten]);

  // ── Filter zurücksetzen → Seite auf 1 ────────────────────────────────────────

  function resetPage() { setPage(1); }

  function alleFilterZuruecksetzen() {
    setQ(""); setStadt(""); setKategorie(""); setTemperatur("");
    setCrawlStatus(""); setMinScore(0); setNurWebseite(false);
    setNurEmail(false); setNurTelefon(false); setMaxTage(0);
    setMinWebseiteBedarf(0); setMinAutomation(0);
    setPage(1);
  }

  // ── Sortierung toggeln ───────────────────────────────────────────────────────

  function toggleSort(feld: SortField) {
    if (sortBy === feld) {
      setSortDir((d) => (d === "desc" ? "asc" : "desc"));
    } else {
      setSortBy(feld);
      setSortDir("desc");
    }
    resetPage();
  }

  function sortPfeil(feld: SortField) {
    if (sortBy !== feld) return <span className="text-slate-300 ml-1">↕</span>;
    return <span className="text-blue-500 ml-1">{sortDir === "desc" ? "↓" : "↑"}</span>;
  }

  // ── Render ───────────────────────────────────────────────────────────────────

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Alle Leads</h1>
          <p className="text-slate-500 mt-0.5 text-sm">
            Dauerhaft gespeicherte Leads aus allen Suchläufen
            {pagination && (
              <span className="ml-2 font-medium text-slate-700">
                · {pagination.total.toLocaleString("de-DE")} gesamt
              </span>
            )}
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setZeigeFilter((v) => !v)}
            className="text-sm bg-slate-100 hover:bg-slate-200 text-slate-700 px-4 py-2 rounded-lg transition-colors"
          >
            {zeigeFilter ? "Filter ausblenden" : "Filter einblenden"}
          </button>
          <button
            onClick={() => exportCSV(baueParams())}
            className="text-sm bg-slate-800 hover:bg-slate-900 text-white px-4 py-2 rounded-lg transition-colors"
          >
            ↓ CSV Export
          </button>
        </div>
      </div>

      {/* ── Filterbereich ── */}
      {zeigeFilter && (
        <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-4">
          {/* Zeile 1: Freitext + Stadt + Kategorie */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <label className="text-xs font-medium text-slate-600 mb-1 block">Freitext-Suche</label>
              <input
                value={q}
                onChange={(e) => { setQ(e.target.value); resetPage(); }}
                placeholder="Name, Stadt, E-Mail…"
                className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="text-xs font-medium text-slate-600 mb-1 block">Stadt</label>
              <input
                value={stadt}
                onChange={(e) => { setStadt(e.target.value); resetPage(); }}
                placeholder="z.B. Worms"
                className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="text-xs font-medium text-slate-600 mb-1 block">Kategorie</label>
              <select
                value={kategorie}
                onChange={(e) => { setKategorie(e.target.value); resetPage(); }}
                className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">Alle Kategorien</option>
                {KATEGORIEN.map((k) => (
                  <option key={k.wert} value={k.wert}>{k.label}</option>
                ))}
              </select>
            </div>
          </div>

          {/* Zeile 2: Temperatur + Crawl-Status + Min-Score */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <label className="text-xs font-medium text-slate-600 mb-1 block">Lead-Temperatur</label>
              <select
                value={temperatur}
                onChange={(e) => { setTemperatur(e.target.value); resetPage(); }}
                className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">Alle</option>
                <option value="HEISS">Heiß</option>
                <option value="WARM">Warm</option>
                <option value="KALT">Kalt</option>
              </select>
            </div>
            <div>
              <label className="text-xs font-medium text-slate-600 mb-1 block">Crawl-Status</label>
              <select
                value={crawlStatus}
                onChange={(e) => { setCrawlStatus(e.target.value); resetPage(); }}
                className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">Alle</option>
                <option value="neu">Neu</option>
                <option value="wiederverwendet">Wiederverwendet</option>
                <option value="aktualisiert">Aktualisiert</option>
              </select>
            </div>
            <div>
              <label className="text-xs font-medium text-slate-600 mb-1 block">
                Mindest-Score: <strong>{minScore}</strong>
              </label>
              <input
                type="range"
                min={0} max={100} step={5}
                value={minScore}
                onChange={(e) => { setMinScore(Number(e.target.value)); resetPage(); }}
                className="w-full"
              />
            </div>
          </div>

          {/* Zeile 3: Letzte X Tage + Bedarf-Filter */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <label className="text-xs font-medium text-slate-600 mb-1 block">
                Gecrawlt in letzten Tagen: <strong>{maxTage === 0 ? "alle" : maxTage}</strong>
              </label>
              <input
                type="range"
                min={0} max={90} step={1}
                value={maxTage}
                onChange={(e) => { setMaxTage(Number(e.target.value)); resetPage(); }}
                className="w-full"
              />
            </div>
            <div>
              <label className="text-xs font-medium text-slate-600 mb-1 block">
                Min. Website-Bedarf: <strong>{minWebseiteBedarf}</strong>
              </label>
              <input
                type="range"
                min={0} max={100} step={5}
                value={minWebseiteBedarf}
                onChange={(e) => { setMinWebseiteBedarf(Number(e.target.value)); resetPage(); }}
                className="w-full"
              />
            </div>
            <div>
              <label className="text-xs font-medium text-slate-600 mb-1 block">
                Min. Automations-Bedarf: <strong>{minAutomation}</strong>
              </label>
              <input
                type="range"
                min={0} max={100} step={5}
                value={minAutomation}
                onChange={(e) => { setMinAutomation(Number(e.target.value)); resetPage(); }}
                className="w-full"
              />
            </div>
          </div>

          {/* Zeile 4: Checkboxen */}
          <div className="flex flex-wrap gap-4 pt-1">
            {[
              [nurWebseite, setNurWebseite, "Nur mit Website"],
              [nurEmail,    setNurEmail,    "Nur mit E-Mail"],
              [nurTelefon,  setNurTelefon,  "Nur mit Telefon"],
            ].map(([val, setter, label]) => (
              <label key={label as string} className="flex items-center gap-2 text-sm cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={val as boolean}
                  onChange={(e) => { (setter as (v: boolean) => void)(e.target.checked); resetPage(); }}
                  className="rounded"
                />
                <span className="text-slate-700">{label as string}</span>
              </label>
            ))}
            <button
              onClick={alleFilterZuruecksetzen}
              className="ml-auto text-xs text-slate-400 hover:text-slate-600"
            >
              Alle Filter zurücksetzen
            </button>
          </div>
        </div>
      )}

      {/* Fehlermeldung */}
      {fehler && (
        <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg px-4 py-3 text-sm">
          {fehler}
        </div>
      )}

      {/* Lade-Spinner */}
      {laden && (
        <div className="flex items-center justify-center py-12 text-slate-400">
          <svg className="animate-spin h-6 w-6 mr-3 text-blue-500" viewBox="0 0 24 24" fill="none">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4l3-3-3-3v4a8 8 0 100 16v-4l-3 3 3 3v-4a8 8 0 01-8-8z" />
          </svg>
          Leads werden geladen…
        </div>
      )}

      {/* ── Tabelle ── */}
      {!laden && leads.length > 0 && (
        <div className="space-y-3">
          <div className="overflow-x-auto rounded-xl border border-slate-200">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 border-b border-slate-200">
                <tr>
                  {/* Sortierbare Spalten */}
                  {(
                    [
                      ["Unternehmen", "name"],
                      ["Stadt", "stadt"],
                      ["Score", "leadScore"],
                    ] as [string, SortField][]
                  ).map(([h, f]) => (
                    <th
                      key={h}
                      onClick={() => toggleSort(f)}
                      className="text-left px-3 py-2.5 font-medium text-slate-600 whitespace-nowrap cursor-pointer hover:bg-slate-100 select-none"
                    >
                      {h}{sortPfeil(f)}
                    </th>
                  ))}
                  {["Kategorie", "Temp.", "Status", "Website", "Email", "Tel.", "Details"].map((h) => (
                    <th key={h} className="text-left px-3 py-2.5 font-medium text-slate-600 whitespace-nowrap">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {leads.map((lead) => (
                  <Fragment key={lead.id}>
                    <tr
                      className="hover:bg-slate-50 cursor-pointer"
                      onClick={() => setExpandedId(expandedId === lead.id ? null : lead.id)}
                    >
                      <td className="px-3 py-2.5 font-medium text-slate-900 max-w-[160px] truncate">
                        {lead.name}
                      </td>
                      <td className="px-3 py-2.5 text-slate-500 whitespace-nowrap">
                        {lead.stadt ?? "—"}
                      </td>
                      <td className="px-3 py-2.5 font-bold text-slate-900 whitespace-nowrap">
                        {lead.leadScore}
                      </td>
                      <td className="px-3 py-2.5 text-slate-500 whitespace-nowrap">
                        {lead.kategorie ?? "—"}
                      </td>
                      <td className="px-3 py-2.5 whitespace-nowrap">
                        {tempBadge(lead.leadTemperatur)}
                      </td>
                      <td className="px-3 py-2.5 whitespace-nowrap">
                        {herkunftBadge(lead.crawlStatus)}
                      </td>
                      <td className="px-3 py-2.5 whitespace-nowrap">
                        {lead.hatWebseite && lead.webseite ? (
                          <a
                            href={lead.webseite}
                            target="_blank"
                            rel="noopener noreferrer"
                            onClick={(e) => e.stopPropagation()}
                            className="text-blue-600 hover:underline truncate max-w-[110px] block"
                          >
                            {lead.webseite.replace(/^https?:\/\//, "").slice(0, 25)}
                          </a>
                        ) : (
                          <span className="text-slate-300">—</span>
                        )}
                      </td>
                      <td className="px-3 py-2.5 whitespace-nowrap">
                        {lead.email ? (
                          <button
                            onClick={(e) => { e.stopPropagation(); kopiereText(lead.email!); }}
                            title="Kopieren"
                            className="text-blue-600 hover:underline text-left truncate max-w-[130px] block"
                          >
                            {lead.email.slice(0, 22)}
                          </button>
                        ) : (
                          <span className="text-slate-300">—</span>
                        )}
                      </td>
                      <td className="px-3 py-2.5 text-slate-600 whitespace-nowrap">
                        {lead.telefon ? (
                          <button
                            onClick={(e) => { e.stopPropagation(); kopiereText(lead.telefon!); }}
                            title="Kopieren"
                            className="hover:text-blue-600"
                          >
                            {lead.telefon}
                          </button>
                        ) : (
                          <span className="text-slate-300">—</span>
                        )}
                      </td>
                      <td className="px-3 py-2.5 text-slate-400 text-xs whitespace-nowrap">
                        {expandedId === lead.id ? "▲" : "▼"}
                      </td>
                    </tr>

                    {/* Expandierter Detailbereich */}
                    {expandedId === lead.id && (
                      <tr className="bg-slate-50">
                        <td colSpan={10} className="px-4 py-4">
                          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs">
                            <div>
                              <p className="font-semibold text-slate-500 uppercase tracking-wide mb-1">Schmerzpunkte</p>
                              <p className="text-slate-700">{lead.wahrscheinlicheSchmerzpunkte ?? "—"}</p>
                            </div>
                            <div>
                              <p className="font-semibold text-slate-500 uppercase tracking-wide mb-1">Empfohlene Angebote</p>
                              <p className="text-slate-700">{lead.empfohleneAngebote ?? "—"}</p>
                            </div>
                            <div>
                              <p className="font-semibold text-slate-500 uppercase tracking-wide mb-1">Erstkontakt-Nachricht</p>
                              <p className="text-slate-700 whitespace-pre-wrap">{lead.erstesKontaktnachricht ?? "—"}</p>
                            </div>
                          </div>

                          {/* Öffnungszeiten */}
                          {lead.oeffnungszeiten && (
                            <div className="mt-3 pt-3 border-t border-slate-200 text-xs">
                              <p className="font-semibold text-slate-500 uppercase tracking-wide mb-1">Öffnungszeiten</p>
                              <p className="text-slate-700 font-mono">{lead.oeffnungszeiten}</p>
                            </div>
                          )}

                          {/* Aktions-Zeile */}
                          <div className="flex flex-wrap items-center gap-3 mt-3 pt-3 border-t border-slate-200">
                            <div className="flex gap-4 text-xs text-slate-500">
                              <span>Website-Bedarf: <strong>{lead.webseiteBedarfScore}</strong></span>
                              <span>Automation-Bedarf: <strong>{lead.automationBedarfScore}</strong></span>
                              {lead.bewertung && (
                                <span>Bewertung: <strong>{lead.bewertung.toFixed(1)}</strong>{lead.bewertungsanzahl ? ` (${lead.bewertungsanzahl})` : ""}</span>
                              )}
                              <span>Erstellt: <strong>{fmtDatum(lead.erstelltAm)}</strong></span>
                              {lead.lastCrawledAt && (
                                <span>Gecrawlt: <strong>{fmtDatum(lead.lastCrawledAt)}</strong></span>
                              )}
                            </div>
                            <div className="ml-auto flex gap-2">
                              {lead.webseite && (
                                <a
                                  href={lead.webseite}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="text-xs bg-slate-100 hover:bg-slate-200 text-slate-700 px-3 py-1.5 rounded-lg"
                                >
                                  Website öffnen
                                </a>
                              )}
                              {lead.email && (
                                <button
                                  onClick={() => kopiereText(lead.email!)}
                                  className="text-xs bg-slate-100 hover:bg-slate-200 text-slate-700 px-3 py-1.5 rounded-lg"
                                >
                                  E-Mail kopieren
                                </button>
                              )}
                              {lead.telefon && (
                                <button
                                  onClick={() => kopiereText(lead.telefon!)}
                                  className="text-xs bg-slate-100 hover:bg-slate-200 text-slate-700 px-3 py-1.5 rounded-lg"
                                >
                                  Tel. kopieren
                                </button>
                              )}
                            </div>
                          </div>
                        </td>
                      </tr>
                    )}
                  </Fragment>
                ))}
              </tbody>
            </table>
          </div>

          {/* ── Pagination ── */}
          {pagination && pagination.totalPages > 1 && (
            <div className="flex items-center justify-between px-1">
              <p className="text-sm text-slate-500">
                Seite {pagination.page} von {pagination.totalPages} ·{" "}
                {pagination.total.toLocaleString("de-DE")} Leads gesamt
              </p>
              <div className="flex gap-1">
                <button
                  onClick={() => setPage(1)}
                  disabled={page === 1}
                  className="px-2 py-1 text-xs rounded border border-slate-200 disabled:opacity-40 hover:bg-slate-100"
                >
                  «
                </button>
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="px-2 py-1 text-xs rounded border border-slate-200 disabled:opacity-40 hover:bg-slate-100"
                >
                  ‹
                </button>
                {/* Seitenzahlen */}
                {Array.from({ length: Math.min(5, pagination.totalPages) }, (_, i) => {
                  const start = Math.max(1, Math.min(page - 2, pagination.totalPages - 4));
                  const p = start + i;
                  if (p > pagination.totalPages) return null;
                  return (
                    <button
                      key={p}
                      onClick={() => setPage(p)}
                      className={`px-2.5 py-1 text-xs rounded border ${
                        p === page
                          ? "bg-blue-600 border-blue-600 text-white"
                          : "border-slate-200 hover:bg-slate-100"
                      }`}
                    >
                      {p}
                    </button>
                  );
                })}
                <button
                  onClick={() => setPage((p) => Math.min(pagination.totalPages, p + 1))}
                  disabled={page === pagination.totalPages}
                  className="px-2 py-1 text-xs rounded border border-slate-200 disabled:opacity-40 hover:bg-slate-100"
                >
                  ›
                </button>
                <button
                  onClick={() => setPage(pagination.totalPages)}
                  disabled={page === pagination.totalPages}
                  className="px-2 py-1 text-xs rounded border border-slate-200 disabled:opacity-40 hover:bg-slate-100"
                >
                  »
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Leer-Zustand */}
      {!laden && leads.length === 0 && !fehler && (
        <div className="text-center py-16 text-slate-400">
          {pagination?.total === 0
            ? "Keine Leads gefunden. Filter anpassen oder zuerst eine Suche starten."
            : "Noch keine Leads vorhanden. Starte eine Suche auf der Startseite."}
        </div>
      )}
    </div>
  );
}
