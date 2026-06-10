import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { assetsApi, type AssetSW } from "../../api/endpoints/assets";
import { biaApi, type CriticalProcess } from "../../api/endpoints/bia";
import { CriticalityGuide } from "./CriticalityGuide";
import { useTranslation } from "react-i18next";

export function NewAssetModalSW({ plants, onClose }: { plants: { id: string; code: string; name: string }[]; onClose: () => void }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [form, setForm] = useState<Partial<AssetSW>>({ asset_type: "SW", criticality: 3, approval_status: "in_valutazione" });
  const [error, setError] = useState("");

  const { data: processesData } = useQuery({
    queryKey: ["critical-processes"],
    queryFn: () => biaApi.list({ status: "approvato" }),
    retry: false,
  });
  const processes: CriticalProcess[] = processesData?.results ?? [];

  const mutation = useMutation({
    mutationFn: assetsApi.createSW,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["assets-sw"] }); onClose(); },
    onError: (e: any) => setError(e?.response?.data?.detail || t("common.save_error")),
  });

  function handleChange(e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) {
    const v = e.target.type === "number" ? Number(e.target.value) : e.target.value;
    setForm(prev => ({ ...prev, [e.target.name]: v || undefined }));
  }

  function handleProcessesChange(e: React.ChangeEvent<HTMLSelectElement>) {
    setForm(prev => ({ ...prev, processes: Array.from(e.target.selectedOptions).map(o => o.value) }));
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-6 max-h-[90vh] overflow-y-auto">
        <h3 className="text-lg font-semibold mb-4">{t("assets.sw.new_title")}</h3>
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
            <input name="name" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" placeholder={t("assets.sw.name_placeholder")} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("assets.vendor_label")}</label>
              <input name="vendor" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" placeholder="Able Tech, SAP…" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("assets.sw.version_label")}</label>
              <input name="version" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" placeholder="3.2.1" />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("assets.sw.approval_status_label")}</label>
              <select name="approval_status" defaultValue="in_valutazione" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm">
                <option value="approvato">{t("assets.sw.status_approvato")}</option>
                <option value="in_valutazione">{t("assets.sw.status_in_valutazione")}</option>
                <option value="deprecato">{t("assets.sw.status_deprecato")}</option>
                <option value="vietato">{t("assets.sw.status_vietato")}</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("assets.sw.license_type_label")}</label>
              <select name="license_type" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm">
                <option value="">— {t("common.select")} —</option>
                <option value="commerciale">{t("assets.sw.license_commerciale")}</option>
                <option value="open_source">{t("assets.sw.license_open_source")}</option>
                <option value="saas">SaaS</option>
                <option value="freeware">Freeware</option>
              </select>
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("assets.sw.eos_label")}</label>
            <input type="date" name="end_of_support" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("eval_assistant.bia.columns.level")} (1-5)</label>
            <select name="criticality" defaultValue="3" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm">
              {[1,2,3,4,5].map(n => <option key={n} value={n}>{n}</option>)}
            </select>
            <CriticalityGuide />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("assets.sw.external_ref_label")}</label>
            <input name="external_ref" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" placeholder={t("assets.sw.external_ref_placeholder")} />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("assets.bia_processes_label")}</label>
            <select multiple name="processes" onChange={handleProcessesChange} className="w-full border rounded px-3 py-2 text-sm h-24">
              {processes.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
          </div>
        </div>
        {error && <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded mt-3">{error}</p>}
        <div className="flex justify-end gap-2 mt-4">
          <button onClick={onClose} className="px-4 py-2 border rounded text-sm text-gray-600 hover:bg-gray-50">{t("actions.cancel")}</button>
          <button
            onClick={() => mutation.mutate(form)}
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

export function EditAssetModalSW({ asset, onClose }: { asset: AssetSW; onClose: () => void }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [form, setForm] = useState<Partial<AssetSW>>({
    name: asset.name, criticality: asset.criticality,
    vendor: asset.vendor, version: asset.version,
    approval_status: asset.approval_status, license_type: asset.license_type || "",
    end_of_support: asset.end_of_support ?? "", external_ref: asset.external_ref,
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
    mutationFn: (payload: Partial<AssetSW>) =>
      assetsApi.updateSW(asset.id, { ...payload, end_of_support: (payload.end_of_support as string) || null }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["assets-sw"] }); onClose(); },
    onError: (e: any) => setError(e?.response?.data?.detail || t("common.save_error")),
  });

  function handleChange(e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) {
    const v = e.target.type === "number" ? Number(e.target.value) : e.target.value;
    setForm(prev => ({ ...prev, [e.target.name]: v }));
  }

  function handleProcessesChange(e: React.ChangeEvent<HTMLSelectElement>) {
    setForm(prev => ({ ...prev, processes: Array.from(e.target.selectedOptions).map(o => o.value) }));
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-6 max-h-[90vh] overflow-y-auto">
        <h3 className="text-lg font-semibold mb-4">{t("actions.edit")} — {asset.name}</h3>
        <div className="space-y-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("plants.fields.name")} *</label>
            <input name="name" value={form.name ?? ""} onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("assets.vendor_label")}</label>
              <input name="vendor" value={form.vendor ?? ""} onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("assets.sw.version_label")}</label>
              <input name="version" value={form.version ?? ""} onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("assets.sw.approval_status_label")}</label>
              <select name="approval_status" value={form.approval_status ?? "in_valutazione"} onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm">
                <option value="approvato">{t("assets.sw.status_approvato")}</option>
                <option value="in_valutazione">{t("assets.sw.status_in_valutazione")}</option>
                <option value="deprecato">{t("assets.sw.status_deprecato")}</option>
                <option value="vietato">{t("assets.sw.status_vietato")}</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("assets.sw.license_type_label")}</label>
              <select name="license_type" value={form.license_type ?? ""} onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm">
                <option value="">— {t("common.select")} —</option>
                <option value="commerciale">{t("assets.sw.license_commerciale")}</option>
                <option value="open_source">{t("assets.sw.license_open_source")}</option>
                <option value="saas">SaaS</option>
                <option value="freeware">Freeware</option>
              </select>
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("assets.sw.eos_label")}</label>
            <input type="date" name="end_of_support" value={form.end_of_support ?? ""} onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("eval_assistant.bia.columns.level")} (1-5)</label>
            <select name="criticality" value={form.criticality ?? 3} onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm">
              {[1,2,3,4,5].map(n => <option key={n} value={n}>{n}</option>)}
            </select>
            <CriticalityGuide />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("assets.sw.external_ref_label")}</label>
            <input name="external_ref" value={form.external_ref ?? ""} onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("assets.bia_processes_label")}</label>
            <select multiple name="processes" value={(form.processes as string[]) ?? []} onChange={handleProcessesChange} className="w-full border rounded px-3 py-2 text-sm h-24">
              {processes.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
          </div>
        </div>
        {error && <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded mt-3">{error}</p>}
        <div className="flex justify-end gap-2 mt-4">
          <button onClick={onClose} className="px-4 py-2 border rounded text-sm text-gray-600 hover:bg-gray-50">{t("actions.cancel")}</button>
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
