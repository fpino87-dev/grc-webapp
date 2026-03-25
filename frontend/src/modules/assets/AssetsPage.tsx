import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { assetsApi, type AssetIT, type AssetOT, type RegisterChangeResult } from "../../api/endpoints/assets";
import { plantsApi } from "../../api/endpoints/plants";
import { biaApi, type CriticalProcess } from "../../api/endpoints/bia";
import { StatusBadge } from "../../components/ui/StatusBadge";
import { ModuleHelp } from "../../components/ui/ModuleHelp";
import { useTranslation } from "react-i18next";
import i18n from "../../i18n";

function CriticalityBadge({ value }: { value: number }) {
  const { t } = useTranslation();
  const colors: Record<number, string> = {
    1: "bg-green-100 text-green-800",
    2: "bg-green-100 text-green-700",
    3: "bg-yellow-100 text-yellow-800",
    4: "bg-orange-100 text-orange-800",
    5: "bg-red-100 text-red-800",
  };
  const labelKey = value >= 1 && value <= 5 ? `assets.criticality_${value}_label` : null;
  const descKey = value >= 1 && value <= 5 ? `assets.criticality_${value}_desc` : null;
  const lvl = {
    label: labelKey ? t(labelKey) : String(value),
    color: colors[value] ?? "bg-gray-100 text-gray-600",
    desc: descKey ? t(descKey) : "",
  };
  return (
    <div className="relative group inline-flex">
      <span
        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded
                        text-xs font-medium cursor-help ${lvl.color}`}
      >
        {value} — {lvl.label}
      </span>
      {lvl.desc && (
        <div
          className="absolute bottom-full left-0 mb-1 w-60 bg-gray-900
                        text-white text-xs rounded p-2 shadow-lg
                        hidden group-hover:block z-50 pointer-events-none"
        >
          {lvl.desc}
        </div>
      )}
    </div>
  );
}

function ChangeBadges({ asset }: { asset: AssetIT | AssetOT }) {
  const { t } = useTranslation();
  return (
    <>
      {asset.has_recent_change && (
        <span className="text-xs px-2 py-0.5 rounded-full bg-amber-100 text-amber-700 border border-amber-300 ml-2">
          {t("assets.change_days_ago", { days: asset.change_age_days })}
        </span>
      )}
      {asset.needs_revaluation && (
        <span className="text-xs px-2 py-0.5 rounded-full bg-red-100 text-red-700 border border-red-300 ml-2">
          {t("assets.reassessment_required")}
        </span>
      )}
    </>
  );
}

function RegisterChangeForm({
  asset,
  assetType,
  onClose,
}: {
  asset: AssetIT | AssetOT;
  assetType: "IT" | "OT";
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [changeRef, setChangeRef] = useState("");
  const [changeDesc, setChangeDesc] = useState("");
  const [portalUrl, setPortalUrl] = useState("");
  const [result, setResult] = useState<RegisterChangeResult | null>(null);

  const registerMutation = useMutation({
    mutationFn: () =>
      assetsApi.registerChange(asset.id, assetType, {
        change_ref: changeRef,
        change_desc: changeDesc,
        portal_url: portalUrl,
      }),
    onSuccess: (res) => {
      setResult(res);
      qc.invalidateQueries({ queryKey: [assetType === "IT" ? "assets-it" : "assets-ot"] });
    },
  });

  const clearMutation = useMutation({
    mutationFn: () => assetsApi.clearRevaluation(asset.id, assetType),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [assetType === "IT" ? "assets-it" : "assets-ot"] });
      onClose();
    },
  });

  return (
    <div className="border border-amber-200 bg-amber-50 rounded-lg p-4 mt-4">
      {/* Existing change info */}
      {asset.last_change_ref && (
        <div className="mb-4">
          <div className="flex items-center justify-between mb-2">
            <span className="font-medium text-amber-800 text-sm">{t("assets.last_change_registered")}</span>
            {asset.change_portal_url && (
              <a href={asset.change_portal_url} target="_blank" rel="noreferrer" className="text-blue-600 text-sm hover:underline">
                {t("assets.open_ticket")}
              </a>
            )}
          </div>
          <p className="text-sm"><strong>{t("assets.ref_label")}</strong> {asset.last_change_ref}</p>
          <p className="text-sm"><strong>{t("assets.date_label")}</strong> {asset.last_change_date ? new Date(asset.last_change_date).toLocaleDateString(i18n.language || "it") : "—"}</p>
          <p className="text-sm"><strong>{t("assets.description_label")}</strong> {asset.last_change_desc || "—"}</p>
          {asset.needs_revaluation && (
            <div className="mt-2 flex items-center gap-2">
              <span className="text-sm text-red-600">
                {t("assets.reassessment_since", { date: asset.needs_revaluation_since ? new Date(asset.needs_revaluation_since).toLocaleDateString(i18n.language || "it") : "—" })}
              </span>
              <button
                onClick={() => clearMutation.mutate()}
                disabled={clearMutation.isPending}
                className="px-3 py-1 bg-green-600 text-white text-xs rounded hover:bg-green-700 disabled:opacity-50"
              >
                {t("assets.mark_reassessed")}
              </button>
            </div>
          )}
        </div>
      )}

      {/* Register change form */}
      {result ? (
        <div className="bg-white rounded border border-green-200 p-3">
          <p className="text-sm font-medium text-green-700 mb-1">{t("assets.change_registered_title")}</p>
          <p className="text-xs text-gray-600">{t("assets.ref_label")} {result.ref}</p>
          <p className="text-xs text-gray-600">
            Impattati: {result.affected.controls} controlli, {result.affected.risks} risk assessment,{" "}
            {result.affected.processes} processi
          </p>
          <button onClick={onClose} className="mt-2 text-xs text-blue-600 hover:underline">{t("common.close")}</button>
        </div>
      ) : (
        <>
          <p className="text-xs font-semibold text-amber-800 uppercase tracking-wide mb-2">{t("assets.register_change_title")}</p>
          <div className="space-y-2">
            <input
              value={changeRef}
              onChange={(e) => setChangeRef(e.target.value)}
              placeholder="Riferimento ticket (es. JIRA-1234) *"
              className="w-full border rounded px-3 py-1.5 text-sm"
            />
            <input
              value={changeDesc}
              onChange={(e) => setChangeDesc(e.target.value)}
              placeholder="Descrizione breve del change"
              className="w-full border rounded px-3 py-1.5 text-sm"
            />
            <input
              value={portalUrl}
              onChange={(e) => setPortalUrl(e.target.value)}
              placeholder="URL ticket (opzionale)"
              className="w-full border rounded px-3 py-1.5 text-sm"
            />
          </div>
          {registerMutation.isError && (
            <p className="text-xs text-red-600 mt-1">{t("assets.register_error")}</p>
          )}
          <div className="flex gap-2 mt-3">
            <button
              onClick={() => registerMutation.mutate()}
              disabled={!changeRef || registerMutation.isPending}
              className="px-3 py-1.5 bg-amber-600 text-white text-sm rounded hover:bg-amber-700 disabled:opacity-50"
            >
              {registerMutation.isPending ? t("assets.registering") : t("assets.register_change_btn")}
            </button>
            <button onClick={onClose} className="px-3 py-1.5 border rounded text-sm text-gray-600 hover:bg-gray-50">
              {t("actions.cancel")}
            </button>
          </div>
        </>
      )}
    </div>
  );
}

function NewAssetModal({ assetType, plants, onClose }: { assetType: "IT" | "OT"; plants: { id: string; code: string; name: string }[]; onClose: () => void }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [form, setForm] = useState<Record<string, unknown>>({ asset_type: assetType, criticality: 3 });
  const [error, setError] = useState("");

  const { data: processesData } = useQuery({
    queryKey: ["critical-processes"],
    queryFn: () => biaApi.list({ status: "approvato" }),
    retry: false,
  });
  const processes: CriticalProcess[] = processesData?.results ?? [];

  const mutation = useMutation({
    mutationFn: assetType === "IT" ? assetsApi.createIT : assetsApi.createOT,
    onSuccess: () => { qc.invalidateQueries({ queryKey: [assetType === "IT" ? "assets-it" : "assets-ot"] }); onClose(); },
    onError: (e: any) => setError(e?.response?.data?.detail || t("common.save_error")),
  });

  function handleChange(e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) {
    const v =
      e.target.type === "checkbox"
        ? (e.target as HTMLInputElement).checked
        : e.target.type === "number"
        ? Number(e.target.value)
        : e.target.value;
    setForm((prev) => ({ ...prev, [e.target.name]: v }));
  }

  function handleProcessesChange(e: React.ChangeEvent<HTMLSelectElement>) {
    const selected = Array.from(e.target.selectedOptions).map((o) => o.value);
    setForm((prev) => ({ ...prev, processes: selected }));
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-6">
        <h3 className="text-lg font-semibold mb-4">{t("assets.new_asset_title", { type: assetType })}</h3>
        <div className="space-y-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("tasks.fields.plant")} *</label>
            <select name="plant" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm">
              <option value="">{t("common.select")}</option>
              {plants.map(p => <option key={p.id} value={p.id}>{p.code} — {p.name}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("plants.fields.name")} *</label>
            <input name="name" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("assets.bia_processes_label")}</label>
            <select
              multiple
              name="processes"
              onChange={handleProcessesChange}
              className="w-full border rounded px-3 py-2 text-sm h-28"
            >
              {processes.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
            <p className="mt-1 text-xs text-gray-500">
              {t("assets.bia_processes_hint")}
            </p>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("eval_assistant.bia.columns.level")} (1-5)</label>
            <select name="criticality" defaultValue="3" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm">
              {[1,2,3,4,5].map(n => <option key={n} value={n}>{n}</option>)}
            </select>
            <details className="mt-2 text-xs">
              <summary className="text-blue-600 cursor-pointer hover:underline">
                {t("assets.criticality_guide_title")}
              </summary>
              <table className="mt-2 w-full border-collapse text-xs">
                <thead>
                  <tr className="bg-gray-50 text-left">
                    <th className="border px-2 py-1">{t("assets.criticality_table_value")}</th>
                    <th className="border px-2 py-1">{t("assets.criticality_table_label")}</th>
                    <th className="border px-2 py-1">{t("assets.criticality_table_downtime")}</th>
                    <th className="border px-2 py-1">{t("assets.criticality_table_bcp")}</th>
                  </tr>
                </thead>
                <tbody>
                  {([
                    [1, t("assets.criticality_1_label"), t("assets.downtime_7d_plus"), t("assets.bcp_not_required")],
                    [2, t("assets.criticality_2_label"), t("assets.downtime_3_7d"), t("assets.bcp_not_required")],
                    [3, t("assets.criticality_3_label"), t("assets.downtime_24_72h"), t("assets.bcp_recommended")],
                    [4, t("assets.criticality_4_label"), t("assets.downtime_4_24h"), t("assets.bcp_mandatory")],
                    [5, t("assets.criticality_5_label"), t("assets.downtime_sub_4h"), t("assets.bcp_mandatory")],
                  ] as [number, string, string, string][]).map(([v,l,d,b]) => (
                    <tr key={v}>
                      <td className="border px-2 py-1 text-center font-bold">{v}</td>
                      <td className="border px-2 py-1">{l}</td>
                      <td className="border px-2 py-1">{d}</td>
                      <td className="border px-2 py-1 text-center">{b}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </details>
          </div>
          {assetType === "IT" ? (
            <>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">{t("assets.deployment_label")}</label>
                <select
                  name="deployment_type"
                  defaultValue="on_prem"
                  onChange={handleChange}
                  className="w-full border rounded px-3 py-2 text-sm"
                >
                  <option value="on_prem">{t("assets.deploy_on_prem")}</option>
                  <option value="iaas">{t("assets.deploy_iaas")}</option>
                  <option value="paas">{t("assets.deploy_paas")}</option>
                  <option value="saas">{t("assets.deploy_saas")}</option>
                </select>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">{t("assets.provider_label")}</label>
                  <input
                    name="provider"
                    onChange={handleChange}
                    className="w-full border rounded px-3 py-2 text-sm"
                    placeholder={t("assets.provider_placeholder")}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">{t("assets.service_name_label")}</label>
                  <input
                    name="service_name"
                    onChange={handleChange}
                    className="w-full border rounded px-3 py-2 text-sm"
                    placeholder={t("assets.service_placeholder")}
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">{t("assets.fqdn_label")}</label>
                <input name="fqdn" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" placeholder={t("assets.fqdn_placeholder")} />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">{t("assets.os_label")}</label>
                <input name="os" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" placeholder={t("assets.os_placeholder")} />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">{t("assets.eol_label")}</label>
                  <input
                    type="date"
                    name="eol_date"
                    onChange={handleChange}
                    className="w-full border rounded px-3 py-2 text-sm"
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">{t("assets.data_classification_label")}</label>
                  <select
                    name="data_classification"
                    defaultValue=""
                    onChange={handleChange}
                    className="w-full border rounded px-3 py-2 text-sm"
                  >
                    <option value="">— {t("common.select")} —</option>
                    <option value="public">{t("assets.data_class_public")}</option>
                    <option value="internal">{t("assets.data_class_internal")}</option>
                    <option value="confidential">{t("assets.data_class_confidential")}</option>
                    <option value="restricted">{t("assets.data_class_restricted")}</option>
                  </select>
                </div>
                <div className="flex items-center gap-2 mt-6">
                  <input type="checkbox" id="internet_exposed" name="internet_exposed" onChange={handleChange} className="rounded" />
                  <label htmlFor="internet_exposed" className="text-sm text-gray-700">{t("assets.internet_exposed_label")}</label>
                </div>
              </div>
            </>
          ) : (
            <>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">{t("assets.ot_category_label")}</label>
                <select name="category" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm">
                  <option value="">— {t("common.select")} —</option>
                  {["PLC","SCADA","HMI","RTU","sensore","altro"].map(c => <option key={c} value={c}>{c}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">{t("assets.purdue_level_label")}</label>
                <select name="purdue_level" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm">
                  <option value="">— {t("common.select")} —</option>
                  {[0,1,2,3,4].map(n => <option key={n} value={n}>L{n}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">{t("assets.vendor_label")}</label>
                <input name="vendor" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" />
              </div>
            </>
          )}
        </div>
        {error && <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded mt-3">{error}</p>}
        <div className="flex justify-end gap-2 mt-4">
          <button onClick={onClose} className="px-4 py-2 border rounded text-sm text-gray-600 hover:bg-gray-50">{t("actions.cancel")}</button>
          <button
            onClick={() => mutation.mutate(form as any)}
            disabled={mutation.isPending || !form.plant || !form.name}
            className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700 disabled:opacity-50"
          >
            {mutation.isPending ? t("common.saving") : t("actions.save")}
          </button>
        </div>
      </div>
    </div>
  );
}

function EditAssetModalIT({ asset, onClose }: { asset: AssetIT; onClose: () => void }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [form, setForm] = useState<Partial<AssetIT>>({
    name: asset.name,
    criticality: asset.criticality,
    deployment_type: asset.deployment_type,
    provider: asset.provider ?? "",
    service_name: asset.service_name ?? "",
    fqdn: asset.fqdn,
    os: asset.os,
    eol_date: asset.eol_date ?? "",
    data_classification: asset.data_classification ?? "",
    internet_exposed: asset.internet_exposed,
    processes: asset.processes ?? [],
  });
  const [error, setError] = useState("");

  const { data: processesData } = useQuery({
    queryKey: ["critical-processes"],
    queryFn: () => biaApi.list({ status: "approvato" }),
    retry: false,
  });
  const processes: CriticalProcess[] = processesData?.results ?? [];

  const mutation = useMutation({
    mutationFn: (payload: Partial<AssetIT>) => {
      const normalized: Partial<AssetIT> = {
        ...payload,
        // normalizza date vuote a null per evitare errori DRF
        eol_date: (payload.eol_date as string) || null,
      };
      return assetsApi.updateIT(asset.id, normalized);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["assets-it"] });
      onClose();
    },
    onError: (e: any) => setError(e?.response?.data?.detail || t("common.save_error")),
  });

  function handleChange(e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) {
    const v =
      e.target.type === "checkbox"
        ? (e.target as HTMLInputElement).checked
        : e.target.type === "number"
        ? Number(e.target.value)
        : e.target.value;
    setForm((prev) => ({ ...prev, [e.target.name]: v }));
  }

  function handleProcessesChange(e: React.ChangeEvent<HTMLSelectElement>) {
    const selected = Array.from(e.target.selectedOptions).map((o) => o.value);
    setForm((prev) => ({ ...prev, processes: selected }));
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-6">
        <h3 className="text-lg font-semibold mb-4">{t("actions.edit")} asset IT</h3>
        <div className="space-y-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("plants.fields.name")} *</label>
            <input
              name="name"
              value={form.name ?? ""}
              onChange={handleChange}
              className="w-full border rounded px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("assets.bia_processes_label")}</label>
            <select
              multiple
              name="processes"
              value={(form.processes as string[]) ?? []}
              onChange={handleProcessesChange}
              className="w-full border rounded px-3 py-2 text-sm h-28"
            >
              {processes.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Criticità (1-5)</label>
            <select
              name="criticality"
              value={form.criticality ?? 3}
              onChange={handleChange}
              className="w-full border rounded px-3 py-2 text-sm"
            >
              {[1, 2, 3, 4, 5].map((n) => (
                <option key={n} value={n}>
                  {n}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("assets.deployment_label")}</label>
            <select
              name="deployment_type"
              value={form.deployment_type ?? "on_prem"}
              onChange={handleChange}
              className="w-full border rounded px-3 py-2 text-sm"
            >
              <option value="on_prem">{t("assets.deploy_on_prem")}</option>
              <option value="iaas">{t("assets.deploy_iaas")}</option>
              <option value="paas">{t("assets.deploy_paas")}</option>
              <option value="saas">{t("assets.deploy_saas")}</option>
            </select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("assets.provider_label")}</label>
              <input
                name="provider"
                value={form.provider ?? ""}
                onChange={handleChange}
                className="w-full border rounded px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("assets.service_name_label")}</label>
              <input
                name="service_name"
                value={form.service_name ?? ""}
                onChange={handleChange}
                className="w-full border rounded px-3 py-2 text-sm"
              />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("assets.fqdn_label")}</label>
            <input
              name="fqdn"
              value={form.fqdn ?? ""}
              onChange={handleChange}
              className="w-full border rounded px-3 py-2 text-sm"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("assets.os_label")}</label>
              <input
                name="os"
                value={form.os ?? ""}
                onChange={handleChange}
                className="w-full border rounded px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("assets.eol_label")}</label>
              <input
                type="date"
                name="eol_date"
                value={form.eol_date ?? ""}
                onChange={handleChange}
                className="w-full border rounded px-3 py-2 text-sm"
              />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("assets.data_classification_label")}</label>
              <select
                name="data_classification"
                value={form.data_classification ?? ""}
                onChange={handleChange}
                className="w-full border rounded px-3 py-2 text-sm"
              >
                <option value="">— {t("common.select")} —</option>
                <option value="public">{t("assets.data_class_public")}</option>
                <option value="internal">{t("assets.data_class_internal")}</option>
                <option value="confidential">{t("assets.data_class_confidential")}</option>
                <option value="restricted">{t("assets.data_class_restricted")}</option>
              </select>
            </div>
            <div className="flex items-center gap-2 mt-6">
              <input
                type="checkbox"
                id="edit_internet_exposed"
                name="internet_exposed"
                checked={!!form.internet_exposed}
                onChange={handleChange}
                className="rounded"
              />
              <label htmlFor="edit_internet_exposed" className="text-sm text-gray-700">
                {t("assets.internet_exposed_label")}
              </label>
            </div>
          </div>
        </div>
        {error && <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded mt-3">{error}</p>}
        <div className="flex justify-end gap-2 mt-4">
          <button onClick={onClose} className="px-4 py-2 border rounded text-sm text-gray-600 hover:bg-gray-50">
            {t("actions.cancel")}
          </button>
          <button
            onClick={() => mutation.mutate(form)}
            disabled={mutation.isPending || !form.name}
            className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700 disabled:opacity-50"
          >
            {mutation.isPending ? t("common.saving") : t("actions.save")}
          </button>
        </div>
      </div>
    </div>
  );
}

function ITTab({ search }: { search: string }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [editAsset, setEditAsset] = useState<AssetIT | null>(null);

  const deleteMutation = useMutation({
    mutationFn: (id: string) => assetsApi.deleteIT(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["assets-it"] }),
    onError: (e: any) => window.alert(e?.response?.data?.detail || t("common.error")),
  });

  const { data, isLoading } = useQuery({
    queryKey: ["assets-it"],
    queryFn: () => assetsApi.listIT(),
    retry: false,
  });
  const { data: procData } = useQuery({
    queryKey: ["critical-processes"],
    queryFn: () => biaApi.list({ status: "approvato" }),
    retry: false,
  });
  const processes: CriticalProcess[] = procData?.results ?? [];

  const assets: AssetIT[] = (data?.results ?? []).filter((a) => {
    if (!search) return true;
    const s = search.toLowerCase();
    return (
      a.name.toLowerCase().includes(s) ||
      (a.fqdn || "").toLowerCase().includes(s) ||
      (a.service_name || "").toLowerCase().includes(s) ||
      (a.provider || "").toLowerCase().includes(s)
    );
  });

  if (isLoading) {
    return <div className="p-8 text-center text-gray-400">Caricamento...</div>;
  }

  return (
    <>
    <table className="w-full text-sm">
      <thead className="bg-gray-50 border-b border-gray-200">
        <tr>
          <th className="text-left px-4 py-3 font-medium text-gray-600">Nome</th>
          <th className="text-left px-4 py-3 font-medium text-gray-600">Deployment</th>
          <th className="text-left px-4 py-3 font-medium text-gray-600">FQDN</th>
          <th className="text-left px-4 py-3 font-medium text-gray-600">OS</th>
          <th className="text-left px-4 py-3 font-medium text-gray-600">Criticità</th>
          <th className="text-left px-4 py-3 font-medium text-gray-600">Esposto internet</th>
          <th className="text-left px-4 py-3 font-medium text-gray-600">Processi BIA</th>
          <th className="text-left px-4 py-3 font-medium text-gray-600">EOL</th>
          <th className="px-4 py-3"></th>
        </tr>
      </thead>
      <tbody className="divide-y divide-gray-100">
        {assets.length === 0 ? (
          <tr>
            <td colSpan={8} className="px-4 py-8 text-center text-gray-400">
              Nessun asset IT trovato
            </td>
          </tr>
        ) : (
          assets.map((a) => (
            <>
              <tr key={a.id} className="hover:bg-gray-50 transition-colors">
                <td className="px-4 py-3 font-medium text-gray-800">
                  {a.name}
                  <ChangeBadges asset={a} />
                </td>
                <td className="px-4 py-3 text-gray-600 text-xs">
                  {a.deployment_type === "saas"
                    ? "SaaS"
                    : a.deployment_type === "paas"
                    ? "PaaS"
                    : a.deployment_type === "iaas"
                    ? "IaaS"
                    : "On-prem"}
                  {(a.provider || a.service_name) && (
                    <div className="text-[11px] text-gray-500">
                      {[a.provider, a.service_name].filter(Boolean).join(" — ")}
                    </div>
                  )}
                </td>
                <td className="px-4 py-3 text-gray-600 font-mono text-xs">{a.fqdn}</td>
                <td className="px-4 py-3 text-gray-600">{a.os}</td>
                <td className="px-4 py-3"><CriticalityBadge value={a.criticality} /></td>
                <td className="px-4 py-3"><StatusBadge status={a.internet_exposed ? "si" : "no"} /></td>
                <td className="px-4 py-3 text-gray-600 text-xs">
                  {(() => {
                    const linked = processes.filter((p) => (a.processes || []).includes(p.id));
                    return linked.length ? linked.map((p) => p.name).join(", ") : "—";
                  })()}
                </td>
                <td className="px-4 py-3 text-gray-500 text-xs">
                  {a.eol_date ? new Date(a.eol_date).toLocaleDateString(i18n.language || "it") : "—"}
                </td>
                <td className="px-4 py-3">
                  <button
                    onClick={() => setExpandedId(expandedId === a.id ? null : a.id)}
                    className="text-xs text-blue-600 hover:underline border border-blue-200 rounded px-2 py-0.5"
                  >
                    {expandedId === a.id ? "Chiudi" : "Change"}
                  </button>
                  <button
                    onClick={() => setEditAsset(a)}
                    className="ml-2 text-xs text-gray-700 hover:underline border border-gray-200 rounded px-2 py-0.5"
                  >
                    Modifica
                  </button>
                  <button
                    type="button"
                    title={t("assets.actions.delete_title")}
                    onClick={() => {
                      if (!window.confirm(t("assets.actions.delete_confirm", { name: a.name }))) return;
                      deleteMutation.mutate(a.id);
                    }}
                    disabled={deleteMutation.isPending}
                    className="ml-2 text-xs text-red-600 border border-red-200 rounded px-2 py-0.5 hover:bg-red-50 disabled:opacity-50"
                  >
                    🗑
                  </button>
                </td>
              </tr>
              {expandedId === a.id && (
                <tr key={`${a.id}-detail`}>
                  <td colSpan={7} className="px-4 pb-4">
                    <RegisterChangeForm asset={a} assetType="IT" onClose={() => setExpandedId(null)} />
                  </td>
                </tr>
              )}
            </>
          ))
        )}
      </tbody>
    </table>
    {editAsset && <EditAssetModalIT asset={editAsset} onClose={() => setEditAsset(null)} />}
    </>
  );
}

function OTTab({ search }: { search: string }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const deleteMutation = useMutation({
    mutationFn: (id: string) => assetsApi.deleteOT(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["assets-ot"] }),
    onError: (e: any) => window.alert(e?.response?.data?.detail || t("common.error")),
  });

  const { data, isLoading } = useQuery({
    queryKey: ["assets-ot"],
    queryFn: () => assetsApi.listOT(),
    retry: false,
  });
  const { data: procData } = useQuery({
    queryKey: ["critical-processes"],
    queryFn: () => biaApi.list({ status: "approvato" }),
    retry: false,
  });
  const processes: CriticalProcess[] = procData?.results ?? [];

  const assets: AssetOT[] = (data?.results ?? []).filter(
    (a) =>
      !search ||
      a.name.toLowerCase().includes(search.toLowerCase()) ||
      a.vendor.toLowerCase().includes(search.toLowerCase())
  );

  if (isLoading) {
    return <div className="p-8 text-center text-gray-400">Caricamento...</div>;
  }

  return (
    <table className="w-full text-sm">
      <thead className="bg-gray-50 border-b border-gray-200">
        <tr>
          <th className="text-left px-4 py-3 font-medium text-gray-600">Nome</th>
          <th className="text-left px-4 py-3 font-medium text-gray-600">Categoria</th>
          <th className="text-left px-4 py-3 font-medium text-gray-600">Livello Purdue</th>
          <th className="text-left px-4 py-3 font-medium text-gray-600">Patchable</th>
          <th className="text-left px-4 py-3 font-medium text-gray-600">Vendor</th>
          <th className="text-left px-4 py-3 font-medium text-gray-600">Criticità</th>
          <th className="text-left px-4 py-3 font-medium text-gray-600">Processi BIA</th>
          <th className="px-4 py-3"></th>
        </tr>
      </thead>
      <tbody className="divide-y divide-gray-100">
        {assets.length === 0 ? (
          <tr>
            <td colSpan={8} className="px-4 py-8 text-center text-gray-400">
              Nessun asset OT trovato
            </td>
          </tr>
        ) : (
          assets.map((a) => (
            <>
              <tr key={a.id} className="hover:bg-gray-50 transition-colors">
                <td className="px-4 py-3 font-medium text-gray-800">
                  {a.name}
                  <ChangeBadges asset={a} />
                </td>
                <td className="px-4 py-3">
                  <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800">
                    {a.category}
                  </span>
                </td>
                <td className="px-4 py-3 text-gray-600">{a.purdue_level}</td>
                <td className="px-4 py-3"><StatusBadge status={a.patchable ? "si" : "no"} /></td>
                <td className="px-4 py-3 text-gray-600">{a.vendor}</td>
                <td className="px-4 py-3"><CriticalityBadge value={a.criticality} /></td>
                <td className="px-4 py-3 text-gray-600 text-xs">
                  {(() => {
                    const linked = processes.filter((p) => (a.processes || []).includes(p.id));
                    return linked.length ? linked.map((p) => p.name).join(", ") : "—";
                  })()}
                </td>
                <td className="px-4 py-3">
                  <button
                    onClick={() => setExpandedId(expandedId === a.id ? null : a.id)}
                    className="text-xs text-blue-600 hover:underline border border-blue-200 rounded px-2 py-0.5"
                  >
                    {expandedId === a.id ? "Chiudi" : "Change"}
                  </button>
                  <button
                    type="button"
                    title={t("assets.actions.delete_title")}
                    onClick={() => {
                      if (!window.confirm(t("assets.actions.delete_confirm", { name: a.name }))) return;
                      deleteMutation.mutate(a.id);
                    }}
                    disabled={deleteMutation.isPending}
                    className="ml-2 text-xs text-red-600 border border-red-200 rounded px-2 py-0.5 hover:bg-red-50 disabled:opacity-50"
                  >
                    🗑
                  </button>
                </td>
              </tr>
              {expandedId === a.id && (
                <tr key={`${a.id}-detail`}>
                  <td colSpan={8} className="px-4 pb-4">
                    <RegisterChangeForm asset={a} assetType="OT" onClose={() => setExpandedId(null)} />
                  </td>
                </tr>
              )}
            </>
          ))
        )}
      </tbody>
    </table>
  );
}

export function AssetsPage() {
  const [activeTab, setActiveTab] = useState<"IT" | "OT">("IT");
  const [search, setSearch] = useState("");
  const [showNew, setShowNew] = useState(false);

  const { data: plants } = useQuery({
    queryKey: ["plants"],
    queryFn: () => plantsApi.list(),
    retry: false,
  });

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold text-gray-900 flex items-center">
          Asset IT/OT
          <ModuleHelp
            title="Asset IT e OT — M04"
            description="Censisce tutti gli asset informatici (server, servizi cloud, database)
    e operativi (PLC, SCADA, HMI). La criticità determina la priorità
    nelle valutazioni di rischio e l'obbligo di BCP."
            steps={[
              "Classifica l'asset come IT (inclusi servizi cloud) o OT",
              "Per gli asset IT imposta il tipo di deployment (on-prem, IaaS, PaaS, SaaS) e, se cloud, provider e nome servizio",
              "Assegna criticità 1-5 (vedi tabella nel form) e collega i processi critici della BIA",
              "Usa 'Registra change' per collegare i ticket di change management e marcare gli asset da rivalutare",
              "Rivedi periodicamente l'elenco per aggiungere nuovi servizi cloud critici o modifiche architetturali",
            ]}
            connections={[
              { module: "M05 BIA", relation: "Asset collegato a processo critico" },
              { module: "M06 Risk", relation: "Asset (on-prem o cloud) oggetto di risk assessment e weighted score" },
              { module: "M16 BCP", relation: "Asset critico (≥4) richiede piano BCP e test periodici" },
            ]}
            configNeeded={[
              "Creare prima i Plant in M01",
              "Creare i processi BIA (M05) prima di collegare gli asset",
              "Mantenere allineato l'elenco dei servizi SaaS/PaaS/IaaS critici con il catalogo IT",
            ]}
          />
        </h2>
        <button onClick={() => setShowNew(true)} className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700">
          + Nuovo asset {activeTab}
        </button>
      </div>

      <div className="mb-4 flex items-center gap-4">
        <div className="flex border-b border-gray-200">
          {(["IT", "OT"] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab
                  ? "border-primary-600 text-primary-600"
                  : "border-transparent text-gray-500 hover:text-gray-700"
              }`}
            >
              Asset {tab}
            </button>
          ))}
        </div>
        <input
          type="text"
          placeholder="Cerca per nome..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="ml-auto border rounded px-3 py-1.5 text-sm w-64 focus:outline-none focus:ring-2 focus:ring-primary-400"
        />
      </div>

      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        {activeTab === "IT" ? (
          <ITTab search={search} />
        ) : (
          <OTTab search={search} />
        )}
      </div>

      {showNew && plants && (
        <NewAssetModal assetType={activeTab} plants={plants} onClose={() => setShowNew(false)} />
      )}
    </div>
  );
}
