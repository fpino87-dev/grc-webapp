import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { apiClient } from "../../api/client";
import { plantsApi } from "../../api/endpoints/plants";
import { controlsApi, type FrameworkGovernanceMeta } from "../../api/endpoints/controls";

interface RiskAppetitePolicy {
  id: string;
  plant: string | null;
  framework_code: string;
  max_acceptable_score: number;
  max_red_risks_count: number;
  max_unacceptable_score: number;
  valid_from: string;
  valid_until: string | null;
  review_frequency_months?: number;
  notes?: string;
  approved_by_name?: string | null;
  is_active?: boolean;
}

type EditingPolicy = Partial<RiskAppetitePolicy> & { id?: string };

function formatDate(dateStr?: string | null, locale = "it") {
  if (!dateStr) return "—";
  const dt = new Date(dateStr);
  if (Number.isNaN(dt.getTime())) return String(dateStr);
  return dt.toLocaleDateString(locale);
}

export function RiskAppetiteGovernanceTab() {
  const { t, i18n } = useTranslation();
  const qc = useQueryClient();
  const [editing, setEditing] = useState<EditingPolicy | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<RiskAppetitePolicy | null>(null);

  const { data: policies = [], isLoading, error } = useQuery({
    queryKey: ["risk-appetite-policies"],
    queryFn: async () => {
      const res = await apiClient.get<RiskAppetitePolicy[] | { results?: RiskAppetitePolicy[] }>("/risk/appetite-policies/");
      const body = res.data;
      return Array.isArray(body) ? body : body.results ?? [];
    },
    retry: false,
  });

  const { data: plants = [] } = useQuery({
    queryKey: ["plants"],
    queryFn: plantsApi.list,
    retry: false,
  });

  const { data: frameworks = [] } = useQuery({
    queryKey: ["frameworks-governance"],
    queryFn: () => controlsApi.frameworksGovernance() as Promise<FrameworkGovernanceMeta[]>,
    retry: false,
  });

  const saveMutation = useMutation({
    mutationFn: async () => {
      if (!editing) return;
      const payload: Partial<RiskAppetitePolicy> = {
        plant: editing.plant ?? null,
        framework_code: editing.framework_code ?? "",
        max_acceptable_score: Number(editing.max_acceptable_score ?? 14),
        max_red_risks_count: Number(editing.max_red_risks_count ?? 3),
        max_unacceptable_score: Number(editing.max_unacceptable_score ?? 20),
        valid_from: editing.valid_from!,
        valid_until: editing.valid_until ?? null,
        notes: editing.notes ?? "",
      };
      if (editing.id) {
        await apiClient.patch(`/risk/appetite-policies/${editing.id}/`, payload);
      } else {
        await apiClient.post("/risk/appetite-policies/", payload);
      }
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["risk-appetite-policies"] });
      setEditing(null);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: string) => {
      await apiClient.delete(`/risk/appetite-policies/${id}/`);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["risk-appetite-policies"] });
      setConfirmDelete(null);
    },
  });

  function openNew() {
    setEditing({
      framework_code: "",
      max_acceptable_score: 14,
      max_red_risks_count: 3,
      max_unacceptable_score: 20,
      valid_from: new Date().toISOString().slice(0, 10),
      valid_until: null,
      plant: null,
      notes: "",
    });
  }

  function editPolicy(p: RiskAppetitePolicy) {
    setEditing({
      ...p,
    });
  }

  function plantLabel(p: RiskAppetitePolicy): string {
    if (!p.plant) return "Org-wide";
    const plant = plants.find((pl: any) => pl.id === p.plant);
    if (plant) return `[${plant.code}] ${plant.name}`;
    return "Plant";
  }

  function frameworkLabel(code: string): string {
    if (!code) return t("risk.appetite.all_frameworks", { defaultValue: "Tutti i framework" });
    const fw = (frameworks as FrameworkGovernanceMeta[]).find((f) => f.code === code);
    return fw ? `${fw.code} — ${fw.name}` : code;
  }

  return (
    <div className="space-y-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">
            {t("governance.risk_appetite.title", { defaultValue: "Risk Appetite" })}
          </h3>
          <p className="text-sm text-gray-500 mt-1">
            {t("governance.risk_appetite.subtitle", {
              defaultValue:
                "Definisci le soglie di rischio accettabile per plant e framework: score massimo accettabile, limiti sui rischi rossi e soglia non accettabile.",
            })}
          </p>
        </div>
        <div className="text-xs text-gray-400 max-w-sm">
          {t("governance.risk_appetite.note", {
            defaultValue:
              "Solo una policy attiva per combinazione Plant/Framework: la più recente per data di inizio viene usata in M06 per confrontare Inerente/Residuo/Weighted.",
          })}
        </div>
      </div>

      <div className="flex items-center justify-between">
        <h4 className="text-sm font-semibold text-gray-700">
          {t("governance.risk_appetite.table_title", { defaultValue: "Policy di Risk Appetite" })}
        </h4>
        <button
          type="button"
          onClick={openNew}
          className="px-3 py-1.5 rounded bg-primary-600 text-white text-xs font-medium hover:bg-primary-700"
        >
          {t("governance.risk_appetite.new", { defaultValue: "+ Nuova policy" })}
        </button>
      </div>

      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        {isLoading ? (
          <div className="p-6 text-sm text-gray-400">{t("common.loading")}</div>
        ) : error ? (
          <div className="p-6 text-sm text-red-600">{t("common.error")}</div>
        ) : !policies.length ? (
          <div className="p-6 text-sm text-gray-400 italic">
            {t("governance.risk_appetite.empty", {
              defaultValue: "Nessuna policy configurata. Definisci almeno una soglia org-wide o per plant.",
            })}
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-4 py-2 text-left font-medium text-gray-600">
                  {t("governance.risk_appetite.columns.plant", { defaultValue: "Plant" })}
                </th>
                <th className="px-4 py-2 text-left font-medium text-gray-600">
                  {t("governance.risk_appetite.columns.framework", { defaultValue: "Framework" })}
                </th>
                <th className="px-4 py-2 text-left font-medium text-gray-600">
                  {t("governance.risk_appetite.columns.max_acceptable", { defaultValue: "Score max accettabile" })}
                </th>
                <th className="px-4 py-2 text-left font-medium text-gray-600">
                  {t("governance.risk_appetite.columns.max_red", { defaultValue: "Max rischi rossi" })}
                </th>
                <th className="px-4 py-2 text-left font-medium text-gray-600">
                  {t("governance.risk_appetite.columns.max_unacceptable", {
                    defaultValue: "Score non accettabile",
                  })}
                </th>
                <th className="px-4 py-2 text-left font-medium text-gray-600">
                  {t("governance.risk_appetite.columns.valid_from", { defaultValue: "Valido da" })}
                </th>
                <th className="px-4 py-2 text-left font-medium text-gray-600">
                  {t("governance.risk_appetite.columns.valid_until", { defaultValue: "Valido fino" })}
                </th>
                <th className="px-4 py-2 text-left font-medium text-gray-600">
                  {t("governance.risk_appetite.columns.status", { defaultValue: "Stato" })}
                </th>
                <th className="px-4 py-2 text-right font-medium text-gray-600">
                  {t("governance.risk_appetite.columns.actions", { defaultValue: "Azioni" })}
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {policies.map((p) => (
                <tr key={p.id} className="hover:bg-gray-50">
                  <td className="px-4 py-2 text-xs text-gray-800">{plantLabel(p)}</td>
                  <td className="px-4 py-2 text-xs text-gray-800">{frameworkLabel(p.framework_code)}</td>
                  <td className="px-4 py-2 text-gray-800">{p.max_acceptable_score}</td>
                  <td className="px-4 py-2 text-gray-800">{p.max_red_risks_count}</td>
                  <td className="px-4 py-2 text-gray-800">{p.max_unacceptable_score}</td>
                  <td className="px-4 py-2 text-xs text-gray-700">{formatDate(p.valid_from, i18n.language)}</td>
                  <td className="px-4 py-2 text-xs text-gray-700">{formatDate(p.valid_until, i18n.language)}</td>
                  <td className="px-4 py-2 text-xs">
                    {p.is_active ? (
                      <span className="inline-flex items-center px-2 py-0.5 rounded-full bg-green-100 text-green-700">
                        {t("status.attivo", { defaultValue: "Attiva" })}
                      </span>
                    ) : (
                      <span className="inline-flex items-center px-2 py-0.5 rounded-full bg-gray-100 text-gray-600">
                        {t("status.archived", { defaultValue: "Non attiva" })}
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-2 text-right">
                    <button
                      type="button"
                      onClick={() => editPolicy(p)}
                      className="text-xs text-indigo-600 hover:text-indigo-800 border border-indigo-200 rounded px-2 py-0.5 mr-2"
                    >
                      {t("actions.edit", { defaultValue: "Modifica" })}
                    </button>
                    <button
                      type="button"
                      onClick={() => setConfirmDelete(p)}
                      className="text-xs text-red-600 hover:text-red-800 border border-red-200 rounded px-2 py-0.5"
                    >
                      {t("actions.delete", { defaultValue: "Elimina" })}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Modal create/edit */}
      {editing && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl p-6 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold text-gray-900">
                {editing.id
                  ? t("governance.risk_appetite.edit_title", { defaultValue: "Modifica policy Risk Appetite" })
                  : t("governance.risk_appetite.new_title", { defaultValue: "Nuova policy Risk Appetite" })}
              </h3>
              <button
                type="button"
                onClick={() => setEditing(null)}
                className="text-gray-400 hover:text-gray-600 text-xl leading-none"
              >
                ×
              </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Plant</label>
                <select
                  value={editing.plant ?? ""}
                  onChange={(e) =>
                    setEditing((prev) => prev && { ...prev, plant: e.target.value || null })
                  }
                  className="w-full border rounded px-3 py-2 text-sm"
                >
                  <option value="">{t("governance.risk_appetite.org_wide", { defaultValue: "Org-wide (tutti i plant)" })}</option>
                  {plants.map((pl: any) => (
                    <option key={pl.id} value={pl.id}>
                      [{pl.code}] {pl.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Framework</label>
                <select
                  value={editing.framework_code ?? ""}
                  onChange={(e) =>
                    setEditing((prev) => prev && { ...prev, framework_code: e.target.value })
                  }
                  className="w-full border rounded px-3 py-2 text-sm"
                >
                  <option value="">
                    {t("governance.risk_appetite.framework_all", {
                      defaultValue: "Tutti i framework",
                    })}
                  </option>
                  {(frameworks as FrameworkGovernanceMeta[]).map((fw) => (
                    <option key={fw.id} value={fw.code}>
                      {fw.code} — {fw.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Score max accettabile *
                </label>
                <input
                  type="number"
                  min={1}
                  max={25}
                  value={editing.max_acceptable_score ?? ""}
                  onChange={(e) =>
                    setEditing((prev) => prev && { ...prev, max_acceptable_score: Number(e.target.value) })
                  }
                  className="w-full border rounded px-3 py-2 text-sm"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Max rischi rossi contemporanei *
                </label>
                <input
                  type="number"
                  min={0}
                  value={editing.max_red_risks_count ?? ""}
                  onChange={(e) =>
                    setEditing((prev) => prev && { ...prev, max_red_risks_count: Number(e.target.value) })
                  }
                  className="w-full border rounded px-3 py-2 text-sm"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Score non accettabile *
                </label>
                <input
                  type="number"
                  min={1}
                  max={25}
                  value={editing.max_unacceptable_score ?? ""}
                  onChange={(e) =>
                    setEditing((prev) => prev && { ...prev, max_unacceptable_score: Number(e.target.value) })
                  }
                  className="w-full border rounded px-3 py-2 text-sm"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Valido da *</label>
                <input
                  type="date"
                  value={editing.valid_from ?? ""}
                  onChange={(e) =>
                    setEditing((prev) => prev && { ...prev, valid_from: e.target.value })
                  }
                  className="w-full border rounded px-3 py-2 text-sm"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Valido fino</label>
                <input
                  type="date"
                  value={editing.valid_until ?? ""}
                  onChange={(e) =>
                    setEditing((prev) => prev && { ...prev, valid_until: e.target.value || null })
                  }
                  className="w-full border rounded px-3 py-2 text-sm"
                />
              </div>

              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-gray-700 mb-1">Note (opzionale)</label>
                <textarea
                  value={editing.notes ?? ""}
                  onChange={(e) =>
                    setEditing((prev) => prev && { ...prev, notes: e.target.value })
                  }
                  rows={3}
                  className="w-full border rounded px-3 py-2 text-sm"
                  placeholder="Note approvazione, riferimenti a delibere management, ecc."
                />
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setEditing(null)}
                className="px-4 py-2 border rounded text-sm text-gray-600 hover:bg-gray-50"
              >
                {t("actions.cancel", { defaultValue: "Annulla" })}
              </button>
              <button
                type="button"
                onClick={() => saveMutation.mutate()}
                disabled={
                  saveMutation.isPending ||
                  !editing.valid_from ||
                  editing.max_acceptable_score == null ||
                  editing.max_red_risks_count == null ||
                  editing.max_unacceptable_score == null
                }
                className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700 disabled:opacity-50"
              >
                {saveMutation.isPending
                  ? t("common.saving", { defaultValue: "Salvataggio..." })
                  : t("actions.save", { defaultValue: "Salva" })}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal delete */}
      {confirmDelete && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-6 space-y-4">
            <h3 className="text-lg font-semibold text-gray-900">
              {t("governance.risk_appetite.delete_title", { defaultValue: "Elimina policy" })}
            </h3>
            <p className="text-sm text-gray-600">
              {t("governance.risk_appetite.delete_body", {
                defaultValue:
                  "Sei sicuro di voler eliminare questa policy di Risk Appetite? Le valutazioni M06 useranno eventuali altre policy attive.",
              })}
            </p>
            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setConfirmDelete(null)}
                className="px-4 py-2 border rounded text-sm text-gray-600 hover:bg-gray-50"
              >
                {t("actions.cancel", { defaultValue: "Annulla" })}
              </button>
              <button
                type="button"
                onClick={() => deleteMutation.mutate(confirmDelete.id)}
                disabled={deleteMutation.isPending}
                className="px-4 py-2 bg-red-600 text-white rounded text-sm hover:bg-red-700 disabled:opacity-50"
              >
                {deleteMutation.isPending
                  ? t("common.deleting", { defaultValue: "Eliminazione..." })
                  : t("actions.delete", { defaultValue: "Elimina" })}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

