import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import {
  assetsApi,
  FACILITY_CATEGORIES,
  type AssetFacility,
  type FacilityCategory,
} from "../../api/endpoints/assets";
import { suppliersApi, type Supplier } from "../../api/endpoints/suppliers";
import { CriticalityGuide } from "./CriticalityGuide";

/** L'autonomia nominale ha senso solo dove c'è una batteria o un serbatoio. */
const AUTONOMY_CATEGORIES: FacilityCategory[] = ["ups", "gruppo_elettrogeno"];

export function NewFacilityModal({
  plants,
  onClose,
}: {
  plants: { id: string; code: string; name: string }[];
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [form, setForm] = useState<Record<string, unknown>>({
    criticality: 3,
    category: "ups",
    maintenance_frequency_months: 6,
  });
  const [error, setError] = useState("");

  const { data: suppliersData } = useQuery({
    queryKey: ["suppliers", "active"],
    queryFn: () => suppliersApi.list({ status: "attivo" }),
    retry: false,
  });
  const suppliers: Supplier[] = suppliersData?.results ?? [];

  const mutation = useMutation<AssetFacility, any, Partial<AssetFacility>>({
    mutationFn: (data) => assetsApi.createFacility(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["assets-facility"] });
      onClose();
    },
    onError: (e: any) =>
      setError(
        e?.response?.data?.rated_autonomy_minutes?.[0] ||
          e?.response?.data?.detail ||
          t("common.save_error")
      ),
  });

  function handleChange(
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>
  ) {
    const target = e.target;
    const v =
      target.type === "number"
        ? target.value === ""
          ? null
          : Number(target.value)
        : target.value;
    setForm((prev) => ({ ...prev, [target.name]: v }));
  }

  const category = form.category as FacilityCategory;
  const showAutonomy = AUTONOMY_CATEGORIES.includes(category);
  const canSave = Boolean(form.plant && String(form.name ?? "").trim());

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-6 max-h-[90vh] overflow-y-auto">
        <h3 className="text-lg font-semibold mb-1">{t("assets.facility.new_title")}</h3>
        <p className="text-xs text-gray-500 mb-4">{t("assets.facility.new_hint")}</p>

        <div className="space-y-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {t("tasks.fields.plant")} *
            </label>
            <select name="plant" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm">
              <option value="">{t("common.select")}</option>
              {plants.map((p) => (
                <option key={p.id} value={p.id}>{p.code} — {p.name}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {t("plants.fields.name")} *
            </label>
            <input name="name" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {t("assets.cols.category")}
              </label>
              <select
                name="category"
                value={category}
                onChange={handleChange}
                className="w-full border rounded px-3 py-2 text-sm"
              >
                {FACILITY_CATEGORIES.map((c) => (
                  <option key={c} value={c}>{t(`assets.facility.categories.${c}`)}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {t("assets.facility.location")}
              </label>
              <input name="location" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {t("assets.cols.criticality")}
            </label>
            <input
              type="number" name="criticality" min={1} max={5}
              value={String(form.criticality ?? 3)}
              onChange={handleChange}
              className="w-full border rounded px-3 py-2 text-sm"
            />
            <CriticalityGuide />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {t("assets.cols.vendor")}
              </label>
              <input name="vendor" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {t("assets.facility.model")}
              </label>
              <input name="model" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {t("assets.facility.serial_number")}
              </label>
              <input name="serial_number" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {t("assets.facility.installation_date")}
              </label>
              <input type="date" name="installation_date" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" />
            </div>
          </div>

          {showAutonomy && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {t("assets.facility.rated_autonomy")}
              </label>
              <input
                type="number" name="rated_autonomy_minutes" min={0}
                onChange={handleChange}
                className="w-full border rounded px-3 py-2 text-sm"
              />
              <p className="text-xs text-gray-500 mt-1">{t("assets.facility.rated_autonomy_hint")}</p>
            </div>
          )}

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {t("assets.maintenance.cadence")}
              </label>
              <select
                name="maintenance_frequency_months"
                value={String(form.maintenance_frequency_months ?? "")}
                onChange={handleChange}
                className="w-full border rounded px-3 py-2 text-sm"
              >
                <option value="">{t("assets.maintenance.no_cadence")}</option>
                {[3, 6, 12, 24].map((m) => (
                  <option key={m} value={m}>{t("assets.maintenance.every_months", { count: m })}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {t("assets.facility.maintainer")}
              </label>
              <select name="maintainer_supplier" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm">
                <option value="">{t("common.optional")}</option>
                {suppliers.map((s) => (
                  <option key={s.id} value={s.id}>{s.name}</option>
                ))}
              </select>
            </div>
          </div>
          <p className="text-xs text-gray-500">{t("assets.maintenance.cadence_hint")}</p>
        </div>

        {error && <p className="text-sm text-red-600 mt-2">{error}</p>}

        <div className="flex justify-end gap-2 mt-4">
          <button onClick={onClose} className="px-4 py-2 border rounded text-sm text-gray-600 hover:bg-gray-50">
            {t("actions.cancel")}
          </button>
          <button
            onClick={() => mutation.mutate(form as Partial<AssetFacility>)}
            disabled={!canSave || mutation.isPending}
            className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700 disabled:opacity-50"
          >
            {mutation.isPending ? t("common.saving") : t("actions.save")}
          </button>
        </div>
      </div>
    </div>
  );
}
