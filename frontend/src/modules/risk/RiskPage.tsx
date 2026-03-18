import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "../../api/client";
import { riskApi, type RiskAssessment, type RiskMitigationPlan, type SuggestResidualResult, THREAT_CATEGORIES, PROB_LABELS, IMPACT_LABELS } from "../../api/endpoints/risk";
import { plantsApi } from "../../api/endpoints/plants";
import { biaApi, type CriticalProcess } from "../../api/endpoints/bia";
import { usersApi, type GrcUser } from "../../api/endpoints/users";
import { useAuthStore } from "../../store/auth";
import { StatusBadge } from "../../components/ui/StatusBadge";
import { AssistenteValutazione } from "../../components/ui/AssistenteValutazione";
import { ModuleHelp } from "../../components/ui/ModuleHelp";
import i18n from "../../i18n";

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

const RISK_LEVEL_COLORS: Record<string, string> = {
  verde:  "bg-green-100 text-green-800",
  giallo: "bg-yellow-100 text-yellow-800",
  rosso:  "bg-red-100 text-red-800",
};
const RISK_LEVEL_ICONS: Record<string, string> = {
  verde: "🟢", giallo: "🟡", rosso: "🔴",
};

function RiskInherentResidualBadges({ assessment }: { assessment: RiskAssessment }) {
  if (!assessment.inherent_score && !assessment.score) return null;
  return (
    <div className="flex flex-wrap items-center gap-3 px-6 py-3 bg-gray-50 border-t border-gray-100">
      {assessment.inherent_score != null && (
        <div className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium ${RISK_LEVEL_COLORS[assessment.inherent_risk_level ?? "verde"]}`}>
          <span>{RISK_LEVEL_ICONS[assessment.inherent_risk_level ?? "verde"]}</span>
          <span>Inerente: score {assessment.inherent_score}</span>
        </div>
      )}
      {assessment.inherent_score != null && assessment.score != null && (
        <span className="text-gray-400 text-sm">→</span>
      )}
      {assessment.score != null && (
        <div className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium ${RISK_LEVEL_COLORS[assessment.risk_level ?? "verde"]}`}>
          <span>{RISK_LEVEL_ICONS[assessment.risk_level ?? "verde"]}</span>
          <span>Residuo: score {assessment.score}</span>
        </div>
      )}
      {assessment.risk_reduction_pct != null && (
        <span className="text-xs text-green-700 bg-green-50 border border-green-200 px-2 py-1 rounded">
          Riduzione: {assessment.risk_reduction_pct}% grazie ai controlli
        </span>
      )}
    </div>
  );
}

function SuggestResidualPanel({ assessment }: { assessment: RiskAssessment }) {
  const qc = useQueryClient();
  const [suggestion, setSuggestion] = useState<SuggestResidualResult | null>(null);

  const { refetch, isFetching } = useQuery({
    queryKey: ["suggest-residual", assessment.id],
    queryFn: () => riskApi.suggestResidual(assessment.id),
    enabled: false,
  });

  async function handleSuggest() {
    const { data } = await refetch();
    if (data) setSuggestion(data);
  }

  return (
    <div className="px-6 py-3 border-t border-gray-100">
      <div className="flex items-center gap-3">
        <button
          onClick={handleSuggest}
          disabled={isFetching}
          className="text-xs px-3 py-1.5 border border-indigo-300 text-indigo-600 rounded hover:bg-indigo-50 disabled:opacity-50"
        >
          {isFetching ? "Calcolo..." : "💡 Suggerisci rischio residuo"}
        </button>
        {suggestion && (
          <span className="text-xs text-gray-600">{suggestion.reason}</span>
        )}
      </div>
    </div>
  );
}

function FormalAcceptancePanel({ assessment }: { assessment: RiskAssessment }) {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [note, setNote] = useState("");
  const [expiry, setExpiry] = useState("");
  const [err, setErr] = useState("");

  const mutation = useMutation({
    mutationFn: () => riskApi.acceptRisk(assessment.id, note, expiry || undefined),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["risk-assessments"] });
      setOpen(false);
    },
    onError: (e: unknown) => {
      const msg = (e as { response?: { data?: { error?: string } } })?.response?.data?.error ?? "Errore";
      setErr(msg);
    },
  });

  if (assessment.risk_level === "verde" && !assessment.risk_accepted_formally) return null;

  if (assessment.risk_accepted_formally) {
    const expDate = assessment.risk_acceptance_expiry ? new Date(assessment.risk_acceptance_expiry) : null;
    const expired = expDate ? expDate < new Date() : false;
    return (
      <div className="px-6 py-3 border-t border-gray-100">
        <div className={`flex items-center gap-2 text-xs px-3 py-2 rounded-lg ${expired ? "bg-red-50 text-red-700" : "bg-green-50 text-green-700"}`}>
          <span>{expired ? "⚠️" : "✅"}</span>
          <span>
            Accettato da <strong>{assessment.accepted_by_name ?? "—"}</strong> il {assessment.risk_accepted_at ? new Date(assessment.risk_accepted_at).toLocaleDateString(i18n.language || "it") : "—"}
            {expDate && <> — {expired ? "scaduto il" : "scade il"} <strong>{expDate.toLocaleDateString(i18n.language || "it")}</strong></>}
          </span>
        </div>
      </div>
    );
  }

  return (
    <div className="px-6 py-3 border-t border-gray-100">
      {!open ? (
        <button
          onClick={() => setOpen(true)}
          className="text-xs px-3 py-1.5 border border-yellow-300 text-yellow-700 rounded hover:bg-yellow-50"
        >
          ⚠️ Accetta rischio formalmente
        </button>
      ) : (
        <div className="space-y-2 max-w-lg">
          <p className="text-xs font-medium text-gray-700">Accettazione formale del rischio residuo</p>
          <textarea
            value={note}
            onChange={e => { setNote(e.target.value); setErr(""); }}
            placeholder={`Nota obbligatoria${assessment.risk_level === "rosso" ? " (min 50 caratteri per rischi critici)" : ""}`}
            className="w-full border rounded px-2 py-1.5 text-xs resize-none"
            rows={3}
          />
          <input
            type="date"
            value={expiry}
            onChange={e => setExpiry(e.target.value)}
            className="border rounded px-2 py-1.5 text-xs w-full"
            placeholder="Scadenza accettazione"
          />
          {err && <p className="text-xs text-red-600">⛔ {err}</p>}
          <div className="flex gap-2">
            <button
              onClick={() => mutation.mutate()}
              disabled={mutation.isPending}
              className="px-3 py-1.5 bg-yellow-600 text-white text-xs rounded hover:bg-yellow-700 disabled:opacity-50"
            >
              {mutation.isPending ? "Salvataggio..." : "Conferma accettazione"}
            </button>
            <button onClick={() => setOpen(false)} className="px-3 py-1.5 border rounded text-xs text-gray-600 hover:bg-gray-50">
              Annulla
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

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
              <span className="text-xs text-gray-400 shrink-0">scad. {new Date(plan.due_date).toLocaleDateString(i18n.language || "it")}</span>
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

function NewAssessmentModal({ plants, onClose }: { plants: { id: string; code: string; name: string }[]; onClose: () => void }) {
  const qc = useQueryClient();
  const selectedPlant = useAuthStore(s => s.selectedPlant);
  const [form, setForm] = useState<Partial<RiskAssessment>>({
    assessment_type: "IT",
    probability: null,
    impact: null,
    plant: selectedPlant?.id ?? "",
  });
  const [error, setError] = useState("");

  const plantId = form.plant;

  const { data: processes } = useQuery({
    queryKey: ["bia-processes", plantId],
    queryFn: () => biaApi.list(plantId ? { plant: plantId, page_size: "200" } : {}),
    enabled: !!plantId,
    retry: false,
  });

  const { data: users } = useQuery({
    queryKey: ["users"],
    queryFn: () => usersApi.list(),
    retry: false,
  });

  const mutation = useMutation({
    mutationFn: () => riskApi.create(form),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["risk-assessments"] }); onClose(); },
    onError: (e: any) => setError(e?.response?.data?.detail || JSON.stringify(e?.response?.data) || "Errore"),
  });

  function set(field: string, value: unknown) { setForm(f => ({ ...f, [field]: value })); }

  const canSave = !!form.plant && !!form.name && !!form.probability && !!form.impact;

  const selectedProcess = processes?.results?.find(p => p.id === form.critical_process);

  // Estimate ALE locally for display (probability × impact × downtime_cost_hour)
  function estimateAle(): string | null {
    if (!selectedProcess?.downtime_cost_hour) return null;
    if (!form.probability || !form.impact) return null;
    const oreMap: Record<number, number> = {1:1, 2:4, 3:24, 4:72, 5:168};
    const probMap: Record<number, number> = {1:0.1, 2:0.3, 3:1.0, 4:3.0, 5:10.0};
    const ore = oreMap[form.impact] ?? 24;
    const prob = probMap[form.probability] ?? 1.0;
    let ale = parseFloat(selectedProcess.downtime_cost_hour) * ore * prob;
    if (selectedProcess.danno_reputazionale >= 4) ale *= 1.3;
    if (selectedProcess.danno_normativo >= 4) ale *= 1.2;
    return new Intl.NumberFormat("it-IT", { style: "currency", currency: "EUR" }).format(ale);
  }

  const alePreview = estimateAle();

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl flex flex-col max-h-[92vh]">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100 shrink-0">
          <h3 className="text-lg font-semibold">Nuovo scenario di rischio</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-2xl w-8 h-8 flex items-center justify-center rounded hover:bg-gray-100">×</button>
        </div>

        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Nome scenario / rischio *</label>
            <input value={form.name ?? ""} onChange={e => set("name", e.target.value)}
              placeholder="es. Ransomware su server di produzione MES"
              className="w-full border rounded px-3 py-2 text-sm" />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Sito *</label>
              <select value={form.plant ?? ""} onChange={e => { set("plant", e.target.value); set("critical_process", null); }} className="w-full border rounded px-3 py-2 text-sm">
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

          {/* Owner rischio */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Owner rischio</label>
            <select value={form.owner ?? ""} onChange={e => set("owner", e.target.value || null)} className="w-full border rounded px-3 py-2 text-sm">
              <option value="">— nessun owner —</option>
              {users?.map(u => (
                <option key={u.id} value={u.id}>
                  {u.first_name || u.last_name ? `${u.first_name} ${u.last_name}`.trim() : u.username} ({u.email})
                </option>
              ))}
            </select>
          </div>

          {/* Processo BIA collegato */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Processo BIA collegato (opzionale)</label>
            <select
              value={form.critical_process ?? ""}
              onChange={e => set("critical_process", e.target.value || null)}
              disabled={!plantId}
              className="w-full border rounded px-3 py-2 text-sm disabled:bg-gray-50"
            >
              <option value="">— nessun processo BIA —</option>
              {processes?.results?.map(p => (
                <option key={p.id} value={p.id}>
                  {p.name} [criticità {p.criticality}]
                </option>
              ))}
            </select>
            {selectedProcess && (
              <div className="mt-1.5 px-3 py-2 bg-blue-50 rounded text-xs text-blue-700 flex gap-3">
                <span>Costo orario fermo: <strong>{selectedProcess.downtime_cost_hour ? new Intl.NumberFormat("it-IT", {style:"currency",currency:"EUR"}).format(parseFloat(selectedProcess.downtime_cost_hour)) : "—"}</strong></span>
                <span>Criticità: <strong>{selectedProcess.criticality}</strong>/5</span>
              </div>
            )}
          </div>

          {/* P × I inerente (prima dei controlli) */}
          <div className="border border-orange-200 rounded-lg p-4 bg-orange-50/30">
            <p className="text-sm font-medium text-orange-800 mb-1">Rischio inerente (prima dei controlli)</p>
            <p className="text-xs text-orange-600 mb-3">Valuta il rischio come se non esistessero controlli di sicurezza</p>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Probabilità inerente</label>
                <select
                  value={form.inherent_probability ?? ""}
                  onChange={e => set("inherent_probability", e.target.value ? Number(e.target.value) : null)}
                  className="w-full border rounded px-2 py-1.5 text-sm"
                >
                  <option value="">— seleziona —</option>
                  {[1,2,3,4,5].map(v => <option key={v} value={v}>{PROB_LABELS[v]}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Impatto inerente</label>
                <select
                  value={form.inherent_impact ?? ""}
                  onChange={e => set("inherent_impact", e.target.value ? Number(e.target.value) : null)}
                  className="w-full border rounded px-2 py-1.5 text-sm"
                >
                  <option value="">— seleziona —</option>
                  {[1,2,3,4,5].map(v => <option key={v} value={v}>{IMPACT_LABELS[v]}</option>)}
                </select>
              </div>
              {form.inherent_probability && form.inherent_impact && (
                <div className="col-span-2">
                  <div className={`rounded px-3 py-2 text-center text-sm font-semibold ${matrixColor(form.inherent_probability, form.inherent_impact)}`}>
                    Score inerente: {form.inherent_probability} × {form.inherent_impact} = {form.inherent_probability * form.inherent_impact}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* P × I residuo */}
          <div className="border border-gray-200 rounded-lg p-4">
            <p className="text-sm font-medium text-gray-700 mb-3">Rischio residuo (P × I dopo i controlli)</p>
            <ProbImpactSelector
              probability={form.probability ?? null}
              impact={form.impact ?? null}
              onChange={(field, value) => set(field, value)}
            />
          </div>

          {/* ALE calcolato (readonly) */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">ALE calcolato dalla BIA</label>
            {alePreview ? (
              <>
                <div className="w-full border border-dashed border-blue-300 bg-blue-50 rounded px-3 py-2 text-sm font-semibold text-blue-800">
                  {alePreview}
                </div>
                <p className="text-xs text-gray-400 mt-1">Calcolato automaticamente da probabilità × impatto × costo fermo BIA</p>
              </>
            ) : (
              <div className="w-full border border-dashed border-gray-200 bg-gray-50 rounded px-3 py-2 text-sm text-gray-400">
                {selectedProcess
                  ? "Seleziona probabilità e impatto per stimare l'ALE"
                  : "Collega un processo BIA per calcolare l'ALE"}
              </div>
            )}
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

interface RiskAppetitePolicy {
  id: string;
  max_acceptable_score: number;
  max_red_risks_count: number;
  max_unacceptable_score: number;
  valid_from: string;
  valid_until: string | null;
  approved_by_name: string | null;
  is_active: boolean;
  framework_code: string;
}

function RiskAppetiteCard({ plantId }: { plantId?: string }) {
  const { data: policy, isLoading, isError } = useQuery({
    queryKey: ["risk-appetite", plantId],
    queryFn: () => {
      const params = new URLSearchParams();
      if (plantId) params.set("plant", plantId);
      return apiClient.get<RiskAppetitePolicy>(
        `/risk/appetite-policies/active/?${params.toString()}`
      ).then(r => r.data);
    },
    retry: false,
  });

  if (isLoading) return null;
  if (isError || !policy) return null;

  return (
    <div className="mb-4 bg-blue-50 border border-blue-200 rounded-lg px-4 py-3 flex flex-wrap gap-6 items-center text-sm">
      <div>
        <span className="text-xs text-blue-500 font-medium uppercase">Risk Appetite Policy</span>
        {policy.framework_code && <span className="ml-2 text-xs text-blue-400">{policy.framework_code}</span>}
      </div>
      <div className="text-gray-700">
        Score max accettabile: <strong className="text-orange-600">{policy.max_acceptable_score}</strong>
      </div>
      <div className="text-gray-700">
        Max rischi rossi: <strong className="text-red-600">{policy.max_red_risks_count}</strong>
      </div>
      <div className="text-gray-700">
        Valida fino: <strong>{policy.valid_until ? new Date(policy.valid_until).toLocaleDateString(i18n.language || "it") : "—"}</strong>
      </div>
      {policy.approved_by_name && (
        <div className="text-gray-500 text-xs">Approvata da: {policy.approved_by_name}</div>
      )}
    </div>
  );
}

export function RiskPage() {
  const [typeFilter, setTypeFilter] = useState<"" | "IT" | "OT">("");
  const [statusFilter, setStatusFilter] = useState("");
  const [showNew, setShowNew] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
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
      <RiskAppetiteCard plantId={selectedPlant?.id} />
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold text-gray-900 flex items-center">
          Risk Assessment
          <ModuleHelp
            title="Risk Assessment IT/OT — M06"
            description="Valuta il rischio di ogni asset con matrice probabilità×impatto
    (score 1-25). Calcola ALE automaticamente dai dati BIA.
    Score >14 genera task di mitigazione e PDCA automaticamente."
            steps={[
              "Crea assessment collegando asset e processo BIA",
              "Inserisci rischio inerente (probabilità e impatto SENZA controlli)",
              "Completa le dimensioni di valutazione IT o OT",
              "Premi 'Completa assessment': score e ALE vengono calcolati automaticamente",
              "Se score > soglia policy: task urgente al risk manager",
              "Accetta formalmente i rischi residui con nota e scadenza revisione",
            ]}
            connections={[
              { module: "M04 Asset", relation: "Asset oggetto della valutazione" },
              { module: "M05 BIA", relation: "ALE calcolato da downtime_cost BIA" },
              { module: "M11 PDCA", relation: "Rischio rosso apre PDCA automatico" },
              { module: "M08 Task", relation: "Task mitigazione auto-creato se score > soglia" },
            ]}
            configNeeded={[
              "Configurare RiskAppetitePolicy per soglie personalizzate",
              "Collegare processi BIA per calcolo ALE automatico",
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
            + Nuovo scenario
          </button>
        </div>
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
                <th className="text-left px-4 py-3 font-medium text-gray-600">Owner</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">P × I</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Score</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Weighted</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">ALE</th>
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
                      <div className="text-xs text-gray-400">{a.assessment_type}{a.critical_process_name && ` · ${a.critical_process_name}`}</div>
                    </td>
                    <td className="px-4 py-3 text-gray-600 text-xs">
                      {THREAT_CATEGORIES.find(c => c.value === a.threat_category)?.label ?? "—"}
                    </td>
                    <td className="px-4 py-3 text-gray-600 text-xs">{a.owner_name ?? <span className="text-gray-300">—</span>}</td>
                    <td className="px-4 py-3 text-gray-600">
                      {a.probability && a.impact
                        ? <span className={`text-xs font-mono font-bold px-1.5 py-0.5 rounded ${matrixColor(a.probability, a.impact)}`}>{a.probability}×{a.impact}</span>
                        : <span className="text-gray-400">—</span>}
                    </td>
                    <td className="px-4 py-3"><RiskLevelBadge score={a.score} /></td>
                    <td className="px-4 py-3"><RiskLevelBadge score={a.weighted_score} /></td>
                    <td className="px-4 py-3 text-gray-600 text-xs">
                      {a.ale_calcolato
                        ? <span className="text-blue-700 font-medium">{formatAle(a.ale_calcolato)}</span>
                        : formatAle(a.ale_annuo)}
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={a.status} />
                      {a.needs_revaluation && (
                        <span className="text-xs px-2 py-0.5 rounded-full bg-amber-100 text-amber-700 ml-1">
                          Rivalutare
                        </span>
                      )}
                    </td>
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
                        <RiskInherentResidualBadges assessment={a} />
                        <SuggestResidualPanel assessment={a} />
                        <FormalAcceptancePanel assessment={a} />
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
      <AssistenteValutazione open={drawerOpen} onClose={() => setDrawerOpen(false)} />
    </div>
  );
}
