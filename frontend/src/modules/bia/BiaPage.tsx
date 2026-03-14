import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { biaApi, type CriticalProcess } from "../../api/endpoints/bia";
import { plantsApi } from "../../api/endpoints/plants";
import { StatusBadge } from "../../components/ui/StatusBadge";

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

function NewProcessModal({ plants, onClose }: { plants: { id: string; code: string; name: string }[]; onClose: () => void }) {
  const qc = useQueryClient();
  const [form, setForm] = useState<Partial<CriticalProcess>>({ criticality: 3 });

  const mutation = useMutation({
    mutationFn: biaApi.create,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["bia"] }); onClose(); },
  });

  function handleChange(e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) {
    const val = e.target.name === "criticality" ? Number(e.target.value) : e.target.value;
    setForm(prev => ({ ...prev, [e.target.name]: val }));
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-lg p-6">
        <h3 className="text-lg font-semibold mb-4">Nuovo processo critico</h3>
        <div className="space-y-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Sito *</label>
            <select name="plant" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm">
              <option value="">— seleziona —</option>
              {plants.map(p => <option key={p.id} value={p.id}>{p.code} — {p.name}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Nome processo *</label>
            <input name="name" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Criticità (1-5)</label>
              <select name="criticality" defaultValue="3" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm">
                {[1,2,3,4,5].map(n => <option key={n} value={n}>{n}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Costo downtime/h (€)</label>
              <input name="downtime_cost_hour" type="number" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" placeholder="0.00" />
            </div>
          </div>
        </div>
        {mutation.isError && <p className="text-sm text-red-600 mt-2">Errore durante il salvataggio</p>}
        <div className="flex justify-end gap-2 mt-4">
          <button onClick={onClose} className="px-4 py-2 border rounded text-sm text-gray-600 hover:bg-gray-50">Annulla</button>
          <button
            onClick={() => mutation.mutate(form)}
            disabled={mutation.isPending}
            className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700 disabled:opacity-50"
          >
            {mutation.isPending ? "Salvataggio..." : "Crea processo"}
          </button>
        </div>
      </div>
    </div>
  );
}

export function BiaPage() {
  const [showNew, setShowNew] = useState(false);
  const [filterStatus, setFilterStatus] = useState("");
  const qc = useQueryClient();

  const params = filterStatus ? { status: filterStatus } : undefined;

  const { data, isLoading } = useQuery({
    queryKey: ["bia", filterStatus],
    queryFn: () => biaApi.list(params),
    retry: false,
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

  const processes = data?.results ?? [];

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold text-gray-900">Rischio — Business Impact Analysis</h2>
        <button onClick={() => setShowNew(true)} className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700">
          + Nuovo processo
        </button>
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
                <th className="text-left px-4 py-3 font-medium text-gray-600">Costo downtime/h</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Rep</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Norm</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Op</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {processes.map(p => (
                <tr key={p.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3 font-medium text-gray-800">{p.name}</td>
                  <td className="px-4 py-3"><CriticalityBar value={p.criticality} /></td>
                  <td className="px-4 py-3"><StatusBadge status={p.status} /></td>
                  <td className="px-4 py-3 text-gray-600">{p.downtime_cost_hour ? `€${Number(p.downtime_cost_hour).toLocaleString("it-IT")}` : "—"}</td>
                  <td className="px-4 py-3 text-gray-600">{p.danno_reputazionale}</td>
                  <td className="px-4 py-3 text-gray-600">{p.danno_normativo}</td>
                  <td className="px-4 py-3 text-gray-600">{p.danno_operativo}</td>
                  <td className="px-4 py-3">
                    {p.status === "validato" && (
                      <button
                        onClick={() => approveMutation.mutate(p.id)}
                        disabled={approveMutation.isPending}
                        className="text-xs text-green-700 border border-green-300 rounded px-2 py-0.5 hover:bg-green-50 disabled:opacity-50"
                      >
                        Approva
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {showNew && plants && <NewProcessModal plants={plants} onClose={() => setShowNew(false)} />}
    </div>
  );
}
