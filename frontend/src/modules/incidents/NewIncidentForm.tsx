import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { incidentsApi, type Incident } from "../../api/endpoints/incidents";
import { useTranslation } from "react-i18next";
import { nowLocalForInput } from "../../utils/dates";

export function NewIncidentForm({
  plants,
  onClose,
}: {
  plants: { id: string; code: string; name: string }[];
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [form, setForm] = useState<Partial<Incident>>({
    severity: "media",
    nis2_notifiable: "da_valutare",
    // datetime-local vuole l'ora locale del browser, non UTC (di sera l'UTC
    // arretrava data/ora di rilevamento — dato critico per i termini NIS2)
    detected_at: nowLocalForInput(),
  });

  const mutation = useMutation({
    mutationFn: incidentsApi.create,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["incidents"] });
      onClose();
    },
  });

  function handleChange(
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>
  ) {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-lg p-6">
        <h3 className="text-lg font-semibold mb-4">{t("incidents.new.title")}</h3>
        <div className="space-y-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("incidents.fields.plant")}</label>
            <select name="plant" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm">
              <option value="">{t("common.select")}</option>
              {plants.map((p) => (
                <option key={p.id} value={p.id}>{p.code} — {p.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("incidents.fields.title")}</label>
            <input name="title" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("incidents.fields.description")}</label>
            <textarea name="description" onChange={handleChange} rows={3} className="w-full border rounded px-3 py-2 text-sm" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("incidents.fields.severity")}</label>
              <select name="severity" onChange={handleChange} defaultValue="media" className="w-full border rounded px-3 py-2 text-sm">
                {["bassa", "media", "alta", "critica"].map((s) => (
                  <option key={s} value={s}>{t(`status.${s}`)}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("incidents.fields.nis2_notifiable")}</label>
              <select name="nis2_notifiable" onChange={handleChange} defaultValue="da_valutare" className="w-full border rounded px-3 py-2 text-sm">
                {["si", "no", "da_valutare"].map((s) => (
                  <option key={s} value={s}>{t(`status.${s}`)}</option>
                ))}
              </select>
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("incidents.fields.detected_at")}</label>
            <input type="datetime-local" name="detected_at" defaultValue={form.detected_at as string} onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" />
          </div>
        </div>
        {mutation.isError && (
          <p className="text-sm text-red-600 mt-2">{t("common.save_error")}</p>
        )}
        <div className="flex justify-end gap-2 mt-4">
          <button onClick={onClose} className="px-4 py-2 border rounded text-sm text-gray-600 hover:bg-gray-50">
            {t("actions.cancel")}
          </button>
          <button
            onClick={() => mutation.mutate(form)}
            disabled={mutation.isPending}
            className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700 disabled:opacity-50"
          >
            {mutation.isPending ? t("common.saving") : t("incidents.new.submit")}
          </button>
        </div>
      </div>
    </div>
  );
}
