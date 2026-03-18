import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { biaApi, type CriticalProcess } from "../../api/endpoints/bia";
import { plantsApi } from "../../api/endpoints/plants";
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
const RTO_STATUS_LABELS: Record<string, string> = {
  ok: "RTO OK",
  warning: "RTO ⚠",
  critical: "RTO ✗",
  unknown: "—",
};

function RtoBcpBadge({ status }: { status: string }) {
  return (
    <span className={`text-xs px-2 py-0.5 rounded font-medium ${RTO_STATUS_COLORS[status] ?? RTO_STATUS_COLORS.unknown}`}>
      {RTO_STATUS_LABELS[status] ?? "—"}
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
        <h3 className="text-lg font-semibold mb-4">Nuovo processo critico</h3>
        <div className="space-y-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Sito *</label>
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
            <label className="block text-sm font-medium text-gray-700 mb-1">Nome processo *</label>
            <input
              name="name"
              value={(form.name as string) ?? ""}
              onChange={handleChange}
              className="w-full border rounded px-3 py-2 text-sm"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Criticità (1-5)</label>
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
              <label className="block text-sm font-medium text-gray-700 mb-1">Costo downtime/h (€)</label>
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
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Target BCP/BIA (ISO 22301)</p>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">MTPD (ore)</label>
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
              <label className="block text-sm font-medium text-gray-700 mb-1">MBCO (%)</label>
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
              <label className="block text-sm font-medium text-gray-700 mb-1">RTO target (ore)</label>
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
              <label className="block text-sm font-medium text-gray-700 mb-1">RPO target (ore)</label>
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
        {mutation.isError && <p className="text-sm text-red-600 mt-2">Errore durante il salvataggio</p>}
        <div className="flex justify-end gap-2 mt-4">
          <button onClick={onClose} className="px-4 py-2 border rounded text-sm text-gray-600 hover:bg-gray-50">Annulla</button>
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
            {mutation.isPending ? "Salvataggio..." : initial ? "Salva modifiche" : "Crea processo"}
          </button>
        </div>
      </div>
    </div>
  );
}

export function BiaPage() {
  const [showNew, setShowNew] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [filterStatus, setFilterStatus] = useState("");
  const [selectedProcessId, setSelectedProcessId] = useState<string | null>(null);
  const [editProcess, setEditProcess] = useState<CriticalProcess | null>(null);
  const qc = useQueryClient();

  const params = filterStatus ? { status: filterStatus } : undefined;

  const { data, isLoading } = useQuery({
    queryKey: ["bia", filterStatus],
    queryFn: () => biaApi.list(params),
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
            ]}
            connections={[
              { module: "M04 Asset", relation: "Asset collegato al processo" },
              { module: "M06 Risk", relation: "ALE = downtime_cost × ore × probabilità" },
              { module: "M16 BCP", relation: "RTO/RPO BIA validano e vincolano il piano BCP" },
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
      <AssistenteValutazione open={drawerOpen} onClose={() => setDrawerOpen(false)} />
    </div>
  );
}
