import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { assetsApi, type AssetIT } from "../../api/endpoints/assets";
import { biaApi, type CriticalProcess } from "../../api/endpoints/bia";
import { useTranslation } from "react-i18next";

export function EditAssetModalIT({ asset, onClose }: { asset: AssetIT; onClose: () => void }) {
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
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-6 max-h-[90vh] overflow-y-auto">
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
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("assets.criticality_label")} (1-5)</label>
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
