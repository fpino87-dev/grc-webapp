import { useState, Fragment } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { pdcaApi, type PdcaCycle } from "../../api/endpoints/pdca";
import { plantsApi } from "../../api/endpoints/plants";
import { StatusBadge } from "../../components/ui/StatusBadge";
import { apiClient } from "../../api/client";

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

type Evidence = { id: string; title: string };

function PhaseStepper({ cycle }: { cycle: PdcaCycle & { reopened_as?: string | null } }) {
  const phases = ["plan", "do", "check", "act"] as const;
  const labels: Record<(typeof phases)[number], string> = {
    plan: "PLAN",
    do: "DO",
    check: "CHECK",
    act: "ACT",
  };
  const currentIndex = phases.indexOf((cycle.fase_corrente || "plan") as any);

  if (cycle.fase_corrente === "chiuso") {
    return (
      <div className="flex items-center gap-2 text-xs">
        {phases.map((p) => (
          <span key={p} className="px-2 py-0.5 rounded-full bg-gray-100 text-gray-500">
            {labels[p]}
          </span>
        ))}
        <span className="ml-2 inline-flex items-center px-2 py-0.5 rounded-full bg-gray-800 text-white text-[10px] font-semibold">
          CHIUSO
        </span>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-2 text-xs">
      {phases.map((p, idx) => {
        const isDone = idx < currentIndex;
        const isCurrent = idx === currentIndex;
        return (
          <Fragment key={p}>
            <span
              className={`px-2 py-0.5 rounded-full border text-[11px] font-medium ${
                isCurrent
                  ? "bg-primary-600 text-white border-primary-600"
                  : isDone
                  ? "bg-green-100 text-green-800 border-green-200"
                  : "bg-gray-50 text-gray-500 border-gray-200"
              }`}
            >
              {isDone ? "✓ " : ""}
              {labels[p]}
            </span>
            {idx < phases.length - 1 && <span className="text-gray-400 text-[10px]">→</span>}
          </Fragment>
        );
      })}
    </div>
  );
}

function AdvanceButtons({
  cycle,
  onUpdated,
}: {
  cycle: PdcaCycle & { reopened_as?: string | null };
  onUpdated: () => void;
}) {
  const qc = useQueryClient();
  const [open, setOpen] = useState<"plan" | "do" | "check" | "act" | null>(null);
  const [notes, setNotes] = useState("");
  const [outcome, setOutcome] = useState<"" | "ok" | "partial" | "ko">("");
  const [evidenceId, setEvidenceId] = useState("");
  const [error, setError] = useState("");
  const { data: evidences } = useQuery<Evidence[]>({
    queryKey: ["pdca-evidences", cycle.plant],
    enabled: open === "do",
    queryFn: async () => {
      const res = await apiClient.get("/documents/evidences/", {
        params: { plant: cycle.plant },
      });
      return res.data.results || res.data;
    },
  });

  const advanceMutation = useMutation({
    mutationFn: async () => {
      const payload: any = { notes };
      if (open === "do") payload.evidence_id = evidenceId || undefined;
      if (open === "check") payload.outcome = outcome;
      const res = await apiClient.post(`/pdca/${cycle.id}/advance/`, payload);
      return res.data;
    },
    onSuccess: () => {
      setOpen(null);
      setNotes("");
      setOutcome("");
      setEvidenceId("");
      setError("");
      qc.invalidateQueries({ queryKey: ["pdca"] });
      onUpdated();
    },
    onError: (e: any) => {
      const msg = e?.response?.data?.error || "Errore durante l'avanzamento di fase.";
      setError(String(msg));
    },
  });

  const closeMutation = useMutation({
    mutationFn: async () => {
      const res = await apiClient.post(`/pdca/${cycle.id}/close/`, {
        act_description: notes,
      });
      return res.data;
    },
    onSuccess: () => {
      setOpen(null);
      setNotes("");
      setError("");
      qc.invalidateQueries({ queryKey: ["pdca"] });
      onUpdated();
    },
    onError: (e: any) => {
      const msg = e?.response?.data?.error || "Errore durante la chiusura del ciclo.";
      setError(String(msg));
    },
  });

  const fase = cycle.fase_corrente;

  function renderModal() {
    if (!open) return null;
    const titleMap: Record<string, string> = {
      plan: "Avanza a DO",
      do: "Avanza a CHECK",
      check: "Avanza ad ACT",
      act: "Chiudi ciclo",
    };
    return (
      <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg shadow-xl w-full max-w-lg p-6">
          <h3 className="text-lg font-semibold mb-4">{titleMap[open]}</h3>
          <div className="space-y-4">
            {open === "plan" && (
              <>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Descrivi l&apos;azione pianificata *
                </label>
                <textarea
                  className="w-full border rounded px-3 py-2 text-sm min-h-[100px]"
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="Minimo 20 caratteri..."
                />
              </>
            )}
            {open === "do" && (
              <>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Note implementazione (opzionale)
                </label>
                <textarea
                  className="w-full border rounded px-3 py-2 text-sm min-h-[80px]"
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                />
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Allega evidenza implementazione *
                  </label>
                  <select
                    className="w-full border rounded px-3 py-2 text-sm"
                    value={evidenceId}
                    onChange={(e) => setEvidenceId(e.target.value)}
                  >
                    <option value="">— seleziona evidenza —</option>
                    {(evidences || []).map((ev) => (
                      <option key={ev.id} value={ev.id}>
                        {ev.title}
                      </option>
                    ))}
                  </select>
                </div>
              </>
            )}
            {open === "check" && (
              <>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Descrivi il risultato della verifica *
                </label>
                <textarea
                  className="w-full border rounded px-3 py-2 text-sm min-h-[80px]"
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="Minimo 10 caratteri..."
                />
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Esito verifica *
                  </label>
                  <select
                    className="w-full border rounded px-3 py-2 text-sm"
                    value={outcome}
                    onChange={(e) => setOutcome(e.target.value as any)}
                  >
                    <option value="">— seleziona esito —</option>
                    <option value="ok">✅ Efficace</option>
                    <option value="partial">🟡 Parzialmente efficace</option>
                    <option value="ko">❌ Non efficace — aprirà nuovo ciclo</option>
                  </select>
                </div>
                {outcome === "ko" && (
                  <p className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded px-3 py-2">
                    ⚠️ Selezionando &quot;Non efficace&quot; verrà aperto automaticamente un nuovo ciclo PLAN.
                  </p>
                )}
              </>
            )}
            {open === "act" && (
              <>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Descrivi l&apos;azione standardizzata *
                </label>
                <textarea
                  className="w-full border rounded px-3 py-2 text-sm min-h-[100px]"
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="Es: La procedura X è stata aggiornata e comunicata a tutti i responsabili..."
                />
              </>
            )}
            {error && <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded">{error}</p>}
          </div>
          <div className="flex justify-end gap-2 mt-4">
            <button
              type="button"
              onClick={() => {
                setOpen(null);
                setError("");
              }}
              className="px-4 py-2 border rounded text-sm text-gray-600 hover:bg-gray-50"
            >
              Annulla
            </button>
            {open === "act" ? (
              <button
                type="button"
                onClick={() => closeMutation.mutate()}
                disabled={closeMutation.isPending}
                className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700 disabled:opacity-50"
              >
                {closeMutation.isPending ? "Chiusura..." : "Chiudi ciclo"}
              </button>
            ) : (
              <button
                type="button"
                onClick={() => advanceMutation.mutate()}
                disabled={advanceMutation.isPending}
                className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700 disabled:opacity-50"
              >
                {advanceMutation.isPending ? "Avanzamento..." : "Conferma"}
              </button>
            )}
          </div>
        </div>
      </div>
    );
  }

  if (fase === "chiuso") {
    return (
      <>
        <p className="text-xs text-gray-500">
          Chiuso il {new Date(cycle.closed_at || cycle.updated_at).toLocaleDateString("it-IT")}
        </p>
        {cycle.act_description && (
          <p className="mt-1 text-xs text-gray-700 whitespace-pre-wrap">{cycle.act_description}</p>
        )}
      </>
    );
  }

  let buttonLabel = "";
  if (fase === "plan") buttonLabel = "Avanza a DO →";
  else if (fase === "do") buttonLabel = "Avanza a CHECK →";
  else if (fase === "check") buttonLabel = "Avanza ad ACT →";
  else if (fase === "act") buttonLabel = "Chiudi ciclo ✓";

  const onClick = () => {
    if (fase === "plan" || fase === "do" || fase === "check" || fase === "act") {
      setOpen(fase as any);
    }
  };

  return (
    <>
      <button
        type="button"
        onClick={onClick}
        className="px-3 py-1.5 text-xs rounded-md bg-primary-50 text-primary-700 hover:bg-primary-100"
      >
        {buttonLabel}
      </button>
      {cycle.reopened_as && (
        <div className="mt-2 text-[11px] text-blue-700 bg-blue-50 border border-blue-200 rounded px-2 py-1">
          ⟳ Questo ciclo ha generato un nuovo ciclo PLAN per esito CHECK non efficace.
        </div>
      )}
      {renderModal()}
    </>
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
                <th className="text-left px-4 py-3 font-medium text-gray-600">Fasi</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Azione</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Creato il</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {cycles.map((c) => (
                <tr key={c.id} className="hover:bg-gray-50 transition-colors align-top">
                  <td className="px-4 py-3 font-medium text-gray-800">
                    {c.title}
                    {c.reopened_as && (
                      <div className="mt-1 text-[11px] text-blue-700 bg-blue-50 border border-blue-200 rounded px-2 py-1 inline-block">
                        ⟳ Riciclo aperto per CHECK non efficace
                      </div>
                    )}
                  </td>
                  <td className="px-4 py-3 text-gray-600 text-xs uppercase">{c.trigger_type}</td>
                  <td className="px-4 py-3 text-gray-600 text-xs">{c.scope_type}</td>
                  <td className="px-4 py-3">
                    <PhaseStepper cycle={c as any} />
                  </td>
                  <td className="px-4 py-3">
                    <AdvanceButtons cycle={c as any} onUpdated={() => {}} />
                  </td>
                  <td className="px-4 py-3 text-gray-500 text-xs">
                    {new Date(c.created_at).toLocaleDateString("it-IT")}
                  </td>
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
