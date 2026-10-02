// Classi di rischio della procedura D-ITA-INF-23: la classe si legge solo
// dalla matrice probabilità × impatto (stessa tabella di risk.services.risk_class).
export type RiskClass = "very_low" | "low" | "medium" | "high" | "critical";

export const RISK_CLASSES: RiskClass[] = ["very_low", "low", "medium", "high", "critical"];

const MATRIX: Record<number, RiskClass[]> = {
  5: ["medium", "high", "high", "critical", "critical"],
  4: ["low", "medium", "high", "critical", "critical"],
  3: ["low", "medium", "medium", "high", "critical"],
  2: ["very_low", "low", "medium", "high", "high"],
  1: ["very_low", "low", "low", "medium", "high"],
};

export function riskClass(probability?: number | null, impact?: number | null): RiskClass | null {
  if (!probability || !impact) return null;
  return MATRIX[probability]?.[impact - 1] ?? null;
}

export function classRank(cls?: string | null): number {
  return RISK_CLASSES.indexOf(cls as RiskClass);
}

// Colori: cella della matrice piena, badge tenue.
export const CLASS_CELL: Record<RiskClass, string> = {
  very_low: "bg-green-300 text-green-900",
  low: "bg-green-500 text-white",
  medium: "bg-yellow-400 text-gray-900",
  high: "bg-orange-500 text-white",
  critical: "bg-red-600 text-white",
};

export const CLASS_BADGE: Record<RiskClass, string> = {
  very_low: "bg-green-50 text-green-700 border-green-200",
  low: "bg-green-100 text-green-800 border-green-300",
  medium: "bg-yellow-100 text-yellow-800 border-yellow-300",
  high: "bg-orange-100 text-orange-800 border-orange-300",
  critical: "bg-red-100 text-red-800 border-red-300",
};

export function classBadge(cls?: string | null): string {
  return CLASS_BADGE[cls as RiskClass] ?? "bg-gray-50 text-gray-500 border-gray-200";
}
