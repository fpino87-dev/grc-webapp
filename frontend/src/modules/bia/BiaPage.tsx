import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { biaApi, treatmentOptionsApi, type CriticalProcess } from "../../api/endpoints/bia";
import { plantsApi } from "../../api/endpoints/plants";
import { useAuthStore } from "../../store/auth";
import { StatusBadge } from "../../components/ui/StatusBadge";
import { AssistenteValutazione } from "../../components/ui/AssistenteValutazione";
import { ModuleHelp } from "../../components/ui/ModuleHelp";

function CriticalityBar({ value }: { value: number }) {
  const pct = (value / 5) * 100;
  const color = value >= 4 ? "bg-red-500" : value >= 3 ? "bg-orange-400" : "bg-yellow-400";
  return (
    <div className="flex items-center gap-2">
      <div className="w-20 h-2 bg-gray-200 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs text-gray-600">{value}/5</span>
    </div>
  );
}

const RTO_STATUS_COLORS: Record<string, string> = {
  ok: "bg-green-100 text-green-700",
  warning: "bg-yellow-100 text-yellow-700",
  critical: "bg-red-100 text-red-700",
  unknown: "bg-gray-100 text-gray-500",
};

function RtoBcpBadge({ status }: { status: string }) {
  const { t } = useTranslation();
  const labelMap: Record<string, string> = {
    ok: t("bia.rto_ok"),
    warning: t("bia.rto_warning"),
    critical: t("bia.rto_critical"),
  };
  return (
    <span className={`text-xs px-2 py-0.5 rounded font-medium ${RTO_STATUS_COLORS[status] ?? RTO_STATUS_COLORS.unknown}`}>
      {labelMap[status] ?? "—"}
    </span>
  );
}

function NewProcessModal({
  plants,
  onClose,
  initial,
}: {
  plants: { id: string; code: string; name: string }[];
  onClose: () => void;
  initial?: CriticalProcess | null;
}) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [form, setForm] = useState<Partial<CriticalProcess>>(
    initial
      ? {
          ...initial,
          plant: initial.plant,
        }
      : { criticality: 3 }
  );

  const mutation = useMutation({
    mutationFn: (data: Partial<CriticalProcess>) =>
      initial ? biaApi.update(initial.id, data) : biaApi.create(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["bia"] });
      onClose();
    },
  });

  function handleChange(e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) {
    const numericFields = [
      "criticality",
      "mtpd_hours",
      "mbco_pct",
      "downtime_cost_hour",
      "rto_target_hours",
      "rpo_target_hours",
    ];
    const val = numericFields.includes(e.target.name)
      ? (e.target.value ? Number(e.target.value) : null)
      : e.target.value;
    setForm(prev => ({ ...prev, [e.target.name]: val }));
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-lg p-6 max-h-screen overflow-y-auto">
        <h3 className="text-lg font-semibold mb-4">{t("bia.new_process_title")}</h3>
        <div className="space-y-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("bia.site_label")}</label>
            <select
              name="plant"
              value={(form as any).plant ?? ""}
              onChange={handleChange}
              className="w-full border rounded px-3 py-2 text-sm"
            >
              <option value="">— seleziona —</option>
              {plants.map(p => <option key={p.id} value={p.id}>{p.code} — {p.name}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("bia.process_name_label")}</label>
            <input
              name="name"
              value={(form.name as string) ?? ""}
              onChange={handleChange}
              className="w-full border rounded px-3 py-2 text-sm"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("bia.criticality_label")}</label>
              <select
                name="criticality"
                value={form.criticality ?? 3}
                onChange={handleChange}
                className="w-full border rounded px-3 py-2 text-sm"
              >
                {[1,2,3,4,5].map(n => <option key={n} value={n}>{n}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("bia.downtime_cost_label")}</label>
              <input
                name="downtime_cost_hour"
                type="number"
                value={form.downtime_cost_hour as any ?? ""}
                onChange={handleChange}
                className="w-full border rounded px-3 py-2 text-sm"
                placeholder="0.00"
              />
            </div>
          </div>

          <hr className="my-1" />
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">{t("bia.bcp_bia_section")}</p>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("bia.mtpd_label")}</label>
              <input
                name="mtpd_hours"
                type="number"
                min="0"
                value={form.mtpd_hours as any ?? ""}
                onChange={handleChange}
                className="w-full border rounded px-3 py-2 text-sm"
                placeholder="es. 48"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("bia.mbco_label")}</label>
              <input
                name="mbco_pct"
                type="number"
                min="0"
                max="100"
                value={form.mbco_pct as any ?? ""}
                onChange={handleChange}
                className="w-full border rounded px-3 py-2 text-sm"
                placeholder="es. 70"
              />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("bia.rto_label")}</label>
              <input
                name="rto_target_hours"
                type="number"
                min="0"
                value={form.rto_target_hours as any ?? ""}
                onChange={handleChange}
                className="w-full border rounded px-3 py-2 text-sm"
                placeholder="es. 24"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("bia.rpo_label")}</label>
              <input
                name="rpo_target_hours"
                type="number"
                min="0"
                value={form.rpo_target_hours as any ?? ""}
                onChange={handleChange}
                className="w-full border rounded px-3 py-2 text-sm"
                placeholder="es. 4"
              />
            </div>
          </div>
        </div>
        {mutation.isError && <p className="text-sm text-red-600 mt-2">{t("bia.save_error")}</p>}
        <div className="flex justify-end gap-2 mt-4">
          <button onClick={onClose} className="px-4 py-2 border rounded text-sm text-gray-600 hover:bg-gray-50">{t("actions.cancel")}</button>
          <button
            onClick={() =>
              mutation.mutate({
                plant: (form as any).plant,
                name: form.name,
                criticality: form.criticality,
                downtime_cost_hour: form.downtime_cost_hour,
                mtpd_hours: form.mtpd_hours,
                mbco_pct: form.mbco_pct,
                rto_target_hours: form.rto_target_hours,
                rpo_target_hours: form.rpo_target_hours,
              })
            }
            disabled={mutation.isPending}
            className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700 disabled:opacity-50"
          >
            {mutation.isPending ? t("governance.workflow.saving") : initial ? t("bia.save_changes") : t("bia.create_process")}
          </button>
        </div>
      </div>
    </div>
  );
}

function TreatmentsModal({ process, onClose }: { process: CriticalProcess; onClose: () => void }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const emptyForm = { id: "", title: "", ale_reduction_pct: "", cost_implementation: "", cost_annual: "" };
  const [form, setForm] = useState(emptyForm);

  const { data: treatments = [], isLoading } = useQuery({
    queryKey: ["treatment-options", process.id],
    queryFn: () => treatmentOptionsApi.listByProcess(process.id),
  });

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["treatment-options", process.id] });
    qc.invalidateQueries({ queryKey: ["reporting-risk-bia-bcp"] });
  };

  const saveMutation = useMutation({
    mutationFn: () => {
      const payload = {
        process: process.id,
        title: form.title.trim(),
        ale_reduction_pct: Number(form.ale_reduction_pct),
        cost_implementation: form.cost_implementation || "0",
        cost_annual: form.cost_annual || "0",
      };
      return form.id ? treatmentOptionsApi.update(form.id, payload) : treatmentOptionsApi.create(payload);
    },
    onSuccess: () => { invalidate(); setForm(emptyForm); },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => treatmentOptionsApi.delete(id),
    onSuccess: invalidate,
  });

  const canSave = form.title.trim() !== "" && form.ale_reduction_pct !== "" && !saveMutation.isPending;

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl p-6 max-h-screen overflow-y-auto">
        <h3 className="text-lg font-semibold">{t("bia.treatments.title", { process: process.name })}</h3>
        <p className="text-xs text-gray-400 mt-0.5 mb-3">{t("bia.treatments.subtitle")}</p>

        <div className="bg-purple-50 border border-purple-100 rounded-md px-3 py-2 mb-4">
          <p className="text-xs font-semibold text-purple-800">{t("bia.treatments.help_title")}</p>
          <p className="text-xs text-purple-900/80 mt-0.5">{t("bia.treatments.help_body")}</p>
          <p className="text-xs text-purple-900/70 mt-1 italic">{t("bia.treatments.help_example")}</p>
        </div>

        {isLoading ? (
          <div className="py-6 text-center text-gray-400 text-sm">{t("bia.treatments.loading")}</div>
        ) : treatments.length === 0 ? (
          <p className="text-sm text-gray-400 mb-4">{t("bia.treatments.empty")}</p>
        ) : (
          <table className="w-full text-sm mb-4">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-3 py-2 font-medium text-gray-600">{t("bia.treatments.col_title")}</th>
                <th className="text-right px-3 py-2 font-medium text-gray-600">{t("bia.treatments.col_reduction")}</th>
                <th className="text-right px-3 py-2 font-medium text-gray-600">{t("bia.treatments.col_capex")}</th>
                <th className="text-right px-3 py-2 font-medium text-gray-600">{t("bia.treatments.col_opex")}</th>
                <th className="px-3 py-2"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {treatments.map(tr => (
                <tr key={tr.id} className="hover:bg-gray-50">
                  <td className="px-3 py-2 font-medium text-gray-800">{tr.title}</td>
                  <td className="px-3 py-2 text-right tabular-nums text-gray-600">{tr.ale_reduction_pct}%</td>
                  <td className="px-3 py-2 text-right tabular-nums text-gray-600">{tr.cost_implementation}</td>
                  <td className="px-3 py-2 text-right tabular-nums text-gray-600">{tr.cost_annual}</td>
                  <td className="px-3 py-2 text-right whitespace-nowrap">
                    <button
                      onClick={() => setForm({ id: tr.id, title: tr.title, ale_reduction_pct: String(tr.ale_reduction_pct), cost_implementation: tr.cost_implementation, cost_annual: tr.cost_annual })}
                      className="text-xs text-blue-700 border border-blue-300 rounded px-2 py-0.5 hover:bg-blue-50 mr-1"
                    >
                      {t("bia.treatments.edit")}
                    </button>
                    <button
                      onClick={() => { if (window.confirm(t("bia.treatments.delete_confirm"))) deleteMutation.mutate(tr.id); }}
                      disabled={deleteMutation.isPending}
                      className="text-xs text-red-700 border border-red-300 rounded px-2 py-0.5 hover:bg-red-50 disabled:opacity-50"
                    >
                      {t("bia.treatments.delete")}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        <div className="border-t border-gray-100 pt-4">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
            {form.id ? t("bia.treatments.edit") : t("bia.treatments.add")}
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div className="sm:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("bia.treatments.field_title")}</label>
              <input value={form.title} onChange={e => setForm(p => ({ ...p, title: e.target.value }))} className="w-full border rounded px-3 py-1.5 text-sm" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("bia.treatments.field_reduction")}</label>
              <input type="number" min={0} max={100} value={form.ale_reduction_pct} onChange={e => setForm(p => ({ ...p, ale_reduction_pct: e.target.value }))} className="w-full border rounded px-3 py-1.5 text-sm" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("bia.treatments.field_capex")}</label>
              <input type="number" min={0} step="0.01" value={form.cost_implementation} onChange={e => setForm(p => ({ ...p, cost_implementation: e.target.value }))} className="w-full border rounded px-3 py-1.5 text-sm" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("bia.treatments.field_opex")}</label>
              <input type="number" min={0} step="0.01" value={form.cost_annual} onChange={e => setForm(p => ({ ...p, cost_annual: e.target.value }))} className="w-full border rounded px-3 py-1.5 text-sm" />
            </div>
          </div>
          {saveMutation.isError && <p className="text-sm text-red-600 mt-2">{t("bia.treatments.save_error")}</p>}
          <div className="flex gap-2 mt-3">
            <button onClick={() => saveMutation.mutate()} disabled={!canSave} className="px-4 py-1.5 bg-primary-600 text-white rounded text-sm hover:bg-primary-700 disabled:opacity-50">
              {saveMutation.isPending ? t("governance.workflow.saving") : t("bia.treatments.save")}
            </button>
            {form.id && (
              <button onClick={() => setForm(emptyForm)} className="px-4 py-1.5 border border-gray-300 rounded text-sm hover:bg-gray-50">
                {t("bia.treatments.cancel")}
              </button>
            )}
          </div>
        </div>

        <div className="flex justify-end mt-5 border-t border-gray-100 pt-4">
          <button onClick={onClose} className="px-4 py-1.5 border border-gray-300 rounded text-sm hover:bg-gray-50">
            {t("bia.treatments.close")}
          </button>
        </div>
      </div>
    </div>
  );
}

export function BiaPage() {
  const { t } = useTranslation();
  const [showNew, setShowNew] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [filterStatus, setFilterStatus] = useState("");
  const [selectedProcessId, setSelectedProcessId] = useState<string | null>(null);
  const [editProcess, setEditProcess] = useState<CriticalProcess | null>(null);
  const qc = useQueryClient();

  const selectedPlant = useAuthStore(s => s.selectedPlant);
  const params = {
    ...(filterStatus ? { status: filterStatus } : {}),
    ...(selectedPlant?.id ? { plant: selectedPlant.id } : {}),
  };
  const listParams = Object.keys(params).length ? params : undefined;

  const { data, isLoading } = useQuery({
    queryKey: ["bia", filterStatus, selectedPlant?.id],
    queryFn: () => biaApi.list(listParams),
    retry: false,
  });

  const validateMutation = useMutation({
    mutationFn: biaApi.validate,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["bia"] }),
  });

  const { data: plants } = useQuery({
    queryKey: ["plants"],
    queryFn: () => plantsApi.list(),
    retry: false,
  });

  const approveMutation = useMutation({
    mutationFn: biaApi.approve,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["bia"] }),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => biaApi.deleteWithCascade(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["bia"] }),
  });

  const processes = data?.results ?? [];

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold text-gray-900 flex items-center">
          Rischio — Business Impact Analysis
          <ModuleHelp
            title="Business Impact Analysis — M05"
            description="Valuta l'impatto economico e operativo del fermo di ogni
    processo critico. Definisce i target RTO/RPO/MTPD che guidano
    il BCP e pesano il calcolo dell'ALE nel Risk Assessment."
            steps={[
              "Crea il processo critico con owner responsabile",
              "Inserisci costo orario fermo (€) e fatturato esposto annuo",
              "Definisci MTPD (ore massime tollerabili), RTO e RPO target",
              "Valida il processo (compliance officer)",
              "Approva (management) — da questo momento guida il Risk Assessment",
              "Il Risk Assessment userà downtime_cost per calcolare l'ALE automaticamente",
              "Definisci i trattamenti (pulsante «Trattamenti») con costo e % di riduzione ALE → alimentano il ROSI nel Reporting",
            ]}
            connections={[
              { module: "M04 Asset", relation: "Asset collegato al processo" },
              { module: "M06 Risk", relation: "ALE = downtime_cost × ore × probabilità" },
              { module: "M16 BCP", relation: "RTO/RPO BIA validano e vincolano il piano BCP" },
              { module: "M18 Reporting", relation: "ROSI = ALE evitata − costo annualizzato del trattamento" },
            ]}
            configNeeded={[
              "Creare prima i Plant (M01) e gli Asset (M04)",
            ]}
          />
        </h2>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setDrawerOpen(true)}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm font-medium"
          >
            <span>?</span> Guida alla valutazione
          </button>
          <button onClick={() => setShowNew(true)} className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700">
            + Nuovo processo
          </button>
        </div>
      </div>

      <div className="flex items-center gap-3 mb-4">
        <label className="text-sm text-gray-600">Stato:</label>
        <select value={filterStatus} onChange={e => setFilterStatus(e.target.value)} className="border rounded px-3 py-1.5 text-sm">
          <option value="">Tutti</option>
          <option value="bozza">Bozza</option>
          <option value="validato">Validato</option>
          <option value="approvato">Approvato</option>
        </select>
      </div>

      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-gray-400">Caricamento...</div>
        ) : processes.length === 0 ? (
          <div className="p-8 text-center text-gray-400">Nessun processo registrato</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Processo</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Criticità</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Stato</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">MTPD</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">RTO</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">RPO</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">MBCO</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">BCP</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {processes.map(p => (
                <tr
                  key={p.id}
                  className="hover:bg-gray-50 transition-colors cursor-pointer"
                  onClick={() => setSelectedProcessId(p.id)}
                >
                  <td className="px-4 py-3 font-medium text-gray-800">{p.name}</td>
                  <td className="px-4 py-3"><CriticalityBar value={p.criticality} /></td>
                  <td className="px-4 py-3"><StatusBadge status={p.status} /></td>
                  <td className="px-4 py-3 text-gray-600 text-xs">{p.mtpd_hours != null ? `${p.mtpd_hours}h` : "—"}</td>
                  <td className="px-4 py-3 text-gray-600 text-xs">{p.rto_target_hours != null ? `${p.rto_target_hours}h` : "—"}</td>
                  <td className="px-4 py-3 text-gray-600 text-xs">{p.rpo_target_hours != null ? `${p.rpo_target_hours}h` : "—"}</td>
                  <td className="px-4 py-3 text-gray-600 text-xs">{p.mbco_pct != null ? `${p.mbco_pct}%` : "—"}</td>
                  <td className="px-4 py-3"><RtoBcpBadge status={p.rto_bcp_status} /></td>
                  <td className="px-4 py-3" onClick={e => e.stopPropagation()}>
                    <div className="flex gap-2">
                      <button
                        onClick={() => setEditProcess(p)}
                        className="text-xs text-blue-700 border border-blue-300 rounded px-2 py-0.5 hover:bg-blue-50"
                      >
                        Modifica
                      </button>
                      <button
                        onClick={() => setSelectedProcessId(p.id)}
                        className="text-xs text-purple-700 border border-purple-300 rounded px-2 py-0.5 hover:bg-purple-50"
                      >
                        {t("bia.treatments.manage")}
                      </button>
                      {p.status === "bozza" && (
                        <button
                          onClick={() => validateMutation.mutate(p.id)}
                          disabled={validateMutation.isPending}
                          className="text-xs text-indigo-700 border border-indigo-300 rounded px-2 py-0.5 hover:bg-indigo-50 disabled:opacity-50"
                        >
                          Valida
                        </button>
                      )}
                      {p.status === "validato" && (
                        <button
                          onClick={() => approveMutation.mutate(p.id)}
                          disabled={approveMutation.isPending}
                          className="text-xs text-green-700 border border-green-300 rounded px-2 py-0.5 hover:bg-green-50 disabled:opacity-50"
                        >
                          Approva
                        </button>
                      )}
                      {(p.status === "bozza" || p.status === "validato" || p.status === "approvato") && (
                        <button
                          onClick={() => {
                            if (window.confirm("Eliminare questo processo BIA con dipendenze (pulizia prova)?")) {
                              deleteMutation.mutate(p.id);
                            }
                          }}
                          disabled={deleteMutation.isPending}
                          className="text-xs text-red-700 border border-red-300 rounded px-2 py-0.5 hover:bg-red-50 disabled:opacity-50"
                        >
                          Elimina
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {showNew && plants && <NewProcessModal plants={plants} onClose={() => setShowNew(false)} />}
      {editProcess && plants && (
        <NewProcessModal
          plants={plants}
          initial={editProcess}
          onClose={() => setEditProcess(null)}
        />
      )}
      {selectedProcessId && (() => {
        const proc = processes.find(p => p.id === selectedProcessId);
        return proc ? <TreatmentsModal process={proc} onClose={() => setSelectedProcessId(null)} /> : null;
      })()}
      <AssistenteValutazione open={drawerOpen} onClose={() => setDrawerOpen(false)} />
    </div>
  );
}
