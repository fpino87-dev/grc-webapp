import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { riskApi, type RiskAssessment, type RiskMitigationPlan, THREAT_CATEGORIES, PROB_LABELS, IMPACT_LABELS } from "../../api/endpoints/risk";
import { plantsApi } from "../../api/endpoints/plants";
import { useAuthStore } from "../../store/auth";
import { StatusBadge } from "../../components/ui/StatusBadge";

// ── Risk matrix cell colour ──────────────────────────────────────────────────
function matrixColor(p: number, i: number): string {
  const s = p * i;
  if (s <= 4) return "bg-green-100 text-green-800";
  if (s <= 9) return "bg-yellow-100 text-yellow-800";
  if (s <= 14) return "bg-orange-100 text-orange-800";
  return "bg-red-100 text-red-800";
}

function RiskLevelBadge({ score }: { score: number | null }) {
  if (score === null) return <span className="text-gray-400 text-xs">—</span>;
  const cls = score > 14 ? "bg-red-100 text-red-800" : score > 7 ? "bg-orange-100 text-orange-800" : score > 4 ? "bg-yellow-100 text-yellow-800" : "bg-green-100 text-green-800";
  const label = score > 14 ? "Critico" : score > 7 ? "Alto" : score > 4 ? "Medio" : "Basso";
  return <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium ${cls}`}>{score} — {label}</span>;
}

function formatAle(ale: string | null) {
  if (!ale) return "—";
  const n = parseFloat(ale);
  return isNaN(n) ? ale : new Intl.NumberFormat("it-IT", { style: "currency", currency: "EUR" }).format(n);
}

// ── P×I selector ─────────────────────────────────────────────────────────────
function ProbImpactSelector({
  probability, impact, onChange,
}: {
  probability: number | null; impact: number | null;
  onChange: (field: "probability" | "impact", value: number) => void;
}) {
  return (
    <div className="grid grid-cols-2 gap-4">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Probabilità *</label>
        <div className="space-y-1">
          {[1,2,3,4,5].map(v => (
            <label key={v} className={`flex items-center gap-2 px-3 py-1.5 rounded cursor-pointer border text-sm transition-colors ${probability === v ? "border-primary-500 bg-primary-50 font-medium" : "border-gray-200 hover:border-gray-300"}`}>
              <input type="radio" name="probability" value={v} checked={probability === v} onChange={() => onChange("probability", v)} className="accent-primary-600" />
              {PROB_LABELS[v]}
            </label>
          ))}
        </div>
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Impatto *</label>
        <div className="space-y-1">
          {[1,2,3,4,5].map(v => (
            <label key={v} className={`flex items-center gap-2 px-3 py-1.5 rounded cursor-pointer border text-sm transition-colors ${impact === v ? "border-primary-500 bg-primary-50 font-medium" : "border-gray-200 hover:border-gray-300"}`}>
              <input type="radio" name="impact" value={v} checked={impact === v} onChange={() => onChange("impact", v)} className="accent-primary-600" />
              {IMPACT_LABELS[v]}
            </label>
          ))}
        </div>
      </div>
      {probability && impact && (
        <div className="col-span-2">
          <div className={`rounded px-3 py-2 text-center text-sm font-semibold ${matrixColor(probability, impact)}`}>
            Score: {probability} × {impact} = {probability * impact}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Mitigation plans panel ────────────────────────────────────────────────────
function MitigationPanel({ assessmentId }: { assessmentId: string }) {
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<Partial<RiskMitigationPlan>>({});

  const { data: plans = [] } = useQuery({
    queryKey: ["mitigation-plans", assessmentId],
    queryFn: () => riskApi.mitigationPlans(assessmentId),
  });

  const createMutation = useMutation({
    mutationFn: () => riskApi.createPlan({ ...form, assessment: assessmentId }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["mitigation-plans", assessmentId] }); setShowForm(false); setForm({}); },
  });

  const completeMutation = useMutation({
    mutationFn: (id: string) => riskApi.completePlan(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["mitigation-plans", assessmentId] }),
  });

  return (
    <div className="px-6 py-4 bg-gray-50 border-t border-gray-200">
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-sm font-semibold text-gray-700">Piani di mitigazione ({plans.length})</h4>
        <button onClick={() => setShowForm(s => !s)} className="text-xs px-2 py-1 bg-primary-600 text-white rounded hover:bg-primary-700">
          + Aggiungi piano
        </button>
      </div>

      {showForm && (
        <div className="bg-white border border-gray-200 rounded p-3 mb-3 space-y-2">
          <textarea
            placeholder="Descrizione azione *"
            value={form.action ?? ""}
            onChange={e => setForm(p => ({ ...p, action: e.target.value }))}
            className="w-full border rounded px-2 py-1.5 text-sm" rows={2}
          />
          <div className="flex gap-2">
            <input type="date" placeholder="Scadenza *" value={form.due_date ?? ""}
              onChange={e => setForm(p => ({ ...p, due_date: e.target.value }))}
              className="border rounded px-2 py-1.5 text-sm flex-1" />
            <button onClick={() => createMutation.mutate()} disabled={createMutation.isPending || !form.action || !form.due_date}
              className="px-3 py-1.5 bg-primary-600 text-white text-xs rounded hover:bg-primary-700 disabled:opacity-50">Salva</button>
            <button onClick={() => setShowForm(false)} className="px-3 py-1.5 border rounded text-xs text-gray-600 hover:bg-gray-50">Annulla</button>
          </div>
        </div>
      )}

      {plans.length === 0 ? (
        <p className="text-xs text-gray-400">Nessun piano di mitigazione registrato</p>
      ) : (
        <div className="space-y-2">
          {plans.map(plan => (
            <div key={plan.id} className="flex items-center gap-3 bg-white rounded border border-gray-200 px-3 py-2 text-sm">
              <span className={`w-2 h-2 rounded-full shrink-0 ${plan.completed_at ? "bg-green-500" : "bg-orange-400"}`} />
              <span className="flex-1 text-gray-700">{plan.action}</span>
              <span className="text-xs text-gray-400 shrink-0">scad. {new Date(plan.due_date).toLocaleDateString("it-IT")}</span>
              {!plan.completed_at ? (
                <button onClick={() => completeMutation.mutate(plan.id)} className="text-xs text-green-700 hover:underline shrink-0">Completa</button>
              ) : (
                <span className="text-xs text-green-600 shrink-0">✓ Completato</span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── New assessment modal ──────────────────────────────────────────────────────
function NewAssessmentModal({ plants, onClose }: { plants: { id: string; code: string; name: string }[]; onClose: () => void }) {
  const qc = useQueryClient();
  const [form, setForm] = useState<Partial<RiskAssessment>>({ assessment_type: "IT", probability: null, impact: null });
  const [error, setError] = useState("");

  const mutation = useMutation({
    mutationFn: () => riskApi.create(form),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["risk-assessments"] }); onClose(); },
    onError: (e: any) => setError(e?.response?.data?.detail || JSON.stringify(e?.response?.data) || "Errore"),
  });

  function set(field: string, value: unknown) { setForm(f => ({ ...f, [field]: value })); }

  const canSave = !!form.plant && !!form.name && !!form.probability && !!form.impact;

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl flex flex-col max-h-[92vh]">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100 shrink-0">
          <h3 className="text-lg font-semibold">Nuovo scenario di rischio</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-2xl w-8 h-8 flex items-center justify-center rounded hover:bg-gray-100">×</button>
        </div>

        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
          {/* Scenario */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Nome scenario / rischio *</label>
            <input value={form.name ?? ""} onChange={e => set("name", e.target.value)}
              placeholder="es. Ransomware su server di produzione MES"
              className="w-full border rounded px-3 py-2 text-sm" />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Sito *</label>
              <select value={form.plant ?? ""} onChange={e => set("plant", e.target.value)} className="w-full border rounded px-3 py-2 text-sm">
                <option value="">— seleziona —</option>
                {plants.map(p => <option key={p.id} value={p.id}>{p.code} — {p.name}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Categoria minaccia</label>
              <select value={form.threat_category ?? ""} onChange={e => set("threat_category", e.target.value)} className="w-full border rounded px-3 py-2 text-sm">
                <option value="">— seleziona —</option>
                {THREAT_CATEGORIES.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Tipo asset</label>
              <div className="flex gap-4 mt-1">
                {(["IT", "OT"] as const).map(t => (
                  <label key={t} className="flex items-center gap-2 cursor-pointer">
                    <input type="radio" name="assessment_type" value={t} checked={form.assessment_type === t} onChange={() => set("assessment_type", t)} className="accent-primary-600" />
                    <span className="text-sm font-medium">{t}</span>
                  </label>
                ))}
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Trattamento previsto</label>
              <select value={form.treatment ?? ""} onChange={e => set("treatment", e.target.value)} className="w-full border rounded px-3 py-2 text-sm">
                <option value="">— seleziona —</option>
                <option value="mitigare">Mitigare</option>
                <option value="accettare">Accettare</option>
                <option value="trasferire">Trasferire (es. assicurazione)</option>
                <option value="evitare">Evitare</option>
              </select>
            </div>
          </div>

          {/* P × I */}
          <div className="border border-gray-200 rounded-lg p-4">
            <p className="text-sm font-medium text-gray-700 mb-3">Valutazione del rischio (P × I)</p>
            <ProbImpactSelector
              probability={form.probability ?? null}
              impact={form.impact ?? null}
              onChange={(field, value) => set(field, value)}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">ALE annuo stimato (€)</label>
            <input type="number" min="0" step="1000" value={form.ale_annuo ?? ""} onChange={e => set("ale_annuo", e.target.value || null)}
              placeholder="Perdita attesa annua — opzionale"
              className="w-full border rounded px-3 py-2 text-sm" />
          </div>
        </div>

        {error && <p className="text-sm text-red-600 bg-red-50 px-6 py-2">{error}</p>}
        <div className="flex justify-end gap-2 px-6 py-4 border-t border-gray-100 shrink-0">
          <button onClick={onClose} className="px-4 py-2 border rounded text-sm text-gray-600 hover:bg-gray-50">Annulla</button>
          <button onClick={() => mutation.mutate()} disabled={mutation.isPending || !canSave}
            className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700 disabled:opacity-50">
            {mutation.isPending ? "Salvataggio..." : "Crea scenario"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────
export function RiskPage() {
  const [typeFilter, setTypeFilter] = useState<"" | "IT" | "OT">("");
  const [statusFilter, setStatusFilter] = useState("");
  const [showNew, setShowNew] = useState(false);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const selectedPlant = useAuthStore(s => s.selectedPlant);
  const qc = useQueryClient();

  const params: Record<string, string> = { page_size: "200" };
  if (typeFilter) params.assessment_type = typeFilter;
  if (statusFilter) params.status = statusFilter;
  if (selectedPlant?.id) params.plant = selectedPlant.id;

  const { data, isLoading } = useQuery({
    queryKey: ["risk-assessments", typeFilter, statusFilter, selectedPlant?.id],
    queryFn: () => riskApi.list(params),
    retry: false,
  });

  const { data: plants } = useQuery({ queryKey: ["plants"], queryFn: () => plantsApi.list(), retry: false });

  const completeMutation = useMutation({
    mutationFn: (id: string) => riskApi.complete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["risk-assessments"] }),
  });

  const acceptMutation = useMutation({
    mutationFn: (id: string) => riskApi.accept(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["risk-assessments"] }),
  });

  const assessments: RiskAssessment[] = data?.results ?? [];

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold text-gray-900">Risk Assessment</h2>
        <button onClick={() => setShowNew(true)} className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700">
          + Nuovo scenario
        </button>
      </div>

      <div className="mb-4 flex items-center gap-3">
        <div>
          <label className="text-xs text-gray-500 mr-1">Tipo:</label>
          <select value={typeFilter} onChange={e => setTypeFilter(e.target.value as "" | "IT" | "OT")}
            className="border rounded px-2 py-1.5 text-sm">
            <option value="">Tutti</option>
            <option value="IT">IT</option>
            <option value="OT">OT</option>
          </select>
        </div>
        <div>
          <label className="text-xs text-gray-500 mr-1">Stato:</label>
          <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}
            className="border rounded px-2 py-1.5 text-sm">
            <option value="">Tutti</option>
            <option value="bozza">Bozza</option>
            <option value="completato">Completato</option>
            <option value="archiviato">Archiviato</option>
          </select>
        </div>
      </div>

      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-gray-400">Caricamento...</div>
        ) : assessments.length === 0 ? (
          <div className="p-8 text-center">
            <p className="text-gray-400 mb-2">Nessuno scenario di rischio registrato</p>
            <button onClick={() => setShowNew(true)} className="text-sm text-primary-600 hover:underline">Crea il primo scenario →</button>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-600 w-8"></th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Scenario</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Minaccia</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Sito</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">P × I</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Score</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">ALE</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Trattamento</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Stato</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody>
              {assessments.map(a => (
                <>
                  <tr key={a.id}
                    onClick={() => setExpandedId(prev => prev === a.id ? null : a.id)}
                    className="hover:bg-gray-50 transition-colors cursor-pointer border-b border-gray-100"
                  >
                    <td className="px-4 py-3 text-gray-400 text-xs">{expandedId === a.id ? "▼" : "▶"}</td>
                    <td className="px-4 py-3">
                      <div className="font-medium text-gray-800">{a.name || <span className="text-gray-400 italic">—</span>}</div>
                      <div className="text-xs text-gray-400">{a.assessment_type}</div>
                    </td>
                    <td className="px-4 py-3 text-gray-600 text-xs">
                      {THREAT_CATEGORIES.find(c => c.value === a.threat_category)?.label ?? "—"}
                    </td>
                    <td className="px-4 py-3 text-gray-600">{a.plant_name || a.plant}</td>
                    <td className="px-4 py-3 text-gray-600">
                      {a.probability && a.impact
                        ? <span className={`text-xs font-mono font-bold px-1.5 py-0.5 rounded ${matrixColor(a.probability, a.impact)}`}>{a.probability}×{a.impact}</span>
                        : <span className="text-gray-400">—</span>}
                    </td>
                    <td className="px-4 py-3"><RiskLevelBadge score={a.score} /></td>
                    <td className="px-4 py-3 text-gray-600">{formatAle(a.ale_annuo)}</td>
                    <td className="px-4 py-3 text-gray-600 capitalize text-xs">{a.treatment || "—"}</td>
                    <td className="px-4 py-3"><StatusBadge status={a.status} /></td>
                    <td className="px-4 py-3 whitespace-nowrap" onClick={e => e.stopPropagation()}>
                      {a.status === "bozza" && !!a.probability && !!a.impact && (
                        <button onClick={() => completeMutation.mutate(a.id)} disabled={completeMutation.isPending}
                          className="text-xs text-blue-700 border border-blue-300 rounded px-2 py-0.5 hover:bg-blue-50 disabled:opacity-50 whitespace-nowrap">
                          Completa
                        </button>
                      )}
                      {a.status === "completato" && !a.risk_accepted && (
                        <button onClick={() => acceptMutation.mutate(a.id)} disabled={acceptMutation.isPending}
                          className="text-xs text-green-700 border border-green-300 rounded px-2 py-0.5 hover:bg-green-50 disabled:opacity-50 whitespace-nowrap">
                          Accetta rischio
                        </button>
                      )}
                      {a.risk_accepted && <span className="text-xs text-green-600 font-medium">✓ Accettato</span>}
                    </td>
                  </tr>
                  {expandedId === a.id && (
                    <tr key={`${a.id}-detail`}>
                      <td colSpan={10} className="p-0">
                        <MitigationPanel assessmentId={a.id} />
                      </td>
                    </tr>
                  )}
                </>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {showNew && plants && <NewAssessmentModal plants={plants} onClose={() => setShowNew(false)} />}
    </div>
  );
}
