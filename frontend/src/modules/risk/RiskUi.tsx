import { useTranslation } from "react-i18next";
import { IMPACT_DIMENSIONS, type ImpactDimension } from "../../api/endpoints/risk";
import { classBadge, riskClass, type RiskClass } from "./riskClasses";

/** Badge della classe di rischio (testo tradotto, colore della matrice). */
export function ClassBadge({ cls, size = "sm" }: { cls?: string | null; size?: "sm" | "xs" }) {
  const { t } = useTranslation();
  if (!cls) return <span className="text-gray-300 text-xs">—</span>;
  const pad = size === "xs" ? "px-1.5 py-0 text-[11px]" : "px-2 py-0.5 text-xs";
  return (
    <span className={`inline-block rounded-full border font-medium whitespace-nowrap ${pad} ${classBadge(cls)}`}>
      {t(`risk.classes.${cls}`)}
    </span>
  );
}

/** Classe attuale → attesa, compatta per gli elenchi. */
export function ClassTransition({ current, expected }: { current?: string | null; expected?: string | null }) {
  return (
    <span className="inline-flex items-center gap-1 whitespace-nowrap">
      <ClassBadge cls={current} />
      {expected && expected !== current && (
        <>
          <span className="text-gray-400 text-xs">→</span>
          <ClassBadge cls={expected} size="xs" />
        </>
      )}
    </span>
  );
}

/**
 * Scelta di un livello 1–5 con il criterio della procedura accanto a ogni
 * valore (probabilità o una dimensione d'impatto). `criteria(level)` restituisce
 * il testo del criterio; `allowEmpty` aggiunge "non pertinente".
 */
export function LevelPicker({
  value, onChange, criteria, disabled, allowEmpty = false, emptyLabel,
}: {
  value: number | null;
  onChange: (v: number | null) => void;
  criteria: (level: number) => string;
  disabled?: boolean;
  allowEmpty?: boolean;
  emptyLabel?: string;
}) {
  return (
    <div className="space-y-1">
      {allowEmpty && (
        <label className={`flex items-start gap-2 rounded px-2 py-1 text-xs ${value == null ? "bg-gray-100" : ""}`}>
          <input type="radio" checked={value == null} disabled={disabled} onChange={() => onChange(null)} className="mt-0.5" />
          <span className="text-gray-500">{emptyLabel}</span>
        </label>
      )}
      {[5, 4, 3, 2, 1].map(level => (
        <label
          key={level}
          className={`flex items-start gap-2 rounded px-2 py-1 text-xs cursor-pointer ${
            value === level ? "bg-primary-50 ring-1 ring-primary-200" : "hover:bg-gray-50"
          } ${disabled ? "cursor-default opacity-80" : ""}`}
        >
          <input type="radio" checked={value === level} disabled={disabled} onChange={() => onChange(level)} className="mt-0.5" />
          <span className="font-semibold w-4 text-gray-700">{level}</span>
          <span className="text-gray-600">{criteria(level)}</span>
        </label>
      ))}
    </div>
  );
}

export type ImpactValues = Partial<Record<ImpactDimension, number | null>>;

/** Impatto complessivo = caso peggiore fra le dimensioni (anteprima client). */
export function overallImpact(values: ImpactValues): number | null {
  const nums = IMPACT_DIMENSIONS.map(d => values[d]).filter((v): v is number => !!v);
  return nums.length ? Math.max(...nums) : null;
}

/** Impatto minimo dato dalla classe di protezione delle informazioni colpite
 * (§7.2): vale solo per minacce alla riservatezza. Specchio di
 * `threat_impact_floor` nel backend. */
const CONFIDENTIALITY_FLOOR: Record<string, number> = { very_high: 5, high: 4, normal: 3, low: 2 };

export function impactFloor(cia: readonly string[] | undefined, levels: readonly string[]): number | null {
  if (!cia?.includes("C")) return null;
  const values = levels.map(l => CONFIDENTIALITY_FLOOR[l]).filter((v): v is number => !!v);
  return values.length ? Math.max(...values) : null;
}

/** Anteprima della classe dalla matrice (la classe vera la calcola il backend):
 * impatto mai sotto la soglia e override mai sotto la classe della soglia. */
export function previewClass(
  probability: number | null, impact: number | null, override = 0, floor: number | null = null,
): RiskClass | null {
  const effective = impact && floor ? Math.max(impact, floor) : impact;
  const base = riskClass(probability, effective);
  if (!base) return null;
  const order: RiskClass[] = ["very_low", "low", "medium", "high", "critical"];
  const floorCls = floor ? riskClass(probability, floor) : null;
  const min = floorCls ? order.indexOf(floorCls) : 0;
  const idx = Math.max(min, Math.min(4, order.indexOf(base) + override));
  return order[idx];
}

export function Section({ title, children, right }: { title: string; children: React.ReactNode; right?: React.ReactNode }) {
  return (
    <section className="border-t border-gray-100 pt-4 mt-4 first:border-t-0 first:pt-0 first:mt-0">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-semibold text-gray-800">{title}</h3>
        {right}
      </div>
      {children}
    </section>
  );
}

/** Passo numerato della scheda del rischio: aperto mostra il contenuto, chiuso
 * un riassunto di una riga. `done` = null per un passo facoltativo. */
export function Step({ id, n, title, done, open, onToggle, summary, right, children }: {
  id: string; n: number; title: string; done: boolean | null; open: boolean; onToggle: () => void;
  summary?: React.ReactNode; right?: React.ReactNode; children: React.ReactNode;
}) {
  return (
    <section id={id} className="border border-gray-200 rounded-lg scroll-mt-4">
      <div className="flex items-center gap-3 px-4 py-3">
        <button type="button" onClick={onToggle} aria-expanded={open} className="flex-1 min-w-0 flex items-center gap-3 text-left">
          <StepDot n={n} done={done} />
          <span className="min-w-0">
            <span className="block text-sm font-semibold text-gray-900">{title}</span>
            {!open && summary && <span className="block text-xs text-gray-600 truncate">{summary}</span>}
          </span>
        </button>
        {open && right}
      </div>
      {open && <div className="px-4 pb-4">{children}</div>}
    </section>
  );
}

export function StepDot({ n, done }: { n: number; done: boolean | null }) {
  return done ? (
    <span className="w-6 h-6 shrink-0 rounded-full bg-green-700 text-white text-xs inline-flex items-center justify-center" aria-hidden="true">✓</span>
  ) : (
    <span className={`w-6 h-6 shrink-0 rounded-full border-2 text-xs inline-flex items-center justify-center ${done === false
      ? "border-primary-600 text-primary-700" : "border-gray-300 text-gray-500"}`} aria-hidden="true">{n}</span>
  );
}

export function Field({ label, children, hint }: { label: string; children: React.ReactNode; hint?: string }) {
  return (
    <label className="block mb-3">
      <span className="block text-xs font-medium text-gray-600 mb-1">{label}</span>
      {children}
      {hint && <span className="block text-[11px] text-gray-400 mt-1">{hint}</span>}
    </label>
  );
}

export const inputCls = "w-full border border-gray-300 rounded px-2.5 py-1.5 text-sm disabled:bg-gray-50 disabled:text-gray-600";

export function ErrorBox({ message }: { message: string | null }) {
  if (!message) return null;
  return <div className="text-sm text-red-700 bg-red-50 border border-red-200 rounded px-3 py-2 my-2">{message}</div>;
}
