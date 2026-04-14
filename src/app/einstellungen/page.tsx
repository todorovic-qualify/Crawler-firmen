"use client";

import { useState, useEffect } from "react";
import { KATEGORIEN } from "@/types";

// ── Types ─────────────────────────────────────────────────────────────────────

interface CrawlerKonfig {
  max_concurrent: number;
  delay_seconds: number;
  proxy_url: string;
  nominatim_url: string;
  overpass_url: string;
}

interface ScoringFaktoren {
  kein_website: number;
  website_sehr_schwach: number;
  website_ausbaufaehig: number;
  kein_cta: number;
  keine_buchung_kontakt: number;
  kein_buchungssystem: number;
  veraltet_indikatoren: number;
  keine_email: number;
  telefon_intensiv_bonus: number;
  buchung_intensiv_bonus: number;
  lead_reaktionsabhaengig: number;
  whatsapp_potential: number;
  moderner_starker_auftritt: number;
}

interface ScoringKonfig {
  heiss_schwelle: number;
  warm_schwelle: number;
  faktoren: ScoringFaktoren;
}

interface KategorieProfil {
  telefon_intensiv: boolean;
  buchung_intensiv: boolean;
  ki_telefon: boolean;
  whatsapp: boolean;
  booking: boolean;
  automation_bonus: number;
  webseite_bonus: number;
  hauptangebot: string;
  pitch: string;
}

interface AppKonfig {
  crawler: CrawlerKonfig;
  scoring: ScoringKonfig;
  kategorien: Record<string, KategorieProfil>;
}

// ── Labels ────────────────────────────────────────────────────────────────────

const FAKTOR_META: Record<keyof ScoringFaktoren, { label: string; group: string }> = {
  kein_website:             { label: "Kein Website vorhanden",               group: "Website" },
  website_sehr_schwach:     { label: "Website sehr schwach (Score < 30)",    group: "Website" },
  website_ausbaufaehig:     { label: "Website ausbaufähig (Score < 50)",     group: "Website" },
  kein_cta:                 { label: "Kein Call-to-Action",                  group: "Website" },
  keine_buchung_kontakt:    { label: "Keine Buchungs-/Kontaktoption",         group: "Website" },
  kein_buchungssystem:      { label: "Kein Buchungssystem",                  group: "Website" },
  veraltet_indikatoren:     { label: "Veraltete HTML-Indikatoren",           group: "Website" },
  moderner_starker_auftritt:{ label: "Moderner, starker Auftritt (Abzug)",   group: "Website" },
  keine_email:              { label: "Keine E-Mail-Adresse",                 group: "Kontakt" },
  telefon_intensiv_bonus:   { label: "Telefon-intensives Segment",           group: "Kategorie" },
  buchung_intensiv_bonus:   { label: "Buchungs-intensives Segment",          group: "Kategorie" },
  lead_reaktionsabhaengig:  { label: "Lead-Reaktion entscheidend",           group: "Kategorie" },
  whatsapp_potential:       { label: "WhatsApp-Potential nicht genutzt",     group: "Kategorie" },
};

const FAKTOR_GRUPPEN = ["Website", "Kontakt", "Kategorie"];

// ── Helpers ───────────────────────────────────────────────────────────────────

type Tab = "crawler" | "scoring" | "kategorien";

function Toggle({ value, onChange }: { value: boolean; onChange: (v: boolean) => void }) {
  return (
    <button
      type="button"
      onClick={() => onChange(!value)}
      className={`relative w-10 h-6 rounded-full transition-colors shrink-0 ${
        value ? "bg-blue-500" : "bg-slate-300"
      }`}
    >
      <span
        className={`absolute top-1 w-4 h-4 bg-white rounded-full shadow transition-transform ${
          value ? "left-5" : "left-1"
        }`}
      />
    </button>
  );
}

function Slider({
  value,
  min,
  max,
  onChange,
  color = "blue",
}: {
  value: number;
  min: number;
  max: number;
  onChange: (v: number) => void;
  color?: "blue" | "red" | "orange" | "slate";
}) {
  const accentMap = {
    blue: "accent-blue-500",
    red: "accent-red-500",
    orange: "accent-orange-400",
    slate: "accent-slate-400",
  };
  return (
    <input
      type="range"
      min={min}
      max={max}
      value={value}
      onChange={(e) => onChange(Number(e.target.value))}
      className={`w-full ${accentMap[color]}`}
    />
  );
}

function genPythonCode(konfig: AppKonfig): string {
  const py = (v: boolean) => (v ? "True" : "False");
  const q = (s: string) => `"${s.replace(/\\/g, "\\\\").replace(/"/g, '\\"')}"`;
  const lines: string[] = [];

  lines.push("# ═══════════════════════════════════════════════════════════════");
  lines.push("# Generiert von LeadScout Einstellungen");
  lines.push(`# ${new Date().toLocaleString("de-DE")}`);
  lines.push("# ═══════════════════════════════════════════════════════════════");
  lines.push("");
  lines.push("# ── 1. .env  ────────────────────────────────────────────────────");
  lines.push(`CRAWLER_MAX_CONCURRENT="${konfig.crawler.max_concurrent}"`);
  lines.push(`CRAWLER_DELAY_SECONDS="${konfig.crawler.delay_seconds}"`);
  if (konfig.crawler.proxy_url) lines.push(`CRAWLER_PROXY_URL="${konfig.crawler.proxy_url}"`);
  lines.push(`NOMINATIM_URL="${konfig.crawler.nominatim_url}"`);
  lines.push(`OVERPASS_URL="${konfig.crawler.overpass_url}"`);
  lines.push("");
  lines.push("# ── 2. crawler/scorer.py  ───────────────────────────────────────");
  lines.push("");
  lines.push("# Temperatur-Schwellenwerte (in bewerte())");
  lines.push(`HEISS_SCHWELLE = ${konfig.scoring.heiss_schwelle}`);
  lines.push(`WARM_SCHWELLE  = ${konfig.scoring.warm_schwelle}`);
  lines.push("");
  lines.push("# Scoring-Faktoren");
  lines.push("DEFAULT_FAKTOREN = {");
  for (const [k, v] of Object.entries(konfig.scoring.faktoren)) {
    lines.push(`    ${q(k)}: ${v},`);
  }
  lines.push("}");
  lines.push("");
  lines.push("# Kategorie-Profile");
  lines.push("KATEGORIE_PROFILE: dict[str, dict] = {");
  for (const [kat, p] of Object.entries(konfig.kategorien)) {
    lines.push(`    ${q(kat)}: {`);
    lines.push(`        "telefon_intensiv": ${py(p.telefon_intensiv)},`);
    lines.push(`        "buchung_intensiv": ${py(p.buchung_intensiv)},`);
    lines.push(`        "automation_bonus": ${p.automation_bonus},`);
    lines.push(`        "webseite_bonus": ${p.webseite_bonus},`);
    lines.push(`        "ki_telefon": ${py(p.ki_telefon)},`);
    lines.push(`        "whatsapp": ${py(p.whatsapp)},`);
    lines.push(`        "booking": ${py(p.booking)},`);
    lines.push(`        "hauptangebot": ${q(p.hauptangebot)},`);
    lines.push(`        "pitch": ${q(p.pitch)},`);
    lines.push(`    },`);
  }
  lines.push("}");
  return lines.join("\n");
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function EinstellungenSeite() {
  const [tab, setTab] = useState<Tab>("crawler");
  const [konfig, setKonfig] = useState<AppKonfig | null>(null);
  const [laden, setLaden] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [saveState, setSaveState] = useState<"idle" | "ok" | "err">("idle");
  const [fehler, setFehler] = useState<string | null>(null);
  const [selectedKat, setSelectedKat] = useState<string>("restaurant");
  const [pythonModal, setPythonModal] = useState(false);
  const [kopiert, setKopiert] = useState(false);

  useEffect(() => {
    fetch("/api/einstellungen")
      .then((r) => r.json())
      .then((d) => { setKonfig(d); setLaden(false); })
      .catch(() => setLaden(false));
  }, []);

  function setCrawler<K extends keyof CrawlerKonfig>(key: K, val: CrawlerKonfig[K]) {
    setKonfig((prev) => prev ? { ...prev, crawler: { ...prev.crawler, [key]: val } } : prev);
  }

  function setFaktor(key: keyof ScoringFaktoren, val: number) {
    setKonfig((prev) => prev ? {
      ...prev,
      scoring: { ...prev.scoring, faktoren: { ...prev.scoring.faktoren, [key]: val } },
    } : prev);
  }

  function setSchwelle(key: "heiss_schwelle" | "warm_schwelle", val: number) {
    setKonfig((prev) => prev ? { ...prev, scoring: { ...prev.scoring, [key]: val } } : prev);
  }

  function setKategorie<K extends keyof KategorieProfil>(kat: string, key: K, val: KategorieProfil[K]) {
    setKonfig((prev) => prev ? {
      ...prev,
      kategorien: { ...prev.kategorien, [kat]: { ...prev.kategorien[kat], [key]: val } },
    } : prev);
  }

  async function handleSpeichern() {
    if (!konfig) return;
    setIsSaving(true);
    setFehler(null);
    try {
      const res = await fetch("/api/einstellungen", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(konfig),
      });
      if (!res.ok) throw new Error("Speichern fehlgeschlagen");
      setSaveState("ok");
      setTimeout(() => setSaveState("idle"), 3000);
    } catch (e) {
      setFehler(e instanceof Error ? e.message : "Fehler");
      setSaveState("err");
    } finally {
      setIsSaving(false);
    }
  }

  async function handleZuruecksetzen() {
    if (!confirm("Alle Einstellungen auf Standardwerte zurücksetzen?")) return;
    await fetch("/api/einstellungen", { method: "DELETE" });
    const d = await fetch("/api/einstellungen").then((r) => r.json());
    setKonfig(d);
    setSaveState("ok");
    setTimeout(() => setSaveState("idle"), 2000);
  }

  function handleKopieren() {
    if (!konfig) return;
    navigator.clipboard.writeText(genPythonCode(konfig));
    setKopiert(true);
    setTimeout(() => setKopiert(false), 2500);
  }

  if (laden || !konfig) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <p className="text-slate-400">Einstellungen werden geladen…</p>
      </div>
    );
  }

  const currentKat = konfig.kategorien[selectedKat];
  const katLabel = KATEGORIEN.find((k) => k.wert === selectedKat)?.label ?? selectedKat;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Einstellungen</h1>
          <p className="text-slate-500 mt-1 text-sm">
            Alle Crawler- und Scoring-Parameter die sonst in Python konfiguriert werden
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={handleZuruecksetzen}
            className="text-sm text-slate-500 hover:text-slate-700 px-3 py-2 rounded-lg hover:bg-slate-100 transition-colors"
          >
            Zurücksetzen
          </button>
          <button
            onClick={() => setPythonModal(true)}
            className="text-sm border border-slate-300 hover:bg-slate-50 text-slate-700 px-4 py-2 rounded-lg transition-colors font-mono"
          >
            {"</>"}  Python-Code
          </button>
          <button
            onClick={handleSpeichern}
            disabled={isSaving}
            className={`text-sm font-medium px-5 py-2 rounded-lg transition-colors text-white ${
              saveState === "ok"
                ? "bg-green-500"
                : saveState === "err"
                ? "bg-red-500"
                : "bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300"
            }`}
          >
            {isSaving ? "Speichert…" : saveState === "ok" ? "✓ Gespeichert" : "Speichern"}
          </button>
        </div>
      </div>

      {fehler && (
        <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg px-4 py-3 text-sm">
          {fehler}
        </div>
      )}

      {/* Tabs */}
      <div className="border-b border-slate-200">
        <nav className="-mb-px flex">
          {(
            [
              ["crawler",    "Crawler"],
              ["scoring",    "Scoring"],
              ["kategorien", "Kategorie-Profile"],
            ] as [Tab, string][]
          ).map(([t, label]) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`px-5 py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
                tab === t
                  ? "border-blue-600 text-blue-600"
                  : "border-transparent text-slate-500 hover:text-slate-700"
              }`}
            >
              {label}
            </button>
          ))}
        </nav>
      </div>

      {/* ── Tab: Crawler ────────────────────────────────────────────────────── */}
      {tab === "crawler" && (
        <div className="space-y-4">
          {/* HTTP & Rate-Limiting */}
          <div className="bg-white rounded-xl border border-slate-200 p-6">
            <h2 className="text-base font-semibold text-slate-800 mb-1">HTTP & Rate-Limiting</h2>
            <p className="text-xs text-slate-400 mb-5">
              Entspricht <code className="bg-slate-100 px-1 py-0.5 rounded">CRAWLER_MAX_CONCURRENT</code> und{" "}
              <code className="bg-slate-100 px-1 py-0.5 rounded">CRAWLER_DELAY_SECONDS</code> in der <code className="bg-slate-100 px-1 py-0.5 rounded">.env</code>
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Max. parallele Anfragen
                </label>
                <input
                  type="number"
                  min={1}
                  max={20}
                  value={konfig.crawler.max_concurrent}
                  onChange={(e) => setCrawler("max_concurrent", Number(e.target.value))}
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <p className="text-xs text-slate-400 mt-1.5">
                  Gleichzeitige HTTP-Verbindungen pro Crawler-Job
                </p>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Verzögerung zwischen Anfragen (Sek.)
                </label>
                <input
                  type="number"
                  min={0.1}
                  max={30}
                  step={0.5}
                  value={konfig.crawler.delay_seconds}
                  onChange={(e) => setCrawler("delay_seconds", Number(e.target.value))}
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <p className="text-xs text-slate-400 mt-1.5">
                  Mindest-Pause pro Domain (verhindert Blockierung)
                </p>
              </div>
            </div>
          </div>

          {/* Proxy */}
          <div className="bg-white rounded-xl border border-slate-200 p-6">
            <h2 className="text-base font-semibold text-slate-800 mb-1">Proxy</h2>
            <p className="text-xs text-slate-400 mb-5">
              Entspricht <code className="bg-slate-100 px-1 py-0.5 rounded">CRAWLER_PROXY_URL</code> in der <code className="bg-slate-100 px-1 py-0.5 rounded">.env</code>
            </p>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Proxy URL{" "}
                <span className="text-slate-400 font-normal">(optional)</span>
              </label>
              <input
                type="text"
                value={konfig.crawler.proxy_url}
                onChange={(e) => setCrawler("proxy_url", e.target.value)}
                placeholder="http://user:pass@proxy.example.com:8080"
                className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <p className="text-xs text-slate-400 mt-1.5">
                Leer lassen für keine Proxy-Nutzung. Nützlich für rotierende IP-Pools.
              </p>
            </div>
          </div>

          {/* API-Endpunkte */}
          <div className="bg-white rounded-xl border border-slate-200 p-6">
            <h2 className="text-base font-semibold text-slate-800 mb-1">API-Endpunkte</h2>
            <p className="text-xs text-slate-400 mb-5">
              Entspricht <code className="bg-slate-100 px-1 py-0.5 rounded">NOMINATIM_URL</code> und <code className="bg-slate-100 px-1 py-0.5 rounded">OVERPASS_URL</code>
            </p>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Nominatim URL{" "}
                  <span className="text-slate-400 font-normal">– Geocoding (Ort → Koordinaten)</span>
                </label>
                <input
                  type="text"
                  value={konfig.crawler.nominatim_url}
                  onChange={(e) => setCrawler("nominatim_url", e.target.value)}
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <p className="text-xs text-slate-400 mt-1.5">
                  Öffentlicher Endpunkt kostenlos. Bei hohem Volumen eigene Nominatim-Instanz empfohlen.
                </p>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Overpass API URL{" "}
                  <span className="text-slate-400 font-normal">– OpenStreetMap Datenabfrage</span>
                </label>
                <input
                  type="text"
                  value={konfig.crawler.overpass_url}
                  onChange={(e) => setCrawler("overpass_url", e.target.value)}
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <p className="text-xs text-slate-400 mt-1.5">
                  Findet lokale Unternehmen per Umkreissuche. Alternativer Server: <code>https://overpass.kumi.systems/api/interpreter</code>
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── Tab: Scoring ────────────────────────────────────────────────────── */}
      {tab === "scoring" && (
        <div className="space-y-4">
          {/* Schwellenwerte */}
          <div className="bg-white rounded-xl border border-slate-200 p-6">
            <h2 className="text-base font-semibold text-slate-800 mb-1">Temperatur-Schwellenwerte</h2>
            <p className="text-sm text-slate-500 mb-5">
              Ab welchem Score wird ein Lead als heiß, warm oder kalt eingestuft?
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="text-sm font-medium text-slate-700 flex items-center gap-1.5">
                    <span>🔥</span> Heiß ab Score
                  </label>
                  <span className="text-lg font-bold text-red-600">{konfig.scoring.heiss_schwelle}</span>
                </div>
                <Slider
                  value={konfig.scoring.heiss_schwelle}
                  min={50}
                  max={95}
                  color="red"
                  onChange={(v) => setSchwelle("heiss_schwelle", v)}
                />
                <div className="flex justify-between text-xs text-slate-400 mt-1">
                  <span>50</span><span>95</span>
                </div>
              </div>
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="text-sm font-medium text-slate-700 flex items-center gap-1.5">
                    <span>☀️</span> Warm ab Score
                  </label>
                  <span className="text-lg font-bold text-orange-500">{konfig.scoring.warm_schwelle}</span>
                </div>
                <Slider
                  value={konfig.scoring.warm_schwelle}
                  min={10}
                  max={Math.min(74, konfig.scoring.heiss_schwelle - 1)}
                  color="orange"
                  onChange={(v) => setSchwelle("warm_schwelle", v)}
                />
                <div className="flex justify-between text-xs text-slate-400 mt-1">
                  <span>10</span><span>{Math.min(74, konfig.scoring.heiss_schwelle - 1)}</span>
                </div>
              </div>
            </div>
            <div className="mt-4 flex flex-wrap gap-2">
              <span className="bg-red-50 text-red-700 border border-red-200 px-3 py-1.5 rounded-lg text-sm font-medium">
                🔥 Heiß: ≥ {konfig.scoring.heiss_schwelle} Pkt.
              </span>
              <span className="bg-orange-50 text-orange-700 border border-orange-200 px-3 py-1.5 rounded-lg text-sm font-medium">
                ☀️ Warm: {konfig.scoring.warm_schwelle}–{konfig.scoring.heiss_schwelle - 1} Pkt.
              </span>
              <span className="bg-slate-50 text-slate-600 border border-slate-200 px-3 py-1.5 rounded-lg text-sm font-medium">
                ❄️ Kalt: &lt; {konfig.scoring.warm_schwelle} Pkt.
              </span>
            </div>
          </div>

          {/* Scoring-Faktoren */}
          <div className="bg-white rounded-xl border border-slate-200 p-6">
            <h2 className="text-base font-semibold text-slate-800 mb-1">Scoring-Faktoren</h2>
            <p className="text-sm text-slate-500 mb-5">
              Wie viele Punkte gibt jeder erkannte Zustand? Entspricht den Konstanten in <code className="bg-slate-100 px-1 rounded">crawler/scorer.py</code>.
            </p>
            <div className="space-y-6">
              {FAKTOR_GRUPPEN.map((gruppe) => {
                const keys = (Object.keys(konfig.scoring.faktoren) as (keyof ScoringFaktoren)[]).filter(
                  (k) => FAKTOR_META[k].group === gruppe
                );
                return (
                  <div key={gruppe}>
                    <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">
                      {gruppe}
                    </p>
                    <div className="space-y-3">
                      {keys.map((key) => {
                        const val = konfig.scoring.faktoren[key];
                        const isAbzug = val < 0 || key === "moderner_starker_auftritt";
                        return (
                          <div key={key} className="flex items-center gap-3">
                            <div className="w-56 shrink-0">
                              <p className="text-sm text-slate-700 leading-tight">
                                {FAKTOR_META[key].label}
                              </p>
                            </div>
                            <div className="flex-1">
                              <Slider
                                value={val}
                                min={isAbzug ? -30 : 0}
                                max={isAbzug ? 0 : 30}
                                color={isAbzug ? "slate" : "blue"}
                                onChange={(v) => setFaktor(key, v)}
                              />
                            </div>
                            <span
                              className={`w-12 text-sm font-bold text-right tabular-nums ${
                                val > 0 ? "text-green-600" : val < 0 ? "text-red-500" : "text-slate-400"
                              }`}
                            >
                              {val > 0 ? "+" : ""}
                              {val}
                            </span>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* ── Tab: Kategorien ─────────────────────────────────────────────────── */}
      {tab === "kategorien" && (
        <div className="grid grid-cols-1 lg:grid-cols-[220px_1fr] gap-4">
          {/* Kategorie-Liste */}
          <div className="bg-white rounded-xl border border-slate-200 p-3 h-fit lg:sticky lg:top-4">
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider px-2 mb-2">
              Kategorien
            </p>
            <div className="space-y-0.5">
              {KATEGORIEN.map((k) => (
                <button
                  key={k.wert}
                  onClick={() => setSelectedKat(k.wert)}
                  className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors ${
                    selectedKat === k.wert
                      ? "bg-blue-50 text-blue-700 font-medium"
                      : "text-slate-700 hover:bg-slate-50"
                  }`}
                >
                  {k.label}
                </button>
              ))}
            </div>
          </div>

          {/* Kategorie-Formular */}
          {currentKat && (
            <div className="space-y-4">
              <div className="bg-white rounded-xl border border-slate-200 p-6">
                <h2 className="text-lg font-semibold text-slate-900 mb-1">{katLabel}</h2>
                <p className="text-xs text-slate-400 mb-5">
                  Entspricht <code className="bg-slate-100 px-1 rounded">KATEGORIE_PROFILE[&quot;{selectedKat}&quot;]</code> in <code className="bg-slate-100 px-1 rounded">crawler/scorer.py</code>
                </p>

                {/* Branchenmerkmale */}
                <div className="mb-6">
                  <h3 className="text-sm font-semibold text-slate-700 mb-3">Branchenmerkmale</h3>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    {(
                      [
                        ["telefon_intensiv", "Telefon-intensiv"],
                        ["buchung_intensiv", "Buchungs-intensiv"],
                        ["ki_telefon",       "KI-Telefonagent anbieten"],
                        ["whatsapp",         "WhatsApp-Automation anbieten"],
                        ["booking",          "Buchungssystem anbieten"],
                      ] as [keyof KategorieProfil, string][]
                    ).map(([field, label]) => (
                      <label key={field} className="flex items-center gap-3 cursor-pointer select-none">
                        <Toggle
                          value={currentKat[field] as boolean}
                          onChange={(v) => setKategorie(selectedKat, field, v)}
                        />
                        <span className="text-sm text-slate-700">{label}</span>
                      </label>
                    ))}
                  </div>
                </div>

                {/* Bonus-Punkte */}
                <div className="mb-6">
                  <h3 className="text-sm font-semibold text-slate-700 mb-3">Bonus-Punkte</h3>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
                    <div>
                      <div className="flex justify-between mb-1">
                        <label className="text-sm text-slate-700">Automatisierungs-Bonus</label>
                        <span className="text-sm font-bold text-green-600">+{currentKat.automation_bonus}</span>
                      </div>
                      <Slider
                        value={currentKat.automation_bonus}
                        min={0}
                        max={20}
                        onChange={(v) => setKategorie(selectedKat, "automation_bonus", v)}
                      />
                      <div className="flex justify-between text-xs text-slate-400 mt-0.5">
                        <span>0</span><span>20</span>
                      </div>
                      <p className="text-xs text-slate-400 mt-1">
                        Immer addiert – misst Automatisierungspotenzial der Branche
                      </p>
                    </div>
                    <div>
                      <div className="flex justify-between mb-1">
                        <label className="text-sm text-slate-700">Website-Bedarf-Bonus</label>
                        <span className="text-sm font-bold text-blue-600">+{currentKat.webseite_bonus}</span>
                      </div>
                      <Slider
                        value={currentKat.webseite_bonus}
                        min={0}
                        max={20}
                        onChange={(v) => setKategorie(selectedKat, "webseite_bonus", v)}
                      />
                      <div className="flex justify-between text-xs text-slate-400 mt-0.5">
                        <span>0</span><span>20</span>
                      </div>
                      <p className="text-xs text-slate-400 mt-1">
                        Zuschlag auf den Website-Bedarf-Score (0–100)
                      </p>
                    </div>
                  </div>
                </div>

                {/* Verkaufsinhalte */}
                <div>
                  <h3 className="text-sm font-semibold text-slate-700 mb-3">Verkaufsinhalte</h3>
                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm text-slate-700 mb-1">
                        Hauptangebot{" "}
                        <span className="text-slate-400 font-normal">
                          – erscheint in "Empfohlene Angebote" und Erstkontakt-Nachrichten
                        </span>
                      </label>
                      <input
                        type="text"
                        value={currentKat.hauptangebot}
                        onChange={(e) => setKategorie(selectedKat, "hauptangebot", e.target.value)}
                        className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                    </div>
                    <div>
                      <label className="block text-sm text-slate-700 mb-1">
                        Sales-Pitch{" "}
                        <span className="text-slate-400 font-normal">– individueller Aufhänger pro Branche</span>
                      </label>
                      <textarea
                        value={currentKat.pitch}
                        onChange={(e) => setKategorie(selectedKat, "pitch", e.target.value)}
                        rows={3}
                        className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-y"
                      />
                    </div>
                  </div>
                </div>
              </div>

              {/* Vorschau */}
              <div className="bg-slate-50 rounded-xl border border-slate-200 p-5">
                <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">
                  Vorschau – Python-Profil
                </p>
                <pre className="text-xs font-mono text-slate-600 overflow-x-auto whitespace-pre">
{`KATEGORIE_PROFILE["${selectedKat}"] = {
    "telefon_intensiv": ${currentKat.telefon_intensiv ? "True" : "False"},
    "buchung_intensiv": ${currentKat.buchung_intensiv ? "True" : "False"},
    "automation_bonus": ${currentKat.automation_bonus},
    "webseite_bonus":   ${currentKat.webseite_bonus},
    "ki_telefon": ${currentKat.ki_telefon ? "True" : "False"},
    "whatsapp":   ${currentKat.whatsapp ? "True" : "False"},
    "booking":    ${currentKat.booking ? "True" : "False"},
    "hauptangebot": "${currentKat.hauptangebot.replace(/"/g, '\\"')}",
    "pitch": "${currentKat.pitch.replace(/"/g, '\\"')}",
}`}
                </pre>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── Python-Code Modal ─────────────────────────────────────────────────── */}
      {pythonModal && (
        <div
          className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
          onClick={(e) => { if (e.target === e.currentTarget) setPythonModal(false); }}
        >
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-3xl max-h-[85vh] flex flex-col">
            <div className="flex items-center justify-between px-5 py-4 border-b border-slate-200">
              <div>
                <h2 className="text-base font-semibold text-slate-900">Python-Code exportieren</h2>
                <p className="text-xs text-slate-400 mt-0.5">
                  Kopiere diesen Code in deine Python-Dateien
                </p>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={handleKopieren}
                  className={`text-sm px-3 py-1.5 rounded-lg transition-colors font-medium ${
                    kopiert
                      ? "bg-green-100 text-green-700"
                      : "bg-slate-100 hover:bg-slate-200 text-slate-700"
                  }`}
                >
                  {kopiert ? "✓ Kopiert!" : "Alles kopieren"}
                </button>
                <button
                  onClick={() => setPythonModal(false)}
                  className="text-slate-400 hover:text-slate-600 text-xl w-8 h-8 flex items-center justify-center rounded hover:bg-slate-100"
                >
                  ×
                </button>
              </div>
            </div>
            <div className="overflow-auto flex-1 p-5">
              <pre className="text-xs font-mono bg-slate-950 text-green-300 p-4 rounded-lg whitespace-pre overflow-x-auto leading-relaxed">
                {genPythonCode(konfig)}
              </pre>
            </div>
            <div className="px-5 py-3 border-t border-slate-200 bg-slate-50 rounded-b-xl">
              <div className="flex flex-wrap gap-4 text-xs text-slate-500">
                <span>
                  <strong className="text-slate-700">Zeilen 1–6:</strong> In <code className="bg-slate-200 px-1 rounded">.env</code> eintragen
                </span>
                <span>
                  <strong className="text-slate-700">Rest:</strong> In <code className="bg-slate-200 px-1 rounded">crawler/scorer.py</code> ersetzen
                </span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
