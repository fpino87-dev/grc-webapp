import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { incidentsApi, type Incident } from "../../api/endpoints/incidents";
import { plantsApi } from "../../api/endpoints/plants";
import { useAuthStore } from "../../store/auth";
import { StatusBadge } from "../../components/ui/StatusBadge";
import { ModuleHelp } from "../../components/ui/ModuleHelp";
import { useTranslation } from "react-i18next";
import i18n from "../../i18n";

function NewIncidentForm({
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
    detected_at: new Date().toISOString().slice(0, 16),
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

export function IncidentsList() {
  const { t } = useTranslation();
  const [showNew, setShowNew] = useState(false);
  const qc = useQueryClient();
  const selectedPlant = useAuthStore(s => s.selectedPlant);

  const params: Record<string, string> = {};
  if (selectedPlant?.id) params.plant = selectedPlant.id;

  const { data, isLoading } = useQuery({
    queryKey: ["incidents", selectedPlant?.id],
    queryFn: () => incidentsApi.list(params),
    retry: false,
  });

  const { data: plants } = useQuery({
    queryKey: ["plants"],
    queryFn: () => plantsApi.list(),
    retry: false,
  });

  const closeMutation = useMutation({
    mutationFn: incidentsApi.close,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["incidents"] }),
  });

  const incidents = data?.results ?? [];
  const dateLocale = i18n.language || "it";

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold text-gray-900 flex items-center">
          {t("incidents.title")}
          <ModuleHelp
            title={t("incidents.help.title")}
            description={t("incidents.help.description")}
            steps={[
              t("incidents.help.steps.1"),
              t("incidents.help.steps.2"),
              t("incidents.help.steps.3"),
              t("incidents.help.steps.4"),
              t("incidents.help.steps.5"),
            ]}
            connections={[
              { module: t("incidents.help.connections.pdca.module"), relation: t("incidents.help.connections.pdca.relation") },
              { module: t("incidents.help.connections.lessons.module"), relation: t("incidents.help.connections.lessons.relation") },
              { module: t("incidents.help.connections.tasks.module"), relation: t("incidents.help.connections.tasks.relation") },
            ]}
            configNeeded={[t("incidents.help.config_needed.1")]}
          />
        </h2>
        <button
          onClick={() => setShowNew(true)}
          className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700"
        >
          {t("incidents.new.open")}
        </button>
      </div>

      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-gray-400">{t("common.loading")}</div>
        ) : incidents.length === 0 ? (
          <div className="p-8 text-center text-gray-400">{t("incidents.empty")}</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("incidents.table.title")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("incidents.table.severity")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("incidents.table.nis2")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("incidents.table.status")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("incidents.table.detected_at")}</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {incidents.map((inc) => (
                <tr key={inc.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3 font-medium text-gray-800">{inc.title}</td>
                  <td className="px-4 py-3"><StatusBadge status={inc.severity} /></td>
                  <td className="px-4 py-3"><StatusBadge status={inc.nis2_notifiable} /></td>
                  <td className="px-4 py-3"><StatusBadge status={inc.status} /></td>
                  <td className="px-4 py-3 text-gray-500 text-xs">
                    {new Date(inc.detected_at).toLocaleString(dateLocale)}
                  </td>
                  <td className="px-4 py-3">
                    {inc.status !== "chiuso" && (
                      <button
                        onClick={() => closeMutation.mutate(inc.id)}
                        className="text-xs text-gray-500 hover:text-red-600 border border-gray-300 rounded px-2 py-0.5 hover:border-red-300"
                      >
                        {t("common.close")}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {showNew && plants && (
        <NewIncidentForm plants={plants} onClose={() => setShowNew(false)} />
      )}
    </div>
  );
}
