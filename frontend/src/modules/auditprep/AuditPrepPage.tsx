import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { auditPrepApi, type AuditPrep, type EvidenceItem } from "../../api/endpoints/auditPrep";
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

export function AuditPrepPage() {
  const [showNew, setShowNew] = useState(false);
  const [expandedId, setExpandedId] = useState<string | null>(null);

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
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold text-gray-900">Compliance — Audit Preparation</h2>
        <button onClick={() => setShowNew(true)} className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700">
          + Nuova preparazione
        </button>
      </div>

      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
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
                    <tr key={`${prep.id}-evidence`}>
                      <td colSpan={7} className="p-0">
                        <EvidencePanel prepId={prep.id} />
                      </td>
                    </tr>
                  )}
                </>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {showNew && <NewPrepModal frameworks={frameworks} plants={plants} onClose={() => setShowNew(false)} />}
    </div>
  );
}
