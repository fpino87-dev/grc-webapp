import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { pdcaApi, type PdcaCycle } from "../../api/endpoints/pdca";
import { plantsApi } from "../../api/endpoints/plants";
import { StatusBadge } from "../../components/ui/StatusBadge";

function NewCycleModal({ plants, onClose }: { plants: { id: string; code: string; name: string }[]; onClose: () => void }) {
  const qc = useQueryClient();
  const [form, setForm] = useState<Partial<PdcaCycle>>({ trigger_type: "incident", scope_type: "plant" });
  const [error, setError] = useState("");

  const mutation = useMutation({
    mutationFn: pdcaApi.create,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["pdca"] }); onClose(); },
    onError: (e: any) => setError(e?.response?.data?.detail || "Errore durante il salvataggio"),
  });

  function handleChange(e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) {
    setForm(prev => ({ ...prev, [e.target.name]: e.target.value }));
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-6">
        <h3 className="text-lg font-semibold mb-4">Nuovo ciclo PDCA</h3>
        <div className="space-y-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Sito *</label>
            <select name="plant" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm">
              <option value="">— seleziona —</option>
              {plants.map(p => <option key={p.id} value={p.id}>{p.code} — {p.name}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Titolo *</label>
            <input name="title" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" placeholder="es. Miglioramento gestione incidenti" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Tipo trigger</label>
              <select name="trigger_type" defaultValue="incident" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm">
                <option value="incident">Incidente</option>
                <option value="audit">Audit</option>
                <option value="management_review">Revisione direzione</option>
                <option value="risk">Rischio</option>
                <option value="manual">Manuale</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Ambito</label>
              <select name="scope_type" defaultValue="plant" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm">
                <option value="plant">Sito</option>
                <option value="org">Organizzazione</option>
                <option value="process">Processo</option>
              </select>
            </div>
          </div>
        </div>
        {error && <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded mt-3">{error}</p>}
        <div className="flex justify-end gap-2 mt-4">
          <button onClick={onClose} className="px-4 py-2 border rounded text-sm text-gray-600 hover:bg-gray-50">Annulla</button>
          <button
            onClick={() => mutation.mutate(form)}
            disabled={mutation.isPending || !form.plant || !form.title}
            className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700 disabled:opacity-50"
          >
            {mutation.isPending ? "Salvataggio..." : "Crea ciclo"}
          </button>
        </div>
      </div>
    </div>
  );
}

export function PdcaPage() {
  const [showNew, setShowNew] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ["pdca"],
    queryFn: () => pdcaApi.list(),
    retry: false,
  });

  const { data: plants } = useQuery({
    queryKey: ["plants"],
    queryFn: () => plantsApi.list(),
    retry: false,
  });

  const cycles = data?.results ?? [];

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold text-gray-900">PDCA — Miglioramento continuo</h2>
        <button onClick={() => setShowNew(true)} className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700">
          + Nuovo ciclo
        </button>
      </div>

      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-gray-400">Caricamento...</div>
        ) : cycles.length === 0 ? (
          <div className="p-8 text-center">
            <p className="text-gray-400 mb-2">Nessun ciclo PDCA registrato</p>
            <button onClick={() => setShowNew(true)} className="text-sm text-primary-600 hover:underline">Crea il primo ciclo →</button>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Titolo</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Trigger</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Ambito</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Fase corrente</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Creato il</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {cycles.map(c => (
                <tr key={c.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3 font-medium text-gray-800">{c.title}</td>
                  <td className="px-4 py-3 text-gray-600 text-xs uppercase">{c.trigger_type}</td>
                  <td className="px-4 py-3 text-gray-600 text-xs">{c.scope_type}</td>
                  <td className="px-4 py-3"><StatusBadge status={c.fase_corrente || "plan"} /></td>
                  <td className="px-4 py-3 text-gray-500 text-xs">{new Date(c.created_at).toLocaleDateString("it-IT")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {showNew && plants && <NewCycleModal plants={plants} onClose={() => setShowNew(false)} />}
    </div>
  );
}
