import { Fragment, useEffect, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useLocation } from "react-router-dom";
import { scrollAndHighlight } from "../../lib/scrollAndHighlight";
import { riskApi, type RiskAssessment, THREAT_CATEGORIES } from "../../api/endpoints/risk";
import { plantsApi } from "../../api/endpoints/plants";
import { useAuthStore } from "../../store/auth";
import { AssistenteValutazione } from "../../components/ui/AssistenteValutazione";
import { ModuleHelp } from "../../components/ui/ModuleHelp";
import { RiskContinuityWizard } from "./RiskContinuityWizard";
import { RiskIntegratedRegisters } from "./RiskIntegratedRegisters";
import { matrixColor, formatAle, riskLevelFromScore, isActiveTreatment } from "./riskUtils";
import { RiskLevelBadge, RiskInherentResidualBadges, TreatmentDeadlineBadge, EffectiveStatusBadge } from "./RiskBadges";
import { SuggestResidualPanel, FormalAcceptancePanel } from "./RiskDetailPanels";
import { MitigationPanel } from "./MitigationPanel";
import { NewAssessmentModal } from "./NewAssessmentModal";
import { EditAssessmentModal } from "./EditAssessmentModal";
import { RiskAppetiteCard } from "./RiskAppetiteCard";
import { useTranslation } from "react-i18next";

export function RiskPage() {
  const { t } = useTranslation();
  const location = useLocation();
  const [typeFilter, setTypeFilter] = useState<"" | "IT" | "OT">("");
  const [statusFilter, setStatusFilter] = useState("");
  const [treatmentFilter, setTreatmentFilter] = useState("");
  const [incompleteFilter, setIncompleteFilter] = useState(false);
  const [showNew, setShowNew] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [showWizard, setShowWizard] = useState(false);
  const [editAssessment, setEditAssessment] = useState<RiskAssessment | null>(null);
  const selectedPlant = useAuthStore(s => s.selectedPlant);
  const qc = useQueryClient();

  // Deep-link dal govrico Assistant: scrolla ed evidenzia la riga del rischio.
  useEffect(() => {
    const state = location.state as { openRiskId?: string } | null;
    if (state?.openRiskId) {
      setExpandedId(state.openRiskId);
      scrollAndHighlight(state.openRiskId);
    }
  }, [location.state]);

  const params: Record<string, string> = { page_size: "200" };
  if (typeFilter) params.assessment_type = typeFilter;
  if (statusFilter) params.status = statusFilter;
  if (treatmentFilter) params.treatment = treatmentFilter;
  if (selectedPlant?.id) params.plant = selectedPlant.id;

  const { data, isLoading } = useQuery({
    queryKey: ["risk-assessments", typeFilter, statusFilter, treatmentFilter, selectedPlant?.id],
    queryFn: () => riskApi.list(params),
    retry: false,
  });

  const { data: plants } = useQuery({ queryKey: ["plants"], queryFn: () => plantsApi.list(), retry: false });

  const completeMutation = useMutation({
    mutationFn: (id: string) => riskApi.complete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["risk-assessments"] }),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => riskApi.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["risk-assessments"] }),
  });

  const reopenMutation = useMutation({
    mutationFn: (id: string) => riskApi.reopen(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["risk-assessments"] }),
  });

  const rawAssessments: RiskAssessment[] = data?.results ?? [];

  function isIncomplete(a: RiskAssessment): boolean {
    if (a.status === "archiviato") return false;
    if (a.status === "bozza") return true;
    const isActive = isActiveTreatment(a.treatment);
    const allPlansDone = a.mitigation_plans_count > 0 && a.mitigation_plans_completed === a.mitigation_plans_count;
    const isVerde = a.score !== null && riskLevelFromScore(a.score) === "verde";
    if (isActive && !allPlansDone) return true;
    if (!isVerde && !a.risk_accepted_formally) return true;
    if (a.needs_revaluation) return true;
    return false;
  }

  const assessments = incompleteFilter ? rawAssessments.filter(isIncomplete) : rawAssessments;

  return (
    <div>
      <RiskAppetiteCard plantId={selectedPlant?.id} />
      <RiskIntegratedRegisters plantId={selectedPlant?.id} />
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold text-gray-900 flex items-center">
          Risk Assessment
          <ModuleHelp
            title={t("eval_assistant.risk_module.title")}
            description={t("eval_assistant.risk_module.description")}
            steps={[
              t("eval_assistant.risk_module.steps.1"),
              t("eval_assistant.risk_module.steps.2"),
              t("eval_assistant.risk_module.steps.3"),
              t("eval_assistant.risk_module.steps.4"),
              t("eval_assistant.risk_module.steps.5"),
              t("eval_assistant.risk_module.steps.6"),
            ]}
            connections={[
              { module: "M04 Asset", relation: t("eval_assistant.risk_module.connections.assets") },
              { module: "M05 BIA", relation: t("eval_assistant.risk_module.connections.bia") },
              { module: "M00 Governance", relation: t("eval_assistant.risk_module.connections.governance") },
              { module: "M11 PDCA", relation: t("eval_assistant.risk_module.connections.pdca") },
              { module: "M08 Task", relation: t("eval_assistant.risk_module.connections.tasks") },
            ]}
            configNeeded={[
              t("eval_assistant.risk_module.config_needed.1"),
              t("eval_assistant.risk_module.config_needed.2"),
            ]}
          />
        </h2>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowWizard(true)}
            className="flex items-center gap-2 px-4 py-2 border border-primary-200 text-primary-700 rounded-lg hover:bg-primary-50 text-sm font-medium"
          >
            <span>🧭</span> {t("risk.wizard_title")}
          </button>
          <button
            onClick={() => setDrawerOpen(true)}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm font-medium"
          >
            <span>?</span> {t("risk.guide_btn")}
          </button>
          <button
            onClick={async () => {
              try {
                const resp = await riskApi.exportExcel({ plant: selectedPlant?.id, include_draft: false });
                const url = window.URL.createObjectURL(new Blob([resp.data]));
                const a = document.createElement("a");
                a.href = url;
                a.download = `risk_register${selectedPlant?.id ? `_${selectedPlant.code}` : ""}.xlsx`;
                a.click();
                window.URL.revokeObjectURL(url);
              } catch {
                window.alert(t("risk.error_generic"));
              }
            }}
            className="flex items-center gap-2 px-4 py-2 border border-green-300 text-green-700 rounded-lg hover:bg-green-50 text-sm font-medium"
          >
            <span>⬇</span> {t("risk.export_excel")}
          </button>
          <button onClick={() => setShowNew(true)} className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700">
            + {t("risk.new_btn")}
          </button>
        </div>
      </div>

      <div className="mb-4 flex items-center gap-3">
        <div>
          <label className="text-xs text-gray-500 mr-1">{t("risk.filter_type")}:</label>
          <select value={typeFilter} onChange={e => setTypeFilter(e.target.value as "" | "IT" | "OT")}
            className="border rounded px-2 py-1.5 text-sm">
            <option value="">{t("risk.filter_all")}</option>
            <option value="IT">IT</option>
            <option value="OT">OT</option>
          </select>
        </div>
        <div>
          <label className="text-xs text-gray-500 mr-1">{t("risk.filter_status")}:</label>
          <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}
            className="border rounded px-2 py-1.5 text-sm">
            <option value="">{t("risk.filter_all")}</option>
            <option value="bozza">{t("status.bozza")}</option>
            <option value="completato">{t("status.completato")}</option>
            <option value="archiviato">{t("risk.status_archiviato")}</option>
          </select>
        </div>
        <div>
          <label className="text-xs text-gray-500 mr-1">{t("risk.filter_treatment")}:</label>
          <select value={treatmentFilter} onChange={e => setTreatmentFilter(e.target.value)}
            className="border rounded px-2 py-1.5 text-sm">
            <option value="">{t("risk.filter_all")}</option>
            <option value="mitigare">{t("risk.treatment_mitigare")}</option>
            <option value="trasferire">{t("risk.treatment_trasferire")}</option>
            <option value="accettare">{t("risk.treatment_accettare")}</option>
            <option value="evitare">{t("risk.treatment_evitare")}</option>
          </select>
        </div>
        <div>
          <label className="text-xs text-gray-500 mr-1">{t("risk.filter_completeness")}:</label>
          <select value={incompleteFilter ? "incomplete" : ""} onChange={e => setIncompleteFilter(e.target.value === "incomplete")}
            className="border rounded px-2 py-1.5 text-sm">
            <option value="">{t("risk.filter_all")}</option>
            <option value="incomplete">{t("risk.filter_incomplete")}</option>
          </select>
        </div>
      </div>

      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-gray-400">{t("common.loading")}</div>
        ) : assessments.length === 0 ? (
          <div className="p-8 text-center">
            <p className="text-gray-400 mb-2">{t("risk.empty")}</p>
            <button onClick={() => setShowNew(true)} className="text-sm text-primary-600 hover:underline">{t("risk.create_first")} →</button>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-600 w-8"></th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("risk.col_scenario")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("risk.col_threat")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Owner</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("risk.col_inherent")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("risk.col_residual")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("risk.col_score", "Score")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("risk.col_weighted")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("risk.col_ale")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("risk.filter_status")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("risk.plan_col_header")}</th>
                <th className="text-left px-4 py-3 font-medium text-blue-700 bg-blue-50">NIS2</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody>
              {assessments.map(a => (
                <Fragment key={a.id}>
                  <tr
                    data-row-id={a.id}
                    onClick={() => setExpandedId(prev => prev === a.id ? null : a.id)}
                    className="hover:bg-gray-50 transition-colors cursor-pointer border-b border-gray-100"
                  >
                    <td className="px-4 py-3 text-gray-400 text-xs">{expandedId === a.id ? "▼" : "▶"}</td>
                    <td className="px-4 py-3">
                      <div className="font-medium text-gray-800">{a.name || <span className="text-gray-400 italic">—</span>}</div>
                      <div className="text-xs text-gray-400">{a.assessment_type}{a.critical_process_name && ` · ${a.critical_process_name}`}</div>
                    </td>
                    <td className="px-4 py-3 text-gray-600 text-xs">
                      {(() => { const cat = THREAT_CATEGORIES.find(c => c.value === a.threat_category); return cat ? t(cat.label) : "—"; })()}
                    </td>
                    <td className="px-4 py-3 text-gray-600 text-xs">{a.owner_name ?? <span className="text-gray-300">—</span>}</td>
                    <td className="px-4 py-3 text-gray-600">
                      <div className="space-y-1">
                        <div>
                          {a.inherent_probability && a.inherent_impact
                            ? (
                              <span className={`text-xs font-mono font-bold px-1.5 py-0.5 rounded inline-block ${matrixColor(a.inherent_probability, a.inherent_impact)}`}>
                                {a.inherent_probability}×{a.inherent_impact}
                              </span>
                            )
                            : <span className="text-gray-400">—</span>}
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-gray-600">
                      <div className="space-y-1">
                        <div>
                          {a.probability && a.impact
                            ? (
                              <span className={`text-xs font-mono font-bold px-1.5 py-0.5 rounded inline-block ${matrixColor(a.probability, a.impact)}`}>
                                {a.probability}×{a.impact}
                              </span>
                            )
                            : <span className="text-gray-400">—</span>}
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="space-y-1">
                        <RiskLevelBadge score={a.score} />
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="space-y-1">
                        <RiskLevelBadge score={a.weighted_score} />
                        <div className="text-xs text-gray-500">{t("risk.weighted_on_bia")}</div>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-gray-600 text-xs">
                      <div className="space-y-1">
                        {a.ale_calcolato
                          ? <span className="text-blue-700 font-medium">{formatAle(a.ale_calcolato)}</span>
                          : <span>{formatAle(a.ale_annuo)}</span>}
                        <div className="text-xs text-gray-500">
                          {a.critical_process_name
                            ? (a.ale_calcolato ? t("risk.ale_calculated") : t("risk.ale_estimate"))
                            : t("risk.ale_no_bia")}
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <EffectiveStatusBadge assessment={a} />
                    </td>
                    <td className="px-4 py-3">
                      <TreatmentDeadlineBadge assessment={a} />
                    </td>
                    <td className="px-4 py-3 bg-blue-50/30" onClick={e => e.stopPropagation()}>
                      <div className="space-y-1">
                        {a.nis2_art21_category && (
                          <span className="block text-xs px-1.5 py-0.5 rounded bg-blue-100 text-blue-800 font-mono whitespace-nowrap">
                            {a.nis2_art21_category.replace("art21_", "Art.21(2)(").concat(")")}
                          </span>
                        )}
                        {a.nis2_relevance && (
                          <span className={`block text-xs px-1.5 py-0.5 rounded whitespace-nowrap ${
                            a.nis2_relevance === "significativo" ? "bg-red-100 text-red-700" :
                            a.nis2_relevance === "potenzialmente_significativo" ? "bg-orange-100 text-orange-700" :
                            "bg-gray-100 text-gray-600"
                          }`}>
                            {a.nis2_relevance === "significativo" ? t("risk.nis2_sig") :
                             a.nis2_relevance === "potenzialmente_significativo" ? t("risk.nis2_pot_sig") :
                             a.nis2_relevance === "non_significativo" ? t("risk.nis2_non_sig") : "—"}
                          </span>
                        )}
                        {!a.nis2_art21_category && !a.nis2_relevance && <span className="text-xs text-gray-300">—</span>}
                      </div>
                    </td>
                    <td className="px-3 py-3 whitespace-nowrap" onClick={e => e.stopPropagation()}>
                      <div className="flex items-center gap-1">
                        {a.status === "bozza" && !!a.probability && !!a.impact && (
                          <button onClick={() => completeMutation.mutate(a.id)} disabled={completeMutation.isPending}
                            className="text-xs text-blue-700 border border-blue-300 rounded px-2 py-1 hover:bg-blue-50 disabled:opacity-50 font-medium">
                            {t("risk.complete_btn")}
                          </button>
                        )}
                        {a.status === "completato" && (
                          <button
                            onClick={() => {
                              if (window.confirm(t("risk.reopen_confirm"))) reopenMutation.mutate(a.id);
                            }}
                            disabled={reopenMutation.isPending}
                            title={t("risk.reopen_label")}
                            className="p-1.5 text-gray-400 hover:text-orange-600 hover:bg-orange-50 rounded transition-colors disabled:opacity-50"
                          >
                            <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4" viewBox="0 0 20 20" fill="currentColor">
                              <path fillRule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clipRule="evenodd" />
                            </svg>
                          </button>
                        )}
                        {a.status !== "archiviato" && (
                          <button
                            onClick={() => setEditAssessment(a)}
                            title={t("risk.edit_btn")}
                            className="p-1.5 text-gray-500 hover:text-purple-700 hover:bg-purple-50 rounded transition-colors"
                          >
                            <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4" viewBox="0 0 20 20" fill="currentColor">
                              <path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z" />
                            </svg>
                          </button>
                        )}
                        <button
                          onClick={() => {
                            if (window.confirm(t("risk.delete_confirm"))) {
                              deleteMutation.mutate(a.id);
                            }
                          }}
                          disabled={deleteMutation.isPending}
                          title={t("risk.delete_btn")}
                          className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded transition-colors disabled:opacity-50"
                        >
                          <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4" viewBox="0 0 20 20" fill="currentColor">
                            <path fillRule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clipRule="evenodd" />
                          </svg>
                        </button>
                      </div>
                    </td>
                  </tr>
                  {expandedId === a.id && (
                    <tr>
                      <td colSpan={13} className="p-0">
                        <RiskInherentResidualBadges assessment={a} />
                        <SuggestResidualPanel assessment={a} />
                        <FormalAcceptancePanel assessment={a} />
                        <MitigationPanel assessmentId={a.id} />
                      </td>
                    </tr>
                  )}
                </Fragment>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {showNew && plants && <NewAssessmentModal plants={plants} onClose={() => setShowNew(false)} />}
      <AssistenteValutazione open={drawerOpen} onClose={() => setDrawerOpen(false)} />
      {showWizard && <RiskContinuityWizard onClose={() => setShowWizard(false)} />}
      {editAssessment && (
        <EditAssessmentModal
          assessment={editAssessment}
          onClose={() => setEditAssessment(null)}
        />
      )}
    </div>
  );
}
