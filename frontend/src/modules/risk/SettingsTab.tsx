import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import {
  ASSET_TYPES, apiError, riskApi, type AssetType, type InformationClass, type ProtectionLevel,
  type ResolvedPolicy, type ThreatEntry,
} from "../../api/endpoints/risk";
import { RISK_CLASSES, type RiskClass } from "./riskClasses";
import { ErrorBox, Field, inputCls } from "./RiskUi";
import type { RegisterId } from "./RiskPage";

const SECTIONS = ["governance", "catalog", "information"] as const;
type SectionKey = typeof SECTIONS[number];
const ROLE_TOKENS = ["risk_owner", "plant_manager", "site_risk_manager", "it_manager", "hr_manager",
  "purchasing_manager", "production_manager", "engineering_manager", "ciso"];
const LEVELS: ProtectionLevel[] = ["low", "normal", "high", "very_high"];

export function SettingsTab({ registerId, policy, plants }: {
  registerId: RegisterId; policy: ResolvedPolicy; plants: { id: string; code: string; name: string }[];
}) {
  const { t } = useTranslation();
  const [section, setSection] = useState<SectionKey>("governance");
  return (
    <div>
      <div className="inline-flex rounded-lg border border-gray-200 bg-white p-1 gap-1 mb-4">
        {SECTIONS.map(s => (
          <button key={s} onClick={() => setSection(s)}
            className={`px-3 py-1.5 text-sm rounded-md font-medium ${section === s ? "bg-primary-600 text-white" : "text-gray-600 hover:bg-gray-50"}`}>
            {t(`risk.settings.sections.${s}`)}
          </button>
        ))}
      </div>
      {section === "governance" && <GovernanceSettings registerId={registerId} policy={policy} plants={plants} />}
      {section === "catalog" && <CatalogSettings canEdit={policy.user_org_scope} />}
      {section === "information" && <InformationSettings registerId={registerId} canEditGroup={policy.user_org_scope} />}
    </div>
  );
}

// ── Governo del rischio ──────────────────────────────────────────────────────

function GovernanceSettings({ registerId, policy, plants }: {
  registerId: RegisterId; policy: ResolvedPolicy; plants: { id: string; name: string }[];
}) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const canEdit = policy.user_org_scope;
  const [orgDraft, setOrgDraft] = useState<ResolvedPolicy | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const { data: orgPolicy } = useQuery({ queryKey: ["risk-policy", null], queryFn: () => riskApi.resolvedPolicy(null), retry: false });
  const { data: presets } = useQuery({ queryKey: ["risk-presets"], queryFn: () => riskApi.presets(), retry: false });
  useEffect(() => { if (orgPolicy) setOrgDraft(orgPolicy); }, [orgPolicy]);

  const save = useMutation({
    mutationFn: (args: { plant: string | null; payload: Partial<ResolvedPolicy> }) => riskApi.savePolicy(args.plant, args.payload),
    onSuccess: () => { setError(null); setSaved(true); qc.invalidateQueries({ queryKey: ["risk-policy"] }); },
    onError: e => setError(apiError(e, t("risk.errors.generic"))),
  });
  if (!orgDraft) return <p className="text-sm text-gray-400">{t("common.loading")}</p>;
  const d = orgDraft;
  const setD = (patch: Partial<ResolvedPolicy>) => { setSaved(false); setOrgDraft({ ...d, ...patch }); };
  const setRule = (cls: RiskClass, patch: Partial<ResolvedPolicy["acceptance_matrix"][RiskClass]>) =>
    setD({ acceptance_matrix: { ...d.acceptance_matrix, [cls]: { ...d.acceptance_matrix[cls], ...patch } } });
  const sitePlant = registerId ? plants.find(p => p.id === registerId) : null;

  return (
    <div className="space-y-4">
      <div className="bg-white rounded-lg border border-gray-200 p-5">
        <div className="flex items-start justify-between gap-3 mb-3">
          <div>
            <h3 className="text-sm font-semibold text-gray-800">{t("risk.settings.org_policy")}</h3>
            <p className="text-xs text-gray-500">{t(d.configured ? "risk.settings.configured" : "risk.settings.defaults")}</p>
          </div>
          {!canEdit && <span className="text-xs text-gray-500">{t("risk.settings.read_only")}</span>}
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <Field label={t("risk.settings.preset")} hint={t(`risk.settings.preset_hint.${d.preset}`)}>
            <select value={d.preset} disabled={!canEdit} className={inputCls}
              onChange={e => {
                const preset = e.target.value as ResolvedPolicy["preset"];
                setD({ ...(presets?.[preset] ?? {}), preset });
              }}>
              {(["centralizzato", "federato", "sito_singolo"] as const).map(p => <option key={p} value={p}>{t(`risk.settings.presets.${p}`)}</option>)}
            </select>
          </Field>
          <Field label={t("risk.settings.escalation_days")}>
            <input type="number" min={1} value={d.overdue_escalation_days} disabled={!canEdit} className={inputCls}
              onChange={e => setD({ overdue_escalation_days: Number(e.target.value) })} />
          </Field>
          <Field label={t("risk.settings.review_months")}>
            <input type="number" min={1} value={d.review_frequency_months} disabled={!canEdit} className={inputCls}
              onChange={e => setD({ review_frequency_months: Number(e.target.value) })} />
          </Field>
        </div>
        <label className="flex items-center gap-2 text-sm mb-4">
          <input type="checkbox" checked={d.group_register_enabled} disabled={!canEdit}
            onChange={e => setD({ group_register_enabled: e.target.checked })} />
          {t("risk.settings.group_register")}
        </label>

        <h4 className="text-xs font-semibold text-gray-600 mb-2">{t("risk.settings.acceptance_matrix")}</h4>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead className="bg-gray-50 text-gray-600">
              <tr>
                <th className="text-left px-2 py-1.5">{t("risk.settings.col_class")}</th>
                <th className="text-left px-2 py-1.5">{t("risk.settings.col_roles")}</th>
                <th className="text-left px-2 py-1.5">{t("risk.settings.col_scope")}</th>
                <th className="text-left px-2 py-1.5">{t("risk.settings.col_body")}</th>
                <th className="text-left px-2 py-1.5">{t("risk.settings.col_opinion")}</th>
                <th className="text-left px-2 py-1.5">{t("risk.settings.col_months")}</th>
                <th className="text-left px-2 py-1.5" title={t("risk.settings.col_treatment_months_hint")}>{t("risk.settings.col_treatment_months")}</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {[...RISK_CLASSES].reverse().map(cls => {
                const rule = d.acceptance_matrix[cls];
                return (
                  <tr key={cls}>
                    <td className="px-2 py-1.5 font-medium">{t(`risk.classes.${cls}`)}</td>
                    <td className="px-2 py-1.5">
                      <div className="flex flex-wrap gap-x-2 gap-y-0.5">
                        {ROLE_TOKENS.map(r => (
                          <label key={r} className="flex items-center gap-1">
                            <input type="checkbox" disabled={!canEdit} checked={rule.roles.includes(r)}
                              onChange={e => setRule(cls, { roles: e.target.checked ? [...rule.roles, r] : rule.roles.filter(x => x !== r) })} />
                            {t(`risk.acceptance_roles.${r}`, { defaultValue: t(`governance.roles.${r}`) })}
                          </label>
                        ))}
                      </div>
                    </td>
                    <td className="px-2 py-1.5">
                      <select value={rule.scope} disabled={!canEdit} className="border rounded px-1 py-0.5"
                        onChange={e => setRule(cls, { scope: e.target.value as "plant" | "org" })}>
                        <option value="plant">{t("risk.settings.scope_plant")}</option>
                        <option value="org">{t("risk.settings.scope_org")}</option>
                      </select>
                    </td>
                    <td className="px-2 py-1.5">
                      <input type="checkbox" disabled={!canEdit} checked={rule.requires_body}
                        onChange={e => setRule(cls, { requires_body: e.target.checked })} />
                    </td>
                    <td className="px-2 py-1.5">
                      <select value={d.upper_opinion[cls]} disabled={!canEdit} className="border rounded px-1 py-0.5"
                        onChange={e => setD({ upper_opinion: { ...d.upper_opinion, [cls]: e.target.value as "none" | "notify" | "binding" } })}>
                        {(["none", "notify", "binding"] as const).map(m => <option key={m} value={m}>{t(`risk.settings.opinion.${m}`)}</option>)}
                      </select>
                    </td>
                    <td className="px-2 py-1.5">
                      <input type="number" min={1} value={d.acceptance_max_months[cls]} disabled={!canEdit} className="border rounded px-1 py-0.5 w-16"
                        onChange={e => setD({ acceptance_max_months: { ...d.acceptance_max_months, [cls]: Number(e.target.value) } })} />
                    </td>
                    <td className="px-2 py-1.5 text-gray-600">
                      {policy.treatment_months?.[cls] ? t("risk.settings.months_value", { count: policy.treatment_months[cls] }) : "—"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        <h4 className="text-xs font-semibold text-gray-600 mt-4 mb-2">{t("risk.settings.economic_thresholds")}</h4>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {(["2", "3", "4", "5"] as const).map(level => (
            <Field key={level} label={t("risk.settings.threshold_level", { level })}>
              <input type="number" min={1} value={d.economic_thresholds[level]} disabled={!canEdit} className={inputCls}
                onChange={e => setD({ economic_thresholds: { ...d.economic_thresholds, [level]: Number(e.target.value) } })} />
            </Field>
          ))}
        </div>
        {canEdit && (
          <div className="flex items-center gap-3 mt-2">
            <button
              onClick={() => save.mutate({ plant: null, payload: {
                preset: d.preset, group_register_enabled: d.group_register_enabled,
                acceptance_matrix: d.acceptance_matrix, upper_opinion: d.upper_opinion,
                acceptance_max_months: d.acceptance_max_months, economic_thresholds: d.economic_thresholds,
                overdue_escalation_days: d.overdue_escalation_days, review_frequency_months: d.review_frequency_months,
              } })}
              className="px-3 py-1.5 bg-primary-600 text-white rounded text-sm">{t("risk.settings.save")}</button>
            {saved && <span className="text-xs text-green-700">{t("risk.settings.saved")}</span>}
          </div>
        )}
        <ErrorBox message={error} />
      </div>

      {sitePlant && (
        <SiteThresholds plantId={sitePlant.id} plantName={sitePlant.name} policy={policy} canEdit={canEdit}
          onSave={payload => save.mutate({ plant: sitePlant.id, payload })} />
      )}
    </div>
  );
}

function SiteThresholds({ plantId, plantName, policy, canEdit, onSave }: {
  plantId: string; plantName: string; policy: ResolvedPolicy; canEdit: boolean;
  onSave: (payload: Partial<ResolvedPolicy>) => void;
}) {
  const { t } = useTranslation();
  const [values, setValues] = useState(policy.economic_thresholds);
  useEffect(() => setValues(policy.economic_thresholds), [policy, plantId]);
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-5">
      <h3 className="text-sm font-semibold text-gray-800">{t("risk.settings.site_exception", { site: plantName })}</h3>
      <p className="text-xs text-gray-500 mb-3">
        {t(policy.plant_policy_id ? "risk.settings.site_exception_active" : "risk.settings.site_exception_none")}
      </p>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {(["2", "3", "4", "5"] as const).map(level => (
          <Field key={level} label={t("risk.settings.threshold_level", { level })}>
            <input type="number" min={1} value={values[level]} disabled={!canEdit} className={inputCls}
              onChange={e => setValues({ ...values, [level]: Number(e.target.value) })} />
          </Field>
        ))}
      </div>
      {canEdit && (
        <button onClick={() => onSave({ economic_thresholds: values })} className="px-3 py-1.5 border rounded text-sm">
          {t("risk.settings.save_site")}
        </button>
      )}
    </div>
  );
}

// ── Catalogo minacce ─────────────────────────────────────────────────────────

// Lingue dei titoli delle minacce personalizzate (inglese per primo: obbligatorio).
const THREAT_LANGS = ["en", "it", "fr", "pl", "tr"] as const;
type ThreatLang = typeof THREAT_LANGS[number];
const emptyThreat = {
  code: "", asset_types: [] as AssetType[], cia: [] as string[],
  titles: { en: "", it: "", fr: "", pl: "", tr: "" } as Record<ThreatLang, string>,
};

function CatalogSettings({ canEdit }: { canEdit: boolean }) {
  const { t, i18n } = useTranslation();
  const qc = useQueryClient();
  const [type, setType] = useState<AssetType | "">("");
  const [q, setQ] = useState("");
  const [form, setForm] = useState(emptyThreat);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const { data: threats = [] } = useQuery({
    queryKey: ["risk-threats-admin", type, i18n.language],
    queryFn: () => riskApi.threats({ active: "all", ...(type ? { asset_type: type } : {}) }),
    retry: false,
  });
  const refresh = () => {
    qc.invalidateQueries({ queryKey: ["risk-threats-admin"] });
    qc.invalidateQueries({ queryKey: ["risk-threats"] });
  };
  const reset = () => { setForm(emptyThreat); setEditingId(null); setError(null); };
  const save = useMutation({
    mutationFn: () => {
      // Un titolo per lingua; l'inglese è obbligatorio (lingua di ripiego).
      const translations = Object.fromEntries(
        THREAT_LANGS.filter(l => form.titles[l].trim()).map(l => [l, { title: form.titles[l].trim() }]),
      );
      const payload = { asset_types: form.asset_types, cia: form.cia as ThreatEntry["cia"], translations };
      return editingId ? riskApi.updateThreat(editingId, payload) : riskApi.createThreat({ ...payload, code: form.code });
    },
    onSuccess: () => { reset(); refresh(); },
    onError: e => setError(apiError(e, t("risk.errors.generic"))),
  });
  const startEdit = (th: ThreatEntry) => {
    setEditingId(th.id);
    setForm({
      code: th.code, asset_types: th.asset_types, cia: th.cia,
      titles: Object.fromEntries(THREAT_LANGS.map(l => [l, th.translations[l]?.title ?? ""])) as Record<ThreatLang, string>,
    });
  };
  const toggleActive = useMutation({
    mutationFn: async (th: ThreatEntry) => {
      if (th.active) await riskApi.deactivateThreat(th.id);
      else await riskApi.updateThreat(th.id, { active: true });
    },
    onSuccess: refresh,
    onError: e => setError(apiError(e, t("risk.errors.generic"))),
  });
  const rows = threats.filter(th => !q || `${th.code} ${th.title}`.toLowerCase().includes(q.toLowerCase()));

  return (
    <div className="space-y-4">
      <div className="flex gap-2 text-sm">
        <input value={q} onChange={e => setQ(e.target.value)} placeholder={t("risk.settings.search")} className="border rounded px-2 py-1.5 w-56" />
        <select value={type} onChange={e => setType(e.target.value as AssetType | "")} className="border rounded px-2 py-1.5">
          <option value="">{t("risk.register.all_asset_types")}</option>
          {ASSET_TYPES.map(a => <option key={a} value={a}>{t(`risk.asset_types.${a}`)}</option>)}
        </select>
        <span className="ml-auto text-xs text-gray-400 self-center">{t("risk.settings.catalog_count", { count: rows.length })}</span>
      </div>
      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b text-xs text-gray-600">
            <tr>
              <th className="text-left px-3 py-2 font-medium">{t("risk.settings.col_code")}</th>
              <th className="text-left px-3 py-2 font-medium">{t("risk.settings.col_title")}</th>
              <th className="text-left px-3 py-2 font-medium">{t("risk.settings.col_types")}</th>
              <th className="text-left px-3 py-2 font-medium">CIA</th>
              <th className="text-left px-3 py-2 font-medium">{t("risk.settings.col_source")}</th>
              <th className="px-3 py-2" />
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {rows.map(th => (
              <tr key={th.id} className={th.active ? "" : "opacity-50"}>
                <td className="px-3 py-1.5 font-mono text-xs">{th.code}</td>
                <td className="px-3 py-1.5">{th.title}</td>
                <td className="px-3 py-1.5 text-xs text-gray-600">{th.asset_types.map(a => t(`risk.asset_types.${a}`)).join(", ")}</td>
                <td className="px-3 py-1.5 text-xs">{th.cia.join("")}</td>
                <td className="px-3 py-1.5 text-xs text-gray-500">{t(`risk.settings.source.${th.source}`)}</td>
                <td className="px-3 py-1.5 text-right whitespace-nowrap">
                  {canEdit && th.source === "custom" && (
                    <button onClick={() => startEdit(th)} className="text-xs text-primary-600 hover:underline mr-3">{t("common.edit")}</button>
                  )}
                  {canEdit && th.source === "custom" && (
                    <button onClick={() => toggleActive.mutate(th)} className="text-xs text-primary-600 hover:underline">
                      {t(th.active ? "risk.settings.deactivate" : "risk.settings.reactivate")}
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {canEdit && (
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <h4 className="text-sm font-semibold text-gray-700 mb-2">{t(editingId ? "risk.settings.edit_threat" : "risk.settings.new_threat")}</h4>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <Field label={t("risk.settings.col_code")} hint={t("risk.settings.code_hint")}>
              <input value={form.code} disabled={!!editingId} onChange={e => setForm({ ...form, code: e.target.value.toUpperCase() })} className={inputCls} />
            </Field>
          </div>
          <p className="text-xs text-gray-500 mb-1">{t("risk.settings.titles_hint")}</p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-x-3">
            {THREAT_LANGS.map(l => (
              <Field key={l} label={`${t("risk.settings.col_title")} · ${l.toUpperCase()}${l === "en" ? " *" : ""}`}>
                <input value={form.titles[l]} onChange={e => setForm({ ...form, titles: { ...form.titles, [l]: e.target.value } })} className={inputCls} />
              </Field>
            ))}
          </div>
          <div className="flex flex-wrap gap-3 text-xs mb-3">
            {ASSET_TYPES.map(a => (
              <label key={a} className="flex items-center gap-1">
                <input type="checkbox" checked={form.asset_types.includes(a)}
                  onChange={e => setForm({ ...form, asset_types: e.target.checked ? [...form.asset_types, a] : form.asset_types.filter(x => x !== a) })} />
                {t(`risk.asset_types.${a}`)}
              </label>
            ))}
            <span className="text-gray-300">|</span>
            {["C", "I", "A"].map(c => (
              <label key={c} className="flex items-center gap-1">
                <input type="checkbox" checked={form.cia.includes(c)}
                  onChange={e => setForm({ ...form, cia: e.target.checked ? [...form.cia, c] : form.cia.filter(x => x !== c) })} />
                {c}
              </label>
            ))}
          </div>
          <div className="flex gap-2">
            <button onClick={() => save.mutate()} disabled={!form.code || !form.titles.en.trim() || !form.asset_types.length || save.isPending}
              className="px-3 py-1.5 bg-primary-600 text-white rounded text-sm disabled:opacity-50">
              {t(editingId ? "common.save" : "risk.settings.add_threat")}
            </button>
            {editingId && <button onClick={reset} className="px-3 py-1.5 border rounded text-sm">{t("common.cancel")}</button>}
          </div>
          <ErrorBox message={error} />
        </div>
      )}
    </div>
  );
}

// ── Classi di informazioni ───────────────────────────────────────────────────

const emptyClass = { name: "", description: "", confidentiality: "normal" as ProtectionLevel,
  integrity: "normal" as ProtectionLevel, availability: "normal" as ProtectionLevel };

function InformationSettings({ registerId, canEditGroup }: { registerId: RegisterId; canEditGroup: boolean }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [form, setForm] = useState(emptyClass);
  const [editing, setEditing] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const { data: classes = [] } = useQuery({
    queryKey: ["risk-info-classes", registerId], queryFn: () => riskApi.informationClasses(registerId), retry: false,
  });
  const refresh = () => qc.invalidateQueries({ queryKey: ["risk-info-classes"] });
  const onErr = (e: unknown) => setError(apiError(e, t("risk.errors.generic")));
  const save = useMutation({
    mutationFn: () => editing
      ? riskApi.updateInformationClass(editing, form)
      : riskApi.createInformationClass({ ...form, plant: registerId }),
    onSuccess: () => { setForm(emptyClass); setEditing(null); setError(null); refresh(); },
    onError: onErr,
  });
  const remove = useMutation({ mutationFn: (id: string) => riskApi.deleteInformationClass(id), onSuccess: refresh, onError: onErr });
  const canEdit = (ic: InformationClass) => ic.plant !== null || canEditGroup;
  // Riservatezza con le etichette della classificazione (Pubblico … Segreto), I/A con i livelli.
  const levelLabel = (k: "confidentiality" | "integrity" | "availability", l: string) =>
    t(k === "confidentiality" ? `risk.confidentiality_levels.${l}` : `risk.protection.${l}`);
  const levelSelect = (k: "confidentiality" | "integrity" | "availability") => (
    <Field label={t(`risk.settings.${k}`)}>
      <select value={form[k]} onChange={e => setForm({ ...form, [k]: e.target.value as ProtectionLevel })} className={inputCls}>
        {LEVELS.map(l => <option key={l} value={l}>{levelLabel(k, l)}</option>)}
      </select>
    </Field>
  );

  return (
    <div className="space-y-4">
      <p className="text-xs text-gray-500">{t("risk.settings.information_hint")}</p>
      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        {classes.length === 0 ? <p className="p-6 text-center text-sm text-gray-400">{t("risk.settings.no_classes")}</p> : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b text-xs text-gray-600">
              <tr>
                <th className="text-left px-3 py-2 font-medium">{t("risk.settings.class_name")}</th>
                <th className="text-left px-3 py-2 font-medium">{t("risk.settings.confidentiality")}</th>
                <th className="text-left px-3 py-2 font-medium">{t("risk.settings.integrity")}</th>
                <th className="text-left px-3 py-2 font-medium">{t("risk.settings.availability")}</th>
                <th className="text-left px-3 py-2 font-medium">{t("risk.settings.class_scope")}</th>
                <th className="px-3 py-2" />
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {classes.map(ic => (
                <tr key={ic.id}>
                  <td className="px-3 py-1.5"><span title={ic.description}>{ic.name}</span></td>
                  <td className="px-3 py-1.5 text-xs">{levelLabel("confidentiality", ic.confidentiality)}</td>
                  <td className="px-3 py-1.5 text-xs">{t(`risk.protection.${ic.integrity}`)}</td>
                  <td className="px-3 py-1.5 text-xs">{t(`risk.protection.${ic.availability}`)}</td>
                  <td className="px-3 py-1.5 text-xs text-gray-500">{ic.plant_name ?? t("risk.page.group_register")}</td>
                  <td className="px-3 py-1.5 text-right whitespace-nowrap">
                    {canEdit(ic) && (
                      <>
                        <button onClick={() => { setEditing(ic.id); setForm({ name: ic.name, description: ic.description,
                          confidentiality: ic.confidentiality, integrity: ic.integrity, availability: ic.availability }); }}
                          className="text-xs text-primary-600 hover:underline mr-3">{t("common.edit")}</button>
                        <button onClick={() => { if (window.confirm(t("risk.settings.delete_class_confirm"))) remove.mutate(ic.id); }}
                          className="text-xs text-red-600 hover:underline">{t("common.delete")}</button>
                      </>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
      {(registerId !== null || canEditGroup) && (
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <h4 className="text-sm font-semibold text-gray-700 mb-2">
            {t(editing ? "risk.settings.edit_class" : "risk.settings.new_class")}
          </h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-x-3">
            <Field label={t("risk.settings.class_name")}>
              <input value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} className={inputCls} />
            </Field>
            <Field label={t("risk.settings.class_description")}>
              <input value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} className={inputCls} />
            </Field>
          </div>
          <div className="grid grid-cols-3 gap-3">
            {levelSelect("confidentiality")}{levelSelect("integrity")}{levelSelect("availability")}
          </div>
          <div className="flex gap-2">
            <button onClick={() => save.mutate()} disabled={!form.name.trim()}
              className="px-3 py-1.5 bg-primary-600 text-white rounded text-sm disabled:opacity-50">{t("common.save")}</button>
            {editing && <button onClick={() => { setEditing(null); setForm(emptyClass); }} className="px-3 py-1.5 border rounded text-sm">{t("common.cancel")}</button>}
          </div>
          <ErrorBox message={error} />
        </div>
      )}
    </div>
  );
}
