import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import {
  IMPACT_DIMENSIONS, riskApi, type ImpactDimension, type ResolvedPolicy, type Risk, type RiskInput,
} from "../../api/endpoints/risk";
import { assetsApi } from "../../api/endpoints/assets";
import { suppliersApi } from "../../api/endpoints/suppliers";
import { biaApi } from "../../api/endpoints/bia";
import { usersApi } from "../../api/endpoints/users";
import { plantsApi } from "../../api/endpoints/plants";
import { MixedOwnerField } from "./MixedOwnerField";
import { ClassBadge, Field, LevelPicker, impactFloor, inputCls, overallImpact, previewClass } from "./RiskUi";

const NIS2_AREAS = ["art21_a", "art21_b", "art21_c", "art21_d", "art21_e", "art21_f", "art21_g", "art21_h", "art21_i", "art21_j"];
const TREATING = ["mitigare", "trasferire", "evitare"] as const;
const PLAN_MONTHS: Record<string, number> = { critical: 3, high: 12, medium: 24, low: 60, very_low: 60 };

export type EvaluationState = RiskInput;

export function initialEvaluation(r: Risk): EvaluationState {
  return {
    name: r.name, asset_type: r.asset_type, asset: r.asset, asset_group_label: r.asset_group_label,
    supplier: r.supplier, threat: r.threat, information_classes: r.information_classes,
    business_objectives: r.business_objectives,
    critical_process: r.critical_process, vulnerability: r.vulnerability, consequence: r.consequence,
    probability: r.probability, probability_method: r.probability_method, probability_rationale: r.probability_rationale,
    impact_economic: r.impact_economic, impact_legal: r.impact_legal, impact_customer: r.impact_customer,
    impact_reputational: r.impact_reputational, impact_people: r.impact_people, impact_operational: r.impact_operational,
    impact_rationale: r.impact_rationale,
    legal_or_contract_violation: r.legal_or_contract_violation, treatment: r.treatment,
    treatment_rationale: r.treatment_rationale, expected_probability: r.expected_probability,
    expected_impact: r.expected_impact, owner: r.owner, treatment_owner: r.treatment_owner,
    treatment_owner_external: r.treatment_owner_external, plan_due_date: r.plan_due_date,
    nis2_in_scope: r.nis2_in_scope, nis2_art21_category: r.nis2_art21_category, impacted_systems: r.impacted_systems,
    significant_incident_potential: r.significant_incident_potential,
    significant_incident_note: r.significant_incident_note, affected_plants: r.affected_plants,
  };
}

function euro(n: number, lang: string) {
  return new Intl.NumberFormat(lang, { style: "currency", currency: "EUR", maximumFractionDigits: 0 }).format(n);
}

/** Dati e anteprime condivisi dai passi della scheda (le query sono in cache). */
export function useEvaluationModel(risk: Risk, value: EvaluationState) {
  const { i18n } = useTranslation();
  const plantId = risk.plant;
  const { data: threats = [] } = useQuery({
    queryKey: ["risk-threats", value.asset_type, i18n.language],
    queryFn: () => riskApi.threats({ asset_type: value.asset_type ?? "" }),
    enabled: !!value.asset_type, retry: false,
  });
  const { data: infoClasses = [] } = useQuery({
    queryKey: ["risk-info-classes", plantId], queryFn: () => riskApi.informationClasses(plantId), retry: false,
  });
  const dims = useMemo(() => Object.fromEntries(
    IMPACT_DIMENSIONS.map(d => [d, value[`impact_${d}` as keyof EvaluationState] as number | null]),
  ) as Record<ImpactDimension, number | null>, [value]);
  // Soglia di riservatezza: come nel backend vale per l'impatto attuale e per quello atteso.
  const floor = useMemo(() => impactFloor(
    threats.find(th => th.id === value.threat)?.cia,
    infoClasses.filter(ic => (value.information_classes ?? []).includes(ic.id)).map(ic => ic.confidentiality),
  ), [threats, infoClasses, value.threat, value.information_classes]);
  const floorInfo = infoClasses
    .filter(ic => (value.information_classes ?? []).includes(ic.id) && floor && impactFloor(["C"], [ic.confidentiality]) === floor)
    .map(ic => ic.name);
  const dimsImpact = overallImpact(dims);
  const impact = floor ? Math.max(dimsImpact ?? 0, floor) : dimsImpact;
  const current = previewClass(value.probability ?? null, impact, 0, floor);
  const expected = previewClass(value.expected_probability ?? null, value.expected_impact ?? null, 0, floor);
  const expectedBelowFloor = !!floor && !!value.expected_impact && value.expected_impact < floor;
  return { threats, infoClasses, dims, floor, floorInfo, dimsImpact, impact, current, expected, expectedBelowFloor };
}

export type EvaluationModel = ReturnType<typeof useEvaluationModel>;

type StepProps = {
  risk: Risk;
  value: EvaluationState;
  onChange: (next: EvaluationState) => void;
  editable: boolean;
  model: EvaluationModel;
};

function useSetters(value: EvaluationState, onChange: (next: EvaluationState) => void, editable: boolean) {
  const set = <K extends keyof EvaluationState>(k: K, v: EvaluationState[K]) => onChange({ ...value, [k]: v });
  const textarea = (k: keyof EvaluationState, rows = 2, placeholder?: string) => (
    <textarea value={(value[k] as string) ?? ""} onChange={e => set(k, e.target.value as never)} rows={rows}
      disabled={!editable} className={inputCls} placeholder={placeholder} />
  );
  return { set, textarea };
}

// ── 1 · Scenario ─────────────────────────────────────────────────────────────

/** Cosa può succedere, a cosa, e chi ne risponde (procedura §6). */
export function ScenarioStep({ risk, value, onChange, editable, model }: StepProps) {
  const { t } = useTranslation();
  const { set, textarea } = useSetters(value, onChange, editable);
  const plantId = risk.plant;
  const isGroup = plantId === null;
  const { threats, infoClasses } = model;

  const { data: objectives = [] } = useQuery({
    queryKey: ["risk-business-objectives", plantId], queryFn: () => riskApi.businessObjectives(plantId), retry: false,
  });
  // Proposta: obiettivi misurati dalle dimensioni con l'impatto più alto.
  const suggestedObjectives = useMemo(() => {
    const levels = IMPACT_DIMENSIONS.map(d => [d, value[`impact_${d}` as keyof EvaluationState] as number | null] as const);
    const top = Math.max(0, ...levels.map(([, v]) => v ?? 0));
    if (!top) return [] as string[];
    const worst = new Set(levels.filter(([, v]) => v === top).map(([d]) => d));
    return objectives.filter(o => o.active && o.impact_dimensions.some(d => worst.has(d))).map(o => o.id);
  }, [objectives, value]);
  const { data: users = [] } = useQuery({ queryKey: ["users"], queryFn: () => usersApi.list(), retry: false });
  const { data: plants = [] } = useQuery({ queryKey: ["plants"], queryFn: () => plantsApi.list(), enabled: isGroup, retry: false });
  const { data: processes } = useQuery({
    queryKey: ["bia-processes", plantId], queryFn: () => biaApi.list(plantId ? { plant: plantId } : {}), retry: false,
  });
  const { data: suppliers } = useQuery({
    queryKey: ["suppliers"], queryFn: () => suppliersApi.list(),
    enabled: value.asset_type === "FORNITORI", retry: false,
  });
  const { data: assets = [] } = useQuery({
    queryKey: ["risk-assets", plantId, value.asset_type],
    queryFn: async () => {
      const params: Record<string, string> = plantId ? { plant: plantId } : {};
      if (value.asset_type === "IT") {
        const [it, sw] = await Promise.all([assetsApi.listIT(params), assetsApi.listSW(params)]);
        return [...it.results, ...sw.results].map(a => ({ id: a.id, name: a.name }));
      }
      if (value.asset_type === "OT") return (await assetsApi.listOT(params)).results.map(a => ({ id: a.id, name: a.name }));
      if (value.asset_type === "SEDE") return (await assetsApi.listFacility(params)).results.map(a => ({ id: a.id, name: a.name }));
      return [];
    },
    enabled: ["IT", "OT", "SEDE"].includes(value.asset_type ?? ""), retry: false,
  });

  // Il processo BIA propone le classi di informazioni che usa (se non ne sono state scelte).
  const onProcessChange = (process: string | null) => {
    const proposed = process && !(value.information_classes ?? []).length
      ? infoClasses.filter(ic => (ic.critical_processes ?? []).includes(process)).map(ic => ic.id)
      : value.information_classes;
    onChange({ ...value, critical_process: process, information_classes: proposed });
  };

  return (
    <div>
      <div className="grid grid-cols-2 gap-x-4">
        <Field label={t("risk.drawer.threat")}>
          <select value={value.threat ?? ""} onChange={e => set("threat", e.target.value)} disabled={!editable} className={inputCls}>
            {threats.map(th => <option key={th.id} value={th.id}>{th.code} — {th.title}</option>)}
            {!threats.some(th => th.id === value.threat) && risk.threat && (
              <option value={risk.threat}>{risk.threat_code} — {risk.threat_title}</option>
            )}
          </select>
        </Field>
        <Field label={t("risk.drawer.name")}>
          <input value={value.name ?? ""} onChange={e => set("name", e.target.value)} disabled={!editable} className={inputCls}
            placeholder={risk.threat_title ?? ""} />
        </Field>
        {["IT", "OT", "SEDE"].includes(value.asset_type ?? "") && (
          <Field label={t("risk.drawer.asset")}>
            <select value={value.asset ?? ""} onChange={e => set("asset", e.target.value || null)} disabled={!editable} className={inputCls}>
              <option value="">{t("risk.drawer.asset_group")}</option>
              {assets.map(a => <option key={a.id} value={a.id}>{a.name}</option>)}
            </select>
          </Field>
        )}
        {value.asset_type === "FORNITORI" && (
          <Field label={t("risk.drawer.supplier")}>
            <select value={value.supplier ?? ""} onChange={e => set("supplier", e.target.value || null)} disabled={!editable} className={inputCls}>
              <option value="">{t("risk.drawer.asset_group")}</option>
              {(suppliers?.results ?? []).filter(s => !plantId || !(s.plants ?? []).length || (s.plants ?? []).includes(plantId))
                .map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
          </Field>
        )}
        {!value.asset && !value.supplier && (
          <Field label={t("risk.drawer.asset_group_label")}>
            <input value={value.asset_group_label ?? ""} onChange={e => set("asset_group_label", e.target.value)}
              disabled={!editable} className={inputCls} placeholder={t("risk.drawer.asset_group_placeholder")} />
          </Field>
        )}
        <Field label={t("risk.drawer.process")}>
          <select value={value.critical_process ?? ""} onChange={e => onProcessChange(e.target.value || null)}
            disabled={!editable} className={inputCls}>
            <option value="">—</option>
            {(processes?.results ?? []).map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
        </Field>
      </div>
      <Field label={t("risk.drawer.information_classes")} hint={t("risk.drawer.information_classes_hint")}>
        <div className="flex flex-wrap gap-x-3 gap-y-1">
          {infoClasses.length === 0 && <span className="text-xs text-gray-400">{t("risk.drawer.no_information_classes")}</span>}
          {infoClasses.map(ic => (
            <label key={ic.id} className="flex items-center gap-1 text-xs">
              <input type="checkbox" disabled={!editable} checked={(value.information_classes ?? []).includes(ic.id)}
                onChange={e => set("information_classes", e.target.checked
                  ? [...(value.information_classes ?? []), ic.id]
                  : (value.information_classes ?? []).filter(x => x !== ic.id))} />
              {ic.name} <span className="text-gray-400">({t(`risk.confidentiality_levels.${ic.confidentiality}`)})</span>
            </label>
          ))}
        </div>
      </Field>
      <Field label={t("risk.drawer.business_objectives")} hint={t("risk.drawer.business_objectives_hint")}>
        <div className="flex flex-wrap gap-x-3 gap-y-1">
          {objectives.length === 0 && <span className="text-xs text-gray-400">{t("risk.drawer.no_business_objectives")}</span>}
          {objectives.filter(o => o.active || (value.business_objectives ?? []).includes(o.id)).map(o => (
            <label key={o.id} className="flex items-center gap-1 text-xs" title={o.description}>
              <input type="checkbox" disabled={!editable} checked={(value.business_objectives ?? []).includes(o.id)}
                onChange={e => set("business_objectives", e.target.checked
                  ? [...(value.business_objectives ?? []), o.id]
                  : (value.business_objectives ?? []).filter(x => x !== o.id))} />
              {o.name}
              {suggestedObjectives.includes(o.id) && (
                <span className="text-[10px] px-1 rounded bg-blue-50 text-blue-700">{t("risk.drawer.suggested")}</span>
              )}
            </label>
          ))}
        </div>
        {editable && !(value.business_objectives ?? []).length && suggestedObjectives.length > 0 && (
          <button type="button" onClick={() => set("business_objectives", suggestedObjectives)}
            className="mt-1 text-xs text-primary-600 hover:underline">{t("risk.drawer.use_suggested")}</button>
        )}
      </Field>
      {isGroup && (
        <Field label={t("risk.drawer.affected_plants")}>
          <div className="flex flex-wrap gap-2">
            {plants.map(p => (
              <label key={p.id} className="flex items-center gap-1 text-xs">
                <input type="checkbox" disabled={!editable} checked={(value.affected_plants ?? []).includes(p.id)}
                  onChange={e => set("affected_plants", e.target.checked
                    ? [...(value.affected_plants ?? []), p.id]
                    : (value.affected_plants ?? []).filter(x => x !== p.id))} />
                {p.code}
              </label>
            ))}
          </div>
        </Field>
      )}
      <div className="grid grid-cols-2 gap-x-4">
        <Field label={t("risk.drawer.vulnerability")}>{textarea("vulnerability")}</Field>
        <Field label={t("risk.drawer.consequence")} hint={t("risk.drawer.consequence_hint")}>{textarea("consequence")}</Field>
      </div>
      <Field label={t("risk.drawer.owner")} hint={t("risk.drawer.owner_hint")}>
        <select value={value.owner ?? ""} onChange={e => set("owner", e.target.value ? Number(e.target.value) : null)}
          disabled={!editable} className={`${inputCls} max-w-md`}>
          <option value="">—</option>
          {users.map(u => <option key={u.id} value={u.id}>{`${u.first_name} ${u.last_name}`.trim() || u.username}</option>)}
        </select>
      </Field>
      <div className="border-t border-gray-100 pt-3">
        <p className="text-xs font-medium text-gray-600 mb-2">{t("risk.drawer.nis2")}</p>
        <div className="grid grid-cols-2 gap-x-4">
          <label className="flex items-center gap-2 text-xs mb-3">
            <input type="checkbox" checked={!!value.nis2_in_scope} disabled={!editable} onChange={e => set("nis2_in_scope", e.target.checked)} />
            {t("risk.drawer.nis2_in_scope")}
          </label>
          <label className="flex items-center gap-2 text-xs mb-3">
            <input type="checkbox" checked={!!value.significant_incident_potential} disabled={!editable}
              onChange={e => set("significant_incident_potential", e.target.checked)} />
            {t("risk.drawer.significant_incident")}
          </label>
          {value.nis2_in_scope && (
            <>
              <Field label={t("risk.drawer.nis2_area")}>
                <select value={value.nis2_art21_category ?? ""} onChange={e => set("nis2_art21_category", e.target.value)}
                  disabled={!editable} className={inputCls}>
                  <option value="">—</option>
                  {NIS2_AREAS.map(a => <option key={a} value={a}>{t(`risk.nis2_art21.${a}`)}</option>)}
                </select>
              </Field>
              <Field label={t("risk.drawer.impacted_systems")}>
                <input value={value.impacted_systems ?? ""} onChange={e => set("impacted_systems", e.target.value)}
                  disabled={!editable} className={inputCls} />
              </Field>
            </>
          )}
        </div>
        {value.significant_incident_potential && (
          <Field label={t("risk.drawer.significant_incident_note")}>{textarea("significant_incident_note")}</Field>
        )}
      </div>
    </div>
  );
}

/** Riassunto di una riga del passo 1, quando è chiuso. */
export function scenarioSummary(risk: Risk, value: EvaluationState, model: EvaluationModel, t: (k: string) => string) {
  const threat = model.threats.find(th => th.id === value.threat);
  const info = model.infoClasses.filter(ic => (value.information_classes ?? []).includes(ic.id)).map(ic => ic.name);
  return [
    threat ? `${threat.code} — ${threat.title}` : risk.threat_code,
    risk.asset_name || risk.supplier_name || value.asset_group_label || null,
    info.length ? `${t("risk.drawer.information_classes")}: ${info.join(", ")}` : null,
    risk.owner_name ? `${t("risk.drawer.owner")}: ${risk.owner_name}` : null,
    value.nis2_in_scope ? "NIS2" : null,
  ].filter(Boolean).join(" · ");
}

// ── 3 · Rischio attuale ──────────────────────────────────────────────────────

/** Probabilità e impatto con le misure esistenti in funzione (procedura §7–§8). */
export function CurrentRiskStep({ value, onChange, editable, model, policy }: StepProps & { policy?: ResolvedPolicy }) {
  const { t, i18n } = useTranslation();
  const { set, textarea } = useSetters(value, onChange, editable);
  const [showCriteria, setShowCriteria] = useState(true);
  const { dims, floor, floorInfo, dimsImpact, impact, current } = model;

  const thresholds = policy?.economic_thresholds;
  const economicCriteria = (level: number) => {
    if (!thresholds) return "";
    const v = (k: "2" | "3" | "4" | "5") => euro(thresholds[k], i18n.language);
    if (level === 5) return t("risk.scales.economic.above", { from: v("5") });
    if (level === 1) return t("risk.scales.economic.below", { to: v("2") });
    const key = String(level) as "2" | "3" | "4";
    const next = String(level + 1) as "3" | "4" | "5";
    return t("risk.scales.economic.between", { from: v(key), to: v(next) });
  };
  const impactCriteria = (d: ImpactDimension) => (level: number) =>
    d === "economic" ? economicCriteria(level) : t(`risk.scales.impact.${d}.${level}`);
  // Criteri del solo metodo scelto (procedura: frequenza storica, oppure FER senza serie storiche).
  const probabilityCriteria = (level: number) => {
    if (value.probability_method === "frequenza") return t(`risk.scales.probability.${level}.frequency`);
    if (value.probability_method === "fer") return t(`risk.scales.probability.${level}.fer`);
    return `${t(`risk.scales.probability.${level}.frequency`)} — ${t(`risk.scales.probability.${level}.fer`)}`;
  };
  const raisedByFloor = !!floor && (dimsImpact ?? 0) < floor;

  return (
    <div>
      <div className="flex justify-end -mt-1 mb-2">
        <button type="button" onClick={() => setShowCriteria(s => !s)} className="text-xs text-primary-600 hover:underline">
          {t(showCriteria ? "risk.drawer.hide_criteria" : "risk.drawer.show_criteria")}
        </button>
      </div>
      <div className="grid grid-cols-2 gap-x-6">
        <div>
          <p className="text-sm font-semibold text-gray-800 mb-2">{t("risk.drawer.probability")}</p>
          <Field label={t("risk.drawer.probability_method")} hint={t("risk.drawer.method_hint")}>
            <div className="flex gap-2">
              {(["frequenza", "fer"] as const).map(m => (
                <button key={m} type="button" disabled={!editable} onClick={() => set("probability_method", m)}
                  className={`px-3 py-1.5 rounded-full border text-xs ${value.probability_method === m
                    ? "border-primary-600 bg-primary-50 text-primary-700 font-medium" : "border-gray-300 text-gray-700"} disabled:opacity-70`}>
                  {t(m === "fer" ? "risk.drawer.method_fer" : "risk.drawer.method_frequency")}
                </button>
              ))}
            </div>
          </Field>
          <Field label={t("risk.drawer.probability_level")}>
            {showCriteria ? (
              <LevelPicker value={value.probability ?? null} onChange={v => set("probability", v)} criteria={probabilityCriteria} disabled={!editable} />
            ) : (
              <input type="number" min={1} max={5} value={value.probability ?? ""} disabled={!editable} className={`${inputCls} w-20`}
                onChange={e => set("probability", e.target.value ? Number(e.target.value) : null)} />
            )}
          </Field>
          <Field label={t("risk.drawer.probability_rationale")} hint={t("risk.drawer.probability_rationale_hint")}>
            {textarea("probability_rationale", 3)}
          </Field>
        </div>
        <div>
          <p className="text-sm font-semibold text-gray-800 mb-2">{t("risk.drawer.impact_dimensions")}</p>
          <div className="space-y-2 mb-2">
            {IMPACT_DIMENSIONS.map(d => (
              <details key={d} className="border rounded" open={showCriteria && !!dims[d]}>
                <summary className="flex items-center justify-between px-3 py-1.5 cursor-pointer text-sm">
                  <span>{t(`risk.dimensions.${d}`)}</span>
                  <span className="text-xs text-gray-500">{dims[d] ?? t("risk.drawer.not_relevant")}</span>
                </summary>
                <div className="px-2 pb-2">
                  <LevelPicker value={dims[d]} onChange={v => set(`impact_${d}` as keyof EvaluationState, v as never)}
                    criteria={impactCriteria(d)} disabled={!editable} allowEmpty emptyLabel={t("risk.drawer.not_relevant")} />
                </div>
              </details>
            ))}
          </div>
          <p className="text-[11px] text-gray-500 mb-2">{t("risk.drawer.impact_worst_case")}</p>
          <Field label={t("risk.drawer.impact_rationale")}>{textarea("impact_rationale", 3)}</Field>
        </div>
      </div>
      <div className="flex flex-wrap items-center gap-3 text-sm bg-gray-50 rounded px-3 py-2">
        <span className="font-medium">{t("risk.drawer.result")}</span>
        <span className="text-gray-700">P {value.probability ?? "—"} × I {impact ?? "—"} =</span>
        <ClassBadge cls={current} />
        {raisedByFloor && (
          <span className="text-xs text-gray-600">
            {t("risk.drawer.result_floor", { floor, from: dimsImpact ?? "—", info: floorInfo.join(", ") })}
          </span>
        )}
      </div>
    </div>
  );
}

// ── 4 · Decisione ────────────────────────────────────────────────────────────

/** "Il rischio attuale è accettabile?": sì = accettare il residuo, no = trattare (§9–§10). */
export function DecisionStep({ risk, value, onChange, editable, model, plan, acceptance }: StepProps & {
  plan: React.ReactNode; acceptance: React.ReactNode;
}) {
  const { t } = useTranslation();
  const { set, textarea } = useSetters(value, onChange, editable);
  const { current, expected, floor, expectedBelowFloor } = model;
  const { data: users = [] } = useQuery({ queryKey: ["users"], queryFn: () => usersApi.list(), retry: false });
  const rule = current ? ({ critical: "mandatory", high: "evaluate" } as Record<string, string>)[current] ?? "acceptable" : null;
  const accepting = value.treatment === "accettare";
  const treating = TREATING.includes(value.treatment as typeof TREATING[number]);
  const notAcceptable = !!value.legal_or_contract_violation;
  const suggestion = notAcceptable || current === "critical" ? "no" : rule === "acceptable" ? "yes" : null;
  const choose = (yes: boolean) => {
    if (yes) set("treatment", "accettare");
    else if (!treating) set("treatment", "mitigare");
  };
  const choiceCls = (on: boolean) => `text-left rounded-lg px-3 py-2.5 border ${on
    ? "border-primary-600 bg-primary-50 ring-1 ring-primary-200" : "border-gray-300 bg-white hover:bg-gray-50"} disabled:opacity-60`;

  return (
    <div>
      {rule && current && (
        <p className="text-sm text-gray-700 mb-3">
          {t(`risk.drawer.rule_${rule}`, { months: PLAN_MONTHS[current] })}
        </p>
      )}
      {!current && <p className="text-sm text-amber-700 mb-3">{t("risk.drawer.decision_needs_evaluation")}</p>}
      <label className="flex items-start gap-2 text-xs mb-3">
        <input type="checkbox" checked={notAcceptable} disabled={!editable}
          onChange={e => onChange({ ...value, legal_or_contract_violation: e.target.checked,
            treatment: e.target.checked && accepting ? "" : value.treatment })} className="mt-0.5" />
        <span>{t("risk.drawer.not_acceptable")}</span>
      </label>
      <fieldset>
        <legend className="text-sm font-semibold text-gray-800 mb-2">{t("risk.drawer.decision_question")}</legend>
        <div className="grid grid-cols-2 gap-3 mb-3">
          <button type="button" disabled={!editable || notAcceptable} onClick={() => choose(true)} className={choiceCls(accepting)}
            aria-pressed={accepting}>
            <span className="block text-sm font-medium">
              {t("risk.drawer.decision_accept")}
              {suggestion === "yes" && <span className="ml-2 text-[10px] px-1 rounded bg-blue-50 text-blue-700">{t("risk.drawer.suggested")}</span>}
            </span>
            <span className="block text-xs text-gray-600 mt-0.5">
              {t(notAcceptable ? "risk.drawer.decision_not_acceptable" : current === "critical"
                ? "risk.drawer.decision_accept_critical" : "risk.drawer.decision_accept_hint")}
            </span>
          </button>
          <button type="button" disabled={!editable} onClick={() => choose(false)} className={choiceCls(treating)} aria-pressed={treating}>
            <span className="block text-sm font-medium">
              {t("risk.drawer.decision_treat")}
              {suggestion === "no" && <span className="ml-2 text-[10px] px-1 rounded bg-blue-50 text-blue-700">{t("risk.drawer.suggested")}</span>}
            </span>
            <span className="block text-xs text-gray-600 mt-0.5">{t("risk.drawer.decision_treat_hint")}</span>
          </button>
        </div>
      </fieldset>

      {accepting && (
        <div className="border-t border-gray-100 pt-3">
          <Field label={t("risk.drawer.acceptance_reason")}
            hint={t(rule === "acceptable" ? "risk.drawer.acceptance_reason_hint" : "risk.drawer.acceptance_reason_hint_high")}>
            {textarea("treatment_rationale", 3)}
          </Field>
          {acceptance}
        </div>
      )}

      {treating && (
        <div className="border-t border-gray-100 pt-3">
          <Field label={t("risk.drawer.treatment_option")}>
            <div className="flex gap-2">
              {TREATING.map(x => (
                <button key={x} type="button" disabled={!editable} onClick={() => set("treatment", x)} aria-pressed={value.treatment === x}
                  className={`px-3 py-1.5 rounded-full border text-sm ${value.treatment === x
                    ? "border-primary-600 bg-primary-50 text-primary-700 font-medium" : "border-gray-300 text-gray-700"} disabled:opacity-70`}>
                  {t(`risk.treatment_${x}`)}
                </button>
              ))}
            </div>
          </Field>
          <Field label={t("risk.drawer.treatment_rationale")} hint={t("risk.drawer.treatment_rationale_hint")}>
            {textarea("treatment_rationale", 3)}
          </Field>
          <div className="grid grid-cols-2 gap-x-4">
            <Field label={t("risk.drawer.treatment_owner")}>
              {editable ? (
                <MixedOwnerField users={users} userId={value.treatment_owner ?? null} external={value.treatment_owner_external ?? ""}
                  noneLabel="—" small
                  onChange={(uid, ext) => onChange({ ...value, treatment_owner: uid ? Number(uid) : null, treatment_owner_external: ext })} />
              ) : (
                <input value={risk.treatment_owner_name ?? ""} disabled className={inputCls} />
              )}
            </Field>
            <Field label={t("risk.drawer.plan_due_date")}>
              <input type="date" value={value.plan_due_date ?? ""} onChange={e => set("plan_due_date", e.target.value || null)}
                disabled={!editable} className={inputCls} />
            </Field>
          </div>
          {plan}
          <div className="mt-3 flex flex-wrap items-center gap-3 text-sm bg-gray-50 rounded px-3 py-2">
            <span className="font-medium">{t("risk.drawer.expected_risk")}</span>
            <label className="flex items-center gap-1 text-xs">P
              <select value={value.expected_probability ?? ""} disabled={!editable} className={`${inputCls} w-16`}
                aria-label={t("risk.drawer.expected_probability")}
                onChange={e => set("expected_probability", e.target.value ? Number(e.target.value) : null)}>
                <option value="">—</option>
                {[1, 2, 3, 4, 5].map(n => <option key={n} value={n}>{n}</option>)}
              </select>
            </label>
            <label className="flex items-center gap-1 text-xs">I
              <select value={value.expected_impact ?? ""} disabled={!editable} className={`${inputCls} w-16`}
                aria-label={t("risk.drawer.expected_impact")}
                onChange={e => set("expected_impact", e.target.value ? Number(e.target.value) : null)}>
                <option value="">—</option>
                {[1, 2, 3, 4, 5].map(n => <option key={n} value={n} disabled={!!floor && n < floor}>{n}</option>)}
              </select>
            </label>
            <span>=</span>
            <ClassBadge cls={expected} />
            {floor && (
              <span className={`text-xs ${expectedBelowFloor ? "text-red-700" : "text-gray-600"}`}>
                {t(expectedBelowFloor ? "risk.drawer.expected_below_floor" : "risk.drawer.expected_floor_note", {
                  floor, value: value.expected_impact,
                })}
              </span>
            )}
          </div>
          <details className="mt-3">
            <summary className="cursor-pointer text-xs text-gray-600">{t("risk.drawer.temporary_acceptance")}</summary>
            <div className="mt-2">{acceptance}</div>
          </details>
        </div>
      )}
    </div>
  );
}

/** Stato dei passi, specchio di `risk_completeness_errors` nel backend. */
export function stepStatus(value: EvaluationState, model: EvaluationModel) {
  const has = (s?: string | null) => !!s && !!s.trim();
  const scenario = !!value.threat && !!(value.business_objectives ?? []).length && !!value.owner;
  const current = !!value.probability && has(value.probability_rationale) && !!model.dimsImpact && has(value.impact_rationale);
  const treating = TREATING.includes(value.treatment as typeof TREATING[number]);
  const highRule = model.current === "high" || model.current === "critical";
  const decision = value.treatment === "accettare"
    ? !value.legal_or_contract_violation && (!highRule || has(value.treatment_rationale))
    : treating && !!model.expected && !model.expectedBelowFloor;
  return { scenario, current, decision };
}
