import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { controlsApi, type RequirementsCheck, type EvidenceRequirement, type AssetRef } from "../../../api/endpoints/controls";
import { StatusBadge } from "../../../components/ui/StatusBadge";
import { AiSuggestionBanner } from "../../../components/ui/AiSuggestionBanner";
import { useAuthStore } from "../../../store/auth";
import i18n from "../../../i18n";
import { STATUS_GUIDE, useRequirementLabel, RequirementsBanner } from "./shared";
import { SOA_APPROVAL_ROLES } from "../roles";

const MATURITY_KEYS: Record<number, string> = {
  0: "controls.maturity_0",
  1: "controls.maturity_1",
  2: "controls.maturity_2",
  3: "controls.maturity_3",
  4: "controls.maturity_4",
  5: "controls.maturity_5",
};

const APPLICABILITY_KEYS: Record<string, string> = {
  applicabile:    "controls.applicability_applicable",
  escluso:        "controls.applicability_excluded",
  non_pertinente: "controls.applicability_not_relevant",
};

export function TabValutazione({
  instanceId,
  requirements,
  currentStatus,
  suggestedStatus,
  suggestedStatusReason,
  evidenceRequirement,
  applicability,
  exclusionJustification,
  naJustification,
  calcMaturityLevel,
  maturityLevelOverride,
  framework,
  approvedInSoa,
  soaApprovedAt,
  soaApprovedByName,
  needsRevaluation,
  needsRevaluationSince,
  initialNotes,
  linkedAssets,
  availableAssets,
}: {
  instanceId: string;
  requirements: RequirementsCheck;
  currentStatus: string;
  suggestedStatus: string;
  suggestedStatusReason: string;
  evidenceRequirement: EvidenceRequirement;
  applicability: string;
  exclusionJustification: string;
  naJustification: string;
  calcMaturityLevel: number;
  maturityLevelOverride: boolean;
  framework: string;
  approvedInSoa: boolean;
  soaApprovedAt: string | null;
  soaApprovedByName: string | null;
  needsRevaluation?: boolean;
  needsRevaluationSince?: string | null;
  initialNotes?: string;
  linkedAssets?: AssetRef[];
  availableAssets?: AssetRef[];
}) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const userRole = useAuthStore(s => s.user?.role ?? "");
  const canApproveSoa = SOA_APPROVAL_ROLES.includes(userRole);
  const [selectedStatus, setSelectedStatus] = useState("");
  const [note, setNote] = useState(currentStatus === "na" ? (naJustification || "") : "");
  const [blockError, setBlockError] = useState("");
  const [applyModalOpen, setApplyModalOpen] = useState(false);
  const [applyNote, setApplyNote] = useState("");
  const [manualOpen, setManualOpen] = useState(false);
  const [selectedApplicability, setSelectedApplicability] = useState(applicability);
  const [justification, setJustification] = useState(exclusionJustification);
  const [applicabilityError, setApplicabilityError] = useState("");
  const [maturityOverrideVal, setMaturityOverrideVal] = useState(calcMaturityLevel);
  const [gapActions, setGapActions] = useState<Array<{ title?: string; priority?: string; description?: string }>>([]);
  const [notesValue, setNotesValue] = useState(initialNotes ?? "");
  const [notesSaved, setNotesSaved] = useState(false);
  const [assetIds, setAssetIds] = useState<string[]>((linkedAssets ?? []).map(a => a.id));
  const [assetsSaved, setAssetsSaved] = useState(false);

  const assetsMutation = useMutation({
    mutationFn: () => controlsApi.updateInstance(instanceId, { assets: assetIds }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["controls"] });
      qc.invalidateQueries({ queryKey: ["control-detail", instanceId] });
      setAssetsSaved(true);
      setTimeout(() => setAssetsSaved(false), 3000);
    },
  });

  const notesMutation = useMutation({
    mutationFn: () => controlsApi.updateInstance(instanceId, { notes: notesValue }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["controls"] });
      qc.invalidateQueries({ queryKey: ["control-detail", instanceId] });
      setNotesSaved(true);
      setTimeout(() => setNotesSaved(false), 2000);
    },
  });

  const requirementLabel = useRequirementLabel();

  const suggestionDiffers = suggestedStatus !== currentStatus;

  const applicabilityMutation = useMutation({
    mutationFn: () => controlsApi.setApplicability(instanceId, selectedApplicability, justification),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["controls"] });
      qc.invalidateQueries({ queryKey: ["control-detail", instanceId] });
      setApplicabilityError("");
    },
    onError: (e: unknown) => {
      const msg = (e as { response?: { data?: { error?: string } } })?.response?.data?.error ?? t("common.error");
      setApplicabilityError(msg);
    },
  });

  const maturityMutation = useMutation({
    mutationFn: () => controlsApi.setMaturity(instanceId, maturityOverrideVal),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["control-detail", instanceId] });
    },
  });

  const soaMutation = useMutation({
    mutationFn: (approved: boolean) => controlsApi.bulkApproveSoa([instanceId], approved),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["controls"] });
      qc.invalidateQueries({ queryKey: ["control-detail", instanceId] });
    },
  });

  const applyMutation = useMutation({
    mutationFn: () => controlsApi.applySuggestion(instanceId, applyNote),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["controls"] });
      qc.invalidateQueries({ queryKey: ["control-detail", instanceId] });
      setApplyModalOpen(false);
    },
    onError: (e: unknown) => {
      const msg = (e as { response?: { data?: { error?: string } } })?.response?.data?.error ?? t("common.error");
      setBlockError(msg);
    },
  });

  const evaluateMutation = useMutation({
    mutationFn: () => controlsApi.evaluate(instanceId, selectedStatus, note),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["controls"] });
      qc.invalidateQueries({ queryKey: ["control-detail", instanceId] });
      setBlockError("");
    },
    onError: (e: unknown) => {
      const msg = (e as { response?: { data?: { error?: string } } })?.response?.data?.error ?? t("common.error");
      setBlockError(msg);
    },
  });

  const noRequirements = !evidenceRequirement ||
    (!evidenceRequirement.documents?.length && !evidenceRequirement.evidences?.length &&
     !evidenceRequirement.min_documents && !evidenceRequirement.min_evidences);

  const reqNotSatisfied = selectedStatus === "compliant" && !requirements.satisfied;

  return (
    <div className="space-y-4">
      {/* Banner rivalutazione da change */}
      {needsRevaluation && (
        <div className="border border-amber-300 bg-amber-50 rounded-lg p-3">
          <p className="text-sm font-medium text-amber-800">{t("controls.drawer.evaluation.revaluation.title")}</p>
          <p className="text-xs text-amber-700 mt-1">
            {t("controls.drawer.evaluation.revaluation.body", {
              since: needsRevaluationSince ? new Date(needsRevaluationSince).toLocaleDateString(i18n.language || "it") : "",
              hasSince: Boolean(needsRevaluationSince),
            })}
          </p>
        </div>
      )}

      {/* Banner requisiti */}
      <RequirementsBanner requirements={requirements} noRequirements={noRequirements} />

      {/* Due box: Stato ufficiale / Suggerimento sistema */}
      <div className="grid grid-cols-2 gap-3">
        <div className="border border-gray-200 rounded-lg p-3">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">{t("controls.drawer.evaluation.official_status")}</p>
          <StatusBadge status={currentStatus} />
        </div>
        <div className="border border-indigo-200 rounded-lg p-3 bg-indigo-50/30">
          <p className="text-xs font-semibold text-indigo-600 uppercase tracking-wide mb-2">{t("controls.drawer.evaluation.system_suggestion")}</p>
          <StatusBadge status={suggestedStatus} />
          {suggestedStatusReason && (
            <p className="text-xs text-gray-500 mt-1.5 leading-snug">{suggestedStatusReason}</p>
          )}
        </div>
      </div>

      {/* Bottone applica suggerimento */}
      {suggestionDiffers && !applyModalOpen && (
        <button
          onClick={() => { setApplyNote(suggestedStatusReason); setApplyModalOpen(true); }}
          className="w-full py-2 bg-indigo-600 text-white rounded text-sm font-medium hover:bg-indigo-700 flex items-center justify-center gap-2"
        >
          <svg viewBox="0 0 12 12" className="w-3.5 h-3.5 fill-current" aria-hidden="true">
            <path d="M3 2l7 4-7 4V2z" />
          </svg>
          {t("controls.drawer.evaluation.apply_suggestion", { status: suggestedStatus })}
        </button>
      )}

      {/* Mini-modal applica suggerimento */}
      {applyModalOpen && (
        <div className="border border-indigo-200 rounded-lg p-3 space-y-2 bg-indigo-50/50">
          <p className="text-sm font-medium text-gray-700">
            {t("controls.drawer.evaluation.apply_suggestion_title")}: <strong>{suggestedStatus}</strong>
          </p>
          <textarea
            value={applyNote}
            onChange={e => setApplyNote(e.target.value)}
            placeholder={t("controls.drawer.evaluation.note_optional")}
            className="w-full border rounded px-3 py-2 text-sm resize-none"
            rows={2}
          />
          {blockError && (
            <div className="bg-red-50 border border-red-200 rounded-lg px-3 py-2 text-sm text-red-700">
              ⛔ {blockError}
            </div>
          )}
          <div className="flex gap-2">
            <button
              onClick={() => applyMutation.mutate()}
              disabled={applyMutation.isPending}
              className="flex-1 py-1.5 bg-indigo-600 text-white rounded text-sm hover:bg-indigo-700 disabled:opacity-50"
            >
              {applyMutation.isPending ? t("controls.drawer.evaluation.applying") : t("actions.confirm")}
            </button>
            <button
              onClick={() => { setApplyModalOpen(false); setBlockError(""); }}
              className="px-3 py-1.5 border rounded text-sm text-gray-600 hover:bg-gray-50"
            >
              {t("actions.cancel")}
            </button>
          </div>
        </div>
      )}

      {/* Applicabilità SOA — solo per ISO 27001 (lo Statement of Applicability è
          un artefatto dell'Annex A ISO 27001; per TISAX/NIS2 la non-applicabilità
          si esprime con lo status N/A). C13 */}
      {framework.includes("ISO") && (
      <div className="border border-gray-200 rounded-lg p-3 space-y-2">
        <p className="text-xs font-semibold text-gray-600 uppercase tracking-wide">{t("controls.drawer.evaluation.applicability.title")}</p>
        <select
          value={selectedApplicability}
          onChange={e => { setSelectedApplicability(e.target.value); setApplicabilityError(""); }}
          className="w-full border rounded px-2 py-1.5 text-sm"
        >
          {Object.entries(APPLICABILITY_KEYS).map(([v, key]) => (
            <option key={v} value={v}>{t(key)}</option>
          ))}
        </select>
        {selectedApplicability === "escluso" && (
          <textarea
            value={justification}
            onChange={e => setJustification(e.target.value)}
            placeholder={t("controls.drawer.evaluation.applicability.exclusion_placeholder")}
            className="w-full border rounded px-2 py-1.5 text-xs resize-none"
            rows={3}
          />
        )}
        {applicabilityError && (
          <p className="text-xs text-red-600">⛔ {applicabilityError}</p>
        )}
        <button
          onClick={() => applicabilityMutation.mutate()}
          disabled={applicabilityMutation.isPending}
          className="w-full py-1.5 bg-gray-700 text-white rounded text-xs hover:bg-gray-800 disabled:opacity-50"
        >
          {applicabilityMutation.isPending ? t("common.saving") : t("controls.drawer.evaluation.applicability.save")}
        </button>
      </div>
      )}

      {/* Maturity Level — solo per TISAX */}
      {(framework.includes("TISAX") || framework.includes("VDA")) && (
        <div className="border border-purple-200 rounded-lg p-3 space-y-2 bg-purple-50/30">
          <div className="flex items-center justify-between">
            <p className="text-xs font-semibold text-purple-700 uppercase tracking-wide">{t("controls.drawer.evaluation.maturity.title")}</p>
            {!maturityLevelOverride && (
              <span className="text-xs text-gray-400 bg-gray-100 px-1.5 rounded">{t("controls.drawer.evaluation.maturity.auto")}</span>
            )}
          </div>
          <div className="flex items-center gap-2">
            <input
              type="range"
              min={0} max={5} step={1}
              value={maturityOverrideVal}
              onChange={e => setMaturityOverrideVal(Number(e.target.value))}
              className="flex-1 accent-purple-600"
            />
            <span className="text-sm font-bold text-purple-700 w-4 text-center">{maturityOverrideVal}</span>
          </div>
          <p className="text-xs text-gray-500">
            {t(MATURITY_KEYS[maturityOverrideVal] ?? `controls.drawer.evaluation.maturity.levels.${maturityOverrideVal}`)}
          </p>
          <button
            onClick={() => maturityMutation.mutate()}
            disabled={maturityMutation.isPending}
            className="w-full py-1.5 bg-purple-600 text-white rounded text-xs hover:bg-purple-700 disabled:opacity-50"
          >
            {maturityMutation.isPending ? t("common.saving") : t("controls.drawer.evaluation.maturity.override")}
          </button>
        </div>
      )}

      {/* Approvazione SoA — solo per ISO 27001 (lo Statement of Applicability è
          l'approvazione formale della direzione, artefatto Annex A ISO 27001). C5 */}
      {framework.includes("ISO") && (
        <div className={`border rounded-lg p-3 space-y-2 ${approvedInSoa ? "border-green-300 bg-green-50/40" : "border-gray-200"}`}>
          <p className="text-xs font-semibold text-gray-600 uppercase tracking-wide">{t("controls.drawer.evaluation.soa.title")}</p>
          {approvedInSoa ? (
            <div className="text-xs text-green-800">
              <p className="font-medium">✓ {t("controls.drawer.evaluation.soa.approved")}</p>
              <p className="text-green-700 mt-0.5">
                {soaApprovedByName ? `${soaApprovedByName} · ` : ""}
                {soaApprovedAt ? new Date(soaApprovedAt).toLocaleDateString(i18n.language || "it") : ""}
              </p>
            </div>
          ) : (
            <p className="text-xs text-gray-500">{t("controls.drawer.evaluation.soa.not_approved")}</p>
          )}
          {/* L'approvazione formale è riservata alla governance (backend:
              SoAApprovalPermission) — gli altri ruoli vedono solo lo stato. */}
          {canApproveSoa && (
            <button
              onClick={() => soaMutation.mutate(!approvedInSoa)}
              disabled={soaMutation.isPending}
              className={`w-full py-1.5 rounded text-xs text-white disabled:opacity-50 ${approvedInSoa ? "bg-gray-500 hover:bg-gray-600" : "bg-green-600 hover:bg-green-700"}`}
            >
              {soaMutation.isPending
                ? t("common.saving")
                : approvedInSoa
                ? t("controls.drawer.evaluation.soa.revoke")
                : t("controls.drawer.evaluation.soa.approve")}
            </button>
          )}
        </div>
      )}

      {/* Cambio manuale — collassabile */}
      {currentStatus === "gap" && (
        <div className="space-y-2">
          <AiSuggestionBanner
            taskType="gap_actions"
            entityId={instanceId}
            autoTrigger={false}
            onAccept={(res) => {
              const parsed = res as { actions?: Array<{ title?: string; priority?: string; description?: string }> };
              setGapActions(parsed.actions ?? []);
            }}
            onIgnore={() => setGapActions([])}
          />
          {gapActions.length > 0 && (
            <div className="border rounded p-2 bg-slate-50">
              <p className="text-xs font-semibold text-slate-700 mb-1">{t("controls.drawer.evaluation.gap_actions_title")}</p>
              {gapActions.map((a, i) => (
                <p key={i} className="text-xs text-slate-700">
                  - [{a.priority ?? "n/a"}] {a.title ?? t("controls.drawer.evaluation.gap_action_fallback")}: {a.description ?? ""}
                </p>
              ))}
            </div>
          )}
        </div>
      )}

      <div className="border border-gray-200 rounded-lg">
        <button
          onClick={() => setManualOpen(o => !o)}
          className="w-full flex items-center justify-between px-3 py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-50"
        >
          <span>{t("controls.drawer.evaluation.manual_change.title")}</span>
          <span className="text-gray-400">{manualOpen ? "▲" : "▼"}</span>
        </button>
        {manualOpen && (
          <div className="px-3 pb-3 border-t border-gray-100 pt-2 space-y-3">
            <select
              value={selectedStatus}
              onChange={e => { setSelectedStatus(e.target.value); setBlockError(""); }}
              className="w-full border rounded px-3 py-2 text-sm"
            >
              <option value="">{t("controls.drawer.evaluation.manual_change.select_status")}</option>
              {STATUS_GUIDE.map(s => (
                <option key={s.status} value={s.status}>{s.icon} {t(`status.${s.status}`, { defaultValue: s.label })}</option>
              ))}
            </select>

            {reqNotSatisfied && (
              <div className="bg-red-50 border border-red-200 rounded-lg px-3 py-2 text-xs text-red-700">
                <p className="font-semibold mb-1">⛔ {t("controls.drawer.evaluation.manual_change.req_block")}</p>
                {requirements.missing_documents.map((m, i) => <p key={i}>• {t("controls.drawer.evaluation.requirements.missing_document")}: {requirementLabel("document", m.type, m.description)}</p>)}
                {requirements.missing_evidences.map((m, i) => <p key={i}>• {t("controls.drawer.evaluation.requirements.missing_evidence")}: {requirementLabel("evidence", m.type, m.description)}</p>)}
                {requirements.expired_evidences.map((e, i) => <p key={i}>• {t("controls.drawer.evaluation.requirements.expired_evidence")}: {e.title} ({e.expired_on})</p>)}
              </div>
            )}

            <textarea
              value={note}
              onChange={e => setNote(e.target.value)}
              placeholder={t("controls.drawer.evaluation.manual_change.note_placeholder")}
              className="w-full border rounded px-3 py-2 text-sm resize-none"
              rows={3}
            />

            {blockError && (
              <div className="bg-red-50 border border-red-200 rounded-lg px-3 py-2 text-sm text-red-700">
                <span className="mr-1">⛔</span>{blockError}
              </div>
            )}

            <button
              onClick={() => evaluateMutation.mutate()}
              disabled={evaluateMutation.isPending || !selectedStatus || reqNotSatisfied}
              title={reqNotSatisfied ? t("controls.drawer.evaluation.manual_change.req_tooltip") : undefined}
              className="w-full py-2 bg-blue-600 text-white rounded text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
            >
              {evaluateMutation.isPending ? t("common.saving") : t("controls.drawer.evaluation.save_evaluation")}
            </button>
          </div>
        )}
      </div>

      {/* Note aggiuntive */}
      <div className="border border-gray-200 rounded-lg p-3 space-y-2">
        <p className="text-xs font-semibold text-gray-600 uppercase tracking-wide">{t("controls.notes_label")}</p>
        <textarea
          value={notesValue}
          onChange={e => { setNotesValue(e.target.value); setNotesSaved(false); }}
          placeholder={t("controls.notes_placeholder")}
          className="w-full border rounded px-3 py-2 text-sm resize-none"
          rows={3}
        />
        <button
          onClick={() => notesMutation.mutate()}
          disabled={notesMutation.isPending}
          className="w-full py-1.5 bg-gray-600 text-white rounded text-xs hover:bg-gray-700 disabled:opacity-50"
        >
          {notesMutation.isPending ? t("common.saving") : notesSaved ? "✓ " + t("common.saved", { defaultValue: "Salvato" }) : t("controls.notes_save")}
        </button>
      </div>

      {/* Asset collegati (P1-5): restringe la cascata di rivalutazione agli asset del controllo */}
      <div className="border border-gray-200 rounded-lg p-3 space-y-2">
        <p className="text-xs font-semibold text-gray-600 uppercase tracking-wide">{t("controls.linked_assets_label")}</p>
        <p className="text-xs text-gray-500">{t("controls.linked_assets_hint")}</p>
        {(availableAssets ?? []).length === 0 ? (
          <p className="text-xs text-gray-400">{t("controls.linked_assets_empty")}</p>
        ) : (
          <>
            <select
              multiple
              value={assetIds}
              onChange={e => { setAssetIds(Array.from(e.target.selectedOptions).map(o => o.value)); setAssetsSaved(false); }}
              className="w-full border rounded px-3 py-2 text-sm h-28"
            >
              {(availableAssets ?? []).map(a => (
                <option key={a.id} value={a.id}>{a.name}{a.asset_type ? ` (${a.asset_type})` : ""}</option>
              ))}
            </select>
            <button
              onClick={() => assetsMutation.mutate()}
              disabled={assetsMutation.isPending}
              className="w-full py-1.5 bg-gray-600 text-white rounded text-xs hover:bg-gray-700 disabled:opacity-50"
            >
              {assetsMutation.isPending ? t("common.saving") : assetsSaved ? "✓ " + t("common.saved", { defaultValue: "Salvato" }) : t("controls.linked_assets_save")}
            </button>
          </>
        )}
      </div>
    </div>
  );
}
