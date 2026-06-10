// Helper condivisi del modulo Risk.
// Allineamento con la logica backend di RiskAssessment.risk_level:
// - <= 7 verde
// - <= 14 giallo
// - > 14 rosso
// Unica definizione delle soglie per tutta la UI del modulo.

export type RiskLevel = "verde" | "giallo" | "rosso";

export function riskLevelFromScore(score: number): RiskLevel {
  if (score <= 7) return "verde";
  if (score <= 14) return "giallo";
  return "rosso";
}

export const RISK_LEVEL_COLORS: Record<string, string> = {
  verde:  "bg-green-100 text-green-800",
  giallo: "bg-yellow-100 text-yellow-800",
  rosso:  "bg-red-100 text-red-800",
};

export const RISK_LEVEL_ICONS: Record<string, string> = {
  verde: "🟢", giallo: "🟡", rosso: "🔴",
};

export function matrixColor(p: number, i: number): string {
  return RISK_LEVEL_COLORS[riskLevelFromScore(p * i)];
}

export const TREATMENT_BADGE: Record<string, string> = {
  mitigare:   "bg-blue-100 text-blue-800",
  trasferire: "bg-purple-100 text-purple-800",
  accettare:  "bg-yellow-100 text-yellow-800",
  evitare:    "bg-gray-100 text-gray-700",
};

export function isActiveTreatment(treatment: string | null | undefined): boolean {
  return treatment === "mitigare" || treatment === "trasferire";
}

export function formatAle(ale: string | null) {
  if (!ale) return "—";
  const n = parseFloat(ale);
  return isNaN(n) ? ale : new Intl.NumberFormat("it-IT", { style: "currency", currency: "EUR" }).format(n);
}
