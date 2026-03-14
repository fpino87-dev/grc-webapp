import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { bcpApi, type BcpPlan } from "../../api/endpoints/bcp";
import { plantsApi } from "../../api/endpoints/plants";
import { StatusBadge } from "../../components/ui/StatusBadge";

function NewBcpModal({ plants, onClose }: { plants: { id: string; code: string; name: string }[]; onClose: () => void }) {
  const qc = useQueryClient();
  const [form, setForm] = useState<Partial<BcpPlan>>({});

  const mutation = useMutation({
    mutationFn: bcpApi.create,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["bcp"] }); onClose(); },
  });

  function handleChange(e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) {
    const val = ["rto_hours", "rpo_hours"].includes(e.target.name) ? (e.target.value ? Number(e.target.value) : null) : e.target.value;
    setForm(prev => ({ ...prev, [e.target.name]: val }));
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-lg p-6">
        <h3 className="text-lg font-semibold mb-4">Nuovo piano BCP</h3>
        <div className="space-y-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Titolo *</label>
            <input name="title" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Sito *</label>
              <select name="plant" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm">
                <option value="">— seleziona —</option>
                {plants.map(p => <option key={p.id} value={p.id}>{p.code} — {p.name}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Versione</label>
              <input name="version" onChange={handleChange} placeholder="1.0" className="w-full border rounded px-3 py-2 text-sm" />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">RTO (ore)</label>
              <input name="rto_hours" type="number" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">RPO (ore)</label>
              <input name="rpo_hours" type="number" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" />
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
            {mutation.isPending ? "Salvataggio..." : "Crea piano"}
          </button>
        </div>
      </div>
    </div>
  );
}

export function BcpPage() {
  const [showNew, setShowNew] = useState(false);
  const qc = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ["bcp"],
    queryFn: () => bcpApi.list(),
    retry: false,
  });

  const { data: plants } = useQuery({
    queryKey: ["plants"],
    queryFn: () => plantsApi.list(),
    retry: false,
  });

  const approveMutation = useMutation({
    mutationFn: bcpApi.approve,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["bcp"] }),
  });

  const plans = data?.results ?? [];

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold text-gray-900">Rischio — Business Continuity Plan</h2>
        <button onClick={() => setShowNew(true)} className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700">
          + Nuovo piano
        </button>
      </div>

      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-gray-400">Caricamento...</div>
        ) : plans.length === 0 ? (
          <div className="p-8 text-center text-gray-400">Nessun piano BCP registrato</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Titolo</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Sito</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Versione</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Stato</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">RTO (h)</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">RPO (h)</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Ultimo test</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Prossimo test</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {plans.map(plan => (
                <tr key={plan.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3 font-medium text-gray-800">{plan.title}</td>
                  <td className="px-4 py-3 text-gray-600">{plan.plant}</td>
                  <td className="px-4 py-3 text-gray-600">{plan.version}</td>
                  <td className="px-4 py-3"><StatusBadge status={plan.status} /></td>
                  <td className="px-4 py-3 text-gray-600">{plan.rto_hours ?? "—"}</td>
                  <td className="px-4 py-3 text-gray-600">{plan.rpo_hours ?? "—"}</td>
                  <td className="px-4 py-3 text-gray-500 text-xs">{plan.last_test_date ? new Date(plan.last_test_date).toLocaleDateString("it-IT") : "—"}</td>
                  <td className="px-4 py-3 text-gray-500 text-xs">{plan.next_test_date ? new Date(plan.next_test_date).toLocaleDateString("it-IT") : "—"}</td>
                  <td className="px-4 py-3">
                    {plan.status === "bozza" && (
                      <button
                        onClick={() => approveMutation.mutate(plan.id)}
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

      {showNew && plants && <NewBcpModal plants={plants} onClose={() => setShowNew(false)} />}
    </div>
  );
}
