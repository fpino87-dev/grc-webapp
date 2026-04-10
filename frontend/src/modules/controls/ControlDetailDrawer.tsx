import { useState, useEffect, useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { controlsApi, type EvidenceRef, type LinkedDocument, type RequirementsCheck, type EvidenceRequirement } from "../../api/endpoints/controls";
import { documentsApi } from "../../api/endpoints/documents";
import { useAuthStore } from "../../store/auth";
import { StatusBadge } from "../../components/ui/StatusBadge";
import { AiSuggestionBanner } from "../../components/ui/AiSuggestionBanner";
import { useTranslation } from "react-i18next";
import i18n from "../../i18n";

// ─── Helpers ──────────────────────────────────────────────────────────────────

function evidenceIcon(type: string): string {
  const map: Record<string, string> = {
    screenshot: "📸", log: "📋", report: "📄",
    verbale: "📝", certificato: "🏆", test_result: "🧪", altro: "📎",
  };
  return map[type] ?? "📎";
}

function docStatusColor(status: string): string {
  const map: Record<string, string> = {
    approvato:   "bg-green-100 text-green-800",
    revisione:   "bg-blue-100 text-blue-700",
    approvazione:"bg-blue-100 text-blue-700",
    bozza:       "bg-gray-100 text-gray-600",
    archiviato:  "bg-gray-200 text-gray-500",
  };
  return map[status] ?? "bg-gray-100 text-gray-500";
}

function ExpiryBadge({ validUntil }: { validUntil: string | null }) {
  const { t } = useTranslation();
  if (!validUntil) return <span className="text-gray-400 text-xs">{t("controls.drawer.expiry.none")}</span>;
  const date = new Date(validUntil);
  const today = new Date();
  const days = Math.ceil((date.getTime() - today.getTime()) / 86400000);
  if (days < 0) return (
    <span className="text-xs px-1.5 py-0.5 rounded bg-red-100 text-red-700 font-medium">
      {t("controls.drawer.expiry.expired_days_ago", { days: Math.abs(days) })}
    </span>
  );
  if (days <= 30) return (
    <span className="text-xs px-1.5 py-0.5 rounded bg-orange-100 text-orange-700 font-medium">
      {t("controls.drawer.expiry.expires_in_days", { days })}
    </span>
  );
  return (
    <span className="text-xs px-1.5 py-0.5 rounded bg-green-100 text-green-700 font-medium">
      {t("controls.drawer.expiry.valid_until", { date: date.toLocaleDateString(i18n.language || "it") })}
    </span>
  );
}

const STATUS_GUIDE = [
  { status: "compliant",    icon: "🟢", label: "Compliant",    reqKey: "controls.drawer.evaluation.status_guide.compliant", badge: "bg-green-100 text-green-800" },
  { status: "parziale",     icon: "🟡", label: "Partial",      reqKey: "controls.drawer.evaluation.status_guide.parziale", badge: "bg-yellow-100 text-yellow-800" },
  { status: "gap",          icon: "🔴", label: "Gap",          reqKey: "controls.drawer.evaluation.status_guide.gap", badge: "bg-red-100 text-red-800" },
  { status: "na",           icon: "⚪", label: "N/A",          reqKey: "controls.drawer.evaluation.status_guide.na", badge: "bg-gray-100 text-gray-600" },
  { status: "non_valutato", icon: "⬜", label: "Not assessed", reqKey: "controls.drawer.evaluation.status_guide.non_valutato", badge: "bg-gray-50 text-gray-500" },
];

type Tab = "cosa" | "valutazione" | "docevidence" | "storico";

// ─── Tab 1: Cos'è ─────────────────────────────────────────────────────────────

function TabCosa({ info }: { info: NonNullable<ReturnType<typeof useDetailInfo>["data"]> }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [guidanceOpen, setGuidanceOpen] = useState(false);
  const [summaryText, setSummaryText] = useState(info.practical_summary || "");

  const explainMut = useMutation({
    mutationFn: () => controlsApi.explainControl(info.control_uuid, i18n.language || "it"),
    onSuccess: (data) => {
      setSummaryText(data.summary);
      qc.invalidateQueries({ queryKey: ["control-detail", info.control_id] });
    },
  });

  return (
    <div className="space-y-4">
      <div>
        <div className="flex flex-wrap gap-2 mb-2">
          <span className="px-2 py-0.5 text-xs font-semibold bg-blue-100 text-blue-800 rounded">{info.framework}</span>
          {info.level && <span className="px-2 py-0.5 text-xs bg-purple-100 text-purple-700 rounded">{info.level}</span>}
          {info.control_category && <span className="px-2 py-0.5 text-xs bg-teal-100 text-teal-700 rounded capitalize">{info.control_category}</span>}
          {info.domain && <span className="px-2 py-0.5 text-xs bg-gray-100 text-gray-600 rounded">{info.domain}</span>}
        </div>
        <h3 className="text-base font-semibold text-gray-900 leading-snug">{info.title}</h3>
        <p className="text-xs font-mono text-gray-400 mt-0.5">{info.control_id}</p>
      </div>

      {info.description ? (
        <div className="bg-blue-50 rounded-lg p-3 text-sm text-gray-700 leading-relaxed">
          {info.description}
        </div>
      ) : (
        <p className="text-sm text-gray-400 italic">{t("controls.drawer.about.no_description")}</p>
      )}

      {/* Spiegazione AI plain-language */}
      <div className="border border-purple-200 rounded-lg overflow-hidden">
        <div className="flex items-center justify-between px-3 py-2 bg-purple-50">
          <span className="text-xs font-semibold text-purple-700 flex items-center gap-1.5">
            ✨ {t("controls.drawer.about.ai_summary_title")}
          </span>
          <button
            onClick={() => explainMut.mutate()}
            disabled={explainMut.isPending}
            className="text-xs px-2 py-0.5 rounded bg-purple-600 text-white hover:bg-purple-700 disabled:opacity-50"
          >
            {explainMut.isPending
              ? t("controls.drawer.about.ai_generating")
              : summaryText
              ? t("controls.drawer.about.ai_regenerate")
              : t("controls.drawer.about.ai_generate")}
          </button>
        </div>
        {summaryText ? (
          <div className="px-3 py-2.5 text-sm text-gray-700 leading-relaxed">
            {summaryText}
          </div>
        ) : (
          <p className="px-3 py-2.5 text-xs text-gray-400 italic">
            {t("controls.drawer.about.ai_summary_empty")}
          </p>
        )}
        {explainMut.isError && (
          <p className="px-3 pb-2 text-xs text-red-600">
            {(explainMut.error as { response?: { data?: { error?: string } } })?.response?.data?.error || t("common.error")}
          </p>
        )}
      </div>

      {/* Riepilogo plain-language di cosa serve per soddisfare il controllo */}
      {(info.evidence_requirement?.documents?.length > 0 ||
        info.evidence_requirement?.evidences?.length > 0 ||
        info.evidence_requirement?.min_documents > 0 ||
        info.evidence_requirement?.min_evidences > 0) && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 space-y-2">
          <p className="text-xs font-semibold text-amber-800 uppercase tracking-wide">
            {t("controls.drawer.about.what_is_needed")}
          </p>
          <ul className="space-y-1">
            {info.evidence_requirement.documents?.filter(d => d.mandatory).map((d, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
                <span className="text-amber-500 shrink-0 mt-0.5">📄</span>
                <span>
                  <span className="font-medium">{t("controls.drawer.about.req_doc")}:</span>{" "}
                  {d.description || t(`documents.type.${d.type}`, { defaultValue: d.type })}
                </span>
              </li>
            ))}
            {info.evidence_requirement.evidences?.filter(e => e.mandatory).map((e, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
                <span className="text-amber-500 shrink-0 mt-0.5">🔬</span>
                <span>
                  <span className="font-medium">{t("controls.drawer.about.req_evidence")}:</span>{" "}
                  {e.description || t(`documents.evidence.types.${e.type}`, { defaultValue: e.type })}
                  {e.max_age_days && (
                    <span className="ml-1 text-xs text-gray-400">
                      ({t("controls.drawer.about.req_max_age", { days: e.max_age_days })})
                    </span>
                  )}
                </span>
              </li>
            ))}
            {info.evidence_requirement.min_documents > 0 && (
              <li className="flex items-start gap-2 text-sm text-gray-700">
                <span className="text-amber-500 shrink-0 mt-0.5">📌</span>
                <span>{t("controls.drawer.about.req_min_docs", { count: info.evidence_requirement.min_documents })}</span>
              </li>
            )}
            {info.evidence_requirement.min_evidences > 0 && (
              <li className="flex items-start gap-2 text-sm text-gray-700">
                <span className="text-amber-500 shrink-0 mt-0.5">📌</span>
                <span>{t("controls.drawer.about.req_min_evidences", { count: info.evidence_requirement.min_evidences })}</span>
              </li>
            )}
            {info.evidence_requirement.notes && (
              <li className="text-xs text-gray-500 italic pl-6">{info.evidence_requirement.notes}</li>
            )}
          </ul>
        </div>
      )}

      {info.implementation_guidance && (
        <div className="border border-gray-200 rounded-lg">
          <button
            onClick={() => setGuidanceOpen(o => !o)}
            className="w-full flex items-center justify-between px-3 py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            <span>{t("controls.drawer.about.guidance")}</span>
            <span className="text-gray-400">{guidanceOpen ? "▲" : "▼"}</span>
          </button>
          {guidanceOpen && (
            <div className="px-3 pb-3 text-sm text-gray-600 leading-relaxed border-t border-gray-100 pt-2">
              {info.implementation_guidance}
            </div>
          )}
        </div>
      )}

      {info.evidence_examples.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">{t("controls.drawer.about.evidence_examples")}</p>
          <div className="space-y-1.5">
            {info.evidence_examples.map((ex, i) => {
              const icon = ex.toLowerCase().includes("screenshot") ? "📸"
                : ex.toLowerCase().includes("log") ? "📋"
                : ex.toLowerCase().includes("certificat") ? "🏆"
                : "📄";
              return (
                <div key={i} className="flex items-center gap-2 text-sm text-gray-700">
                  <span>{icon}</span><span>{ex}</span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {info.mappings.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">{t("controls.drawer.about.mappings")}</p>
          <div className="flex flex-wrap gap-1.5">
            {info.mappings.map((m, i) => (
              <span key={i} className="text-xs bg-indigo-50 border border-indigo-100 text-indigo-700 px-2 py-0.5 rounded">
                {m.relationship} → {m["target_control__framework__code"]} {m["target_control__external_id"]}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Tab 2: Valutazione ───────────────────────────────────────────────────────

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

function TabValutazione({
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
  needsRevaluation,
  needsRevaluationSince,
  initialNotes,
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
  needsRevaluation?: boolean;
  needsRevaluationSince?: string | null;
  initialNotes?: string;
}) {
  const { t } = useTranslation();
  const qc = useQueryClient();
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

  const notesMutation = useMutation({
    mutationFn: () => controlsApi.updateInstance(instanceId, { notes: notesValue }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["controls"] });
      qc.invalidateQueries({ queryKey: ["control-detail", instanceId] });
      setNotesSaved(true);
      setTimeout(() => setNotesSaved(false), 2000);
    },
  });

  function requirementLabel(kind: "document" | "evidence", type: string, description?: string) {
    if (type === "any") return description || "";
    if (kind === "document") return t(`documents.type.${type}`, { defaultValue: description || type });
    return t(`documents.evidence.types.${type}`, { defaultValue: description || type });
  }

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
      {noRequirements ? (
        <div className="bg-gray-50 border border-gray-200 rounded-lg px-3 py-2 text-xs text-gray-500">
          ℹ️ {t("controls.drawer.evaluation.requirements.none")}
        </div>
      ) : !requirements.satisfied ? (
        <div className="bg-red-50 border border-red-200 rounded-lg px-3 py-2 text-xs text-red-800">
          <p className="font-semibold mb-1">⛔ {t("controls.drawer.evaluation.requirements.not_satisfied")}</p>
          {requirements.missing_documents.map((m, i) => (
            <p key={i}>• {t("controls.drawer.evaluation.requirements.missing_document")}: {requirementLabel("document", m.type, m.description)}</p>
          ))}
          {requirements.missing_evidences.map((m, i) => (
            <p key={i}>• {t("controls.drawer.evaluation.requirements.missing_evidence")}: {requirementLabel("evidence", m.type, m.description)}</p>
          ))}
          {requirements.expired_evidences.map((e, i) => (
            <p key={i}>• {t("controls.drawer.evaluation.requirements.expired_evidence")}: {e.title} ({e.expired_on})</p>
          ))}
        </div>
      ) : requirements.warnings.length > 0 ? (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg px-3 py-2 text-xs text-yellow-800">
          <p className="font-semibold mb-1">⚠️ {t("controls.drawer.evaluation.requirements.warning")}</p>
          {requirements.warnings.map((w, i) => <p key={i}>• {w}</p>)}
        </div>
      ) : (
        <div className="bg-green-50 border border-green-200 rounded-lg px-3 py-2 text-xs text-green-800">
          ✅ {t("controls.drawer.evaluation.requirements.satisfied")}
        </div>
      )}

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

      {/* Applicabilità SOA */}
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
              <p className="text-xs font-semibold text-slate-700 mb-1">Azioni suggerite</p>
              {gapActions.map((a, i) => (
                <p key={i} className="text-xs text-slate-700">
                  - [{a.priority ?? "n/a"}] {a.title ?? "Azione"}: {a.description ?? ""}
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
    </div>
  );
}

// ─── Tab 3: Documenti & Evidenze ─────────────────────────────────────────────

function useDebounce(value: string, delay = 300) {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(t);
  }, [value, delay]);
  return debounced;
}

function DocsColumn({
  instanceId,
  documents,
  requirements,
  plant,
}: {
  instanceId: string;
  documents: LinkedDocument[];
  requirements: RequirementsCheck;
  plant: string | null;
}) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [searchQ, setSearchQ] = useState("");
  const debounced = useDebounce(searchQ);

  function requirementLabel(type: string, description?: string) {
    if (type === "any") return description || "";
    return t(`documents.type.${type}`, { defaultValue: description || type });
  }

  const { data: searchResults } = useQuery({
    queryKey: ["doc-search", debounced, plant],
    queryFn: () => documentsApi.searchDocuments(debounced, plant ?? undefined),
    enabled: debounced.length > 2,
  });

  const unlinkMut = useMutation({
    mutationFn: (docId: string) => controlsApi.unlinkDocument(instanceId, docId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["control-detail", instanceId] }),
  });
  const linkMut = useMutation({
    mutationFn: (docId: string) => controlsApi.linkDocument(instanceId, docId),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["control-detail", instanceId] }); setSearchQ(""); },
  });

  const linkedIds = new Set(documents.map(d => d.id));

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 mb-1">
        <span className="text-base">📄</span>
        <span className="text-xs font-semibold text-gray-700 uppercase tracking-wide">{t("controls.drawer.docs.policy_docs")}</span>
        <span className="ml-auto text-xs bg-gray-100 text-gray-600 px-1.5 rounded">{documents.length}</span>
      </div>

      {/* Requisiti mancanti */}
      {requirements.missing_documents.length > 0 && (
        <div className="space-y-1">
          {requirements.missing_documents.map((m, i) => (
            <div key={i} className="flex items-center gap-1.5 text-xs bg-red-50 border border-red-200 rounded px-2 py-1">
              <span className="text-red-500 font-bold shrink-0">!</span>
              <span className="text-red-700">{requirementLabel(m.type, m.description)}</span>
              <span className="ml-auto text-xs text-red-500 font-medium shrink-0">{t("controls.drawer.docs.missing")}</span>
            </div>
          ))}
        </div>
      )}

      {/* Lista documenti collegati */}
      {documents.length === 0 ? (
        <p className="text-xs text-gray-400 italic">{t("controls.drawer.docs.none_linked")}</p>
      ) : (
        <div className="space-y-1.5">
          {documents.map(d => (
            <div key={d.id} className="bg-white border border-gray-200 rounded px-2.5 py-2">
              <div className="flex items-start justify-between gap-1">
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-medium text-gray-800 truncate">{d.title}</p>
                  <div className="flex items-center gap-1 mt-0.5 flex-wrap">
                    <span className="text-xs bg-indigo-50 text-indigo-700 px-1 rounded">
                      {t(`documents.type.${d.document_type}`, { defaultValue: d.document_type })}
                    </span>
                    <span className={`text-xs px-1 rounded ${docStatusColor(d.status)}`}>
                      {t(`status.${d.status}`, { defaultValue: d.status })}
                    </span>
                    {d.review_due_date && (
                      <span className="text-xs text-gray-400">
                        {t("controls.drawer.docs.review_abbrev")} {new Date(d.review_due_date).toLocaleDateString(i18n.language || "it")}
                      </span>
                    )}
                  </div>
                </div>
                <button
                  onClick={() => unlinkMut.mutate(d.id)}
                  disabled={unlinkMut.isPending}
                  className="text-red-400 hover:text-red-600 text-xs shrink-0 ml-1"
                  title={t("controls.drawer.docs.unlink")}
                >
                  ✕
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Collega documento */}
      <div className="border border-dashed border-gray-300 rounded p-2 space-y-1.5">
        <p className="text-xs font-medium text-gray-500">{t("controls.drawer.docs.link_doc")}</p>
        <input
          type="text"
          value={searchQ}
          onChange={e => setSearchQ(e.target.value)}
          placeholder={t("controls.drawer.docs.search_placeholder")}
          className="w-full border rounded px-2 py-1 text-xs"
        />
        {searchResults && searchResults.results.length > 0 && (
          <div className="border rounded divide-y divide-gray-100 max-h-32 overflow-y-auto bg-white">
            {searchResults.results.filter(d => !linkedIds.has(d.id)).slice(0, 8).map(d => (
              <button
                key={d.id}
                onClick={() => linkMut.mutate(d.id)}
                disabled={linkMut.isPending}
                className="w-full text-left px-2 py-1.5 text-xs hover:bg-blue-50 text-gray-700 flex items-center gap-1.5"
              >
                <span className="text-gray-400">📄</span>
                <span className="truncate flex-1">{d.title}</span>
                <span className={`shrink-0 px-1 rounded text-xs ${docStatusColor(d.status)}`}>
                  {t(`status.${d.status}`, { defaultValue: d.status })}
                </span>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Dropzone multi-file upload ───────────────────────────────────────────────

type UploadItem = {
  id: string;
  file: File;
  title: string;
  evidence_type: string;
  valid_until: string;
};

function DropzoneUpload({ instanceId, plant }: { instanceId: string; plant: string | null }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [queue, setQueue] = useState<UploadItem[]>([]);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState({ current: 0, total: 0 });

  const oneYearOut = (() => {
    const d = new Date();
    d.setFullYear(d.getFullYear() + 1);
    return d.toISOString().split("T")[0];
  })();

  function addFiles(files: FileList | File[]) {
    const items: UploadItem[] = Array.from(files).map(file => ({
      id: `${Date.now()}-${Math.random()}`,
      file,
      title: file.name.replace(/\.[^/.]+$/, ""),
      evidence_type: "altro",
      valid_until: oneYearOut,
    }));
    setQueue(prev => [...prev, ...items]);
  }

  function removeItem(id: string) {
    setQueue(prev => prev.filter(i => i.id !== id));
  }

  function updateItem(id: string, field: keyof UploadItem, value: string) {
    setQueue(prev => prev.map(i => i.id === id ? { ...i, [field]: value } : i));
  }

  async function uploadAll() {
    if (!queue.length) return;
    setUploading(true);
    setProgress({ current: 0, total: queue.length });
    for (let i = 0; i < queue.length; i++) {
      const item = queue[i];
      try {
        const ev = await documentsApi.createEvidence({
          file: item.file,
          title: item.title,
          evidence_type: item.evidence_type,
          valid_until: item.valid_until,
          plant: plant ?? undefined,
        });
        await controlsApi.linkEvidence(instanceId, ev.id);
      } catch {
        // continue with next file on error
      }
      setProgress({ current: i + 1, total: queue.length });
    }
    setQueue([]);
    setUploading(false);
    qc.invalidateQueries({ queryKey: ["control-detail", instanceId] });
    qc.invalidateQueries({ queryKey: ["evidences"] });
  }

  const canUpload = queue.length > 0 && queue.every(i => i.title && i.valid_until) && !uploading;

  const EVIDENCE_TYPES_LIST = ["screenshot", "log", "report", "verbale", "certificato", "test_result", "altro"] as const;

  return (
    <div className="space-y-2">
      <div
        className={`border-2 border-dashed rounded-lg p-3 text-center cursor-pointer transition-colors ${isDragging ? "border-green-400 bg-green-50" : "border-gray-300 hover:border-gray-400 hover:bg-gray-50"}`}
        onDragOver={e => { e.preventDefault(); setIsDragging(true); }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={e => { e.preventDefault(); setIsDragging(false); addFiles(e.dataTransfer.files); }}
        onClick={() => fileInputRef.current?.click()}
      >
        <div className="text-xl mb-0.5">📎</div>
        <p className="text-xs text-gray-600 font-medium">{t("controls.drawer.docs.dropzone_hint")}</p>
        <p className="text-xs text-gray-400">{t("controls.drawer.docs.dropzone_or_browse")}</p>
        <p className="text-xs text-gray-300 mt-0.5">PDF · XLS · DOCX · PNG · JPG — max 50 MB</p>
        <input ref={fileInputRef} type="file" multiple className="hidden" onChange={e => e.target.files && addFiles(e.target.files)} />
      </div>

      {queue.length > 0 && (
        <div className="space-y-1.5">
          <p className="text-xs font-medium text-gray-600">{t("controls.drawer.docs.upload_queue_title", { count: queue.length })}</p>
          {queue.map(item => (
            <div key={item.id} className="border rounded p-1.5 bg-gray-50 space-y-1">
              <div className="flex items-center gap-1">
                <span className="text-xs text-gray-400 shrink-0">📎</span>
                <input
                  value={item.title}
                  onChange={e => updateItem(item.id, "title", e.target.value)}
                  className="flex-1 border rounded px-1.5 py-0.5 text-xs min-w-0"
                />
                <button onClick={() => removeItem(item.id)} className="text-red-400 hover:text-red-600 text-xs shrink-0 ml-1">✕</button>
              </div>
              <div className="flex gap-1">
                <select
                  value={item.evidence_type}
                  onChange={e => updateItem(item.id, "evidence_type", e.target.value)}
                  className="border rounded px-1 py-0.5 text-xs flex-1"
                >
                  {EVIDENCE_TYPES_LIST.map(v => (
                    <option key={v} value={v}>{evidenceIcon(v)} {t(`documents.evidence.types.${v}`)}</option>
                  ))}
                </select>
                <input
                  type="date"
                  value={item.valid_until}
                  onChange={e => updateItem(item.id, "valid_until", e.target.value)}
                  className="border rounded px-1 py-0.5 text-xs"
                />
              </div>
            </div>
          ))}
          <button
            onClick={uploadAll}
            disabled={!canUpload}
            className="w-full py-1.5 bg-green-600 text-white text-xs rounded hover:bg-green-700 disabled:opacity-50 font-medium"
          >
            {uploading
              ? t("controls.drawer.docs.uploading_progress", { current: progress.current, total: progress.total })
              : t("controls.drawer.docs.upload_all_link", { count: queue.length })}
          </button>
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────

function EvidencesColumn({
  instanceId,
  evidences,
  requirements,
  plant,
}: {
  instanceId: string;
  evidences: EvidenceRef[];
  requirements: RequirementsCheck;
  plant: string | null;
}) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [searchQ, setSearchQ] = useState("");
  const debounced = useDebounce(searchQ);

  function requirementLabel(type: string, description?: string) {
    if (type === "any") return description || "";
    return t(`documents.evidence.types.${type}`, { defaultValue: description || type });
  }

  const { data: searchResults } = useQuery({
    queryKey: ["ev-search", debounced],
    queryFn: () => documentsApi.searchEvidences(debounced),
    enabled: debounced.length > 2,
  });

  const unlinkMut = useMutation({
    mutationFn: (evId: string) => controlsApi.unlinkEvidence(instanceId, evId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["control-detail", instanceId] }),
  });
  const linkMut = useMutation({
    mutationFn: (evId: string) => controlsApi.linkEvidence(instanceId, evId),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["control-detail", instanceId] }); setSearchQ(""); },
  });

  const linkedEvIds = new Set(evidences.map(e => e.id));

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 mb-1">
        <span className="text-base">🔬</span>
        <span className="text-xs font-semibold text-gray-700 uppercase tracking-wide">{t("controls.drawer.docs.operational_evidence")}</span>
        <span className="ml-auto text-xs bg-gray-100 text-gray-600 px-1.5 rounded">{evidences.length}</span>
      </div>

      {/* Requisiti mancanti */}
      {requirements.missing_evidences.length > 0 && (
        <div className="space-y-1">
          {requirements.missing_evidences.map((m, i) => (
            <div key={i} className="flex items-center gap-1.5 text-xs bg-red-50 border border-red-200 rounded px-2 py-1">
              <span className="text-red-500 font-bold shrink-0">!</span>
              <span className="text-red-700">{requirementLabel(m.type, m.description)}</span>
              <span className="ml-auto text-xs text-red-500 font-medium shrink-0">{t("controls.drawer.docs.missing")}</span>
            </div>
          ))}
        </div>
      )}

      {/* Lista evidenze collegate */}
      {evidences.length === 0 ? (
        <p className="text-xs text-gray-400 italic">{t("controls.drawer.docs.no_evidence_linked")}</p>
      ) : (
        <div className="space-y-1.5">
          {evidences.map(e => (
            <div key={e.id} className="bg-white border border-gray-200 rounded px-2.5 py-2">
              <div className="flex items-start justify-between gap-1">
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-medium text-gray-800 truncate">
                    {evidenceIcon(e.evidence_type)} {e.title}
                  </p>
                  <div className="mt-0.5">
                    <ExpiryBadge validUntil={e.valid_until} />
                  </div>
                </div>
                <button
                  onClick={() => unlinkMut.mutate(e.id)}
                  disabled={unlinkMut.isPending}
                  className="text-red-400 hover:text-red-600 text-xs shrink-0 ml-1"
                  title={t("controls.drawer.docs.unlink")}
                >
                  ✕
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Collega evidenza esistente */}
      <div className="border border-dashed border-gray-300 rounded p-2 space-y-1.5">
        <p className="text-xs font-medium text-gray-500">{t("controls.drawer.docs.link_existing_evidence")}</p>
        <input
          type="text"
          value={searchQ}
          onChange={e => setSearchQ(e.target.value)}
          placeholder={t("controls.drawer.docs.search_placeholder")}
          className="w-full border rounded px-2 py-1 text-xs"
        />
        {searchResults && searchResults.results.length > 0 && (
          <div className="border rounded divide-y divide-gray-100 max-h-32 overflow-y-auto bg-white">
            {searchResults.results.filter(ev => !linkedEvIds.has(ev.id)).slice(0, 8).map(ev => (
              <button
                key={ev.id}
                onClick={() => linkMut.mutate(ev.id)}
                disabled={linkMut.isPending}
                className="w-full text-left px-2 py-1.5 text-xs hover:bg-blue-50 text-gray-700 flex items-center gap-1.5"
              >
                <span>{evidenceIcon(ev.evidence_type)}</span>
                <span className="truncate flex-1">{ev.title}</span>
                {ev.valid_until && <ExpiryBadge validUntil={ev.valid_until} />}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Dropzone caricamento evidenze */}
      <div className="border border-dashed border-green-300 rounded p-2">
        <p className="text-xs font-medium text-green-700 mb-1.5">{t("controls.drawer.docs.upload_new_evidence")}</p>
        <DropzoneUpload instanceId={instanceId} plant={plant} />
      </div>
    </div>
  );
}

function TabDocEvidence({
  instanceId,
  evidences,
  documents,
  requirements,
  evidenceRequirement,
}: {
  instanceId: string;
  evidences: EvidenceRef[];
  documents: LinkedDocument[];
  requirements: RequirementsCheck;
  evidenceRequirement: EvidenceRequirement;
}) {
  const { t } = useTranslation();
  const plant = useAuthStore(s => s.selectedPlant?.id ?? null);
  const noRequirements = !evidenceRequirement ||
    (!evidenceRequirement.documents?.length && !evidenceRequirement.evidences?.length &&
     !evidenceRequirement.min_documents && !evidenceRequirement.min_evidences);

  function requirementLabel(kind: "document" | "evidence", type: string, description?: string) {
    if (type === "any") return description || "";
    if (kind === "document") return t(`documents.type.${type}`, { defaultValue: description || type });
    return t(`documents.evidence.types.${type}`, { defaultValue: description || type });
  }

  return (
    <div className="space-y-3">
      {/* Banner requisiti */}
      {noRequirements ? (
        <div className="bg-gray-50 border border-gray-200 rounded-lg px-3 py-2 text-xs text-gray-500">
          ℹ️ {t("controls.drawer.evaluation.requirements.none")}
        </div>
      ) : !requirements.satisfied ? (
        <div className="bg-red-50 border border-red-200 rounded-lg px-3 py-2 text-xs text-red-800">
          <p className="font-semibold mb-1">⛔ {t("controls.drawer.docs.requirements.not_satisfied_for_compliant")}</p>
          {requirements.missing_documents.map((m, i) => <p key={i}>• {t("controls.drawer.evaluation.requirements.missing_document")}: {requirementLabel("document", m.type, m.description)}</p>)}
          {requirements.missing_evidences.map((m, i) => <p key={i}>• {t("controls.drawer.evaluation.requirements.missing_evidence")}: {requirementLabel("evidence", m.type, m.description)}</p>)}
          {requirements.expired_evidences.map((e, i) => <p key={i}>• {t("controls.drawer.evaluation.requirements.expired_evidence")}: {e.title} ({e.expired_on})</p>)}
        </div>
      ) : requirements.warnings.length > 0 ? (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg px-3 py-2 text-xs text-yellow-800">
          <p className="font-semibold mb-1">⚠️ {t("controls.drawer.evaluation.requirements.warning")}</p>
          {requirements.warnings.map((w, i) => <p key={i}>• {w}</p>)}
        </div>
      ) : (
        <div className="bg-green-50 border border-green-200 rounded-lg px-3 py-2 text-xs text-green-800">
          ✅ {t("controls.drawer.evaluation.requirements.satisfied")}
        </div>
      )}

      {/* Due colonne */}
      <div className="grid grid-cols-2 gap-3">
        <DocsColumn instanceId={instanceId} documents={documents} requirements={requirements} plant={plant} />
        <EvidencesColumn instanceId={instanceId} evidences={evidences} requirements={requirements} plant={plant} />
      </div>
    </div>
  );
}

// ─── Tab 4: Storico ───────────────────────────────────────────────────────────

function TabStorico({ history }: { history: NonNullable<ReturnType<typeof useDetailInfo>["data"]>["evaluation_history"] }) {
  const { t } = useTranslation();
  if (history.length === 0) {
    return <p className="text-sm text-gray-400 italic">{t("controls.drawer.history.empty")}</p>;
  }
  const statusIcon: Record<string, string> = {
    compliant: "🟢", parziale: "🟡", gap: "🔴", na: "⚪", non_valutato: "⬜",
  };
  return (
    <div className="relative">
      <div className="absolute left-3.5 top-0 bottom-0 w-px bg-gray-200" />
      <div className="space-y-4">
        {history.map((h, i) => {
          const status = (h.payload as Record<string, string>)["new_status"] ?? "";
          const note = (h.payload as Record<string, string>)["note"] ?? "";
          return (
            <div key={i} className="relative pl-8">
              <div className="absolute left-1.5 top-1 w-4 h-4 rounded-full bg-white border-2 border-gray-300 flex items-center justify-center text-xs">
                {statusIcon[status] ?? "•"}
              </div>
              <div className="bg-gray-50 border border-gray-200 rounded-lg px-3 py-2">
                <div className="flex items-center justify-between mb-0.5">
                  <span className="text-xs font-medium text-gray-700">{h.user_email_at_time}</span>
                  <span className="text-xs text-gray-400">{new Date(h.timestamp_utc).toLocaleString(i18n.language || "it")}</span>
                </div>
                <p className="text-xs text-gray-600">
                  {t("controls.drawer.history.set_status")} <strong>{t(`status.${status}`, { defaultValue: status })}</strong>
                  {note && <> — <em>"{note}"</em></>}
                </p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ─── Custom hook ──────────────────────────────────────────────────────────────

function useDetailInfo(instanceId: string | null) {
  return useQuery({
    queryKey: ["control-detail", instanceId, i18n.language],
    queryFn: () => controlsApi.detailInfo(instanceId!, i18n.language),
    enabled: !!instanceId,
    retry: false,
  });
}

// ─── Main drawer ─────────────────────────────────────────────────────────────

interface Props {
  instanceId: string | null;
  onClose: () => void;
}

export function ControlDetailDrawer({ instanceId, onClose }: Props) {
  const { t } = useTranslation();
  const [tab, setTab] = useState<Tab>("cosa");
  const { data: info, isLoading } = useDetailInfo(instanceId);
  const qc = useQueryClient();
  const open = !!instanceId;

  const tabs: [Tab, string][] = [
    ["cosa",        t("controls.drawer.tabs.about")],
    ["valutazione", t("controls.drawer.tabs.evaluation")],
    ["docevidence", t("controls.drawer.tabs.documents_evidence")],
    ["storico",     t("controls.drawer.tabs.history")],
  ];

  return (
    <>
      {open && <div className="fixed inset-0 bg-black/30 z-40" onClick={onClose} />}
      <div
        className={`fixed top-0 right-0 h-full z-50 bg-white shadow-2xl flex flex-col transition-transform duration-300 ease-in-out ${open ? "translate-x-0" : "translate-x-full"}`}
        style={{ width: "50vw", minWidth: 520 }}
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100 shrink-0 bg-gradient-to-r from-slate-700 to-slate-800">
          <div>
            <h2 className="text-white font-semibold text-base">{t("controls.drawer.title")}</h2>
            <p className="text-slate-300 text-xs mt-0.5">
              {isLoading ? t("common.loading") : info ? `${info.control_id} — ${info.framework}` : "—"}
            </p>
          </div>
          <button onClick={onClose} className="text-white/80 hover:text-white w-8 h-8 flex items-center justify-center rounded hover:bg-white/10 text-xl">×</button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-gray-200 shrink-0">
          {tabs.map(([t, label]) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`flex-1 py-2.5 text-xs font-medium transition-colors ${
                tab === t
                  ? "border-b-2 border-slate-700 text-slate-800 bg-slate-50"
                  : "text-gray-500 hover:text-gray-700 hover:bg-gray-50"
              }`}
            >
              {label}
              {t === "docevidence" && info && !info.requirements.satisfied && (
                <span className="ml-1 inline-flex w-2 h-2 bg-red-500 rounded-full" />
              )}
              {t === "valutazione" && info && info.suggested_status !== info.current_status && (
                <span className="ml-1 inline-flex w-2 h-2 bg-indigo-400 rounded-full" />
              )}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-5 py-4">
          {isLoading && <div className="text-center text-gray-400 py-8">{t("common.loading")}</div>}
          {!isLoading && info && (
            <>
              {tab === "cosa"        && <TabCosa info={info} />}
              {tab === "valutazione" && (
                <TabValutazione
                  instanceId={instanceId!}
                  requirements={info.requirements}
                  currentStatus={info.current_status}
                  suggestedStatus={info.suggested_status}
                  suggestedStatusReason={info.suggested_status_reason}
                  evidenceRequirement={info.evidence_requirement}
                  applicability={info.applicability}
                  exclusionJustification={info.exclusion_justification}
                  naJustification={info.na_justification ?? ""}
                  calcMaturityLevel={info.calc_maturity_level}
                  maturityLevelOverride={info.maturity_level_override}
                  framework={info.framework}
                  needsRevaluation={info.needs_revaluation}
                  needsRevaluationSince={info.needs_revaluation_since}
                  initialNotes={info.notes}
                />
              )}
              {tab === "docevidence" && (
                <TabDocEvidence
                  instanceId={instanceId!}
                  evidences={info.current_evidences}
                  documents={info.linked_documents}
                  requirements={info.requirements}
                  evidenceRequirement={info.evidence_requirement}
                />
              )}
              {tab === "storico"     && <TabStorico history={info.evaluation_history} />}
            </>
          )}
        </div>
      </div>
    </>
  );
}
