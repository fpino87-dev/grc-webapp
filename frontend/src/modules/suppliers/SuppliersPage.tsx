import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { suppliersApi, type Supplier } from "../../api/endpoints/suppliers";
import { StatusBadge } from "../../components/ui/StatusBadge";
import { apiClient } from "../../api/client";

function NewSupplierModal({ onClose }: { onClose: () => void }) {
  const qc = useQueryClient();
  const [form, setForm] = useState<Partial<Supplier>>({ risk_level: "basso", status: "attivo" });

  const mutation = useMutation({
    mutationFn: suppliersApi.create,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["suppliers"] }); onClose(); },
  });

  function handleChange(e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) {
    setForm(prev => ({ ...prev, [e.target.name]: e.target.value }));
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-lg p-6">
        <h3 className="text-lg font-semibold mb-4">Nuovo fornitore</h3>
        <div className="space-y-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Nome *</label>
            <input name="name" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">P.IVA</label>
              <input name="vat_number" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Paese</label>
              <input name="country" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" placeholder="IT" />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Livello rischio</label>
              <select name="risk_level" defaultValue="basso" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm">
                {["basso","medio","alto","critico"].map(r => <option key={r} value={r}>{r}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Scadenza contratto</label>
              <input name="contract_expiry" type="date" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" />
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
            {mutation.isPending ? "Salvataggio..." : "Crea fornitore"}
          </button>
        </div>
      </div>
    </div>
  );
}

function ExpiryCell({ date }: { date: string | null }) {
  if (!date) return <span className="text-gray-400">—</span>;
  const daysLeft = Math.ceil((new Date(date).getTime() - Date.now()) / (1000 * 60 * 60 * 24));
  const isNear = daysLeft < 30;
  return (
    <span className={isNear ? "text-red-600 font-medium" : "text-gray-600"}>
      {new Date(date).toLocaleDateString("it-IT")}
      {isNear && <span className="ml-1 text-xs">({daysLeft}gg)</span>}
    </span>
  );
}

type SupplierAssessment = {
  id: string;
  assessment_date: string | null;
  status: string;
  score_overall: number | null;
  score_governance: number | null;
  score_security: number | null;
  score_bcp: number | null;
  computed_risk_level: string;
  reviewed_by: string | null;
  reviewed_at: string | null;
  review_notes: string;
};

function AssessmentStatusBadge({ status }: { status: string }) {
  const map: Record<string, { label: string; classes: string }> = {
    pianificato: { label: "Pianificato", classes: "bg-gray-100 text-gray-700" },
    in_corso: { label: "In corso", classes: "bg-blue-100 text-blue-700" },
    completato: { label: "Completato", classes: "bg-amber-100 text-amber-800" },
    approvato: { label: "Approvato", classes: "bg-green-100 text-green-800" },
    rifiutato: { label: "Rifiutato", classes: "bg-red-100 text-red-800" },
  };
  const cfg = map[status] || { label: status, classes: "bg-gray-100 text-gray-700" };
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${cfg.classes}`}>
      {cfg.label}
    </span>
  );
}

function RiskLevelBadge({ level }: { level: string }) {
  const map: Record<string, { label: string; classes: string }> = {
    verde: { label: "Basso", classes: "bg-green-100 text-green-800" },
    giallo: { label: "Medio", classes: "bg-amber-100 text-amber-800" },
    rosso: { label: "Alto", classes: "bg-red-100 text-red-800" },
    nd: { label: "N/D", classes: "bg-gray-100 text-gray-600" },
  };
  const cfg = map[level] || map.nd;
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${cfg.classes}`}
      title="Basato sull'ultimo assessment approvato"
    >
      {cfg.label}
    </span>
  );
}

function AssessmentsTable({ supplierId }: { supplierId: string }) {
  const qc = useQueryClient();
  const [modal, setModal] = useState<
    | null
    | {
        type: "complete" | "approve" | "reject";
        assessment: SupplierAssessment;
      }
  >(null);
  const [scores, setScores] = useState({
    score_governance: "",
    score_security: "",
    score_bcp: "",
    score_overall: "",
    findings: "",
    notes: "",
  });
  const [error, setError] = useState("");

  const { data } = useQuery<{ results: SupplierAssessment[] }>({
    queryKey: ["supplier-assessments", supplierId],
    queryFn: async () => {
      const res = await apiClient.get("/suppliers/assessments/", { params: { supplier: supplierId } });
      return res.data;
    },
  });
  const assessments = data?.results ?? [];

  function openComplete(a: SupplierAssessment) {
    setModal({ type: "complete", assessment: a });
    setError("");
    setScores({
      score_governance: a.score_governance?.toString() ?? "",
      score_security: a.score_security?.toString() ?? "",
      score_bcp: a.score_bcp?.toString() ?? "",
      score_overall: a.score_overall?.toString() ?? "",
      findings: a.review_notes || "",
      notes: "",
    });
  }

  function openApprove(a: SupplierAssessment) {
    setModal({ type: "approve", assessment: a });
    setError("");
    setScores((prev) => ({ ...prev, notes: "" }));
  }

  function openReject(a: SupplierAssessment) {
    setModal({ type: "reject", assessment: a });
    setError("");
    setScores((prev) => ({ ...prev, notes: "" }));
  }

  function computeOverall(g: string, s: string, b: string) {
    const nums = [g, s, b].map((v) => (v ? Number(v) : NaN)).filter((v) => !Number.isNaN(v));
    if (!nums.length) return "";
    return Math.round(nums.reduce((acc, v) => acc + v, 0) / nums.length).toString();
  }

  const completeMutation = useMutation({
    mutationFn: async () => {
      if (!modal) return;
      const payload: any = {
        score_governance: scores.score_governance ? Number(scores.score_governance) : null,
        score_security: scores.score_security ? Number(scores.score_security) : null,
        score_bcp: scores.score_bcp ? Number(scores.score_bcp) : null,
        score_overall: scores.score_overall ? Number(scores.score_overall) : null,
        findings: scores.findings,
      };
      await apiClient.post(`/suppliers/assessments/${modal.assessment.id}/complete/`, payload);
    },
    onSuccess: () => {
      setModal(null);
      qc.invalidateQueries({ queryKey: ["supplier-assessments", supplierId] });
      qc.invalidateQueries({ queryKey: ["suppliers"] });
    },
    onError: (e: any) => {
      const msg = e?.response?.data?.error || "Errore nel completamento assessment.";
      setError(String(msg));
    },
  });

  const approveMutation = useMutation({
    mutationFn: async () => {
      if (!modal) return;
      await apiClient.post(`/suppliers/assessments/${modal.assessment.id}/approve/`, {
        notes: scores.notes,
      });
    },
    onSuccess: () => {
      setModal(null);
      qc.invalidateQueries({ queryKey: ["supplier-assessments", supplierId] });
      qc.invalidateQueries({ queryKey: ["suppliers"] });
    },
    onError: (e: any) => {
      const msg = e?.response?.data?.error || "Errore nell'approvazione assessment.";
      setError(String(msg));
    },
  });

  const rejectMutation = useMutation({
    mutationFn: async () => {
      if (!modal) return;
      await apiClient.post(`/suppliers/assessments/${modal.assessment.id}/reject/`, {
        notes: scores.notes,
      });
    },
    onSuccess: () => {
      setModal(null);
      qc.invalidateQueries({ queryKey: ["supplier-assessments", supplierId] });
      qc.invalidateQueries({ queryKey: ["suppliers"] });
    },
    onError: (e: any) => {
      const msg = e?.response?.data?.error || "Errore nel rifiuto assessment.";
      setError(String(msg));
    },
  });

  return (
    <div className="mt-3 border-t border-gray-100 pt-3">
      <h4 className="text-xs font-semibold text-gray-700 mb-2">Assessment fornitore</h4>
      <table className="w-full text-xs">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-2 py-1 text-left text-gray-600">Data</th>
            <th className="px-2 py-1 text-left text-gray-600">Governance</th>
            <th className="px-2 py-1 text-left text-gray-600">Security</th>
            <th className="px-2 py-1 text-left text-gray-600">BCP</th>
            <th className="px-2 py-1 text-left text-gray-600">Score</th>
            <th className="px-2 py-1 text-left text-gray-600">Risk</th>
            <th className="px-2 py-1 text-left text-gray-600">Stato</th>
            <th className="px-2 py-1 text-left text-gray-600">Azioni</th>
          </tr>
        </thead>
        <tbody>
          {assessments.map((a) => (
            <tr key={a.id} className="border-t border-gray-100">
              <td className="px-2 py-1">
                {a.assessment_date
                  ? new Date(a.assessment_date).toLocaleDateString("it-IT")
                  : "—"}
              </td>
              <td className="px-2 py-1">{a.score_governance ?? "—"}</td>
              <td className="px-2 py-1">{a.score_security ?? "—"}</td>
              <td className="px-2 py-1">{a.score_bcp ?? "—"}</td>
              <td className="px-2 py-1">{a.score_overall ?? "—"}</td>
              <td className="px-2 py-1">
                <RiskLevelBadge level={a.computed_risk_level} />
              </td>
              <td className="px-2 py-1">
                <AssessmentStatusBadge status={a.status} />
              </td>
              <td className="px-2 py-1">
                {["pianificato", "in_corso"].includes(a.status) && (
                  <button
                    type="button"
                    onClick={() => openComplete(a)}
                    className="px-2 py-1 rounded bg-primary-50 text-primary-700 hover:bg-primary-100"
                  >
                    Completa
                  </button>
                )}
                {a.status === "completato" && (
                  <div className="flex gap-1">
                    <button
                      type="button"
                      onClick={() => openApprove(a)}
                      className="px-2 py-1 rounded bg-green-50 text-green-700 hover:bg-green-100"
                    >
                      ✓ Approva
                    </button>
                    <button
                      type="button"
                      onClick={() => openReject(a)}
                      className="px-2 py-1 rounded bg-red-50 text-red-700 hover:bg-red-100"
                    >
                      ✗ Rifiuta
                    </button>
                  </div>
                )}
                {a.status === "approvato" && (
                  <span className="text-[11px] text-green-700">
                    Approvato il{" "}
                    {a.reviewed_at
                      ? new Date(a.reviewed_at).toLocaleDateString("it-IT")
                      : ""}
                  </span>
                )}
                {a.status === "rifiutato" && (
                  <span className="text-[11px] text-red-700">
                    Rifiutato: {a.review_notes || "—"}
                  </span>
                )}
              </td>
            </tr>
          ))}
          {!assessments.length && (
            <tr>
              <td className="px-2 py-2 text-gray-400" colSpan={8}>
                Nessun assessment registrato
              </td>
            </tr>
          )}
        </tbody>
      </table>

      {modal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-lg p-6">
            {modal.type === "complete" && (
              <>
                <h3 className="text-lg font-semibold mb-4">Completa assessment fornitore</h3>
                <div className="grid grid-cols-3 gap-3 mb-3">
                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-1">
                      Score Governance (0-100)
                    </label>
                    <input
                      type="number"
                      className="w-full border rounded px-2 py-1 text-xs"
                      value={scores.score_governance}
                      onChange={(e) =>
                        setScores((prev) => ({
                          ...prev,
                          score_governance: e.target.value,
                          score_overall: computeOverall(
                            e.target.value,
                            prev.score_security,
                            prev.score_bcp,
                          ),
                        }))
                      }
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-1">
                      Score Security (0-100)
                    </label>
                    <input
                      type="number"
                      className="w-full border rounded px-2 py-1 text-xs"
                      value={scores.score_security}
                      onChange={(e) =>
                        setScores((prev) => ({
                          ...prev,
                          score_security: e.target.value,
                          score_overall: computeOverall(
                            prev.score_governance,
                            e.target.value,
                            prev.score_bcp,
                          ),
                        }))
                      }
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-1">
                      Score BCP (0-100)
                    </label>
                    <input
                      type="number"
                      className="w-full border rounded px-2 py-1 text-xs"
                      value={scores.score_bcp}
                      onChange={(e) =>
                        setScores((prev) => ({
                          ...prev,
                          score_bcp: e.target.value,
                          score_overall: computeOverall(
                            prev.score_governance,
                            prev.score_security,
                            e.target.value,
                          ),
                        }))
                      }
                    />
                  </div>
                </div>
                <div className="mb-3">
                  <label className="block text-xs font-medium text-gray-700 mb-1">
                    Score Overall (0-100)
                  </label>
                  <input
                    type="number"
                    className="w-full border rounded px-2 py-1 text-xs"
                    value={scores.score_overall}
                    onChange={(e) =>
                      setScores((prev) => ({ ...prev, score_overall: e.target.value }))
                    }
                  />
                  <p className="mt-1 text-[11px] text-gray-500">
                    Calcolato automaticamente come media, ma modificabile manualmente.
                  </p>
                </div>
                <div className="mb-3">
                  <label className="block text-xs font-medium text-gray-700 mb-1">
                    Findings e osservazioni
                  </label>
                  <textarea
                    className="w-full border rounded px-2 py-1 text-xs min-h-[80px]"
                    value={scores.findings}
                    onChange={(e) =>
                      setScores((prev) => ({ ...prev, findings: e.target.value }))
                    }
                  />
                </div>
              </>
            )}

            {modal.type === "approve" && (
              <>
                <h3 className="text-lg font-semibold mb-4">Approva assessment</h3>
                <label className="block text-xs font-medium text-gray-700 mb-1">
                  Note (opzionali)
                </label>
                <textarea
                  className="w-full border rounded px-2 py-1 text-xs min-h-[80px]"
                  value={scores.notes}
                  onChange={(e) =>
                    setScores((prev) => ({ ...prev, notes: e.target.value }))
                  }
                />
              </>
            )}

            {modal.type === "reject" && (
              <>
                <h3 className="text-lg font-semibold mb-4">Rifiuta assessment</h3>
                <label className="block text-xs font-medium text-gray-700 mb-1">
                  Motivo rifiuto *
                </label>
                <textarea
                  className="w-full border rounded px-2 py-1 text-xs min-h-[80px]"
                  value={scores.notes}
                  onChange={(e) =>
                    setScores((prev) => ({ ...prev, notes: e.target.value }))
                  }
                  placeholder="Motivazione (minimo 10 caratteri)..."
                />
              </>
            )}

            {error && <p className="text-xs text-red-600 bg-red-50 px-3 py-2 rounded mt-2">{error}</p>}

            <div className="flex justify-end gap-2 mt-4">
              <button
                type="button"
                onClick={() => setModal(null)}
                className="px-4 py-2 border rounded text-sm text-gray-600 hover:bg-gray-50"
              >
                Annulla
              </button>
              {modal.type === "complete" && (
                <button
                  type="button"
                  onClick={() => completeMutation.mutate()}
                  disabled={completeMutation.isPending}
                  className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700 disabled:opacity-50"
                >
                  {completeMutation.isPending ? "Completamento..." : "Completa"}
                </button>
              )}
              {modal.type === "approve" && (
                <button
                  type="button"
                  onClick={() => approveMutation.mutate()}
                  disabled={approveMutation.isPending}
                  className="px-4 py-2 bg-green-600 text-white rounded text-sm hover:bg-green-700 disabled:opacity-50"
                >
                  {approveMutation.isPending ? "Approvazione..." : "Approva"}
                </button>
              )}
              {modal.type === "reject" && (
                <button
                  type="button"
                  onClick={() => rejectMutation.mutate()}
                  disabled={rejectMutation.isPending}
                  className="px-4 py-2 bg-red-600 text-white rounded text-sm hover:bg-red-700 disabled:opacity-50"
                >
                  {rejectMutation.isPending ? "Rifiuto..." : "Rifiuta"}
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export function SuppliersPage() {
  const [showNew, setShowNew] = useState(false);
  const [filterRisk, setFilterRisk] = useState("");
  const [filterStatus, setFilterStatus] = useState("");

  const params: Record<string, string> = {};
  if (filterRisk) params.risk_level = filterRisk;
  if (filterStatus) params.status = filterStatus;

  const { data, isLoading } = useQuery({
    queryKey: ["suppliers", filterRisk, filterStatus],
    queryFn: () => suppliersApi.list(Object.keys(params).length ? params : undefined),
    retry: false,
  });

  const suppliers = data?.results ?? [];

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold text-gray-900">Operazioni — Fornitori</h2>
        <button onClick={() => setShowNew(true)} className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700">
          + Nuovo fornitore
        </button>
      </div>

      <div className="flex items-center gap-3 mb-4">
        <label className="text-sm text-gray-600">Rischio:</label>
        <select value={filterRisk} onChange={e => setFilterRisk(e.target.value)} className="border rounded px-3 py-1.5 text-sm">
          <option value="">Tutti</option>
          {["basso","medio","alto","critico"].map(r => <option key={r} value={r}>{r}</option>)}
        </select>
        <label className="text-sm text-gray-600 ml-2">Stato:</label>
        <select value={filterStatus} onChange={e => setFilterStatus(e.target.value)} className="border rounded px-3 py-1.5 text-sm">
          <option value="">Tutti</option>
          {["attivo","sospeso","terminato"].map(s => <option key={s} value={s}>{s}</option>)}
        </select>
      </div>

      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-gray-400">Caricamento...</div>
        ) : suppliers.length === 0 ? (
          <div className="p-8 text-center text-gray-400">Nessun fornitore trovato</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Nome</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">P.IVA</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Paese</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Rischio</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Stato</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Scadenza contratto</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {suppliers.map((s) => (
                <tr key={s.id} className="align-top hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3 font-medium text-gray-800">
                    {s.name}
                    <div className="mt-1">
                      <span className="text-[11px] text-gray-500 mr-2">Rischio fornitore:</span>
                      <StatusBadge status={s.risk_level} />
                    </div>
                  </td>
                  <td className="px-4 py-3 text-gray-600">{s.vat_number || "—"}</td>
                  <td className="px-4 py-3 text-gray-600">{s.country || "—"}</td>
                  <td className="px-4 py-3">
                    <StatusBadge status={s.risk_level} />
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge status={s.status} />
                  </td>
                  <td className="px-4 py-3">
                    <ExpiryCell date={s.contract_expiry} />
                    <AssessmentStatusSection supplierId={s.id} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {showNew && <NewSupplierModal onClose={() => setShowNew(false)} />}
    </div>
  );
}
