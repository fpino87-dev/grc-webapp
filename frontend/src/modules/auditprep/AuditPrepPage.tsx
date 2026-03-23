import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  auditPrepApi,
  type AuditFinding,
  type AuditPrep,
  type AuditProgram,
  type EvidenceItem,
  type PlannedAudit,
} from "../../api/endpoints/auditPrep";
import { plantsApi } from "../../api/endpoints/plants";
import { useAuthStore } from "../../store/auth";
import { StatusBadge } from "../../components/ui/StatusBadge";
import { ModuleHelp } from "../../components/ui/ModuleHelp";

// ─── helpers ──────────────────────────────────────────────────────────────────

function fwLabel(code: string | undefined | null): string {
  if (!code) return "—";
  if (code === "TISAX_L3") return "TISAX AL3 (L2+L3)";
  if (code === "TISAX_L2") return "TISAX AL2";
  return code;
}

function coverageLabel(c: string) {
  return c === "campione" ? "Campione 25%" : c === "esteso" ? "Esteso 50%" : "Full 100%";
}

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = filename; a.click();
  URL.revokeObjectURL(url);
}

const QUARTER_MONTHS: Record<number, string> = { 1: "Gen–Mar", 2: "Apr–Giu", 3: "Lug–Set", 4: "Ott–Dic" };

const AUDIT_STATUS_META: Record<string, { label: string; icon: string; color: string; bg: string }> = {
  planned:     { label: "Pianificato",  icon: "⏳", color: "text-gray-600",  bg: "bg-gray-100" },
  in_progress: { label: "In corso",     icon: "🔵", color: "text-blue-700",  bg: "bg-blue-50"  },
  completed:   { label: "Completato",   icon: "✅", color: "text-green-700", bg: "bg-green-50" },
  cancelled:   { label: "Annullato",    icon: "❌", color: "text-red-600",   bg: "bg-red-50"   },
};

function ReadinessBar({ score }: { score: number | null }) {
  if (score === null) return <span className="text-gray-400 text-xs">—</span>;
  const color = score >= 80 ? "bg-green-500" : score >= 50 ? "bg-yellow-400" : "bg-red-500";
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${score}%` }} />
      </div>
      <span className="text-xs font-medium text-gray-700 w-10">{score}/100</span>
    </div>
  );
}

const FINDING_TYPE_COLORS: Record<string, string> = {
  major_nc:    "bg-red-100 text-red-700",
  minor_nc:    "bg-orange-100 text-orange-700",
  observation: "bg-blue-100 text-blue-700",
  opportunity: "bg-gray-100 text-gray-600",
};

// ─── PrepDrawer ───────────────────────────────────────────────────────────────

function PrepDrawer({ prep, onClose }: { prep: AuditPrep; onClose: () => void }) {
  const qc = useQueryClient();
  const [tab, setTab] = useState<"checklist" | "findings" | "info">("checklist");
  const [showFindingForm, setShowFindingForm] = useState(false);
  const [findingForm, setFindingForm] = useState<Record<string, string>>({ finding_type: "major_nc" });
  const [completingId, setCompletingId] = useState(false);
  const [cancelModal, setCancelModal] = useState(false);
  const [cancelReason, setCancelReason] = useState("");

  const { data: evidences = [] } = useQuery<EvidenceItem[]>({
    queryKey: ["evidence", prep.id],
    queryFn: () => auditPrepApi.evidence(prep.id),
  });
  const { data: findings = [] } = useQuery<AuditFinding[]>({
    queryKey: ["findings", prep.id],
    queryFn: () => auditPrepApi.findings(prep.id),
  });

  const updateEvMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) =>
      auditPrepApi.updateEvidence(id, { status: status as EvidenceItem["status"] }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["evidence", prep.id] }),
  });

  const createFindingMutation = useMutation({
    mutationFn: (data: Record<string, unknown>) => auditPrepApi.createFinding(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["findings", prep.id] });
      setShowFindingForm(false);
      setFindingForm({ finding_type: "major_nc" });
    },
  });

  const completeMutation = useMutation({
    mutationFn: () => auditPrepApi.complete(prep.id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["audit-prep"] }); onClose(); },
  });

  const cancelMutation = useMutation({
    mutationFn: () => auditPrepApi.annulla(prep.id, cancelReason),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["audit-prep"] }); onClose(); },
  });

  const openMajors = findings.filter(f => f.finding_type === "major_nc" && ["open", "in_response"].includes(f.status)).length;

  return (
    <div className="fixed inset-0 z-50 flex">
      <div className="flex-1 bg-black/40" onClick={onClose} />
      <div className="w-full max-w-3xl bg-white shadow-2xl flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-200 flex items-start justify-between">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <StatusBadge status={prep.status} />
              {prep.audit_entry_id && <span className="text-xs text-gray-400">Prog. annuale</span>}
            </div>
            <h2 className="text-lg font-semibold text-gray-900">{prep.title}</h2>
            <p className="text-xs text-gray-500 mt-0.5">
              {fwLabel(prep.framework_code)} · {prep.auditor_name || "—"} · {prep.audit_date || "—"} · {coverageLabel(prep.coverage_type)}
            </p>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl">✕</button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-gray-200 px-6">
          {(["checklist", "findings", "info"] as const).map(t => (
            <button key={t} onClick={() => setTab(t)}
              className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${tab === t ? "border-primary-600 text-primary-600" : "border-transparent text-gray-500 hover:text-gray-700"}`}>
              {t === "checklist" ? "Checklist controlli" : t === "findings" ? `Finding (${findings.length})` : "Info audit"}
            </button>
          ))}
        </div>

        <div className="flex-1 overflow-auto p-6">

          {/* TAB checklist */}
          {tab === "checklist" && (
            <div>
              <ReadinessBar score={prep.readiness_score} />
              <div className="mt-4 space-y-1">
                {evidences.length === 0 && (
                  <p className="text-sm text-gray-400 text-center py-8">Nessuna evidenza caricata</p>
                )}
                {evidences.map(ev => (
                  <div key={ev.id} className="flex items-center gap-3 py-2 border-b border-gray-100">
                    <select
                      value={ev.status}
                      onChange={e => updateEvMutation.mutate({ id: ev.id, status: e.target.value })}
                      className={`text-xs border rounded px-2 py-1 ${ev.status === "presente" ? "border-green-300 bg-green-50" : ev.status === "scaduto" ? "border-yellow-300 bg-yellow-50" : "border-red-200 bg-red-50"}`}
                    >
                      <option value="mancante">❌ Mancante</option>
                      <option value="presente">✅ Presente</option>
                      <option value="scaduto">⚠️ Scaduto</option>
                    </select>
                    <span className="text-sm text-gray-700 flex-1">{ev.description}</span>
                    {ev.notes && <span className="text-xs text-gray-400 truncate max-w-[120px]">{ev.notes}</span>}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* TAB findings */}
          {tab === "findings" && (
            <div>
              <div className="flex justify-between items-center mb-4">
                <div className="flex gap-3 text-xs">
                  {openMajors > 0 && <span className="px-2 py-1 bg-red-100 text-red-700 rounded font-medium">{openMajors} Major NC aperti</span>}
                </div>
                <button onClick={() => setShowFindingForm(s => !s)}
                  className="px-3 py-1.5 bg-primary-600 text-white text-xs rounded hover:bg-primary-700">
                  + Aggiungi finding
                </button>
              </div>

              {showFindingForm && (
                <div className="bg-gray-50 border rounded-lg p-4 mb-4 space-y-3">
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs text-gray-600 mb-1">Tipo *</label>
                      <select value={findingForm.finding_type} onChange={e => setFindingForm(p => ({ ...p, finding_type: e.target.value }))}
                        className="w-full border rounded px-2 py-1.5 text-sm">
                        <option value="major_nc">Major NC</option>
                        <option value="minor_nc">Minor NC</option>
                        <option value="observation">Observation</option>
                        <option value="opportunity">Opportunity</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-xs text-gray-600 mb-1">Data audit *</label>
                      <input type="date" value={findingForm.audit_date || ""} onChange={e => setFindingForm(p => ({ ...p, audit_date: e.target.value }))}
                        className="w-full border rounded px-2 py-1.5 text-sm" />
                    </div>
                  </div>
                  <div>
                    <label className="block text-xs text-gray-600 mb-1">Titolo *</label>
                    <input value={findingForm.title || ""} onChange={e => setFindingForm(p => ({ ...p, title: e.target.value }))}
                      className="w-full border rounded px-2 py-1.5 text-sm" />
                  </div>
                  <div>
                    <label className="block text-xs text-gray-600 mb-1">Descrizione</label>
                    <textarea value={findingForm.description || ""} rows={2} onChange={e => setFindingForm(p => ({ ...p, description: e.target.value }))}
                      className="w-full border rounded px-2 py-1.5 text-sm" />
                  </div>
                  <div className="flex gap-2">
                    <button
                      disabled={!findingForm.title || !findingForm.audit_date || createFindingMutation.isPending}
                      onClick={() => createFindingMutation.mutate({ ...findingForm, audit_prep: prep.id })}
                      className="px-3 py-1.5 bg-primary-600 text-white text-xs rounded disabled:opacity-50">
                      {createFindingMutation.isPending ? "..." : "Salva finding"}
                    </button>
                    <button onClick={() => setShowFindingForm(false)} className="px-3 py-1.5 border rounded text-xs text-gray-600">Annulla</button>
                  </div>
                </div>
              )}

              <div className="space-y-2">
                {findings.map(f => (
                  <div key={f.id} className="border rounded-lg p-3">
                    <div className="flex items-start justify-between">
                      <div className="flex items-center gap-2">
                        <span className={`text-xs px-2 py-0.5 rounded font-medium ${FINDING_TYPE_COLORS[f.finding_type]}`}>{f.finding_type.replace("_", " ").toUpperCase()}</span>
                        <span className="text-sm font-medium text-gray-800">{f.title}</span>
                        {f.is_overdue && <span className="text-xs text-red-600">⚠️ Scaduto</span>}
                      </div>
                      <StatusBadge status={f.status} />
                    </div>
                    {f.description && <p className="text-xs text-gray-500 mt-1">{f.description}</p>}
                    <div className="flex gap-3 mt-1 text-xs text-gray-400">
                      {f.response_deadline && <span>Scadenza: {f.response_deadline}</span>}
                      {f.control_external_id && <span>Controllo: {f.control_external_id}</span>}
                    </div>
                  </div>
                ))}
                {findings.length === 0 && <p className="text-sm text-gray-400 text-center py-6">Nessun finding</p>}
              </div>
            </div>
          )}

          {/* TAB info */}
          {tab === "info" && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div><span className="text-gray-500">Framework:</span> <span className="font-medium">{fwLabel(prep.framework_code)}</span></div>
                <div><span className="text-gray-500">Copertura:</span> <span className="font-medium">{coverageLabel(prep.coverage_type)}</span></div>
                <div><span className="text-gray-500">Auditor:</span> <span className="font-medium">{prep.auditor_name || "—"}</span></div>
                <div><span className="text-gray-500">Data audit:</span> <span className="font-medium">{prep.audit_date || "—"}</span></div>
                <div><span className="text-gray-500">Stato:</span> <StatusBadge status={prep.status} /></div>
                <div><span className="text-gray-500">Readiness:</span> <span className="font-medium">{prep.readiness_score ?? "—"}/100</span></div>
              </div>

              {prep.status === "in_corso" && (
                <div className="flex gap-2 pt-4 border-t border-gray-100">
                  <button
                    onClick={() => { setCompletingId(true); completeMutation.mutate(); }}
                    disabled={completeMutation.isPending || openMajors > 0}
                    className="px-4 py-2 bg-green-600 text-white text-sm rounded hover:bg-green-700 disabled:opacity-50"
                    title={openMajors > 0 ? `Non puoi completare con ${openMajors} Major NC aperti` : undefined}
                  >
                    {completeMutation.isPending ? "..." : "✅ Completa audit"}
                  </button>
                  {openMajors > 0 && (
                    <p className="text-xs text-red-600 self-center">
                      Non puoi completare con {openMajors} Major NC aperti
                    </p>
                  )}
                  <button onClick={() => setCancelModal(true)}
                    className="px-4 py-2 border border-red-200 text-red-700 text-sm rounded hover:bg-red-50">
                    ✕ Annulla audit
                  </button>
                </div>
              )}
              {completeMutation.isError && (
                <p className="text-xs text-red-600">
                  {(completeMutation.error as { response?: { data?: { error?: string } } })?.response?.data?.error || "Errore"}
                </p>
              )}
            </div>
          )}
        </div>

        {/* Footer azioni */}
        <div className="px-6 py-3 border-t border-gray-100 flex gap-2 bg-gray-50">
          <button
            onClick={() => auditPrepApi.downloadPrepReport(prep.id).then(r => downloadBlob(r.data as Blob, `AuditReport_${prep.id}.html`))}
            className="px-3 py-1.5 text-xs border rounded text-gray-600 hover:bg-white">
            📄 Scarica relazione
          </button>
        </div>
      </div>

      {/* Modal annulla */}
      {cancelModal && (
        <div className="fixed inset-0 z-60 bg-black/50 flex items-center justify-center">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-6">
            <h3 className="font-semibold mb-2">Annulla preparazione audit</h3>
            <p className="text-sm text-gray-600 mb-3">Motivo (min 10 caratteri). I finding aperti verranno chiusi.</p>
            <textarea value={cancelReason} onChange={e => setCancelReason(e.target.value)} rows={3}
              className="w-full border rounded px-3 py-2 text-sm" placeholder="Motivo annullamento..." />
            <div className="flex justify-end gap-2 mt-3">
              <button onClick={() => setCancelModal(false)} className="px-4 py-2 border rounded text-sm text-gray-600">Annulla</button>
              <button disabled={cancelReason.trim().length < 10 || cancelMutation.isPending}
                onClick={() => cancelMutation.mutate()}
                className="px-4 py-2 bg-red-600 text-white text-sm rounded disabled:opacity-50">
                {cancelMutation.isPending ? "..." : "Conferma annullamento"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Wizard creazione programma ───────────────────────────────────────────────

interface Framework { id: string; name: string; code: string; }

function ProgramWizard({ plantId, plantCode, onClose }: { plantId: string; plantCode: string; onClose: () => void }) {
  const qc = useQueryClient();
  const [step, setStep] = useState(1);
  const [year, setYear] = useState(new Date().getFullYear() + 1);
  const [title, setTitle] = useState("");
  const [coverageType, setCoverageType] = useState<"campione" | "esteso" | "full">("campione");
  const [selectedFwCodes, setSelectedFwCodes] = useState<string[]>([]);
  const [multiFw, setMultiFw] = useState(true);
  const [suggestedPlan, setSuggestedPlan] = useState<PlannedAudit[]>([]);
  const [editingQ, setEditingQ] = useState<string | null>(null);
  const [editForm, setEditForm] = useState<Partial<PlannedAudit>>({});
  const [approveNow, setApproveNow] = useState(false);
  const [loadingSuggest, setLoadingSuggest] = useState(false);

  const { data: plantFws = [] } = useQuery({
    queryKey: ["plant-frameworks", plantId],
    queryFn: () => plantsApi.plantFrameworks(plantId),
  });

  const frameworks: Framework[] = plantFws.map(pf => ({
    id: pf.framework, code: pf.framework_code, name: pf.framework_name,
  }));

  const hasTisax = frameworks.some(f => f.code.startsWith("TISAX"));
  const displayFrameworks = hasTisax
    ? [{ id: "TISAX", code: "TISAX", name: "TISAX — VDA ISA 6.0" }, ...frameworks.filter(f => !f.code.startsWith("TISAX"))]
    : frameworks;

  function toggleFw(code: string) {
    setSelectedFwCodes(prev =>
      prev.includes(code) ? prev.filter(c => c !== code) : [...prev, code]
    );
  }

  function resolvedFwCodes(): string[] {
    return selectedFwCodes.flatMap(c => {
      if (c === "TISAX") return frameworks.filter(f => f.code.startsWith("TISAX")).map(f => f.code);
      return [c];
    });
  }

  async function loadSuggest() {
    setLoadingSuggest(true);
    try {
      const result = await auditPrepApi.suggestPlan({
        plant: plantId,
        framework_codes: resolvedFwCodes(),
        year,
        coverage_type: coverageType,
      });
      setSuggestedPlan(result.suggested_plan);
    } catch {
      setSuggestedPlan([1, 2, 3, 4].map(q => ({
        id: crypto.randomUUID(),
        quarter: q,
        title: `Audit Q${q} ${year}`,
        framework_codes: resolvedFwCodes(),
        coverage_type: coverageType,
        scope_domains: [],
        suggested_domains: [],
        auditor_type: "interno",
        auditor_name: "",
        auditor_token: null,
        planned_date: `${year}-${["03","06","09","12"][q - 1]}-15`,
        actual_date: null,
        audit_prep_id: null,
        status: "planned",
        notes: "",
      })));
    }
    setLoadingSuggest(false);
  }

  const createMutation = useMutation({
    mutationFn: async () => {
      const fwIds = resolvedFwCodes().flatMap(code =>
        frameworks.filter(f => f.code === code).map(f => f.id)
      );
      const prog = await auditPrepApi.createProgram({
        plant: plantId,
        year,
        title: title || `Programma Audit ${year} — ${plantCode}`,
        coverage_type: coverageType,
        planned_audits: suggestedPlan,
        frameworks: fwIds,
        framework: fwIds[0] || null,
      });
      if (approveNow) {
        await auditPrepApi.approveProgram(prog.id);
      }
      return prog;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["audit-programs"] });
      onClose();
    },
  });

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-3xl max-h-[90vh] flex flex-col">
        <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold">Crea Programma Audit Annuale</h2>
            <div className="flex gap-1 mt-2">
              {[1, 2, 3, 4].map(s => (
                <div key={s} className={`w-8 h-1.5 rounded-full transition-colors ${s <= step ? "bg-primary-600" : "bg-gray-200"}`} />
              ))}
              <span className="text-xs text-gray-500 ml-2">Step {step}/4</span>
            </div>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">✕</button>
        </div>

        <div className="flex-1 overflow-auto p-6">
          {/* STEP 1 */}
          {step === 1 && (
            <div className="space-y-4">
              <h3 className="font-medium text-gray-800">Configurazione base</h3>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm text-gray-600 mb-1">Anno *</label>
                  <input type="number" value={year} onChange={e => setYear(parseInt(e.target.value))}
                    className="w-full border rounded px-3 py-2 text-sm" />
                </div>
                <div>
                  <label className="block text-sm text-gray-600 mb-1">Sito</label>
                  <input value={plantCode} disabled className="w-full border rounded px-3 py-2 text-sm bg-gray-50" />
                </div>
              </div>
              <div>
                <label className="block text-sm text-gray-600 mb-1">Titolo programma (opzionale)</label>
                <input value={title} onChange={e => setTitle(e.target.value)} placeholder={`Programma Audit ${year} — ${plantCode}`}
                  className="w-full border rounded px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="block text-sm text-gray-600 mb-2">Tipo di copertura default</label>
                <div className="space-y-2">
                  {([["campione", "Campione — 25% dei controlli, priorità ai gap"], ["esteso", "Esteso — 50% dei controlli"], ["full", "Full — 100% dei controlli"]] as const).map(([v, l]) => (
                    <label key={v} className={`flex items-center gap-3 border rounded-lg p-3 cursor-pointer ${coverageType === v ? "border-primary-500 bg-primary-50" : "border-gray-200"}`}>
                      <input type="radio" checked={coverageType === v} onChange={() => setCoverageType(v)} />
                      <span className="text-sm">{l}</span>
                    </label>
                  ))}
                </div>
                <p className="text-xs text-gray-400 mt-1">Puoi modificare la copertura per ogni singolo trimestre allo step 3.</p>
              </div>
            </div>
          )}

          {/* STEP 2 */}
          {step === 2 && (
            <div className="space-y-4">
              <h3 className="font-medium text-gray-800">Framework</h3>
              <div className="space-y-2">
                {displayFrameworks.map(fw => (
                  <label key={fw.code} className={`flex items-center gap-3 border rounded-lg p-3 cursor-pointer ${selectedFwCodes.includes(fw.code) ? "border-primary-500 bg-primary-50" : "border-gray-200"}`}>
                    <input type="checkbox" checked={selectedFwCodes.includes(fw.code)} onChange={() => toggleFw(fw.code)} />
                    <span className="text-sm font-medium">{fw.code}</span>
                    <span className="text-xs text-gray-500">{fw.name}</span>
                  </label>
                ))}
              </div>
              <label className={`flex items-center gap-3 border rounded-lg p-3 cursor-pointer mt-3 ${multiFw ? "border-primary-500 bg-primary-50" : "border-gray-200"}`}>
                <input type="checkbox" checked={multiFw} onChange={e => setMultiFw(e.target.checked)} />
                <div>
                  <p className="text-sm font-medium">Audit multi-framework</p>
                  <p className="text-xs text-gray-500">Un unico audit copre tutti i framework selezionati nello stesso trimestre</p>
                </div>
              </label>
            </div>
          )}

          {/* STEP 3 */}
          {step === 3 && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="font-medium text-gray-800">Piano suggerito dal sistema</h3>
                <button onClick={loadSuggest} disabled={loadingSuggest}
                  className="px-3 py-1.5 text-xs bg-primary-600 text-white rounded hover:bg-primary-700 disabled:opacity-50">
                  {loadingSuggest ? "Calcolo..." : "🔄 Rigenera suggerimento"}
                </button>
              </div>

              {suggestedPlan.length === 0 && (
                <div className="text-center py-8">
                  <p className="text-sm text-gray-500 mb-3">Genera il piano suggerito basato sui gap aperti</p>
                  <button onClick={loadSuggest} disabled={loadingSuggest}
                    className="px-4 py-2 bg-primary-600 text-white text-sm rounded hover:bg-primary-700 disabled:opacity-50">
                    {loadingSuggest ? "Calcolo in corso..." : "Genera piano suggerito"}
                  </button>
                </div>
              )}

              <div className="grid grid-cols-2 gap-4">
                {suggestedPlan.map(audit => {
                  const isEditing = editingQ === audit.id;
                  return (
                    <div key={audit.id} className="border border-gray-200 rounded-lg p-4">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-xs font-bold text-gray-500">Q{audit.quarter} — {QUARTER_MONTHS[audit.quarter]}</span>
                        <button onClick={() => { setEditingQ(isEditing ? null : audit.id); setEditForm(audit); }}
                          className="text-xs text-primary-600 hover:underline">
                          {isEditing ? "Chiudi" : "✏️ Modifica"}
                        </button>
                      </div>
                      {!isEditing ? (
                        <div className="space-y-1 text-xs text-gray-600">
                          <p><span className="font-medium">Data:</span> {audit.planned_date}</p>
                          <p><span className="font-medium">Framework:</span> {audit.framework_codes.map(fwLabel).join(", ") || "—"}</p>
                          <p><span className="font-medium">Copertura:</span> {coverageLabel(audit.coverage_type)}</p>
                          <p><span className="font-medium">Domini:</span> {audit.scope_domains.slice(0, 3).join(", ")}{audit.scope_domains.length > 3 ? ` +${audit.scope_domains.length - 3}` : ""}</p>
                          <p><span className="font-medium">Auditor:</span> {audit.auditor_type}</p>
                        </div>
                      ) : (
                        <div className="space-y-2">
                          <input type="date" value={editForm.planned_date || ""} onChange={e => setEditForm(p => ({ ...p, planned_date: e.target.value }))}
                            className="w-full border rounded px-2 py-1 text-xs" />
                          <select value={editForm.coverage_type || "campione"} onChange={e => setEditForm(p => ({ ...p, coverage_type: e.target.value as PlannedAudit["coverage_type"] }))}
                            className="w-full border rounded px-2 py-1 text-xs">
                            <option value="campione">Campione 25%</option>
                            <option value="esteso">Esteso 50%</option>
                            <option value="full">Full 100%</option>
                          </select>
                          <select value={editForm.auditor_type || "interno"} onChange={e => setEditForm(p => ({ ...p, auditor_type: e.target.value as "interno" | "esterno" }))}
                            className="w-full border rounded px-2 py-1 text-xs">
                            <option value="interno">Auditor interno</option>
                            <option value="esterno">Auditor esterno</option>
                          </select>
                          <input placeholder="Nome auditor" value={editForm.auditor_name || ""} onChange={e => setEditForm(p => ({ ...p, auditor_name: e.target.value }))}
                            className="w-full border rounded px-2 py-1 text-xs" />
                          <button onClick={() => {
                            setSuggestedPlan(prev => prev.map(a => a.id === audit.id ? { ...a, ...editForm } : a));
                            setEditingQ(null);
                          }} className="w-full py-1 bg-primary-600 text-white text-xs rounded">Salva</button>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
              {suggestedPlan.length > 0 && (
                <p className="text-xs text-gray-400 mt-2">Il sistema ha prioritizzato i domini con più controlli in stato GAP o PARZIALE.</p>
              )}
            </div>
          )}

          {/* STEP 4 */}
          {step === 4 && (
            <div className="space-y-4">
              <h3 className="font-medium text-gray-800">Riepilogo e conferma</h3>
              <div className="bg-gray-50 rounded-lg p-4 text-sm space-y-1">
                <p><span className="text-gray-500">Anno:</span> <strong>{year}</strong></p>
                <p><span className="text-gray-500">Titolo:</span> <strong>{title || `Programma Audit ${year} — ${plantCode}`}</strong></p>
                <p><span className="text-gray-500">Framework:</span> <strong>{selectedFwCodes.join(", ")}</strong></p>
                <p><span className="text-gray-500">Copertura default:</span> <strong>{coverageLabel(coverageType)}</strong></p>
              </div>
              <table className="w-full text-xs border border-gray-200 rounded">
                <thead className="bg-gray-100">
                  <tr>
                    <th className="px-3 py-2 text-left">Q</th>
                    <th className="px-3 py-2 text-left">Data</th>
                    <th className="px-3 py-2 text-left">Framework</th>
                    <th className="px-3 py-2 text-left">Copertura</th>
                    <th className="px-3 py-2 text-left">Domini</th>
                    <th className="px-3 py-2 text-left">Auditor</th>
                  </tr>
                </thead>
                <tbody>
                  {suggestedPlan.map(a => (
                    <tr key={a.id} className="border-t border-gray-100">
                      <td className="px-3 py-2 font-medium">Q{a.quarter}</td>
                      <td className="px-3 py-2">{a.planned_date}</td>
                      <td className="px-3 py-2">{a.framework_codes.join(", ")}</td>
                      <td className="px-3 py-2">{coverageLabel(a.coverage_type)}</td>
                      <td className="px-3 py-2">{a.scope_domains.length}</td>
                      <td className="px-3 py-2">{a.auditor_type}{a.auditor_name ? ` — ${a.auditor_name}` : ""}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <label className="flex items-center gap-2 cursor-pointer mt-2">
                <input type="checkbox" checked={approveNow} onChange={e => setApproveNow(e.target.checked)} />
                <span className="text-sm">Approva subito il programma</span>
              </label>
              {createMutation.isError && (
                <p className="text-xs text-red-600">Errore durante la creazione del programma</p>
              )}
            </div>
          )}
        </div>

        <div className="px-6 py-4 border-t border-gray-200 flex justify-between">
          <button onClick={() => step > 1 ? setStep(s => s - 1) : onClose()}
            className="px-4 py-2 border rounded text-sm text-gray-600 hover:bg-gray-50">
            {step === 1 ? "Annulla" : "← Indietro"}
          </button>
          {step < 4 ? (
            <button
              disabled={step === 2 && selectedFwCodes.length === 0}
              onClick={() => { if (step === 2) loadSuggest(); setStep(s => s + 1); }}
              className="px-4 py-2 bg-primary-600 text-white text-sm rounded hover:bg-primary-700 disabled:opacity-50">
              Avanti →
            </button>
          ) : (
            <button onClick={() => createMutation.mutate()} disabled={createMutation.isPending}
              className="px-4 py-2 bg-green-600 text-white text-sm rounded hover:bg-green-700 disabled:opacity-50">
              {createMutation.isPending ? "Creazione..." : "✅ Crea programma"}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── QuarterCard ──────────────────────────────────────────────────────────────

function QuarterCard({ audit, programId, onLaunched, onEdit }: {
  audit: PlannedAudit;
  programId: string;
  onLaunched: (prepId: string) => void;
  onEdit: () => void;
}) {
  const qc = useQueryClient();
  const [launching, setLaunching] = useState(false);
  const [confirmLaunch, setConfirmLaunch] = useState(false);
  const meta = AUDIT_STATUS_META[audit.status] ?? AUDIT_STATUS_META.planned;

  const launchMutation = useMutation({
    mutationFn: () => auditPrepApi.launchAudit(programId, audit.id),
    onSuccess: data => {
      qc.invalidateQueries({ queryKey: ["audit-programs"] });
      qc.invalidateQueries({ queryKey: ["audit-prep"] });
      setConfirmLaunch(false);
      onLaunched(data.audit_prep_id);
    },
  });

  return (
    <>
      <div className={`border rounded-xl p-4 ${meta.bg} border-gray-200`}>
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-bold text-gray-500">Q{audit.quarter} — {QUARTER_MONTHS[audit.quarter]}</span>
          <span className={`text-xs font-medium ${meta.color}`}>{meta.icon} {meta.label}</span>
        </div>
        <p className="text-sm font-medium text-gray-800 mb-2 leading-tight">{audit.title}</p>
        <div className="space-y-1 text-xs text-gray-600 mb-3">
          <p>📅 {audit.planned_date}</p>
          <div className="flex flex-wrap gap-1">
            {audit.framework_codes.map(c => (
              <span key={c} className="px-1.5 py-0.5 bg-white border border-gray-200 rounded text-gray-700">{fwLabel(c)}</span>
            ))}
          </div>
          <p>{coverageLabel(audit.coverage_type)} · {audit.auditor_type}</p>
          {audit.auditor_name && <p>👤 {audit.auditor_name}</p>}
          {audit.scope_domains.length > 0 && (
            <p className="text-gray-400">{audit.scope_domains.slice(0, 4).join(", ")}{audit.scope_domains.length > 4 ? ` +${audit.scope_domains.length - 4}` : ""}</p>
          )}
        </div>

        <div className="flex flex-wrap gap-1">
          {audit.status === "planned" && (
            <>
              <button onClick={onEdit} className="px-2 py-1 text-xs border border-gray-300 bg-white rounded hover:bg-gray-50">✏️ Modifica</button>
              <button onClick={() => setConfirmLaunch(true)} className="px-2 py-1 text-xs bg-primary-600 text-white rounded hover:bg-primary-700">▶ Avvia audit</button>
            </>
          )}
          {(audit.status === "in_progress") && audit.audit_prep_id && (
            <button onClick={() => onLaunched(audit.audit_prep_id!)} className="px-2 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700">→ Vai al prep</button>
          )}
          {audit.status === "completed" && (
            <span className="text-xs text-green-700">Score: {audit.audit_prep_id ? "vedi prep" : "—"}</span>
          )}
        </div>
      </div>

      {confirmLaunch && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-sm p-6">
            <h3 className="font-semibold mb-2">Avvia audit Q{audit.quarter}</h3>
            <div className="text-sm text-gray-600 space-y-1 mb-4">
              <p><strong>Framework:</strong> {audit.framework_codes.map(fwLabel).join(", ")}</p>
              <p><strong>Copertura:</strong> {coverageLabel(audit.coverage_type)}</p>
              {audit.auditor_name && <p><strong>Auditor:</strong> {audit.auditor_name}</p>}
            </div>
            {launchMutation.isError && (
              <p className="text-xs text-red-600 mb-2">
                {(launchMutation.error as { response?: { data?: { error?: string } } })?.response?.data?.error || "Errore"}
              </p>
            )}
            <div className="flex gap-2 justify-end">
              <button onClick={() => setConfirmLaunch(false)} className="px-4 py-2 border rounded text-sm">Annulla</button>
              <button onClick={() => launchMutation.mutate()} disabled={launchMutation.isPending}
                className="px-4 py-2 bg-primary-600 text-white text-sm rounded disabled:opacity-50">
                {launchMutation.isPending ? "Avvio..." : "Avvia"}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

// ─── EditAuditModal ───────────────────────────────────────────────────────────

function EditAuditModal({ audit, programId, onClose }: { audit: PlannedAudit; programId: string; onClose: () => void }) {
  const qc = useQueryClient();
  const [form, setForm] = useState<Partial<PlannedAudit>>({ ...audit });

  const saveMutation = useMutation({
    mutationFn: () => auditPrepApi.updateAudit(programId, audit.id, form as Record<string, unknown>),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["audit-programs"] }); onClose(); },
  });

  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6">
        <h3 className="font-semibold mb-4">Modifica audit Q{audit.quarter}</h3>
        <div className="space-y-3">
          <div>
            <label className="block text-xs text-gray-600 mb-1">Data pianificata</label>
            <input type="date" value={form.planned_date || ""} onChange={e => setForm(p => ({ ...p, planned_date: e.target.value }))}
              className="w-full border rounded px-3 py-2 text-sm" />
          </div>
          <div>
            <label className="block text-xs text-gray-600 mb-1">Copertura</label>
            <select value={form.coverage_type || "campione"} onChange={e => setForm(p => ({ ...p, coverage_type: e.target.value as PlannedAudit["coverage_type"] }))}
              className="w-full border rounded px-3 py-2 text-sm">
              <option value="campione">Campione 25%</option>
              <option value="esteso">Esteso 50%</option>
              <option value="full">Full 100%</option>
            </select>
          </div>
          <div>
            <label className="block text-xs text-gray-600 mb-1">Tipo auditor</label>
            <select value={form.auditor_type || "interno"} onChange={e => setForm(p => ({ ...p, auditor_type: e.target.value as "interno" | "esterno" }))}
              className="w-full border rounded px-3 py-2 text-sm">
              <option value="interno">Interno</option>
              <option value="esterno">Esterno</option>
            </select>
          </div>
          <div>
            <label className="block text-xs text-gray-600 mb-1">Nome auditor</label>
            <input value={form.auditor_name || ""} onChange={e => setForm(p => ({ ...p, auditor_name: e.target.value }))}
              className="w-full border rounded px-3 py-2 text-sm" />
          </div>
          <div>
            <label className="block text-xs text-gray-600 mb-1">Note</label>
            <textarea value={form.notes || ""} rows={2} onChange={e => setForm(p => ({ ...p, notes: e.target.value }))}
              className="w-full border rounded px-3 py-2 text-sm" />
          </div>
        </div>
        <div className="flex gap-2 justify-end mt-4">
          <button onClick={onClose} className="px-4 py-2 border rounded text-sm text-gray-600">Annulla</button>
          <button onClick={() => saveMutation.mutate()} disabled={saveMutation.isPending}
            className="px-4 py-2 bg-primary-600 text-white text-sm rounded disabled:opacity-50">
            {saveMutation.isPending ? "..." : "Salva modifiche"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── AuditPrepCard ────────────────────────────────────────────────────────────

function AuditPrepCard({ prep, onOpen, onDelete }: { prep: AuditPrep; onOpen: () => void; onDelete: () => void }) {
  const qc = useQueryClient();
  const { data: findings = [] } = useQuery<AuditFinding[]>({
    queryKey: ["findings", prep.id],
    queryFn: () => auditPrepApi.findings(prep.id),
    staleTime: 60_000,
  });
  const majorOpen = findings.filter(f => f.finding_type === "major_nc" && ["open", "in_response"].includes(f.status)).length;
  const minorOpen = findings.filter(f => f.finding_type === "minor_nc" && ["open", "in_response"].includes(f.status)).length;

  const statusColors: Record<string, string> = {
    in_corso:   "bg-blue-50 border-blue-200",
    completato: "bg-green-50 border-green-200",
    archiviato: "bg-gray-50 border-gray-200",
  };

  return (
    <div className={`border rounded-xl p-4 ${statusColors[prep.status] || "bg-white border-gray-200"}`}>
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2">
          <StatusBadge status={prep.status} />
          {prep.audit_entry_id && <span className="text-xs text-gray-400 border border-gray-200 rounded px-1.5 py-0.5">Prog.</span>}
        </div>
        <button onClick={onDelete} className="text-gray-300 hover:text-red-500 text-sm" title="Elimina">🗑</button>
      </div>
      <h3 className="font-semibold text-gray-900 mb-1">{prep.title}</h3>
      <p className="text-xs text-gray-500 mb-3">
        {fwLabel(prep.framework_code)} · {prep.auditor_name || "—"} · {prep.audit_date || "—"}
      </p>
      <ReadinessBar score={prep.readiness_score} />
      <div className="flex gap-3 mt-2 text-xs text-gray-500">
        {majorOpen > 0 && <span className="text-red-600 font-medium">⚠️ {majorOpen} Major NC</span>}
        {minorOpen > 0 && <span className="text-orange-600">{minorOpen} Minor NC</span>}
      </div>
      <div className="flex gap-2 mt-3">
        <button onClick={onOpen} className="flex-1 px-3 py-1.5 text-xs bg-primary-600 text-white rounded hover:bg-primary-700">Apri</button>
        <button onClick={() => auditPrepApi.downloadPrepReport(prep.id).then(r => downloadBlob(r.data as Blob, `AuditReport_${prep.id}.html`))}
          className="px-3 py-1.5 text-xs border border-gray-200 rounded text-gray-600 hover:bg-white">📄</button>
        {prep.status === "in_corso" && (
          <button onClick={onOpen} className="px-3 py-1.5 text-xs border border-red-200 text-red-600 rounded hover:bg-red-50">Finding</button>
        )}
      </div>
    </div>
  );
}

// ─── NewPrepModal ─────────────────────────────────────────────────────────────

function NewPrepModal({ plants, onClose }: { plants: { id: string; code: string; name: string }[]; onClose: () => void }) {
  const qc = useQueryClient();
  const [form, setForm] = useState<Partial<AuditPrep>>({});
  const [fwKey, setFwKey] = useState("");
  const [tisaxLevel, setTisaxLevel] = useState<"L2" | "L3">("L2");

  const { data: plantFws = [] } = useQuery({
    queryKey: ["plant-frameworks", form.plant],
    queryFn: () => plantsApi.plantFrameworks(form.plant!),
    enabled: !!form.plant,
  });

  const frameworks = plantFws.map(pf => ({ id: pf.framework, code: pf.framework_code, name: pf.framework_name }));
  useEffect(() => { setFwKey(""); setTisaxLevel("L2"); }, [form.plant]);

  const hasTisax = frameworks.some(f => f.code.startsWith("TISAX"));
  const nonTisax = frameworks.filter(f => !f.code.startsWith("TISAX"));

  function resolvedFrameworkId(): string | null {
    if (!fwKey) return null;
    if (fwKey === "TISAX") {
      const code = tisaxLevel === "L2" ? "TISAX_L2" : "TISAX_L3";
      return frameworks.find(f => f.code === code)?.id ?? null;
    }
    return fwKey;
  }

  const mutation = useMutation({
    mutationFn: () => auditPrepApi.create({ ...form, framework: resolvedFrameworkId() ?? undefined }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["audit-prep"] }); onClose(); },
  });

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-lg p-6">
        <h3 className="text-lg font-semibold mb-4">Nuova preparazione audit</h3>
        <div className="space-y-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Titolo *</label>
            <input name="title" onChange={e => setForm(p => ({ ...p, title: e.target.value || undefined }))}
              className="w-full border rounded px-3 py-2 text-sm" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Sito</label>
              <select name="plant" onChange={e => setForm(p => ({ ...p, plant: e.target.value || undefined }))}
                className="w-full border rounded px-3 py-2 text-sm">
                <option value="">— opzionale —</option>
                {plants.map(p => <option key={p.id} value={p.id}>{p.code} — {p.name}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Framework</label>
              <select value={fwKey} onChange={e => setFwKey(e.target.value)} disabled={!form.plant}
                className="w-full border rounded px-3 py-2 text-sm disabled:bg-gray-50 disabled:text-gray-400">
                {!form.plant
                  ? <option value="">— seleziona prima un sito —</option>
                  : frameworks.length === 0
                    ? <option value="">Nessun framework assegnato</option>
                    : <>
                        <option value="">— seleziona —</option>
                        {hasTisax && <option value="TISAX">TISAX — VDA ISA 6.0</option>}
                        {nonTisax.map(f => <option key={f.id} value={f.id}>{f.code} — {f.name}</option>)}
                      </>
                }
              </select>
            </div>
          </div>
          {fwKey === "TISAX" && (
            <div className="flex gap-3">
              {(["L2", "L3"] as const).map(l => (
                <label key={l} className={`flex-1 flex items-start gap-2 border rounded-lg px-3 py-2 cursor-pointer ${tisaxLevel === l ? "border-primary-500 bg-primary-50" : "border-gray-200"}`}>
                  <input type="radio" name="tisax_al" value={l} checked={tisaxLevel === l} onChange={() => setTisaxLevel(l)} className="mt-0.5" />
                  <div>
                    <p className="text-sm font-medium">Assessment Level {l}</p>
                    <p className="text-xs text-gray-500">{l === "L2" ? "Alta protezione — 40 controlli" : "Altissima protezione — 68 controlli (L2+L3)"}</p>
                  </div>
                </label>
              ))}
            </div>
          )}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Data audit</label>
              <input name="audit_date" type="date" onChange={e => setForm(p => ({ ...p, audit_date: e.target.value || null }))}
                className="w-full border rounded px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Auditor</label>
              <input name="auditor_name" onChange={e => setForm(p => ({ ...p, auditor_name: e.target.value }))}
                className="w-full border rounded px-3 py-2 text-sm" />
            </div>
          </div>
        </div>
        {mutation.isError && <p className="text-sm text-red-600 mt-2">Errore durante il salvataggio</p>}
        <div className="flex justify-end gap-2 mt-4">
          <button onClick={onClose} className="px-4 py-2 border rounded text-sm text-gray-600">Annulla</button>
          <button onClick={() => mutation.mutate()} disabled={mutation.isPending || !form.title}
            className="px-4 py-2 bg-primary-600 text-white rounded text-sm disabled:opacity-50">
            {mutation.isPending ? "Salvataggio..." : "Crea preparazione"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────

export function AuditPrepPage() {
  const qc = useQueryClient();
  const selectedPlant = useAuthStore(s => s.selectedPlant);
  const [mainTab, setMainTab] = useState<"program" | "preps">("program");
  const [showWizard, setShowWizard] = useState(false);
  const [showNewPrep, setShowNewPrep] = useState(false);
  const [openPrepId, setOpenPrepId] = useState<string | null>(null);
  const [editAudit, setEditAudit] = useState<{ programId: string; audit: PlannedAudit } | null>(null);
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [deleteProgramId, setDeleteProgramId] = useState<string | null>(null);

  const plantId = selectedPlant?.id;
  const plantParams = plantId ? { plant: plantId } : undefined;

  const { data: prepsData } = useQuery({
    queryKey: ["audit-prep", plantId],
    queryFn: () => auditPrepApi.list(plantParams),
  });

  const { data: programsData, isLoading: programsLoading } = useQuery({
    queryKey: ["audit-programs", plantId],
    queryFn: () => auditPrepApi.programs(plantParams),
  });

  const { data: plants = [] } = useQuery({
    queryKey: ["plants"],
    queryFn: () => plantsApi.list(),
  });

  const preps: AuditPrep[] = prepsData?.results ?? [];
  const programs: AuditProgram[] = programsData?.results ?? [];
  const openPrep = preps.find(p => p.id === openPrepId) ?? null;

  const deletePrepMutation = useMutation({
    mutationFn: (id: string) => auditPrepApi.deletePrep(id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["audit-prep"] }); setDeleteId(null); },
  });

  const deleteProgramMutation = useMutation({
    mutationFn: (id: string) => auditPrepApi.deleteProgram(id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["audit-programs"] }); setDeleteProgramId(null); },
  });

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold text-gray-900 flex items-center gap-2">
          Audit Preparation
          <ModuleHelp
            title="Audit Preparation — M17"
            description="Gestisce il programma audit annuale e l'esecuzione dei singoli audit. Il programma pianifica cosa auditare in ogni trimestre; i prep sono l'esecuzione concreta."
            steps={[
              "Crea il Programma Annuale con il wizard (inizio anno)",
              "Il sistema suggerisce i domini da auditare in base ai gap",
              "Prima del trimestre: clicca 'Avvia audit' per aprire il prep",
              "Durante l'audit: compila le evidenze e aggiungi i finding",
              "Major NC → PDCA automatico aperto",
              "Completa l'audit → relazione scaricabile",
              "Il programma aggiorna automaticamente il % completamento",
            ]}
            connections={[
              { module: "M03 Controlli", relation: "Evidenze collegate ai ControlInstance" },
              { module: "M11 PDCA", relation: "Major NC apre PDCA automatico" },
              { module: "M13 Management Review", relation: "Finding e score compaiono nello snapshot" },
              { module: "M08 Task", relation: "Reminder automatici 30gg/7gg prima dell'audit" },
            ]}
          />
        </h2>
        <div className="flex gap-2">
          {mainTab === "preps" && (
            <button onClick={() => setShowNewPrep(true)}
              className="px-3 py-1.5 bg-primary-600 text-white text-sm rounded hover:bg-primary-700">
              + Nuova preparazione
            </button>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-0 border-b border-gray-200 mb-6">
        {([["program", "📅 Programma Annuale"], ["preps", "🔍 Audit in corso"]] as const).map(([key, label]) => (
          <button key={key} onClick={() => setMainTab(key)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${mainTab === key ? "border-primary-600 text-primary-600" : "border-transparent text-gray-500 hover:text-gray-700"}`}>
            {label}
          </button>
        ))}
      </div>

      {/* ── TAB PROGRAMMA ANNUALE ── */}
      {mainTab === "program" && (
        <div>
          {programsLoading && <p className="text-sm text-gray-400">Caricamento...</p>}

          {!programsLoading && programs.length === 0 && (
            <div className="text-center py-16 bg-white border border-gray-200 rounded-xl">
              <div className="text-4xl mb-3">📅</div>
              <h3 className="text-lg font-semibold text-gray-800 mb-2">Nessun programma annuale</h3>
              <p className="text-sm text-gray-500 mb-6 max-w-md mx-auto">
                Il programma annuale definisce gli audit da eseguire nei 4 trimestri. Crea il primo per pianificare l'anno.
              </p>
              <button onClick={() => setShowWizard(true)} disabled={!plantId}
                className="px-6 py-2.5 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50">
                {plantId ? "Crea programma annuale" : "Seleziona un sito nel topbar"}
              </button>
            </div>
          )}

          {programs.map(prog => (
            <div key={prog.id} className="bg-white border border-gray-200 rounded-xl p-5 mb-6">
              {/* Header programma */}
              <div className="flex items-center justify-between mb-4">
                <div>
                  <div className="flex items-center gap-3">
                    <h3 className="text-base font-semibold text-gray-900">{prog.title}</h3>
                    <span className="text-sm text-gray-400">{prog.year}</span>
                    <StatusBadge status={prog.status} />
                  </div>
                  <div className="flex items-center gap-3 mt-1.5">
                    <div className="flex items-center gap-2 w-48">
                      <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden">
                        <div className="h-full bg-primary-500 rounded-full transition-all"
                          style={{ width: `${prog.completion_pct}%` }} />
                      </div>
                      <span className="text-xs text-gray-500">{prog.completion_pct}%</span>
                    </div>
                    <span className="text-xs text-gray-400">{coverageLabel(prog.coverage_type)}</span>
                  </div>
                </div>
                <div className="flex gap-2">
                  {prog.status === "bozza" && (
                    <button onClick={() => auditPrepApi.approveProgram(prog.id).then(() => qc.invalidateQueries({ queryKey: ["audit-programs"] }))}
                      className="px-3 py-1.5 text-xs bg-green-600 text-white rounded hover:bg-green-700">Approva</button>
                  )}
                  <button onClick={() => auditPrepApi.syncCompletion(prog.id).then(() => qc.invalidateQueries({ queryKey: ["audit-programs"] }))}
                    className="px-3 py-1.5 text-xs border border-gray-200 rounded text-gray-600 hover:bg-gray-50">🔄 Sync</button>
                  <button onClick={() => auditPrepApi.downloadProgramReport(prog.id).then(r => downloadBlob(r.data as Blob, `ProgrammaAudit_${prog.year}.html`))}
                    className="px-3 py-1.5 text-xs border border-gray-200 rounded text-gray-600 hover:bg-gray-50">📄 Relazione</button>
                  <button onClick={() => setDeleteProgramId(prog.id)}
                    className="px-3 py-1.5 text-xs border border-gray-200 rounded text-gray-400 hover:bg-red-50 hover:text-red-600 hover:border-red-200">🗑</button>
                </div>
              </div>

              {/* Timeline 4 trimestri */}
              <div className="grid grid-cols-4 gap-3">
                {[1, 2, 3, 4].map(q => {
                  const audit = prog.planned_audits.find(a => a.quarter === q);
                  if (!audit) return (
                    <div key={q} className="border border-dashed border-gray-200 rounded-xl p-4 text-center text-xs text-gray-300">
                      Q{q} — {QUARTER_MONTHS[q]}<br />Non pianificato
                    </div>
                  );
                  return (
                    <QuarterCard key={q} audit={audit} programId={prog.id}
                      onLaunched={prepId => { setMainTab("preps"); setOpenPrepId(prepId); }}
                      onEdit={() => setEditAudit({ programId: prog.id, audit })}
                    />
                  );
                })}
              </div>
            </div>
          ))}

          {!programsLoading && plantId && (
            <button onClick={() => setShowWizard(true)}
              className="mt-2 px-4 py-2 border border-dashed border-gray-300 text-sm text-gray-500 rounded-lg hover:bg-gray-50 w-full">
              + Aggiungi programma annuale
            </button>
          )}
        </div>
      )}

      {/* ── TAB AUDIT IN CORSO ── */}
      {mainTab === "preps" && (
        <div>
          {preps.length === 0 ? (
            <div className="text-center py-12 bg-white border border-gray-200 rounded-xl">
              <p className="text-sm text-gray-400">Nessuna preparazione audit</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {preps.map(prep => (
                <AuditPrepCard key={prep.id} prep={prep}
                  onOpen={() => setOpenPrepId(prep.id)}
                  onDelete={() => setDeleteId(prep.id)}
                />
              ))}
            </div>
          )}
        </div>
      )}

      {/* Drawer prep aperto */}
      {openPrep && <PrepDrawer prep={openPrep} onClose={() => setOpenPrepId(null)} />}

      {/* Wizard programma */}
      {showWizard && plantId && (
        <ProgramWizard
          plantId={plantId}
          plantCode={selectedPlant?.code ?? ""}
          onClose={() => setShowWizard(false)}
        />
      )}

      {/* Modal nuova preparazione manuale */}
      {showNewPrep && <NewPrepModal plants={plants} onClose={() => setShowNewPrep(false)} />}

      {/* Edit audit pianificato */}
      {editAudit && (
        <EditAuditModal audit={editAudit.audit} programId={editAudit.programId} onClose={() => setEditAudit(null)} />
      )}

      {/* Conferma elimina prep */}
      {deleteId && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-sm p-6">
            <h3 className="font-semibold mb-2">Elimina preparazione</h3>
            <p className="text-sm text-gray-600 mb-4">Operazione irreversibile. I finding verranno eliminati.</p>
            {deletePrepMutation.isError && (
              <p className="text-xs text-red-600 mb-3">
                {(deletePrepMutation.error as { response?: { data?: { error?: string } } })?.response?.data?.error || "Errore"}
              </p>
            )}
            <div className="flex justify-end gap-2">
              <button onClick={() => setDeleteId(null)} className="px-4 py-2 border rounded text-sm">Annulla</button>
              <button onClick={() => deletePrepMutation.mutate(deleteId)} disabled={deletePrepMutation.isPending}
                className="px-4 py-2 bg-red-600 text-white rounded text-sm disabled:opacity-50">
                {deletePrepMutation.isPending ? "..." : "Elimina"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Conferma elimina programma */}
      {deleteProgramId && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-sm p-6">
            <h3 className="font-semibold mb-2">Elimina programma</h3>
            <p className="text-sm text-gray-600 mb-4">Operazione irreversibile. Il programma annuale verrà eliminato.</p>
            <div className="flex justify-end gap-2">
              <button onClick={() => setDeleteProgramId(null)} className="px-4 py-2 border rounded text-sm">Annulla</button>
              <button onClick={() => deleteProgramMutation.mutate(deleteProgramId)} disabled={deleteProgramMutation.isPending}
                className="px-4 py-2 bg-red-600 text-white rounded text-sm disabled:opacity-50">
                {deleteProgramMutation.isPending ? "..." : "Elimina"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
