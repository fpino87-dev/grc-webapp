import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "../../api/client";
import { AssessmentStatusBadge, RiskBadge, type SupplierAssessment } from "./supplierBadges";
import { useTranslation } from "react-i18next";

// ─── AssessmentsTable — Audit terze parti ────────────────────────────────────

export function AssessmentsTable({ supplierId }: { supplierId: string }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [modal, setModal] = useState<null | { type: "complete" | "approve" | "reject"; assessment: SupplierAssessment }>(null);
  const [scores, setScores] = useState({ score_governance: "", score_security: "", score_bcp: "", score_overall: "", findings: "", notes: "" });
  const [error, setError] = useState("");
  const [newDate, setNewDate] = useState("");
  const [showNewForm, setShowNewForm] = useState(false);

  const { data } = useQuery<{ results: SupplierAssessment[] }>({
    queryKey: ["supplier-assessments", supplierId],
    queryFn: async () => {
      const res = await apiClient.get("/suppliers/assessments/", { params: { supplier: supplierId } });
      return res.data;
    },
  });
  const assessments = data?.results ?? [];

  const newAssessmentMutation = useMutation({
    mutationFn: async () => {
      await apiClient.post("/suppliers/assessments/", {
        supplier: supplierId,
        assessment_date: newDate,
        status: "pianificato",
      });
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["supplier-assessments", supplierId] });
      setShowNewForm(false);
      setNewDate("");
    },
    onError: () => setError(t("suppliers.assessments.error_create")),
  });

  function computeOverall(g: string, s: string, b: string) {
    const nums = [g, s, b].map(v => (v ? Number(v) : NaN)).filter(v => !Number.isNaN(v));
    if (!nums.length) return "";
    return Math.round(nums.reduce((a, v) => a + v, 0) / nums.length).toString();
  }

  const completeMutation = useMutation({
    mutationFn: async () => {
      if (!modal) return;
      await apiClient.post(`/suppliers/assessments/${modal.assessment.id}/complete/`, {
        score_governance: scores.score_governance ? Number(scores.score_governance) : null,
        score_security:   scores.score_security   ? Number(scores.score_security)   : null,
        score_bcp:        scores.score_bcp        ? Number(scores.score_bcp)        : null,
        score_overall:    scores.score_overall     ? Number(scores.score_overall)    : null,
        findings: scores.findings,
      });
    },
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["supplier-assessments", supplierId] }); qc.invalidateQueries({ queryKey: ["suppliers"] }); setModal(null); },
    onError: () => setError(t("suppliers.assessments.error_complete")),
  });

  const approveMutation = useMutation({
    mutationFn: async () => {
      if (!modal) return;
      await apiClient.post(`/suppliers/assessments/${modal.assessment.id}/approve/`, { notes: scores.notes });
    },
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["supplier-assessments", supplierId] }); setModal(null); },
    onError: () => setError(t("suppliers.assessments.error_approve")),
  });

  const rejectMutation = useMutation({
    mutationFn: async () => {
      if (!modal) return;
      await apiClient.post(`/suppliers/assessments/${modal.assessment.id}/reject/`, { notes: scores.notes });
    },
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["supplier-assessments", supplierId] }); setModal(null); },
    onError: (e: any) => setError(e?.response?.data?.error || t("suppliers.assessments.error_generic")),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => apiClient.delete(`/suppliers/assessments/${id}/`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["supplier-assessments", supplierId] });
      qc.invalidateQueries({ queryKey: ["suppliers"] });
    },
  });

  return (
    <div className="px-4 pb-4 pt-2">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">{t("suppliers.assessments.section_title")}</span>
        {!showNewForm && (
          <button
            onClick={() => setShowNewForm(true)}
            className="text-xs text-indigo-600 border border-indigo-200 rounded px-2 py-0.5 hover:bg-indigo-50"
          >
            {t("suppliers.assessments.new_btn")}
          </button>
        )}
      </div>
      {showNewForm && (
        <div className="flex items-center gap-2 mb-3 p-2 bg-indigo-50 rounded">
          <label className="text-xs text-gray-600 shrink-0">{t("suppliers.assessments.date_label")}</label>
          <input
            type="date"
            value={newDate}
            onChange={e => setNewDate(e.target.value)}
            className="border rounded px-2 py-1 text-xs"
          />
          <button
            onClick={() => newAssessmentMutation.mutate()}
            disabled={newAssessmentMutation.isPending || !newDate}
            className="text-xs bg-indigo-600 text-white rounded px-2 py-1 disabled:opacity-50"
          >
            {newAssessmentMutation.isPending ? "..." : t("suppliers.assessments.register_btn")}
          </button>
          <button onClick={() => { setShowNewForm(false); setNewDate(""); }} className="text-xs text-gray-500 hover:text-gray-700">
            {t("actions.cancel")}
          </button>
          {error && <span className="text-xs text-red-600">{error}</span>}
        </div>
      )}
      {assessments.length === 0 ? (
        <p className="text-xs text-gray-400 italic">{t("suppliers.assessments.none")}</p>
      ) : (
        <table className="w-full text-xs">
          <thead><tr className="text-gray-500 border-b">
            <th className="text-left py-1 pr-3">{t("suppliers.assessments.col_date")}</th>
            <th className="text-left py-1 pr-3">Gov.</th>
            <th className="text-left py-1 pr-3">Sec.</th>
            <th className="text-left py-1 pr-3">BCP</th>
            <th className="text-left py-1 pr-3">{t("suppliers.assessments.col_overall")}</th>
            <th className="text-left py-1 pr-3">{t("suppliers.assessments.col_risk")}</th>
            <th className="text-left py-1 pr-3">{t("suppliers.assessments.col_status")}</th>
            <th className="py-1"></th>
          </tr></thead>
          <tbody>{assessments.map(a => (
            <tr key={a.id} className="border-b border-gray-50">
              <td className="py-1 pr-3">{a.assessment_date || "—"}</td>
              <td className="py-1 pr-3">{a.score_governance ?? "—"}</td>
              <td className="py-1 pr-3">{a.score_security ?? "—"}</td>
              <td className="py-1 pr-3">{a.score_bcp ?? "—"}</td>
              <td className="py-1 pr-3 font-semibold">{a.score_overall ?? "—"}</td>
              <td className="py-1 pr-3"><RiskBadge level={a.computed_risk_level} /></td>
              <td className="py-1 pr-3"><AssessmentStatusBadge status={a.status} /></td>
              <td className="py-1 space-x-1 whitespace-nowrap">
                {a.status === "pianificato" && <button onClick={() => { setModal({ type: "complete", assessment: a }); setError(""); setScores({ score_governance: "", score_security: "", score_bcp: "", score_overall: "", findings: "", notes: "" }); }} className="text-blue-600 hover:underline">{t("suppliers.assessments.complete")}</button>}
                {a.status === "completato"  && <><button onClick={() => { setModal({ type: "approve", assessment: a }); setError(""); setScores(p => ({...p, notes: ""})); }} className="text-green-600 hover:underline">{t("suppliers.assessments.approve")}</button><button onClick={() => { setModal({ type: "reject", assessment: a }); setError(""); setScores(p => ({...p, notes: ""})); }} className="ml-1 text-red-600 hover:underline">{t("suppliers.assessments.reject")}</button></>}
                <button
                  onClick={() => { if (window.confirm(t("suppliers.assessments.delete_confirm"))) deleteMutation.mutate(a.id); }}
                  disabled={deleteMutation.isPending}
                  className="ml-1 text-red-400 hover:text-red-600 disabled:opacity-40"
                  title={t("suppliers.assessments.delete_title")}
                >
                  ✕
                </button>
              </td>
            </tr>
          ))}</tbody>
        </table>
      )}

      {modal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-5">
            {modal.type === "complete" && (
              <>
                <h3 className="text-base font-semibold mb-3">{t("suppliers.assessments.modal_complete_title")}</h3>
                {["score_governance","score_security","score_bcp"].map(field => (
                  <div key={field} className="mb-2">
                    <label className="block text-xs font-medium text-gray-700 mb-0.5 capitalize">{field.replace("score_","").replace("_"," ")} (0-100)</label>
                    <input type="number" min={0} max={100} value={(scores as any)[field]} onChange={e => { const v = {...scores, [field]: e.target.value}; setScores({...v, score_overall: computeOverall(v.score_governance, v.score_security, v.score_bcp)}); }} className="w-full border rounded px-2 py-1 text-sm" />
                  </div>
                ))}
                <div className="mb-2">
                  <label className="block text-xs font-medium text-gray-700 mb-0.5">{t("suppliers.assessments.overall_auto")}</label>
                  <input type="number" value={scores.score_overall} readOnly className="w-full border rounded px-2 py-1 text-sm bg-gray-50" />
                </div>
                <div className="mb-3">
                  <label className="block text-xs font-medium text-gray-700 mb-0.5">{t("suppliers.assessments.findings_label")}</label>
                  <textarea value={scores.findings} onChange={e => setScores(p => ({...p, findings: e.target.value}))} className="w-full border rounded px-2 py-1 text-sm" rows={2} />
                </div>
                {error && <p className="text-xs text-red-600 mb-2">{error}</p>}
                <div className="flex justify-end gap-2">
                  <button onClick={() => setModal(null)} className="px-3 py-1.5 border rounded text-sm text-gray-600">{t("actions.cancel")}</button>
                  <button onClick={() => completeMutation.mutate()} disabled={completeMutation.isPending} className="px-3 py-1.5 bg-blue-600 text-white rounded text-sm disabled:opacity-50">
                    {completeMutation.isPending ? "..." : t("actions.save")}
                  </button>
                </div>
              </>
            )}
            {(modal.type === "approve" || modal.type === "reject") && (
              <>
                <h3 className="text-base font-semibold mb-3">{modal.type === "approve" ? t("suppliers.assessments.modal_approve_title") : t("suppliers.assessments.modal_reject_title")}</h3>
                <div className="mb-3">
                  <label className="block text-xs font-medium text-gray-700 mb-0.5">{t("suppliers.assessments.notes_label")} {modal.type === "reject" && t("suppliers.assessments.notes_min")}</label>
                  <textarea value={scores.notes} onChange={e => setScores(p => ({...p, notes: e.target.value}))} className="w-full border rounded px-2 py-1 text-sm" rows={3} />
                </div>
                {error && <p className="text-xs text-red-600 mb-2">{error}</p>}
                <div className="flex justify-end gap-2">
                  <button onClick={() => setModal(null)} className="px-3 py-1.5 border rounded text-sm text-gray-600">{t("actions.cancel")}</button>
                  <button onClick={() => modal.type === "approve" ? approveMutation.mutate() : rejectMutation.mutate()} disabled={approveMutation.isPending || rejectMutation.isPending} className={`px-3 py-1.5 text-white rounded text-sm disabled:opacity-50 ${modal.type === "approve" ? "bg-green-600" : "bg-red-600"}`}>
                    {approveMutation.isPending || rejectMutation.isPending ? "..." : modal.type === "approve" ? t("suppliers.assessments.approve") : t("suppliers.assessments.reject")}
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
