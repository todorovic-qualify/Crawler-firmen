import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import type { LeadTemperatur, LeadStatus } from "@/types";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function temperaturFarbe(t: LeadTemperatur): string {
  switch (t) {
    case "HEISS": return "bg-red-100 text-red-800 border-red-200";
    case "WARM":  return "bg-orange-100 text-orange-800 border-orange-200";
    case "KALT":  return "bg-blue-100 text-blue-800 border-blue-200";
  }
}

export function temperaturLabel(t: LeadTemperatur): string {
  switch (t) {
    case "HEISS": return "Heiß";
    case "WARM":  return "Warm";
    case "KALT":  return "Kalt";
  }
}

export function statusLabel(s: LeadStatus): string {
  switch (s) {
    case "NEU":           return "Neu";
    case "KONTAKTIERT":   return "Kontaktiert";
    case "INTERESSIERT":  return "Interessiert";
    case "ABGESCHLOSSEN": return "Abgeschlossen";
    case "UNGEEIGNET":    return "Ungeeignet";
  }
}

export function statusFarbe(s: LeadStatus): string {
  switch (s) {
    case "NEU":           return "bg-slate-100 text-slate-700";
    case "KONTAKTIERT":   return "bg-yellow-100 text-yellow-800";
    case "INTERESSIERT":  return "bg-green-100 text-green-800";
    case "ABGESCHLOSSEN": return "bg-emerald-100 text-emerald-800";
    case "UNGEEIGNET":    return "bg-gray-100 text-gray-500";
  }
}

export function scoreBalken(score: number): string {
  if (score >= 75) return "bg-red-500";
  if (score >= 45) return "bg-orange-500";
  return "bg-blue-500";
}

export function datumFormatieren(d: string | Date): string {
  return new Date(d).toLocaleDateString("de-DE", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function kurzUrl(url: string | null | undefined): string {
  if (!url) return "";
  return url.replace(/^https?:\/\//, "").replace(/\/$/, "");
}
