import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { assetsApi, type AssetIT, type AssetOT } from "../../api/endpoints/assets";
import { biaApi, type CriticalProcess } from "../../api/endpoints/bia";
import { suppliersApi, type Supplier } from "../../api/endpoints/suppliers";
import { CriticalityGuide } from "./CriticalityGuide";
import { useTranslation } from "react-i18next";

export function NewAssetModal({ assetType, plants, onClose }: { assetType: "IT" | "OT"; plants: { id: string; code: string; name: string }[]; onClose: () => void }) {
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

  const { data: suppliersData } = useQuery({
    queryKey: ["suppliers", "active"],
    queryFn: () => suppliersApi.list({ status: "attivo" }),
    retry: false,
  });
  const suppliers: Supplier[] = suppliersData?.results ?? [];

  const mutation = useMutation<AssetIT | AssetOT, any, Partial<AssetIT> & Partial<AssetOT>>({
    mutationFn: (data) =>
      assetType === "IT" ? assetsApi.createIT(data) : assetsApi.createOT(data),
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
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-6 max-h-[90vh] overflow-y-auto">
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
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("assets.maintainer_supplier_label")}</label>
            <select
              name="maintainer_supplier"
              onChange={(e) => setForm((prev) => ({ ...prev, maintainer_supplier: e.target.value || null }))}
              className="w-full border rounded px-3 py-2 text-sm"
            >
              <option value="">{t("common.select")}</option>
              {suppliers.map((s) => (
                <option key={s.id} value={s.id}>{s.name}</option>
              ))}
            </select>
            <p className="mt-1 text-xs text-gray-500">{t("assets.maintainer_supplier_hint")}</p>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("eval_assistant.bia.columns.level")} (1-5)</label>
            <select name="criticality" defaultValue="3" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm">
              {[1,2,3,4,5].map(n => <option key={n} value={n}>{n}</option>)}
            </select>
            <CriticalityGuide />
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
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">{t("assets.fqdn_label")}</label>
                <input name="fqdn" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" placeholder={t("assets.fqdn_placeholder")} />
              </div>
              <div className="flex items-center gap-2">
                <input type="checkbox" id="ot_internet_exposed" name="internet_exposed" onChange={handleChange} className="rounded" />
                <label htmlFor="ot_internet_exposed" className="text-sm text-gray-700">{t("assets.internet_exposed_label")}</label>
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
