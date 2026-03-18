import { useState, useEffect, useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { controlsApi, type EvidenceRef, type LinkedDocument, type RequirementsCheck, type EvidenceRequirement } from "../../api/endpoints/controls";
import { documentsApi, EVIDENCE_TYPE_LABELS } from "../../api/endpoints/documents";
import { useAuthStore } from "../../store/auth";
import { StatusBadge } from "../../components/ui/StatusBadge";
import { useTranslation } from "react-i18next";

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
      {t("controls.drawer.expiry.valid_until", { date: date.toLocaleDateString("it-IT") })}
    </span>
  );
}

const STATUS_GUIDE = [
  { status: "compliant",    icon: "🟢", label: "Compliant",     req: "Evidenza valida non scaduta + data ultima verifica", badge: "bg-green-100 text-green-800" },
  { status: "parziale",     icon: "🟡", label: "Parziale",      req: "Evidenza anche parziale + piano di remediation (task M08)", badge: "bg-yellow-100 text-yellow-800" },
  { status: "gap",          icon: "🔴", label: "Gap",           req: "Nessuno per salvare — task remediation generato automaticamente", badge: "bg-red-100 text-red-800" },
  { status: "na",           icon: "⚪", label: "N/A",           req: "Giustificazione scritta min 20 caratteri. TISAX L3: doppia approvazione", badge: "bg-gray-100 text-gray-600" },
  { status: "non_valutato", icon: "⬜", label: "Non valutato",  req: "Abbassa il compliance score del plant", badge: "bg-gray-50 text-gray-500" },
];

type Tab = "cosa" | "valutazione" | "docevidence" | "storico";

// ─── Tab 1: Cos'è ─────────────────────────────────────────────────────────────

function TabCosa({ info }: { info: NonNullable<ReturnType<typeof useDetailInfo>["data"]> }) {
  const { t } = useTranslation();
  const [guidanceOpen, setGuidanceOpen] = useState(false);
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

const MATURITY_LABELS: Record<number, string> = {
  0: "Non implementato",
  1: "Ad-hoc",
  2: "Pianificato",
  3: "Definito",
  4: "Gestito",
  5: "Ottimizzato",
};

const APPLICABILITY_LABELS: Record<string, string> = {
  applicabile:    "Applicabile",
  escluso:        "Escluso",
  non_pertinente: "Non pertinente",
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
  calcMaturityLevel,
  maturityLevelOverride,
  framework,
  needsRevaluation,
  needsRevaluationSince,
}: {
  instanceId: string;
  requirements: RequirementsCheck;
  currentStatus: string;
  suggestedStatus: string;
  suggestedStatusReason: string;
  evidenceRequirement: EvidenceRequirement;
  applicability: string;
  exclusionJustification: string;
  calcMaturityLevel: number;
  maturityLevelOverride: boolean;
  framework: string;
  needsRevaluation?: boolean;
  needsRevaluationSince?: string | null;
}) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [selectedStatus, setSelectedStatus] = useState("");
  const [note, setNote] = useState("");
  const [blockError, setBlockError] = useState("");
  const [applyModalOpen, setApplyModalOpen] = useState(false);
  const [applyNote, setApplyNote] = useState("");
  const [manualOpen, setManualOpen] = useState(false);
  const [selectedApplicability, setSelectedApplicability] = useState(applicability);
  const [justification, setJustification] = useState(exclusionJustification);
  const [applicabilityError, setApplicabilityError] = useState("");
  const [maturityOverrideVal, setMaturityOverrideVal] = useState(calcMaturityLevel);

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
              since: needsRevaluationSince ? new Date(needsRevaluationSince).toLocaleDateString("it-IT") : "",
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
            <p key={i}>• {t("controls.drawer.evaluation.requirements.missing_document")}: {m.description || m.type}</p>
          ))}
          {requirements.missing_evidences.map((m, i) => (
            <p key={i}>• {t("controls.drawer.evaluation.requirements.missing_evidence")}: {m.description || m.type}</p>
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
          {Object.entries(APPLICABILITY_LABELS).map(([v, l]) => (
            <option key={v} value={v}>{t(`controls.drawer.evaluation.applicability.options.${v}`, { defaultValue: l })}</option>
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
          <p className="text-xs text-gray-500">{MATURITY_LABELS[maturityOverrideVal]}</p>
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
                {requirements.missing_documents.map((m, i) => <p key={i}>• {t("controls.drawer.evaluation.requirements.missing_document")}: {m.description || m.type}</p>)}
                {requirements.missing_evidences.map((m, i) => <p key={i}>• {t("controls.drawer.evaluation.requirements.missing_evidence")}: {m.description || m.type}</p>)}
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
  const qc = useQueryClient();
  const [searchQ, setSearchQ] = useState("");
  const debounced = useDebounce(searchQ);

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
        <span className="text-xs font-semibold text-gray-700 uppercase tracking-wide">Documenti di policy</span>
        <span className="ml-auto text-xs bg-gray-100 text-gray-600 px-1.5 rounded">{documents.length}</span>
      </div>

      {/* Requisiti mancanti */}
      {requirements.missing_documents.length > 0 && (
        <div className="space-y-1">
          {requirements.missing_documents.map((m, i) => (
            <div key={i} className="flex items-center gap-1.5 text-xs bg-red-50 border border-red-200 rounded px-2 py-1">
              <span className="text-red-500 font-bold shrink-0">!</span>
              <span className="text-red-700">{m.description || m.type}</span>
              <span className="ml-auto text-xs text-red-500 font-medium shrink-0">Mancante</span>
            </div>
          ))}
        </div>
      )}

      {/* Lista documenti collegati */}
      {documents.length === 0 ? (
        <p className="text-xs text-gray-400 italic">Nessun documento collegato</p>
      ) : (
        <div className="space-y-1.5">
          {documents.map(d => (
            <div key={d.id} className="bg-white border border-gray-200 rounded px-2.5 py-2">
              <div className="flex items-start justify-between gap-1">
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-medium text-gray-800 truncate">{d.title}</p>
                  <div className="flex items-center gap-1 mt-0.5 flex-wrap">
                    <span className="text-xs bg-indigo-50 text-indigo-700 px-1 rounded">{d.document_type}</span>
                    <span className={`text-xs px-1 rounded ${docStatusColor(d.status)}`}>{d.status}</span>
                    {d.review_due_date && (
                      <span className="text-xs text-gray-400">rev. {new Date(d.review_due_date).toLocaleDateString("it-IT")}</span>
                    )}
                  </div>
                </div>
                <button
                  onClick={() => unlinkMut.mutate(d.id)}
                  disabled={unlinkMut.isPending}
                  className="text-red-400 hover:text-red-600 text-xs shrink-0 ml-1"
                  title="Scollega"
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
        <p className="text-xs font-medium text-gray-500">Collega documento</p>
        <input
          type="text"
          value={searchQ}
          onChange={e => setSearchQ(e.target.value)}
          placeholder="Cerca per titolo..."
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
                <span className={`shrink-0 px-1 rounded text-xs ${docStatusColor(d.status)}`}>{d.status}</span>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function EvidencesColumn({
  instanceId,
  evidences,
  requirements,
}: {
  instanceId: string;
  evidences: EvidenceRef[];
  requirements: RequirementsCheck;
}) {
  const qc = useQueryClient();
  const [searchQ, setSearchQ] = useState("");
  const [newEv, setNewEv] = useState({ title: "", evidence_type: "altro", valid_until: "" });
  const debounced = useDebounce(searchQ);
  const today = new Date().toISOString().split("T")[0];

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
  const createAndLinkMut = useMutation({
    mutationFn: async () => {
      const ev = await documentsApi.createEvidence(newEv);
      return controlsApi.linkEvidence(instanceId, ev.id);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["control-detail", instanceId] });
      setNewEv({ title: "", evidence_type: "altro", valid_until: "" });
    },
  });

  const linkedEvIds = new Set(evidences.map(e => e.id));

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 mb-1">
        <span className="text-base">🔬</span>
        <span className="text-xs font-semibold text-gray-700 uppercase tracking-wide">Evidenze operative</span>
        <span className="ml-auto text-xs bg-gray-100 text-gray-600 px-1.5 rounded">{evidences.length}</span>
      </div>

      {/* Requisiti mancanti */}
      {requirements.missing_evidences.length > 0 && (
        <div className="space-y-1">
          {requirements.missing_evidences.map((m, i) => (
            <div key={i} className="flex items-center gap-1.5 text-xs bg-red-50 border border-red-200 rounded px-2 py-1">
              <span className="text-red-500 font-bold shrink-0">!</span>
              <span className="text-red-700">{m.description || m.type}</span>
              <span className="ml-auto text-xs text-red-500 font-medium shrink-0">Mancante</span>
            </div>
          ))}
        </div>
      )}

      {/* Lista evidenze collegate */}
      {evidences.length === 0 ? (
        <p className="text-xs text-gray-400 italic">Nessuna evidenza collegata</p>
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
                  title="Scollega"
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
        <p className="text-xs font-medium text-gray-500">Collega evidenza esistente</p>
        <input
          type="text"
          value={searchQ}
          onChange={e => setSearchQ(e.target.value)}
          placeholder="Cerca per titolo..."
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

      {/* Carica nuova evidenza */}
      <div className="border border-dashed border-green-300 rounded p-2 space-y-1.5">
        <p className="text-xs font-medium text-green-700">Carica nuova evidenza</p>
        <input
          type="text"
          placeholder="Titolo *"
          value={newEv.title}
          onChange={e => setNewEv(p => ({ ...p, title: e.target.value }))}
          className="w-full border rounded px-2 py-1 text-xs"
        />
        <select
          value={newEv.evidence_type}
          onChange={e => setNewEv(p => ({ ...p, evidence_type: e.target.value }))}
          className="w-full border rounded px-2 py-1 text-xs"
        >
          {Object.entries(EVIDENCE_TYPE_LABELS).map(([v, l]) => (
            <option key={v} value={v}>{evidenceIcon(v)} {l}</option>
          ))}
        </select>
        <div>
          <label className="text-xs text-gray-500 block mb-0.5">Data validità * (non passata)</label>
          <input
            type="date"
            min={today}
            value={newEv.valid_until}
            onChange={e => setNewEv(p => ({ ...p, valid_until: e.target.value }))}
            className="w-full border rounded px-2 py-1 text-xs"
          />
        </div>
        <button
          onClick={() => createAndLinkMut.mutate()}
          disabled={createAndLinkMut.isPending || !newEv.title || !newEv.valid_until}
          className="w-full py-1 bg-green-600 text-white text-xs rounded hover:bg-green-700 disabled:opacity-50"
        >
          {createAndLinkMut.isPending ? "Caricamento..." : "Carica e collega"}
        </button>
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
  const plant = useAuthStore(s => s.selectedPlant?.id ?? null);
  const noRequirements = !evidenceRequirement ||
    (!evidenceRequirement.documents?.length && !evidenceRequirement.evidences?.length &&
     !evidenceRequirement.min_documents && !evidenceRequirement.min_evidences);

  return (
    <div className="space-y-3">
      {/* Banner requisiti */}
      {noRequirements ? (
        <div className="bg-gray-50 border border-gray-200 rounded-lg px-3 py-2 text-xs text-gray-500">
          ℹ️ Nessun requisito documentale definito per questo controllo.
        </div>
      ) : !requirements.satisfied ? (
        <div className="bg-red-50 border border-red-200 rounded-lg px-3 py-2 text-xs text-red-800">
          <p className="font-semibold mb-1">⛔ Requisiti non soddisfatti per Compliant</p>
          {requirements.missing_documents.map((m, i) => <p key={i}>• Documento mancante: {m.description || m.type}</p>)}
          {requirements.missing_evidences.map((m, i) => <p key={i}>• Evidenza mancante: {m.description || m.type}</p>)}
          {requirements.expired_evidences.map((e, i) => <p key={i}>• Evidenza scaduta: {e.title} ({e.expired_on})</p>)}
        </div>
      ) : requirements.warnings.length > 0 ? (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg px-3 py-2 text-xs text-yellow-800">
          <p className="font-semibold mb-1">⚠️ Attenzione</p>
          {requirements.warnings.map((w, i) => <p key={i}>• {w}</p>)}
        </div>
      ) : (
        <div className="bg-green-50 border border-green-200 rounded-lg px-3 py-2 text-xs text-green-800">
          ✅ Tutti i requisiti soddisfatti
        </div>
      )}

      {/* Due colonne */}
      <div className="grid grid-cols-2 gap-3">
        <DocsColumn instanceId={instanceId} documents={documents} requirements={requirements} plant={plant} />
        <EvidencesColumn instanceId={instanceId} evidences={evidences} requirements={requirements} />
      </div>
    </div>
  );
}

// ─── Tab 4: Storico ───────────────────────────────────────────────────────────

function TabStorico({ history }: { history: NonNullable<ReturnType<typeof useDetailInfo>["data"]>["evaluation_history"] }) {
  if (history.length === 0) {
    return <p className="text-sm text-gray-400 italic">Nessuna valutazione registrata.</p>;
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
                  <span className="text-xs text-gray-400">{new Date(h.timestamp_utc).toLocaleString("it-IT")}</span>
                </div>
                <p className="text-xs text-gray-600">
                  ha impostato <strong>{status}</strong>
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

import i18n from "../../i18n";

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
        style={{ width: 560 }}
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
                  calcMaturityLevel={info.calc_maturity_level}
                  maturityLevelOverride={info.maturity_level_override}
                  framework={info.framework}
                  needsRevaluation={info.needs_revaluation}
                  needsRevaluationSince={info.needs_revaluation_since}
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
