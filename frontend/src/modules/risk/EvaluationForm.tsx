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
import { ClassBadge, Field, LevelPicker, Section, inputCls, overallImpact, previewClass } from "./RiskUi";

const NIS2_AREAS = ["art21_a", "art21_b", "art21_c", "art21_d", "art21_e", "art21_f", "art21_g", "art21_h", "art21_i", "art21_j"];

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
    impact_rationale: r.impact_rationale, class_override: r.class_override, override_rationale: r.override_rationale,
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

/** Identificazione, valutazione e trattamento (procedura §6–§9). */
export function EvaluationForm({ risk, value, onChange, editable, policy }: {
  risk: Risk;
  value: EvaluationState;
  onChange: (next: EvaluationState) => void;
  editable: boolean;
  policy?: ResolvedPolicy;
}) {
  const { t, i18n } = useTranslation();
  const set = <K extends keyof EvaluationState>(k: K, v: EvaluationState[K]) => onChange({ ...value, [k]: v });
  const plantId = risk.plant;
  const isGroup = plantId === null;
  const [showCriteria, setShowCriteria] = useState(true);

  const { data: threats = [] } = useQuery({
    queryKey: ["risk-threats", value.asset_type, i18n.language],
    queryFn: () => riskApi.threats({ asset_type: value.asset_type ?? "" }),
    enabled: !!value.asset_type, retry: false,
  });
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
  const { data: infoClasses = [] } = useQuery({
    queryKey: ["risk-info-classes", plantId], queryFn: () => riskApi.informationClasses(plantId), retry: false,
  });
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

  const dims = useMemo(() => Object.fromEntries(
    IMPACT_DIMENSIONS.map(d => [d, value[`impact_${d}` as keyof EvaluationState] as number | null]),
  ) as Record<ImpactDimension, number | null>, [value]);
  const impact = overallImpact(dims);
  const current = previewClass(value.probability ?? null, impact, value.class_override ?? 0);
  const expected = previewClass(value.expected_probability ?? null, value.expected_impact ?? null);
  const rule = current ? { critical: "mandatory", high: "evaluate" }[current as "critical" | "high"] ?? "acceptable" : null;

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

  // Il processo BIA propone le classi di informazioni che usa (se non ne sono state scelte).
  const onProcessChange = (process: string | null) => {
    const proposed = process && !(value.information_classes ?? []).length
      ? infoClasses.filter(ic => (ic.critical_processes ?? []).includes(process)).map(ic => ic.id)
      : value.information_classes;
    onChange({ ...value, critical_process: process, information_classes: proposed });
  };

  const textarea = (k: keyof EvaluationState, rows = 2, placeholder?: string) => (
    <textarea value={(value[k] as string) ?? ""} onChange={e => set(k, e.target.value as never)} rows={rows}
      disabled={!editable} className={inputCls} placeholder={placeholder} />
  );

  return (
    <div>
      <Section title={t("risk.drawer.identification")}>
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
        <div className="grid grid-cols-2 gap-x-3">
          <Field label={t("risk.drawer.name")}>
            <input value={value.name ?? ""} onChange={e => set("name", e.target.value)} disabled={!editable} className={inputCls}
              placeholder={risk.threat_title ?? ""} />
          </Field>
          <Field label={t("risk.drawer.threat")}>
            <select value={value.threat ?? ""} onChange={e => set("threat", e.target.value)} disabled={!editable} className={inputCls}>
              {threats.map(th => <option key={th.id} value={th.id}>{th.code} — {th.title}</option>)}
              {!threats.some(th => th.id === value.threat) && risk.threat && (
                <option value={risk.threat}>{risk.threat_code} — {risk.threat_title}</option>
              )}
            </select>
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
          <div className="flex flex-wrap gap-2">
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
        <Field label={t("risk.drawer.vulnerability")}>{textarea("vulnerability")}</Field>
        <Field label={t("risk.drawer.consequence")} hint={t("risk.drawer.consequence_hint")}>{textarea("consequence")}</Field>
      </Section>

      <Section
        title={t("risk.drawer.evaluation")}
        right={
          <button type="button" onClick={() => setShowCriteria(s => !s)} className="text-xs text-primary-600 hover:underline">
            {t(showCriteria ? "risk.drawer.hide_criteria" : "risk.drawer.show_criteria")}
          </button>
        }
      >
        <div className="flex items-center gap-3 mb-3 text-sm bg-gray-50 rounded px-3 py-2">
          <span>{t("risk.drawer.current_risk")}:</span>
          <span className="text-gray-600">P {value.probability ?? "—"} × I {impact ?? "—"}</span>
          <ClassBadge cls={current} />
          {risk.current_class && current !== risk.current_class && (
            <span className="text-[11px] text-gray-400">{t("risk.drawer.saved_class")}: {t(`risk.classes.${risk.current_class}`)}</span>
          )}
        </div>
        <Field label={t("risk.drawer.probability")}>
          {showCriteria ? (
            <LevelPicker value={value.probability ?? null} onChange={v => set("probability", v)} criteria={probabilityCriteria} disabled={!editable} />
          ) : (
            <input type="number" min={1} max={5} value={value.probability ?? ""} disabled={!editable} className={`${inputCls} w-20`}
              onChange={e => set("probability", e.target.value ? Number(e.target.value) : null)} />
          )}
        </Field>
        <div className="grid grid-cols-2 gap-x-3">
          <Field label={t("risk.drawer.probability_method")}>
            <select value={value.probability_method ?? ""} onChange={e => set("probability_method", e.target.value as never)}
              disabled={!editable} className={inputCls}>
              <option value="">—</option>
              <option value="frequenza">{t("risk.drawer.method_frequency")}</option>
              <option value="fer">{t("risk.drawer.method_fer")}</option>
            </select>
            <p className="text-[11px] text-gray-500 mt-1">{t("risk.drawer.method_hint")}</p>
          </Field>
        </div>
        <Field label={t("risk.drawer.probability_rationale")}>{textarea("probability_rationale")}</Field>

        <p className="text-xs font-medium text-gray-600 mb-1">{t("risk.drawer.impact_dimensions")}</p>
        <div className="space-y-2 mb-3">
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
        <p className="text-[11px] text-gray-400 mb-2">{t("risk.drawer.impact_worst_case")}</p>
        <Field label={t("risk.drawer.impact_rationale")}>{textarea("impact_rationale")}</Field>
        <div className="grid grid-cols-2 gap-x-3">
          <Field label={t("risk.drawer.override")} hint={t("risk.drawer.override_hint")}>
            <select value={value.class_override ?? 0} onChange={e => set("class_override", Number(e.target.value))}
              disabled={!editable} className={inputCls}>
              <option value={-1}>{t("risk.drawer.override_down")}</option>
              <option value={0}>{t("risk.drawer.override_none")}</option>
              <option value={1}>{t("risk.drawer.override_up")}</option>
            </select>
          </Field>
          <label className="flex items-start gap-2 text-xs mt-5">
            <input type="checkbox" checked={!!value.legal_or_contract_violation} disabled={!editable}
              onChange={e => set("legal_or_contract_violation", e.target.checked)} className="mt-0.5" />
            <span>{t("risk.drawer.not_acceptable")}</span>
          </label>
        </div>
        {(value.class_override ?? 0) !== 0 && <Field label={t("risk.drawer.override_rationale")}>{textarea("override_rationale")}</Field>}
      </Section>

      <Section title={t("risk.drawer.treatment")}>
        {rule && (
          <p className="text-xs mb-2 px-2 py-1 rounded bg-gray-50 text-gray-700">
            {t(`risk.drawer.rule_${rule}`, { months: { critical: 3, high: 12, medium: 24, low: 60, very_low: 60 }[current!] })}
          </p>
        )}
        <div className="grid grid-cols-2 gap-x-3">
          <Field label={t("risk.drawer.treatment_option")}>
            <select value={value.treatment ?? ""} onChange={e => set("treatment", e.target.value as never)} disabled={!editable} className={inputCls}>
              <option value="">—</option>
              {["mitigare", "evitare", "trasferire", "accettare"].map(x => <option key={x} value={x}>{t(`risk.treatment_${x}`)}</option>)}
            </select>
          </Field>
          <Field label={t("risk.drawer.plan_due_date")}>
            <input type="date" value={value.plan_due_date ?? ""} onChange={e => set("plan_due_date", e.target.value || null)}
              disabled={!editable} className={inputCls} />
          </Field>
        </div>
        <Field label={t("risk.drawer.treatment_rationale")}>{textarea("treatment_rationale")}</Field>
        {value.treatment && value.treatment !== "accettare" && (
          <div className="grid grid-cols-3 gap-x-3 items-end">
            <Field label={t("risk.drawer.expected_probability")}>
              <select value={value.expected_probability ?? ""} disabled={!editable} className={inputCls}
                onChange={e => set("expected_probability", e.target.value ? Number(e.target.value) : null)}>
                <option value="">—</option>
                {[1, 2, 3, 4, 5].map(n => <option key={n} value={n}>{n}</option>)}
              </select>
            </Field>
            <Field label={t("risk.drawer.expected_impact")}>
              <select value={value.expected_impact ?? ""} disabled={!editable} className={inputCls}
                onChange={e => set("expected_impact", e.target.value ? Number(e.target.value) : null)}>
                <option value="">—</option>
                {[1, 2, 3, 4, 5].map(n => <option key={n} value={n}>{n}</option>)}
              </select>
            </Field>
            <div className="mb-3"><span className="text-xs text-gray-500 mr-1">{t("risk.drawer.expected_risk")}:</span><ClassBadge cls={expected} /></div>
          </div>
        )}
        <div className="grid grid-cols-2 gap-x-3">
          <Field label={t("risk.drawer.owner")} hint={t("risk.drawer.owner_hint")}>
            <select value={value.owner ?? ""} onChange={e => set("owner", e.target.value ? Number(e.target.value) : null)}
              disabled={!editable} className={inputCls}>
              <option value="">—</option>
              {users.map(u => <option key={u.id} value={u.id}>{`${u.first_name} ${u.last_name}`.trim() || u.username}</option>)}
            </select>
          </Field>
          <Field label={t("risk.drawer.treatment_owner")}>
            {editable ? (
              <MixedOwnerField users={users} userId={value.treatment_owner ?? null} external={value.treatment_owner_external ?? ""}
                noneLabel="—" small
                onChange={(uid, ext) => onChange({ ...value, treatment_owner: uid ? Number(uid) : null, treatment_owner_external: ext })} />
            ) : (
              <input value={risk.treatment_owner_name ?? ""} disabled className={inputCls} />
            )}
          </Field>
        </div>
      </Section>

      <Section title={t("risk.drawer.nis2")}>
        <div className="grid grid-cols-2 gap-x-3">
          <label className="flex items-center gap-2 text-xs mb-3">
            <input type="checkbox" checked={!!value.nis2_in_scope} disabled={!editable} onChange={e => set("nis2_in_scope", e.target.checked)} />
            {t("risk.drawer.nis2_in_scope")}
          </label>
          <label className="flex items-center gap-2 text-xs mb-3">
            <input type="checkbox" checked={!!value.significant_incident_potential} disabled={!editable}
              onChange={e => set("significant_incident_potential", e.target.checked)} />
            {t("risk.drawer.significant_incident")}
          </label>
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
        </div>
        {value.significant_incident_potential && (
          <Field label={t("risk.drawer.significant_incident_note")}>{textarea("significant_incident_note")}</Field>
        )}
      </Section>
    </div>
  );
}
