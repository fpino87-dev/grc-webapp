import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { bcpApi, type BcpPlan, type BcpTestObjective } from "../../api/endpoints/bcp";
import { plantsApi } from "../../api/endpoints/plants";
import { biaApi } from "../../api/endpoints/bia";
import { StatusBadge } from "../../components/ui/StatusBadge";
import i18n from "../../i18n";

function NewBcpModal({ plants, onClose }: { plants: { id: string; code: string; name: string }[]; onClose: () => void }) {
  const qc = useQueryClient();
  const [form, setForm] = useState<Partial<BcpPlan>>({});
  const plantId = form.plant;

  const { data: processesData } = useQuery({
    queryKey: ["bia-processes", plantId],
    queryFn: () => biaApi.list(plantId ? { plant: plantId, page_size: "200" } : {}),
    enabled: !!plantId,
    retry: false,
  });

  const processes = processesData?.results ?? [];

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

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Processo BIA collegato *</label>
            <select
              name="critical_process"
              onChange={handleChange}
              className="w-full border rounded px-3 py-2 text-sm"
              value={form.critical_process ?? ""}
            >
              <option value="">— seleziona —</option>
              {processes.map(p => (
                <option key={p.id} value={p.id}>
                  {p.name} [criticità {p.criticality}]
                </option>
              ))}
            </select>
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
            disabled={mutation.isPending || !form.plant || !form.title || !form.critical_process}
            className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700 disabled:opacity-50"
          >
            {mutation.isPending ? "Salvataggio..." : "Crea piano"}
          </button>
        </div>
      </div>
    </div>
  );
}

const TEST_TYPE_LABELS: Record<string, string> = {
  tabletop: "Tabletop / Discussione",
  drill: "Drill / Esercitazione parziale",
  full_interruption: "Full interruption test",
  parallel: "Test parallelo",
};

function RecordTestModal({ plan, onClose }: { plan: BcpPlan; onClose: () => void }) {
  const qc = useQueryClient();
  const [testType, setTestType] = useState("tabletop");
  const [result, setResult] = useState("superato");
  const [rtoAchieved, setRtoAchieved] = useState("");
  const [rpoAchieved, setRpoAchieved] = useState("");
  const [participantsCount, setParticipantsCount] = useState("");
  const [notes, setNotes] = useState("");
  const [objectives, setObjectives] = useState<BcpTestObjective[]>([]);
  const [newObjective, setNewObjective] = useState("");
  const [warnings, setWarnings] = useState<string[]>([]);

  const mutation = useMutation({
    mutationFn: (data: Record<string, unknown>) => bcpApi.recordTest(data),
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: ["bcp"] });
      if (res.warnings?.length) {
        setWarnings(res.warnings);
      } else {
        onClose();
      }
    },
  });

  function addObjective() {
    const txt = newObjective.trim();
    if (!txt) return;
    setObjectives(prev => [...prev, { text: txt, met: false }]);
    setNewObjective("");
  }

  function toggleObjective(idx: number) {
    setObjectives(prev => prev.map((o, i) => i === idx ? { ...o, met: !o.met } : o));
  }

  function removeObjective(idx: number) {
    setObjectives(prev => prev.filter((_, i) => i !== idx));
  }

  function handleSubmit() {
    mutation.mutate({
      plan: plan.id,
      result,
      test_type: testType,
      objectives,
      rto_achieved_hours: rtoAchieved ? Number(rtoAchieved) : null,
      rpo_achieved_hours: rpoAchieved ? Number(rpoAchieved) : null,
      participants_count: participantsCount ? Number(participantsCount) : 0,
      notes,
    });
  }

  if (warnings.length > 0) {
    return (
      <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-6">
          <h3 className="text-lg font-semibold mb-3 text-orange-700">Test registrato con avvisi</h3>
          <div className="space-y-2 mb-4">
            {warnings.map((w, i) => (
              <div key={i} className="flex items-start gap-2 bg-orange-50 border border-orange-200 rounded p-3 text-sm text-orange-800">
                <span className="mt-0.5">⚠</span>
                <span>{w}</span>
              </div>
            ))}
          </div>
          <p className="text-xs text-gray-500 mb-4">
            È stato creato automaticamente un PDCA per gestire lo sforamento RTO/MTPD.
          </p>
          <div className="flex justify-end">
            <button onClick={onClose} className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700">
              Chiudi
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-lg p-6 max-h-screen overflow-y-auto">
        <h3 className="text-lg font-semibold mb-1">Registra test BCP</h3>
        <p className="text-sm text-gray-500 mb-4">{plan.title}</p>

        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Tipo test *</label>
              <select value={testType} onChange={e => setTestType(e.target.value)} className="w-full border rounded px-3 py-2 text-sm">
                {Object.entries(TEST_TYPE_LABELS).map(([v, l]) => (
                  <option key={v} value={v}>{l}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Risultato *</label>
              <select value={result} onChange={e => setResult(e.target.value)} className="w-full border rounded px-3 py-2 text-sm">
                <option value="superato">Superato</option>
                <option value="parziale">Parziale</option>
                <option value="fallito">Fallito</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">RTO raggiunto (h)</label>
              <input
                type="number" min="0" value={rtoAchieved}
                onChange={e => setRtoAchieved(e.target.value)}
                placeholder={plan.rto_hours ? `target: ${plan.rto_hours}h` : "—"}
                className="w-full border rounded px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">RPO raggiunto (h)</label>
              <input
                type="number" min="0" value={rpoAchieved}
                onChange={e => setRpoAchieved(e.target.value)}
                placeholder={plan.rpo_hours ? `target: ${plan.rpo_hours}h` : "—"}
                className="w-full border rounded px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Partecipanti</label>
              <input
                type="number" min="0" value={participantsCount}
                onChange={e => setParticipantsCount(e.target.value)}
                className="w-full border rounded px-3 py-2 text-sm"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Obiettivi del test</label>
            <div className="flex gap-2 mb-2">
              <input
                value={newObjective}
                onChange={e => setNewObjective(e.target.value)}
                onKeyDown={e => e.key === "Enter" && addObjective()}
                placeholder="Aggiungi obiettivo..."
                className="flex-1 border rounded px-3 py-1.5 text-sm"
              />
              <button
                onClick={addObjective}
                className="px-3 py-1.5 border border-gray-300 rounded text-sm text-gray-600 hover:bg-gray-50"
              >
                +
              </button>
            </div>
            {objectives.length > 0 && (
              <div className="space-y-1 max-h-32 overflow-y-auto">
                {objectives.map((o, idx) => (
                  <div key={idx} className="flex items-center gap-2 text-sm">
                    <input
                      type="checkbox"
                      checked={o.met}
                      onChange={() => toggleObjective(idx)}
                      className="rounded"
                    />
                    <span className={o.met ? "line-through text-gray-400" : "text-gray-700"}>{o.text}</span>
                    <button onClick={() => removeObjective(idx)} className="ml-auto text-red-400 hover:text-red-600 text-xs">✕</button>
                  </div>
                ))}
              </div>
            )}
            {objectives.length > 0 && (
              <p className="text-xs text-gray-500 mt-1">
                {objectives.filter(o => o.met).length}/{objectives.length} obiettivi raggiunti
              </p>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Note</label>
            <textarea
              value={notes}
              onChange={e => setNotes(e.target.value)}
              rows={2}
              className="w-full border rounded px-3 py-2 text-sm"
            />
          </div>
        </div>

        {mutation.isError && <p className="text-sm text-red-600 mt-2">Errore durante il salvataggio</p>}

        <div className="flex justify-end gap-2 mt-4">
          <button onClick={onClose} className="px-4 py-2 border rounded text-sm text-gray-600 hover:bg-gray-50">Annulla</button>
          <button
            onClick={handleSubmit}
            disabled={mutation.isPending}
            className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700 disabled:opacity-50"
          >
            {mutation.isPending ? "Salvataggio..." : "Registra test"}
          </button>
        </div>
      </div>
    </div>
  );
}

export function BcpPage() {
  const [showNew, setShowNew] = useState(false);
  const [testPlan, setTestPlan] = useState<BcpPlan | null>(null);
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

  const deleteMutation = useMutation({
    mutationFn: (id: string) => bcpApi.delete(id),
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
                  <td className="px-4 py-3 text-gray-500 text-xs">{plan.last_test_date ? new Date(plan.last_test_date).toLocaleDateString(i18n.language || "it") : "—"}</td>
                  <td className="px-4 py-3 text-gray-500 text-xs">{plan.next_test_date ? new Date(plan.next_test_date).toLocaleDateString(i18n.language || "it") : "—"}</td>
                  <td className="px-4 py-3">
                    <div className="flex gap-1">
                      {plan.status === "bozza" && (
                        <button
                          onClick={() => approveMutation.mutate(plan.id)}
                          disabled={approveMutation.isPending}
                          className="text-xs text-green-700 border border-green-300 rounded px-2 py-0.5 hover:bg-green-50 disabled:opacity-50"
                        >
                          Approva
                        </button>
                      )}
                      <button
                        onClick={() => setTestPlan(plan)}
                        disabled={plan.status === "approvato"}
                        className="text-xs text-blue-700 border border-blue-300 rounded px-2 py-0.5 hover:bg-blue-50 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        {plan.status === "approvato" ? "Test bloccato" : "+ Test"}
                      </button>
                      <button
                        onClick={() => {
                          if (window.confirm("Eliminare questo piano BCP (con i test)?")) {
                            deleteMutation.mutate(plan.id);
                          }
                        }}
                        disabled={deleteMutation.isPending}
                        className="text-xs text-red-700 border border-red-300 rounded px-2 py-0.5 hover:bg-red-50 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        Elimina
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {showNew && plants && <NewBcpModal plants={plants} onClose={() => setShowNew(false)} />}
      {testPlan && <RecordTestModal plan={testPlan} onClose={() => setTestPlan(null)} />}
    </div>
  );
}
