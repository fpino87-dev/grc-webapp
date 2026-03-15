import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { auditPrepApi, type AuditFinding, type AuditPrep, type AuditProgram, type EvidenceItem, type PlannedAudit } from "../../api/endpoints/auditPrep";
import { plantsApi } from "../../api/endpoints/plants";
import { apiClient } from "../../api/client";
import { StatusBadge } from "../../components/ui/StatusBadge";

interface Framework { id: string; name: string; code: string; }

function ReadinessBar({ score }: { score: number | null }) {
  if (score === null) return <span className="text-gray-400 text-xs">—</span>;
  const color = score >= 80 ? "bg-green-500" : score >= 50 ? "bg-yellow-400" : "bg-red-500";
  return (
    <div className="flex items-center gap-2">
      <div className="w-24 h-2 bg-gray-200 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${score}%` }} />
      </div>
      <span className="text-xs text-gray-600">{score}%</span>
    </div>
  );
}

const FINDING_TYPE_LABELS: Record<string, string> = {
  major_nc:    "MAJOR NC",
  minor_nc:    "MINOR NC",
  observation: "OBS",
  opportunity: "OPP",
};

const FINDING_TYPE_COLORS: Record<string, string> = {
  major_nc:    "bg-red-100 text-red-700",
  minor_nc:    "bg-orange-100 text-orange-700",
  observation: "bg-blue-100 text-blue-700",
  opportunity: "bg-gray-100 text-gray-600",
};

function FindingPanel({ prepId }: { prepId: string }) {
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [closingId, setClosingId] = useState<string | null>(null);
  const [closeNotes, setCloseNotes] = useState("");
  const [form, setForm] = useState<Record<string, string>>({ finding_type: "major_nc" });

  const { data: findings = [], isLoading } = useQuery({
    queryKey: ["findings", prepId],
    queryFn: () => auditPrepApi.findings(prepId),
    retry: false,
  });

  const createMutation = useMutation({
    mutationFn: (data: Record<string, unknown>) => auditPrepApi.createFinding(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["findings", prepId] });
      setShowForm(false);
      setForm({ finding_type: "major_nc" });
    },
  });

  const closeMutation = useMutation({
    mutationFn: ({ id, notes }: { id: string; notes: string }) =>
      auditPrepApi.closeFinding(id, { closure_notes: notes }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["findings", prepId] });
      setClosingId(null);
      setCloseNotes("");
    },
  });

  const open = findings.filter((f: AuditFinding) => f.status === "open" || f.status === "in_response");
  const majorOpen = open.filter((f: AuditFinding) => f.finding_type === "major_nc").length;
  const minorOpen = open.filter((f: AuditFinding) => f.finding_type === "minor_nc").length;
  const overdue = findings.filter((f: AuditFinding) => f.is_overdue).length;

  return (
    <div className="px-6 py-4 bg-gray-50 border-t border-gray-200">
      {/* Dashboard summary */}
      {(majorOpen > 0 || minorOpen > 0 || overdue > 0) && (
        <div className="flex gap-3 mb-4">
          {majorOpen > 0 && (
            <span className="px-3 py-1.5 bg-red-100 text-red-700 text-xs font-medium rounded">
              {majorOpen} Major NC aperte
            </span>
          )}
          {minorOpen > 0 && (
            <span className="px-3 py-1.5 bg-orange-100 text-orange-700 text-xs font-medium rounded">
              {minorOpen} Minor NC aperte
            </span>
          )}
          {overdue > 0 && (
            <span className="px-3 py-1.5 bg-red-200 text-red-800 text-xs font-medium rounded">
              {overdue} finding scaduti
            </span>
          )}
        </div>
      )}

      <div className="flex items-center justify-between mb-3">
        <h4 className="text-sm font-semibold text-gray-700">Finding ({findings.length})</h4>
        <button
          onClick={() => setShowForm(s => !s)}
          className="text-xs px-2 py-1 bg-primary-600 text-white rounded hover:bg-primary-700"
        >
          + Aggiungi finding
        </button>
      </div>

      {showForm && (
        <div className="bg-white border border-gray-200 rounded p-3 mb-3 space-y-2">
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="block text-xs text-gray-600 mb-1">Tipo *</label>
              <select
                value={form.finding_type}
                onChange={e => setForm(p => ({ ...p, finding_type: e.target.value }))}
                className="w-full border rounded px-2 py-1.5 text-sm"
              >
                <option value="major_nc">Major Non Conformity</option>
                <option value="minor_nc">Minor Non Conformity</option>
                <option value="observation">Observation</option>
                <option value="opportunity">Opportunity for Improvement</option>
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-600 mb-1">Data audit *</label>
              <input
                type="date"
                value={form.audit_date ?? ""}
                onChange={e => setForm(p => ({ ...p, audit_date: e.target.value }))}
                className="w-full border rounded px-2 py-1.5 text-sm"
              />
            </div>
          </div>
          <input
            placeholder="Titolo *"
            value={form.title ?? ""}
            onChange={e => setForm(p => ({ ...p, title: e.target.value }))}
            className="w-full border rounded px-2 py-1.5 text-sm"
          />
          <textarea
            placeholder="Descrizione"
            value={form.description ?? ""}
            onChange={e => setForm(p => ({ ...p, description: e.target.value }))}
            rows={2}
            className="w-full border rounded px-2 py-1.5 text-sm"
          />
          <input
            placeholder="Nome auditor"
            value={form.auditor_name ?? ""}
            onChange={e => setForm(p => ({ ...p, auditor_name: e.target.value }))}
            className="w-full border rounded px-2 py-1.5 text-sm"
          />
          <div className="flex gap-2">
            <button
              onClick={() => createMutation.mutate({ ...form, audit_prep: prepId })}
              disabled={createMutation.isPending || !form.title || !form.audit_date}
              className="px-3 py-1.5 bg-primary-600 text-white text-xs rounded hover:bg-primary-700 disabled:opacity-50"
            >
              {createMutation.isPending ? "Salvataggio..." : "Crea finding"}
            </button>
            <button onClick={() => setShowForm(false)} className="px-3 py-1.5 border rounded text-xs text-gray-600 hover:bg-gray-50">
              Annulla
            </button>
          </div>
          {createMutation.isError && <p className="text-xs text-red-600">Errore durante il salvataggio</p>}
        </div>
      )}

      {isLoading ? (
        <p className="text-xs text-gray-400">Caricamento...</p>
      ) : findings.length === 0 ? (
        <p className="text-xs text-gray-400">Nessun finding registrato</p>
      ) : (
        <div className="space-y-2">
          {findings.map((f: AuditFinding) => (
            <div key={f.id} className="bg-white border border-gray-200 rounded px-3 py-2 text-sm">
              <div className="flex items-center gap-2 flex-wrap">
                <span className={`text-xs font-bold px-2 py-0.5 rounded ${FINDING_TYPE_COLORS[f.finding_type]}`}>
                  {FINDING_TYPE_LABELS[f.finding_type]}
                </span>
                <span className="font-medium text-gray-800 flex-1">{f.title}</span>
                <StatusBadge status={f.status} />
                {f.control_external_id && (
                  <span className="text-xs font-mono text-gray-500">{f.control_external_id}</span>
                )}
                {f.status !== "closed" && f.status !== "accepted_by_auditor" && (
                  <button
                    onClick={() => { setClosingId(f.id); setCloseNotes(""); }}
                    className="text-xs px-2 py-0.5 border rounded text-gray-600 hover:bg-gray-50"
                  >
                    Chiudi
                  </button>
                )}
              </div>
              {f.response_deadline && (
                <div className="mt-1 text-xs">
                  <span className={
                    f.is_overdue ? "text-red-600 font-medium" :
                    (f.days_remaining !== null && f.days_remaining <= 7) ? "text-orange-600" :
                    "text-gray-500"
                  }>
                    Scadenza: {new Date(f.response_deadline).toLocaleDateString("it-IT")}
                    {f.is_overdue ? " — SCADUTO" : f.days_remaining !== null ? ` (${f.days_remaining}gg)` : ""}
                  </span>
                  {f.pdca_cycle && <span className="ml-2 text-indigo-600">PDCA auto-creato</span>}
                </div>
              )}
              {f.status === "closed" && f.closed_by_name && (
                <p className="mt-1 text-xs text-green-700">
                  Chiuso da {f.closed_by_name} il {f.closed_at ? new Date(f.closed_at).toLocaleDateString("it-IT") : "—"}
                </p>
              )}

              {/* Modal chiusura inline */}
              {closingId === f.id && (
                <div className="mt-2 border-t pt-2 space-y-2">
                  <textarea
                    placeholder="Note di chiusura (obbligatorie per Major/Minor, min 20 caratteri)"
                    value={closeNotes}
                    onChange={e => setCloseNotes(e.target.value)}
                    rows={2}
                    className="w-full border rounded px-2 py-1.5 text-xs"
                  />
                  <div className="flex gap-2">
                    <button
                      onClick={() => closeMutation.mutate({ id: f.id, notes: closeNotes })}
                      disabled={closeMutation.isPending}
                      className="px-3 py-1 bg-green-600 text-white text-xs rounded hover:bg-green-700 disabled:opacity-50"
                    >
                      {closeMutation.isPending ? "..." : "Conferma chiusura"}
                    </button>
                    <button onClick={() => setClosingId(null)} className="px-3 py-1 border rounded text-xs text-gray-600">
                      Annulla
                    </button>
                  </div>
                  {closeMutation.isError && (
                    <p className="text-xs text-red-600">
                      Errore: {(closeMutation.error as { response?: { data?: { error?: string } } })?.response?.data?.error ?? "Errore durante la chiusura"}
                    </p>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function EvidencePanel({ prepId }: { prepId: string }) {
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [newEvidence, setNewEvidence] = useState<Partial<EvidenceItem>>({ status: "mancante" });

  const { data: evidence = [], isLoading } = useQuery({
    queryKey: ["evidence", prepId],
    queryFn: () => auditPrepApi.evidence(prepId),
    retry: false,
  });

  const createMutation = useMutation({
    mutationFn: (data: Partial<EvidenceItem>) => auditPrepApi.createEvidence({ ...data, audit_prep: prepId }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["evidence", prepId] }); setShowForm(false); setNewEvidence({ status: "mancante" }); },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) => auditPrepApi.updateEvidence(id, { status: status as EvidenceItem["status"] }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["evidence", prepId] }),
  });

  const evidenceStatusColor: Record<string, string> = {
    mancante: "bg-red-100 text-red-700",
    presente: "bg-green-100 text-green-700",
    scaduto: "bg-orange-100 text-orange-700",
  };

  return (
    <div className="px-6 py-4 bg-gray-50 border-t border-gray-200">
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-sm font-semibold text-gray-700">Evidenze</h4>
        <button onClick={() => setShowForm(s => !s)} className="text-xs px-2 py-1 bg-primary-600 text-white rounded hover:bg-primary-700">
          + Aggiungi evidenza
        </button>
      </div>

      {showForm && (
        <div className="bg-white border border-gray-200 rounded p-3 mb-3 space-y-2">
          <input
            placeholder="Descrizione evidenza *"
            value={newEvidence.description ?? ""}
            onChange={e => setNewEvidence(p => ({ ...p, description: e.target.value }))}
            className="w-full border rounded px-2 py-1.5 text-sm"
          />
          <div className="flex gap-2 items-center">
            <select
              value={newEvidence.status}
              onChange={e => setNewEvidence(p => ({ ...p, status: e.target.value as EvidenceItem["status"] }))}
              className="border rounded px-2 py-1.5 text-sm"
            >
              <option value="mancante">Mancante</option>
              <option value="presente">Presente</option>
              <option value="scaduto">Scaduto</option>
            </select>
            <input
              type="date"
              placeholder="Scadenza"
              value={newEvidence.due_date ?? ""}
              onChange={e => setNewEvidence(p => ({ ...p, due_date: e.target.value || null }))}
              className="border rounded px-2 py-1.5 text-sm"
            />
            <button
              onClick={() => createMutation.mutate(newEvidence)}
              disabled={createMutation.isPending || !newEvidence.description}
              className="px-3 py-1.5 bg-primary-600 text-white text-xs rounded hover:bg-primary-700 disabled:opacity-50"
            >
              Salva
            </button>
            <button onClick={() => setShowForm(false)} className="px-3 py-1.5 border rounded text-xs text-gray-600 hover:bg-gray-50">Annulla</button>
          </div>
        </div>
      )}

      {isLoading ? (
        <p className="text-xs text-gray-400">Caricamento...</p>
      ) : evidence.length === 0 ? (
        <p className="text-xs text-gray-400">Nessuna evidenza registrata</p>
      ) : (
        <div className="space-y-2">
          {evidence.map((item: EvidenceItem) => (
            <div key={item.id} className="flex items-center gap-3 text-sm bg-white rounded border border-gray-200 px-3 py-2">
              <select
                value={item.status}
                onChange={e => updateMutation.mutate({ id: item.id, status: e.target.value })}
                className={`text-xs rounded px-1.5 py-0.5 border-0 font-medium cursor-pointer ${evidenceStatusColor[item.status] ?? "bg-gray-100 text-gray-600"}`}
              >
                <option value="mancante">mancante</option>
                <option value="presente">presente</option>
                <option value="scaduto">scaduto</option>
              </select>
              <span className="text-gray-700 flex-1">{item.description}</span>
              {item.due_date && (
                <span className="text-gray-400 text-xs shrink-0">
                  scad. {new Date(item.due_date).toLocaleDateString("it-IT")}
                </span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function NewPrepModal({ frameworks, plants, onClose }: { frameworks: Framework[]; plants: { id: string; code: string; name: string }[]; onClose: () => void }) {
  const qc = useQueryClient();
  const [form, setForm] = useState<Partial<AuditPrep>>({});
  const [fwKey, setFwKey] = useState("");          // "TISAX" | framework.id | ""
  const [tisaxLevel, setTisaxLevel] = useState<"L2" | "L3">("L2");

  const hasTisax = frameworks.some(f => f.code.startsWith("TISAX"));
  const nonTisax = frameworks.filter(f => !f.code.startsWith("TISAX"));

  // Resolve the actual framework id to save
  function resolvedFrameworkId(): string | null {
    if (!fwKey) return null;
    if (fwKey === "TISAX") {
      const code = tisaxLevel === "L2" ? "TISAX_L2" : "TISAX_L3";
      return frameworks.find(f => f.code === code)?.id ?? null;
    }
    return fwKey;
  }

  const mutation = useMutation({
    mutationFn: () => auditPrepApi.create({ ...form, framework: resolvedFrameworkId() }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["audit-prep"] }); onClose(); },
  });

  function handleChange(e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) {
    setForm(prev => ({ ...prev, [e.target.name]: e.target.value || null }));
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-lg p-6">
        <h3 className="text-lg font-semibold mb-4">Nuova preparazione audit</h3>
        <div className="space-y-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Titolo *</label>
            <input name="title" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Sito</label>
              <select name="plant" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm">
                <option value="">— opzionale —</option>
                {plants.map(p => <option key={p.id} value={p.id}>{p.code} — {p.name}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Framework</label>
              <select
                value={fwKey}
                onChange={e => setFwKey(e.target.value)}
                className="w-full border rounded px-3 py-2 text-sm"
              >
                <option value="">— opzionale —</option>
                {hasTisax && <option value="TISAX">TISAX — VDA ISA 6.0</option>}
                {nonTisax.map(f => <option key={f.id} value={f.id}>{f.code} — {f.name}</option>)}
              </select>
            </div>
          </div>

          {/* TISAX level sub-selector */}
          {fwKey === "TISAX" && (
            <div className="flex gap-3">
              {(["L2", "L3"] as const).map(l => (
                <label key={l} className={`flex-1 flex items-start gap-2 border rounded-lg px-3 py-2 cursor-pointer transition-colors ${tisaxLevel === l ? "border-primary-500 bg-primary-50" : "border-gray-200 hover:border-gray-300"}`}>
                  <input type="radio" name="tisax_al" value={l} checked={tisaxLevel === l} onChange={() => setTisaxLevel(l)} className="mt-0.5" />
                  <div>
                    <p className="text-sm font-medium text-gray-800">Assessment Level {l}</p>
                    <p className="text-xs text-gray-500">{l === "L2" ? "Alta protezione" : "Altissima protezione + prototipi"}</p>
                  </div>
                </label>
              ))}
            </div>
          )}

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Data audit</label>
              <input name="audit_date" type="date" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Auditor</label>
              <input name="auditor_name" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" />
            </div>
          </div>
        </div>
        {mutation.isError && <p className="text-sm text-red-600 mt-2">Errore durante il salvataggio</p>}
        <div className="flex justify-end gap-2 mt-4">
          <button onClick={onClose} className="px-4 py-2 border rounded text-sm text-gray-600 hover:bg-gray-50">Annulla</button>
          <button
            onClick={() => mutation.mutate()}
            disabled={mutation.isPending || !form.title}
            className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700 disabled:opacity-50"
          >
            {mutation.isPending ? "Salvataggio..." : "Crea preparazione"}
          </button>
        </div>
      </div>
    </div>
  );
}

const AUDIT_STATUS_COLORS: Record<string, string> = {
  planned:   "bg-gray-100 text-gray-600",
  completed: "bg-green-100 text-green-700",
  cancelled: "bg-red-100 text-red-500",
};

function AuditProgramSection({ plantId, frameworks }: { plantId?: string; frameworks: Framework[] }) {
  const qc = useQueryClient();
  const [showNew, setShowNew] = useState(false);
  const [form, setForm] = useState<Partial<AuditProgram>>({});

  const params: Record<string, string> = {};
  if (plantId) params.plant = plantId;

  const { data, isLoading } = useQuery({
    queryKey: ["audit-programs", plantId],
    queryFn: () => auditPrepApi.programs(params),
    retry: false,
  });

  const createMutation = useMutation({
    mutationFn: (d: Partial<AuditProgram>) => auditPrepApi.createProgram(d),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["audit-programs"] }); setShowNew(false); setForm({}); },
  });

  const approveMutation = useMutation({
    mutationFn: (id: string) => auditPrepApi.approveProgram(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["audit-programs"] }),
  });

  const programs: AuditProgram[] = data?.results ?? [];

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-base font-semibold text-gray-800">Programma Audit Annuale</h3>
        <button onClick={() => setShowNew(s => !s)} className="px-3 py-1.5 bg-primary-600 text-white text-sm rounded hover:bg-primary-700">
          + Nuovo programma
        </button>
      </div>

      {showNew && (
        <div className="bg-white border border-gray-200 rounded p-4 mb-4 space-y-3">
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block text-xs text-gray-600 mb-1">Anno *</label>
              <input type="number" placeholder="2026" value={form.year ?? ""}
                onChange={e => setForm(p => ({ ...p, year: parseInt(e.target.value) }))}
                className="w-full border rounded px-2 py-1.5 text-sm" />
            </div>
            <div>
              <label className="block text-xs text-gray-600 mb-1">Framework *</label>
              <select value={form.framework ?? ""}
                onChange={e => setForm(p => ({ ...p, framework: e.target.value }))}
                className="w-full border rounded px-2 py-1.5 text-sm">
                <option value="">— seleziona —</option>
                {frameworks.map(f => <option key={f.id} value={f.id}>{f.code}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-600 mb-1">Sito *</label>
              <input placeholder="Plant ID" value={form.plant ?? plantId ?? ""}
                onChange={e => setForm(p => ({ ...p, plant: e.target.value }))}
                className="w-full border rounded px-2 py-1.5 text-sm" />
            </div>
          </div>
          <input placeholder="Titolo programma *" value={form.title ?? ""}
            onChange={e => setForm(p => ({ ...p, title: e.target.value }))}
            className="w-full border rounded px-2 py-1.5 text-sm" />
          <textarea placeholder="Obiettivi" value={form.objectives ?? ""} rows={2}
            onChange={e => setForm(p => ({ ...p, objectives: e.target.value }))}
            className="w-full border rounded px-2 py-1.5 text-sm" />
          <div className="flex gap-2">
            <button onClick={() => createMutation.mutate({ ...form, plant: form.plant || plantId })}
              disabled={createMutation.isPending || !form.title || !form.year || !form.framework}
              className="px-3 py-1.5 bg-primary-600 text-white text-xs rounded hover:bg-primary-700 disabled:opacity-50">
              {createMutation.isPending ? "..." : "Crea programma"}
            </button>
            <button onClick={() => setShowNew(false)} className="px-3 py-1.5 border rounded text-xs text-gray-600">Annulla</button>
          </div>
        </div>
      )}

      {isLoading ? <p className="text-sm text-gray-400">Caricamento...</p> : programs.length === 0 ? (
        <p className="text-sm text-gray-400">Nessun programma di audit definito</p>
      ) : (
        <div className="space-y-4">
          {programs.map(prog => (
            <div key={prog.id} className="bg-white border border-gray-200 rounded-lg p-4">
              <div className="flex items-center justify-between mb-3">
                <div>
                  <span className="font-semibold text-gray-800">{prog.title}</span>
                  <span className="ml-2 text-xs text-gray-500">{prog.year}</span>
                  <StatusBadge status={prog.status} />
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-xs text-gray-500">{prog.completion_pct}% completato</span>
                  {prog.status === "bozza" && (
                    <button onClick={() => approveMutation.mutate(prog.id)}
                      disabled={approveMutation.isPending}
                      className="px-2 py-1 text-xs bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50">
                      Approva
                    </button>
                  )}
                </div>
              </div>

              {/* Griglia 4 trimestri */}
              <div className="grid grid-cols-4 gap-2">
                {[1,2,3,4].map(q => {
                  const qAudits = prog.planned_audits.filter((a: PlannedAudit) => a.quarter === q);
                  return (
                    <div key={q} className="border border-gray-100 rounded p-2">
                      <div className="text-xs font-medium text-gray-500 mb-2">Q{q}</div>
                      {qAudits.length === 0 ? (
                        <div className="text-xs text-gray-300 italic">nessun audit</div>
                      ) : qAudits.map((a: PlannedAudit, i: number) => (
                        <div key={i} className={`text-xs rounded px-2 py-1 mb-1 ${AUDIT_STATUS_COLORS[a.status] ?? "bg-gray-50"}`}>
                          <div className="font-medium">{a.planned_date}</div>
                          <div className="text-gray-500">{a.auditor_type === "esterno" ? "Esterno" : "Interno"}</div>
                          {a.auditor_name && <div className="truncate">{a.auditor_name}</div>}
                        </div>
                      ))}
                    </div>
                  );
                })}
              </div>

              {prog.next_planned_audit && (
                <p className="mt-2 text-xs text-blue-600">
                  Prossimo audit: {prog.next_planned_audit.planned_date}
                  {prog.next_planned_audit.auditor_name && ` — ${prog.next_planned_audit.auditor_name}`}
                </p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function ExpandedPanel({ prepId }: { prepId: string }) {
  const [tab, setTab] = useState<"evidence"|"findings">("findings");
  return (
    <div>
      <div className="flex gap-0 border-t border-gray-200">
        <button
          onClick={() => setTab("findings")}
          className={`px-4 py-2 text-xs font-medium border-b-2 transition-colors ${tab === "findings" ? "border-primary-600 text-primary-600" : "border-transparent text-gray-500 hover:text-gray-700"}`}
        >
          Finding
        </button>
        <button
          onClick={() => setTab("evidence")}
          className={`px-4 py-2 text-xs font-medium border-b-2 transition-colors ${tab === "evidence" ? "border-primary-600 text-primary-600" : "border-transparent text-gray-500 hover:text-gray-700"}`}
        >
          Evidenze
        </button>
      </div>
      {tab === "findings" ? <FindingPanel prepId={prepId} /> : <EvidencePanel prepId={prepId} />}
    </div>
  );
}

export function AuditPrepPage() {
  const [showNew, setShowNew] = useState(false);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [mainTab, setMainTab] = useState<"preps"|"program">("preps");

  const { data, isLoading } = useQuery({
    queryKey: ["audit-prep"],
    queryFn: () => auditPrepApi.list(),
    retry: false,
  });

  const { data: frameworks = [] } = useQuery({
    queryKey: ["frameworks"],
    queryFn: () => apiClient.get<{ results: Framework[] }>("/controls/frameworks/").then(r => r.data.results),
    retry: false,
  });

  const { data: plants = [] } = useQuery({
    queryKey: ["plants"],
    queryFn: () => plantsApi.list(),
    retry: false,
  });

  const preps = data?.results ?? [];

  function toggleExpand(id: string) {
    setExpandedId(prev => (prev === id ? null : id));
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-xl font-semibold text-gray-900">Compliance — Audit Preparation</h2>
        {mainTab === "preps" && (
          <button onClick={() => setShowNew(true)} className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700">
            + Nuova preparazione
          </button>
        )}
      </div>

      {/* Tab navigation */}
      <div className="flex gap-0 border-b border-gray-200 mb-4">
        <button onClick={() => setMainTab("preps")}
          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${mainTab === "preps" ? "border-primary-600 text-primary-600" : "border-transparent text-gray-500 hover:text-gray-700"}`}>
          Preparazioni Audit
        </button>
        <button onClick={() => setMainTab("program")}
          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${mainTab === "program" ? "border-primary-600 text-primary-600" : "border-transparent text-gray-500 hover:text-gray-700"}`}>
          Programma Annuale
        </button>
      </div>

      {mainTab === "program" && (
        <AuditProgramSection frameworks={frameworks} />
      )}

      {mainTab === "preps" && <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-gray-400">Caricamento...</div>
        ) : preps.length === 0 ? (
          <div className="p-8 text-center text-gray-400">Nessuna preparazione audit registrata</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Titolo</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Sito</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Framework</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Data audit</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Auditor</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Readiness</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Stato</th>
              </tr>
            </thead>
            <tbody>
              {preps.map(prep => (
                <>
                  <tr
                    key={prep.id}
                    onClick={() => toggleExpand(prep.id)}
                    className="hover:bg-gray-50 transition-colors cursor-pointer border-b border-gray-100"
                  >
                    <td className="px-4 py-3 font-medium text-gray-800">
                      <span className="mr-2 text-gray-400 text-xs">{expandedId === prep.id ? "▼" : "▶"}</span>
                      {prep.title}
                    </td>
                    <td className="px-4 py-3 text-gray-600">{prep.plant || "—"}</td>
                    <td className="px-4 py-3 text-gray-600">{prep.framework || "—"}</td>
                    <td className="px-4 py-3 text-gray-500 text-xs">{prep.audit_date ? new Date(prep.audit_date).toLocaleDateString("it-IT") : "—"}</td>
                    <td className="px-4 py-3 text-gray-600">{prep.auditor_name || "—"}</td>
                    <td className="px-4 py-3"><ReadinessBar score={prep.readiness_score} /></td>
                    <td className="px-4 py-3"><StatusBadge status={prep.status} /></td>
                  </tr>
                  {expandedId === prep.id && (
                    <tr key={`${prep.id}-expanded`}>
                      <td colSpan={7} className="p-0">
                        <ExpandedPanel prepId={prep.id} />
                      </td>
                    </tr>
                  )}
                </>
              ))}
            </tbody>
          </table>
        )}
      </div>}

      {showNew && <NewPrepModal frameworks={frameworks} plants={plants} onClose={() => setShowNew(false)} />}
    </div>
  );
}
