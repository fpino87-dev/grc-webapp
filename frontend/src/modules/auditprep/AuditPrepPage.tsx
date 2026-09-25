import { useState, useEffect } from "react";
import { useQueries, useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import {
  auditPrepApi,
  type AuditFinding,
  type AuditPrep,
  type AuditProgram,
  type AuditType,
  type AutoValidateResult,
  type EvidenceItem,
  type PlannedAudit,
  type SyncControlsResult,
} from "../../api/endpoints/auditPrep";
import { plantsApi } from "../../api/endpoints/plants";
import { pdcaApi } from "../../api/endpoints/pdca";
import { apiClient } from "../../api/client";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useAuthStore } from "../../store/auth";
import { StatusBadge } from "../../components/ui/StatusBadge";
import { ModuleHelp } from "../../components/ui/ModuleHelp";

// ─── helpers ──────────────────────────────────────────────────────────────────

function fwLabel(code: string | undefined | null): string {
  if (!code) return "—";
  if (code === "TISAX_L3") return "TISAX AL3 (L2+L3)";
  if (code === "TISAX_L2") return "TISAX AL2";
  if (code === "TISAX_PROTO") return "TISAX Prototype Protection";
  return code;
}

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = filename; a.click();
  URL.revokeObjectURL(url);
}

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

// ─── Audit esterni: tipo, committente, rapporto ufficiale ─────────────────────

const AUDIT_TYPES: AuditType[] = ["interno", "seconda_parte", "terza_parte"];

/** Seconda parte: i punti di verifica sono del cliente → niente checklist né prontezza. */
const usesChecklist = (prep: Pick<AuditPrep, "audit_type">) => prep.audit_type !== "seconda_parte";

/** Riepilogo rilievi al posto della prontezza (audit di seconda parte). */
function FindingsSummary({ prep, findings }: { prep: AuditPrep; findings: AuditFinding[] }) {
  const { t } = useTranslation();
  const open = findings.filter(f => f.status === "open" || f.status === "in_response");
  const nc = open.filter(f => f.finding_type === "major_nc" || f.finding_type === "minor_nc").length;
  return (
    <div className="text-xs text-gray-600 space-y-0.5">
      <p>{t("audit_prep.second_party.summary", { open: open.length, total: findings.length, nc })}</p>
      <p className={prep.report_evidence ? "text-green-700" : "text-amber-700"}>
        {prep.report_evidence ? t("audit_prep.second_party.report_ok") : t("audit_prep.second_party.report_missing")}
      </p>
    </div>
  );
}

/** Badge del tipo di audit, solo per gli audit esterni (seconda/terza parte). */
function AuditTypeBadge({ prep }: { prep: AuditPrep }) {
  const { t } = useTranslation();
  const sites = (prep.group_sites ?? []).map(s => s.plant_code).join(", ");
  return (
    <>
      {prep.audit_type && prep.audit_type !== "interno" && (
        <span className="text-xs text-indigo-700 bg-indigo-50 border border-indigo-200 rounded px-1.5 py-0.5">
          {t(`audit_prep.audit_type.${prep.audit_type}`)}
          {prep.requesting_party ? ` — ${prep.requesting_party}` : ""}
        </span>
      )}
      {prep.group && (
        <span className="text-xs text-teal-700 bg-teal-50 border border-teal-200 rounded px-1.5 py-0.5"
          title={prep.group_title ?? undefined}>
          {t("audit_prep.group.badge", { sites })}
        </span>
      )}
    </>
  );
}

function ExternalAuditSection({ prep }: { prep: AuditPrep }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [auditType, setAuditType] = useState<AuditType>(prep.audit_type ?? "interno");
  const [party, setParty] = useState(prep.requesting_party ?? "");
  const [file, setFile] = useState<File | null>(null);
  const [reportTitle, setReportTitle] = useState("");
  const [error, setError] = useState("");
  const editable = prep.status !== "archiviato";
  const dirty = auditType !== (prep.audit_type ?? "interno") || party.trim() !== (prep.requesting_party ?? "");
  const errMsg = (e: unknown) =>
    (e as { response?: { data?: { error?: string } } })?.response?.data?.error || t("audit_prep.error_generic");

  // Audit multi-sito: tipo e committente sono dati comuni → si salvano sul gruppo.
  const saveMutation = useMutation({
    mutationFn: async (): Promise<unknown> => {
      const data = { audit_type: auditType, requesting_party: auditType === "seconda_parte" ? party.trim() : "" };
      return prep.group ? auditPrepApi.updateGroup(prep.group, data) : auditPrepApi.update(prep.id, data);
    },
    onSuccess: () => { setError(""); qc.invalidateQueries({ queryKey: ["audit-prep"] }); },
    onError: (e) => setError(errMsg(e)),
  });
  const uploadMutation = useMutation({
    mutationFn: () => auditPrepApi.uploadReportFile(prep.id, file!, reportTitle.trim() || undefined),
    onSuccess: () => {
      setFile(null); setReportTitle(""); setError("");
      qc.invalidateQueries({ queryKey: ["audit-prep"] });
    },
    onError: (e) => setError(errMsg(e)),
  });
  const detachMutation = useMutation({
    mutationFn: () => auditPrepApi.detachReportFile(prep.id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["audit-prep"] }),
    onError: (e) => setError(errMsg(e)),
  });

  return (
    <div className="border-t border-gray-100 pt-4 space-y-3">
      <h4 className="text-sm font-semibold text-gray-800">{t("audit_prep.external.section_title")}</h4>
      {prep.group && (
        <p className="text-xs text-teal-800 bg-teal-50 border border-teal-200 rounded px-2 py-1.5">
          {t("audit_prep.group.shared_hint", { sites: prep.group_sites.map(s => s.plant_code).join(", ") })}
          {prep.group_scope_id ? ` · ${t("audit_prep.group.scope_id_label")}: ${prep.group_scope_id}` : ""}
        </p>
      )}
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs text-gray-600 mb-1">{t("audit_prep.external.type_label")}</label>
          <select value={auditType} disabled={!editable} onChange={e => setAuditType(e.target.value as AuditType)}
            className="w-full border rounded px-2 py-1.5 text-sm disabled:bg-gray-50">
            {AUDIT_TYPES.map(a => <option key={a} value={a}>{t(`audit_prep.audit_type.${a}`)}</option>)}
          </select>
        </div>
        {auditType === "seconda_parte" && (
          <div>
            <label className="block text-xs text-gray-600 mb-1">{t("audit_prep.external.party_label")}</label>
            <input value={party} disabled={!editable} onChange={e => setParty(e.target.value)}
              placeholder={t("audit_prep.external.party_placeholder")}
              className="w-full border rounded px-2 py-1.5 text-sm disabled:bg-gray-50" />
          </div>
        )}
      </div>
      {editable && dirty && (
        <button onClick={() => saveMutation.mutate()} disabled={saveMutation.isPending}
          className="px-3 py-1.5 text-xs bg-primary-600 text-white rounded disabled:opacity-50">
          {saveMutation.isPending ? t("audit_prep.saving") : t("audit_prep.external.save_btn")}
        </button>
      )}

      <div>
        <p className="text-xs text-gray-600 mb-1">{t("audit_prep.external.report_label")}</p>
        {prep.report_evidence ? (
          <div className="flex flex-wrap items-center gap-2 text-sm">
            <span className="font-medium">📎 {prep.report_evidence_title}</span>
            <button
              onClick={() => auditPrepApi.downloadReportFile(prep.id).then(blob =>
                downloadBlob(blob, prep.report_evidence_filename || prep.report_evidence_title || "rapporto"))}
              className="text-xs text-primary-700 underline">{t("audit_prep.external.download_btn")}</button>
            {editable && (
              <button onClick={() => detachMutation.mutate()} disabled={detachMutation.isPending}
                className="text-xs text-red-600 underline disabled:opacity-50">{t("audit_prep.external.detach_btn")}</button>
            )}
          </div>
        ) : (
          <p className="text-xs text-gray-400">{t("audit_prep.external.no_report")}</p>
        )}
        {editable && (
          <div className="mt-2 space-y-2">
            <input type="file" aria-label={t("audit_prep.external.file_label")}
              onChange={e => setFile(e.target.files?.[0] ?? null)} className="w-full text-sm" />
            <input value={reportTitle} onChange={e => setReportTitle(e.target.value)}
              placeholder={t("audit_prep.external.report_title_placeholder")}
              className="w-full border rounded px-2 py-1.5 text-sm" />
            <button onClick={() => uploadMutation.mutate()} disabled={!file || uploadMutation.isPending}
              className="px-3 py-1.5 text-xs border border-primary-300 text-primary-700 rounded hover:bg-primary-50 disabled:opacity-50">
              {uploadMutation.isPending ? t("audit_prep.saving")
                : prep.report_evidence ? t("audit_prep.external.replace_btn") : t("audit_prep.external.upload_btn")}
            </button>
            <p className="text-xs text-gray-400">{t("audit_prep.external.report_hint")}</p>
          </div>
        )}
      </div>
      {error && <p className="text-xs text-red-600">{error}</p>}
    </div>
  );
}

// ─── Azioni sul finding: PDCA collegato e chiusura ────────────────────────────

const PHASE_LABEL: Record<string, string> = { plan: "PLAN", do: "DO", check: "CHECK", act: "ACT" };

function FindingActions({ finding, prep }: { finding: AuditFinding; prep: AuditPrep }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const navigate = useNavigate();
  const [mode, setMode] = useState<"" | "link" | "unlink" | "replace" | "close">("");
  const [notice, setNotice] = useState("");
  const [cycleId, setCycleId] = useState("");
  const [reason, setReason] = useState("");
  const [notes, setNotes] = useState("");
  const [evidenceId, setEvidenceId] = useState("");
  const [error, setError] = useState("");
  const isClosed = finding.status === "closed" || finding.status === "accepted_by_auditor";
  const isNc = finding.finding_type === "major_nc" || finding.finding_type === "minor_nc";

  // Rilievo comune di un audit multi-sito: con scope org si può usare un solo
  // PDCA di organizzazione per tutti i siti (il backend ricontrolla).
  const { data: caps } = useQuery({ queryKey: ["pdca-capabilities"], queryFn: pdcaApi.capabilities });
  const commonOrg = !!finding.common_key && !!caps?.can_manage_org;
  // Tutti i PDCA del sito, anche chiusi: azione già eseguita o recupero dello storico.
  // Per un rilievo comune anche quelli di organizzazione (?site = sito + org).
  const { data: allCycles = [] } = useQuery({
    queryKey: ["pdca-linkable", prep.plant, commonOrg],
    queryFn: () => pdcaApi.list(commonOrg ? { site: prep.plant } : { plant: prep.plant }).then(r => r.results),
    enabled: mode === "link" || mode === "replace",
  });
  const cycles = allCycles.filter(c => c.id !== finding.pdca_cycle);
  const cycleLabel = (c: { title: string; fase_corrente: string; plant: string | null }) =>
    `${c.plant === null ? `[${t("audit_prep.common_pdca.org_tag")}] ` : ""}${c.title} — ${PHASE_LABEL[c.fase_corrente] ?? c.fase_corrente.toUpperCase()}`;
  const { data: evidences = [] } = useQuery<{ id: string; title: string }[]>({
    queryKey: ["finding-evidences", prep.plant],
    queryFn: () => apiClient.get("/documents/evidences/", { params: { plant: prep.plant, page_size: 1000 } })
      .then(r => r.data.results || r.data),
    enabled: mode === "close",
  });

  const errMsg = (e: unknown) =>
    (e as { response?: { data?: { error?: string } } })?.response?.data?.error || t("audit_prep.error_generic");
  const done = (data?: unknown) => {
    // Rilievo comune collegato al PDCA di organizzazione: siti rimasti fuori
    // perché hanno già un PDCA in lavorazione.
    const skipped = (data as { common_link?: { skipped?: string[] } | null } | undefined)?.common_link?.skipped ?? [];
    setNotice(skipped.length ? t("audit_prep.common_pdca.skipped", { sites: skipped.join(", ") }) : "");
    setMode(""); setError(""); setReason(""); setNotes(""); setCycleId(""); setEvidenceId("");
    qc.invalidateQueries({ queryKey: ["findings"] });
    qc.invalidateQueries({ queryKey: ["pdca"] });
  };
  const openMut = useMutation({ mutationFn: () => auditPrepApi.openPdca(finding.id), onSuccess: done, onError: e => setError(errMsg(e)) });
  const openCommonMut = useMutation({ mutationFn: () => auditPrepApi.openCommonPdca(finding.id), onSuccess: done, onError: e => setError(errMsg(e)) });
  const linkMut = useMutation({ mutationFn: () => auditPrepApi.linkPdca(finding.id, cycleId), onSuccess: done, onError: e => setError(errMsg(e)) });
  const unlinkMut = useMutation({ mutationFn: () => auditPrepApi.unlinkPdca(finding.id, reason), onSuccess: done, onError: e => setError(errMsg(e)) });
  const closeWithPdcaMut = useMutation({
    mutationFn: () => auditPrepApi.closeWithPdca(finding.id),
    onSuccess: () => { done(); qc.invalidateQueries({ queryKey: ["audit-prep"] }); },
    onError: e => setError(errMsg(e)),
  });
  const replaceMut = useMutation({ mutationFn: () => auditPrepApi.replacePdca(finding.id, cycleId, reason), onSuccess: done, onError: e => setError(errMsg(e)) });
  const closeMut = useMutation({
    mutationFn: () => auditPrepApi.closeFinding(finding.id, { closure_notes: notes, evidence_id: evidenceId || undefined }),
    onSuccess: () => { done(); qc.invalidateQueries({ queryKey: ["audit-prep"] }); },
    onError: e => setError(errMsg(e)),
  });

  const btn = "text-xs border rounded px-2 py-0.5 hover:bg-gray-50 disabled:opacity-50";
  return (
    <div className="mt-2 space-y-2">
      <div className="flex flex-wrap items-center gap-2">
        {finding.pdca_cycle ? (
          <>
            <button onClick={() => navigate(`/pdca?cycle=${finding.pdca_cycle}`)}
              className="text-xs text-primary-700 bg-primary-50 border border-primary-200 rounded px-2 py-0.5 hover:bg-primary-100"
              title={finding.pdca_title ?? undefined}>
              {t(finding.pdca_is_org ? "audit_prep.common_pdca.linked" : "audit_prep.pdca_link.linked",
                { phase: PHASE_LABEL[finding.pdca_phase ?? ""] ?? (finding.pdca_phase ?? "").toUpperCase() })}
            </button>
            {commonOrg && !finding.pdca_is_org && !isClosed && (
              <button onClick={() => openCommonMut.mutate()} disabled={openCommonMut.isPending}
                title={t("audit_prep.common_pdca.open_title")} className={`${btn} text-teal-700 border-teal-200`}>
                {t("audit_prep.common_pdca.open")}
              </button>
            )}
            <button onClick={() => setMode(mode === "replace" ? "" : "replace")} className={`${btn} text-gray-600`}>{t("audit_prep.pdca_link.replace")}</button>
            <button onClick={() => setMode(mode === "unlink" ? "" : "unlink")} className={`${btn} text-gray-500`}>{t("audit_prep.pdca_link.unlink")}</button>
          </>
        ) : (
          <>
            {!isClosed && (
              <button onClick={() => openMut.mutate()} disabled={openMut.isPending} className={`${btn} text-primary-700 border-primary-200`}>
                {t("audit_prep.pdca_link.open")}
              </button>
            )}
            {commonOrg && !isClosed && (
              <button onClick={() => openCommonMut.mutate()} disabled={openCommonMut.isPending}
                title={t("audit_prep.common_pdca.open_title")} className={`${btn} text-teal-700 border-teal-200`}>
                {t("audit_prep.common_pdca.open")}
              </button>
            )}
            <button onClick={() => setMode(mode === "link" ? "" : "link")} className={`${btn} text-gray-600`}
              title={isClosed ? t("audit_prep.pdca_link.retro_hint") : undefined}>
              {t("audit_prep.pdca_link.link_existing")}
            </button>
          </>
        )}
        {!isClosed && finding.pdca_phase === "chiuso" && (
          <button onClick={() => closeWithPdcaMut.mutate()} disabled={closeWithPdcaMut.isPending}
            title={t("audit_prep.pdca_link.close_with_title")}
            className={`${btn} text-white bg-green-600 border-green-600 hover:bg-green-700`}>
            {t("audit_prep.pdca_link.close_with")}
          </button>
        )}
        {!isClosed && (
          <button onClick={() => setMode(mode === "close" ? "" : "close")} className={`${btn} text-green-700 border-green-200`}>
            {t("audit_prep.close_finding.btn")}
          </button>
        )}
      </div>

      {mode === "link" && (
        <div className="flex flex-wrap gap-2 items-center">
          <select value={cycleId} onChange={e => setCycleId(e.target.value)} className="border rounded px-2 py-1 text-xs min-w-[14rem]">
            <option value="">{cycles.length ? t("audit_prep.pdca_link.choose_cycle") : t("audit_prep.pdca_link.no_open_cycles")}</option>
            {cycles.map(c => <option key={c.id} value={c.id}>{cycleLabel(c)}</option>)}
          </select>
          <button onClick={() => linkMut.mutate()} disabled={!cycleId || linkMut.isPending} className={`${btn} text-primary-700`}>{t("audit_prep.pdca_link.link_btn")}</button>
        </div>
      )}
      {mode === "replace" && (
        <div className="space-y-2">
          <p className="text-xs text-amber-800">{t("audit_prep.pdca_link.replace_hint")}</p>
          <div className="flex flex-wrap gap-2 items-center">
            <select value={cycleId} onChange={e => setCycleId(e.target.value)} className="border rounded px-2 py-1 text-xs min-w-[14rem]">
              <option value="">{cycles.length ? t("audit_prep.pdca_link.choose_cycle") : t("audit_prep.pdca_link.no_open_cycles")}</option>
              {cycles.map(c => <option key={c.id} value={c.id}>{cycleLabel(c)}</option>)}
            </select>
            <input value={reason} onChange={e => setReason(e.target.value)} placeholder={t("audit_prep.pdca_link.unlink_reason")}
              className="border rounded px-2 py-1 text-xs flex-1 min-w-[12rem]" />
            <button onClick={() => replaceMut.mutate()} disabled={!cycleId || reason.trim().length < 10 || replaceMut.isPending}
              className={`${btn} text-primary-700`}>{t("audit_prep.pdca_link.replace_confirm")}</button>
          </div>
        </div>
      )}
      {mode === "unlink" && (
        <div className="flex flex-wrap gap-2 items-center">
          <input value={reason} onChange={e => setReason(e.target.value)} placeholder={t("audit_prep.pdca_link.unlink_reason")}
            className="border rounded px-2 py-1 text-xs flex-1 min-w-[14rem]" />
          <button onClick={() => unlinkMut.mutate()} disabled={reason.trim().length < 10 || unlinkMut.isPending} className={`${btn} text-red-600`}>
            {t("audit_prep.pdca_link.unlink_confirm")}
          </button>
        </div>
      )}
      {mode === "close" && (
        <div className="space-y-2 bg-gray-50 border rounded p-2">
          {finding.pdca_cycle && finding.pdca_phase !== "chiuso" && finding.pdca_phase !== "archiviato" && (
            <p className="text-xs text-amber-800">{t("audit_prep.close_finding.pdca_hint")}</p>
          )}
          <textarea value={notes} onChange={e => setNotes(e.target.value)} rows={2}
            placeholder={isNc || finding.pdca_phase === "act" ? t("audit_prep.close_finding.notes_min") : t("audit_prep.close_finding.notes")}
            className="w-full border rounded px-2 py-1 text-xs" />
          <select value={evidenceId} onChange={e => setEvidenceId(e.target.value)} className="w-full border rounded px-2 py-1 text-xs">
            <option value="">{isNc ? t("audit_prep.close_finding.evidence_required") : t("audit_prep.close_finding.evidence_optional")}</option>
            {evidences.map(ev => <option key={ev.id} value={ev.id}>{ev.title}</option>)}
          </select>
          <button onClick={() => closeMut.mutate()} disabled={closeMut.isPending || (isNc && (!evidenceId || notes.trim().length < 20))}
            className="px-3 py-1 text-xs bg-green-600 text-white rounded disabled:opacity-50">
            {t("audit_prep.close_finding.confirm")}
          </button>
        </div>
      )}
      {error && <p className="text-xs text-red-600">{error}</p>}
      {notice && <p className="text-xs text-amber-800">{notice}</p>}
    </div>
  );
}

// ─── PrepDrawer ───────────────────────────────────────────────────────────────

function PrepDrawer({ prep, onClose, initialTab = "checklist" }: {
  prep: AuditPrep; onClose: () => void; initialTab?: "checklist" | "findings" | "info";
}) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const checklist = usesChecklist(prep);
  const [tab, setTab] = useState<"checklist" | "findings" | "info">(
    !checklist && initialTab === "checklist" ? "findings" : initialTab,
  );
  // tipo cambiato in "seconda parte" dal tab Info: la checklist sparisce
  useEffect(() => { if (!checklist && tab === "checklist") setTab("findings"); }, [checklist, tab]);
  const [showFindingForm, setShowFindingForm] = useState(false);
  const [findingForm, setFindingForm] = useState<Record<string, string>>({ finding_type: "major_nc" });
  const [, setCompletingId] = useState(false);
  const [cancelModal, setCancelModal] = useState(false);
  const [cancelReason, setCancelReason] = useState("");
  const [autoValidateModal, setAutoValidateModal] = useState(false);
  const [autoValidateResult, setAutoValidateResult] = useState<AutoValidateResult | null>(null);
  const [syncResult, setSyncResult] = useState<SyncControlsResult | null>(null);

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

  const { data: pdcaCaps } = useQuery({ queryKey: ["pdca-capabilities"], queryFn: pdcaApi.capabilities });
  const findingIsNc = findingForm.finding_type === "major_nc" || findingForm.finding_type === "minor_nc";
  // Rilievo comune NC: di default un solo PDCA di organizzazione (solo scope org).
  const canCommonPdca = !!pdcaCaps?.can_manage_org && findingForm.apply_to_group === "true" && findingIsNc;
  const createFindingMutation = useMutation({
    mutationFn: (data: Record<string, unknown>) => auditPrepApi.createFinding(data),
    onSuccess: () => {
      // un rilievo comune crea finding anche sugli altri siti del gruppo
      qc.invalidateQueries({ queryKey: ["findings"] });
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

  const autoValidateMutation = useMutation({
    mutationFn: () => auditPrepApi.autoValidate(prep.id),
    onSuccess: (result) => {
      setAutoValidateResult(result);
      setAutoValidateModal(false);
      qc.invalidateQueries({ queryKey: ["evidence", prep.id] });
      qc.invalidateQueries({ queryKey: ["findings", prep.id] });
      qc.invalidateQueries({ queryKey: ["audit-prep"] });
    },
  });

  const syncControlsMutation = useMutation({
    mutationFn: () => auditPrepApi.syncControls(prep.id),
    onSuccess: (result) => {
      setSyncResult(result);
      qc.invalidateQueries({ queryKey: ["evidence", prep.id] });
      qc.invalidateQueries({ queryKey: ["audit-prep"] });
    },
  });

  const isHierarchicalFramework = prep.framework_code === "TISAX_L3" || prep.framework_code === "TISAX_PROTO";

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
              <AuditTypeBadge prep={prep} />
              {prep.audit_entry_id && <span className="text-xs text-gray-400">{t("audit_prep.annual_program_tag")}</span>}
            </div>
            <h2 className="text-lg font-semibold text-gray-900">{prep.title}</h2>
            <p className="text-xs text-gray-500 mt-0.5">
              {fwLabel(prep.framework_code)} · {prep.auditor_name || "—"} · {prep.audit_date || "—"}
              {checklist && <> · {t(`audit_prep.coverage_${prep.coverage_type}`)}</>}
            </p>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl">✕</button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-gray-200 px-6">
          {(checklist ? (["checklist", "findings", "info"] as const) : (["findings", "info"] as const)).map(tabKey => (
            <button key={tabKey} onClick={() => setTab(tabKey)}
              className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${tab === tabKey ? "border-primary-600 text-primary-600" : "border-transparent text-gray-500 hover:text-gray-700"}`}>
              {tabKey === "checklist"
                ? t("audit_prep.tab_checklist")
                : tabKey === "findings"
                ? t("audit_prep.tab_findings", { count: findings.length })
                : t("audit_prep.tab_info")}
            </button>
          ))}
        </div>

        <div className="flex-1 overflow-auto p-6">

          {/* TAB checklist */}
          {tab === "checklist" && checklist && (
            <div>
              <ReadinessBar score={prep.readiness_score} />

              {prep.status === "in_corso" && (
                <div className="mt-3 flex flex-wrap justify-end gap-2">
                  {isHierarchicalFramework && (
                    <button
                      onClick={() => syncControlsMutation.mutate()}
                      disabled={syncControlsMutation.isPending}
                      className="px-3 py-1.5 bg-amber-600 text-white text-xs rounded hover:bg-amber-700 disabled:opacity-50 flex items-center gap-1.5"
                      title={t("audit_prep.sync_controls.tooltip")}
                    >
                      <span>🔁</span>
                      {syncControlsMutation.isPending
                        ? t("audit_prep.sync_controls.in_progress")
                        : t("audit_prep.sync_controls.button")}
                    </button>
                  )}
                  {evidences.length > 0 && (
                    <button
                      onClick={() => { setAutoValidateResult(null); setAutoValidateModal(true); }}
                      className="px-3 py-1.5 bg-indigo-600 text-white text-xs rounded hover:bg-indigo-700 flex items-center gap-1.5"
                      title={t("audit_prep.auto_validate.tooltip")}
                    >
                      <span>🤖</span>{t("audit_prep.auto_validate.button")}
                    </button>
                  )}
                </div>
              )}

              {syncResult && (
                <div className="mt-3 rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs">
                  <div className="flex items-start justify-between">
                    <div className="font-semibold text-amber-800 mb-1">
                      {t("audit_prep.sync_controls.summary_title")}
                    </div>
                    <button onClick={() => setSyncResult(null)} className="text-amber-400 hover:text-amber-600">✕</button>
                  </div>
                  <div className="text-amber-800">
                    {t("audit_prep.sync_controls.added", { count: syncResult.added })}
                    {" · "}
                    {t("audit_prep.sync_controls.expanded")}: <b>{syncResult.frameworks_expanded.join(", ")}</b>
                  </div>
                  {syncResult.note && <div className="text-amber-600 mt-1">{syncResult.note}</div>}
                </div>
              )}

              {autoValidateResult && (
                <div className="mt-3 rounded-lg border border-indigo-200 bg-indigo-50 p-3 text-xs">
                  <div className="flex items-start justify-between">
                    <div className="font-semibold text-indigo-800 mb-1">
                      {t("audit_prep.auto_validate.summary_title")}
                    </div>
                    <button onClick={() => setAutoValidateResult(null)} className="text-indigo-400 hover:text-indigo-600">✕</button>
                  </div>
                  <div className="grid grid-cols-4 gap-2 mt-2">
                    <span>✅ {t("audit_prep.ev_present_opt")}: <b>{autoValidateResult.presente}</b></span>
                    <span>⚠️ {t("audit_prep.ev_expired_opt")}: <b>{autoValidateResult.scaduto}</b></span>
                    <span>❌ {t("audit_prep.ev_missing_opt")}: <b>{autoValidateResult.mancante}</b></span>
                    <span>➖ {t("audit_prep.ev_na_opt")}: <b>{autoValidateResult.na ?? 0}</b></span>
                  </div>
                  <div className="mt-2 text-indigo-700">
                    {t("audit_prep.auto_validate.findings_created", { count: autoValidateResult.findings_created })}
                    {autoValidateResult.findings_skipped_existing > 0 && (
                      <> · {t("audit_prep.auto_validate.findings_skipped", { count: autoValidateResult.findings_skipped_existing })}</>
                    )}
                    {(autoValidateResult.findings_obsolete ?? 0) > 0 && (
                      <div className="mt-1 text-amber-700">
                        {t("audit_prep.auto_validate.findings_obsolete", { count: autoValidateResult.findings_obsolete })}
                      </div>
                    )}
                    {" · "}
                    Readiness: <b>{autoValidateResult.readiness_score}/100</b>
                  </div>
                  {autoValidateResult.warning?.code === "missing_extended_controls" && (
                    <div className="mt-3 rounded border border-amber-300 bg-amber-50 p-2 text-amber-800">
                      <div className="font-semibold mb-1">⚠️ {t("audit_prep.auto_validate.warning_missing_extended_title")}</div>
                      <div>
                        {t("audit_prep.auto_validate.warning_missing_extended_body", {
                          requested: autoValidateResult.warning.framework_requested,
                          missing: autoValidateResult.warning.missing_frameworks.join(", "),
                        })}
                      </div>
                    </div>
                  )}
                </div>
              )}

              <div className="mt-4 space-y-1">
                {evidences.length === 0 && (
                  <p className="text-sm text-gray-400 text-center py-8">{t("audit_prep.no_evidence")}</p>
                )}
                {evidences.map(ev => (
                  <div key={ev.id} className="flex items-center gap-3 py-2 border-b border-gray-100">
                    <select
                      value={ev.status}
                      onChange={e => updateEvMutation.mutate({ id: ev.id, status: e.target.value })}
                      className={`text-xs border rounded px-2 py-1 ${ev.status === "presente" ? "border-green-300 bg-green-50" : ev.status === "scaduto" ? "border-yellow-300 bg-yellow-50" : ev.status === "na" ? "border-gray-300 bg-gray-100 text-gray-600" : "border-red-200 bg-red-50"}`}
                    >
                      <option value="mancante">{t("audit_prep.ev_missing_opt")}</option>
                      <option value="presente">{t("audit_prep.ev_present_opt")}</option>
                      <option value="scaduto">{t("audit_prep.ev_expired_opt")}</option>
                      <option value="na">{t("audit_prep.ev_na_opt")}</option>
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
                  {openMajors > 0 && (
                    <span className="px-2 py-1 bg-red-100 text-red-700 rounded font-medium">
                      {t("audit_prep.major_nc_open_count", { count: openMajors })}
                    </span>
                  )}
                </div>
                <button onClick={() => setShowFindingForm(s => !s)}
                  className="px-3 py-1.5 bg-primary-600 text-white text-xs rounded hover:bg-primary-700">
                  {t("audit_prep.add_finding")}
                </button>
              </div>

              {showFindingForm && (
                <div className="bg-gray-50 border rounded-lg p-4 mb-4 space-y-3">
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs text-gray-600 mb-1">{t("audit_prep.type_label")}</label>
                      <select value={findingForm.finding_type} onChange={e => setFindingForm(p => ({ ...p, finding_type: e.target.value }))}
                        className="w-full border rounded px-2 py-1.5 text-sm">
                        <option value="major_nc">Major NC</option>
                        <option value="minor_nc">Minor NC</option>
                        <option value="observation">Observation</option>
                        <option value="opportunity">Opportunity</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-xs text-gray-600 mb-1">{t("audit_prep.audit_date_label")}</label>
                      <input type="date" value={findingForm.audit_date || ""} onChange={e => setFindingForm(p => ({ ...p, audit_date: e.target.value }))}
                        className="w-full border rounded px-2 py-1.5 text-sm" />
                    </div>
                  </div>
                  <div>
                    <label className="block text-xs text-gray-600 mb-1">{t("audit_prep.title_label")}</label>
                    <input value={findingForm.title || ""} onChange={e => setFindingForm(p => ({ ...p, title: e.target.value }))}
                      className="w-full border rounded px-2 py-1.5 text-sm" />
                  </div>
                  <div>
                    <label className="block text-xs text-gray-600 mb-1">{t("audit_prep.description_label")}</label>
                    <textarea value={findingForm.description || ""} rows={2} onChange={e => setFindingForm(p => ({ ...p, description: e.target.value }))}
                      className="w-full border rounded px-2 py-1.5 text-sm" />
                  </div>
                  {prep.group && (
                    <label className="flex items-center gap-2 text-xs text-gray-700">
                      <input type="checkbox" checked={findingForm.apply_to_group === "true"}
                        onChange={e => setFindingForm(p => ({ ...p, apply_to_group: e.target.checked ? "true" : "" }))} />
                      {t("audit_prep.group.common_finding_label", { sites: prep.group_sites.map(s => s.plant_code).join(", ") })}
                    </label>
                  )}
                  {canCommonPdca && (
                    <label className="flex items-center gap-2 text-xs text-gray-700 ml-5">
                      <input type="checkbox" checked={findingForm.common_pdca !== "false"}
                        onChange={e => setFindingForm(p => ({ ...p, common_pdca: e.target.checked ? "true" : "false" }))} />
                      {t("audit_prep.common_pdca.create_label")}
                    </label>
                  )}
                  <div className="flex gap-2">
                    <button
                      disabled={!findingForm.title || !findingForm.audit_date || createFindingMutation.isPending}
                      onClick={() => createFindingMutation.mutate({
                        ...findingForm, audit_prep: prep.id, apply_to_group: findingForm.apply_to_group === "true",
                        common_pdca: canCommonPdca && findingForm.common_pdca !== "false",
                      })}
                      className="px-3 py-1.5 bg-primary-600 text-white text-xs rounded disabled:opacity-50">
                      {createFindingMutation.isPending ? "..." : t("audit_prep.save_finding")}
                    </button>
                    <button onClick={() => setShowFindingForm(false)} className="px-3 py-1.5 border rounded text-xs text-gray-600">
                      {t("audit_prep.cancel_btn")}
                    </button>
                  </div>
                </div>
              )}

              <div className="space-y-2">
                {findings.map(f => (
                  <div key={f.id} className="border rounded-lg p-3">
                    <div className="flex items-start justify-between">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className={`text-xs px-2 py-0.5 rounded font-medium ${FINDING_TYPE_COLORS[f.finding_type]}`}>{f.finding_type.replace("_", " ").toUpperCase()}</span>
                        {f.auto_generated && (
                          <span
                            className="text-xs px-1.5 py-0.5 rounded bg-indigo-100 text-indigo-700 font-medium"
                            title={t("audit_prep.auto_validate.finding_auto_tooltip")}
                          >
                            🤖 {t("audit_prep.auto_validate.finding_auto_badge")}
                          </span>
                        )}
                        <span className="text-sm font-medium text-gray-800">{f.title}</span>
                        {f.common_key && (
                          <span className="text-xs px-1.5 py-0.5 rounded bg-teal-50 text-teal-700 border border-teal-200">
                            {t("audit_prep.group.common_finding_badge")}
                          </span>
                        )}
                        {f.is_overdue && <span className="text-xs text-red-600">{t("audit_prep.finding_overdue")}</span>}
                      </div>
                      <StatusBadge status={f.status} />
                    </div>
                    {f.description && <p className="text-xs text-gray-500 mt-1">{f.description}</p>}
                    <div className="flex gap-3 mt-1 text-xs text-gray-400">
                      {f.response_deadline && <span>{t("audit_prep.finding_deadline")} {f.response_deadline}</span>}
                      {f.control_external_id && <span>{t("audit_prep.finding_control")} {f.control_external_id}</span>}
                    </div>
                    <FindingActions finding={f} prep={prep} />
                  </div>
                ))}
                {findings.length === 0 && <p className="text-sm text-gray-400 text-center py-6">{t("audit_prep.no_findings")}</p>}
              </div>
            </div>
          )}

          {/* TAB info */}
          {tab === "info" && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div><span className="text-gray-500">{t("audit_prep.framework_col")}</span> <span className="font-medium">{fwLabel(prep.framework_code)}</span></div>
                <div><span className="text-gray-500">{t("audit_prep.coverage_col")}</span> <span className="font-medium">{t(`audit_prep.coverage_${prep.coverage_type}`)}</span></div>
                <div><span className="text-gray-500">{t("audit_prep.auditor_col")}</span> <span className="font-medium">{prep.auditor_name || "—"}</span></div>
                <div><span className="text-gray-500">{t("audit_prep.audit_date_label")}</span> <span className="font-medium">{prep.audit_date || "—"}</span></div>
                <div><span className="text-gray-500">{t("audit_prep.tab_info")}:</span> <StatusBadge status={prep.status} /></div>
                {checklist && <div><span className="text-gray-500">Readiness:</span> <span className="font-medium">{prep.readiness_score ?? "—"}/100</span></div>}
              </div>

              <ExternalAuditSection key={prep.id + (prep.report_evidence ?? "")} prep={prep} />

              {prep.status === "in_corso" && (
                <div className="flex gap-2 pt-4 border-t border-gray-100">
                  <button
                    onClick={() => { setCompletingId(true); completeMutation.mutate(); }}
                    disabled={completeMutation.isPending || openMajors > 0}
                    className="px-4 py-2 bg-green-600 text-white text-sm rounded hover:bg-green-700 disabled:opacity-50"
                    title={openMajors > 0 ? t("audit_prep.cannot_complete", { count: openMajors }) : undefined}
                  >
                    {completeMutation.isPending ? "..." : t("audit_prep.complete_audit_btn")}
                  </button>
                  {openMajors > 0 && (
                    <p className="text-xs text-red-600 self-center">
                      {t("audit_prep.cannot_complete", { count: openMajors })}
                    </p>
                  )}
                  <button onClick={() => setCancelModal(true)}
                    className="px-4 py-2 border border-red-200 text-red-700 text-sm rounded hover:bg-red-50">
                    {t("audit_prep.cancel_audit_btn")}
                  </button>
                </div>
              )}
              {completeMutation.isError && (
                <p className="text-xs text-red-600">
                  {(completeMutation.error as { response?: { data?: { error?: string } } })?.response?.data?.error || t("audit_prep.error_generic")}
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
            {t("audit_prep.download_report")}
          </button>
        </div>
      </div>

      {/* Modal conferma validazione automatica */}
      {autoValidateModal && (
        <div className="fixed inset-0 z-60 bg-black/50 flex items-center justify-center">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-lg p-6">
            <h3 className="font-semibold mb-2 flex items-center gap-2">
              <span>🤖</span>{t("audit_prep.auto_validate.modal_title")}
            </h3>
            <p className="text-sm text-gray-600 mb-3">
              {t("audit_prep.auto_validate.modal_intro", { count: evidences.length })}
            </p>
            <ul className="text-xs text-gray-600 list-disc list-inside space-y-1 bg-gray-50 rounded p-3 mb-3">
              <li>{t("audit_prep.auto_validate.rule_present")}</li>
              <li>{t("audit_prep.auto_validate.rule_expired")}</li>
              <li>{t("audit_prep.auto_validate.rule_missing")}</li>
              <li>{t("audit_prep.auto_validate.rule_idempotent")}</li>
            </ul>
            {autoValidateMutation.isError && (
              <p className="text-xs text-red-600 mb-2">
                {(autoValidateMutation.error as { response?: { data?: { error?: string } } })?.response?.data?.error || t("audit_prep.error_generic")}
              </p>
            )}
            <div className="flex justify-end gap-2 mt-3">
              <button
                onClick={() => setAutoValidateModal(false)}
                disabled={autoValidateMutation.isPending}
                className="px-4 py-2 border rounded text-sm text-gray-600"
              >
                {t("audit_prep.cancel_btn")}
              </button>
              <button
                onClick={() => autoValidateMutation.mutate()}
                disabled={autoValidateMutation.isPending}
                className="px-4 py-2 bg-indigo-600 text-white text-sm rounded disabled:opacity-50 flex items-center gap-1.5"
              >
                {autoValidateMutation.isPending ? (
                  <>{t("audit_prep.auto_validate.in_progress")}</>
                ) : (
                  <>🤖 {t("audit_prep.auto_validate.confirm_btn")}</>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal annulla */}
      {cancelModal && (
        <div className="fixed inset-0 z-60 bg-black/50 flex items-center justify-center">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-6">
            <h3 className="font-semibold mb-2">{t("audit_prep.cancel_prep_modal_title")}</h3>
            <p className="text-sm text-gray-600 mb-3">{t("audit_prep.cancel_prep_modal_desc")}</p>
            <textarea value={cancelReason} onChange={e => setCancelReason(e.target.value)} rows={3}
              className="w-full border rounded px-3 py-2 text-sm" placeholder={t("audit_prep.cancel_reason_placeholder")} />
            <div className="flex justify-end gap-2 mt-3">
              <button onClick={() => setCancelModal(false)} className="px-4 py-2 border rounded text-sm text-gray-600">
                {t("audit_prep.cancel_btn")}
              </button>
              <button disabled={cancelReason.trim().length < 10 || cancelMutation.isPending}
                onClick={() => cancelMutation.mutate()}
                className="px-4 py-2 bg-red-600 text-white text-sm rounded disabled:opacity-50">
                {cancelMutation.isPending ? "..." : t("audit_prep.confirm_cancel_btn")}
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
  const { t } = useTranslation();
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

  // TISAX_L2 e TISAX_L3 sono raggruppati come voce "TISAX" nel selettore.
  // TISAX_PROTO (cap. 8) è autonomo e appare come framework separato.
  const hasTisaxL2L3 = frameworks.some(f => f.code === "TISAX_L2" || f.code === "TISAX_L3");
  const displayFrameworks = hasTisaxL2L3
    ? [
        { id: "TISAX", code: "TISAX", name: "TISAX — VDA ISA 6.0" },
        ...frameworks.filter(f => f.code !== "TISAX_L2" && f.code !== "TISAX_L3"),
      ]
    : frameworks;

  function toggleFw(code: string) {
    setSelectedFwCodes(prev =>
      prev.includes(code) ? prev.filter(c => c !== code) : [...prev, code]
    );
  }

  function resolvedFwCodes(): string[] {
    return selectedFwCodes.flatMap(c => {
      if (c === "TISAX") return frameworks
        .filter(f => f.code === "TISAX_L2" || f.code === "TISAX_L3")
        .map(f => f.code);
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

  const quarterLabel = (q: number) => t(`audit_prep.quarter_${q}`);
  const coverageLabel = (c: string) => t(`audit_prep.coverage_${c}`);

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-3xl max-h-[90vh] flex flex-col">
        <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold">{t("audit_prep.create_program_title")}</h2>
            <div className="flex gap-1 mt-2">
              {[1, 2, 3, 4].map(s => (
                <div key={s} className={`w-8 h-1.5 rounded-full transition-colors ${s <= step ? "bg-primary-600" : "bg-gray-200"}`} />
              ))}
              <span className="text-xs text-gray-500 ml-2">{t("audit_prep.step_indicator", { step })}</span>
            </div>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">✕</button>
        </div>

        <div className="flex-1 overflow-auto p-6">
          {/* STEP 1 */}
          {step === 1 && (
            <div className="space-y-4">
              <h3 className="font-medium text-gray-800">{t("audit_prep.step1_title")}</h3>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm text-gray-600 mb-1">{t("audit_prep.year_label")}</label>
                  <input type="number" value={year} onChange={e => setYear(parseInt(e.target.value))}
                    className="w-full border rounded px-3 py-2 text-sm" />
                </div>
                <div>
                  <label className="block text-sm text-gray-600 mb-1">{t("audit_prep.site_label")}</label>
                  <input value={plantCode} disabled className="w-full border rounded px-3 py-2 text-sm bg-gray-50" />
                </div>
              </div>
              <div>
                <label className="block text-sm text-gray-600 mb-1">{t("audit_prep.program_title_optional")}</label>
                <input value={title} onChange={e => setTitle(e.target.value)} placeholder={`Programma Audit ${year} — ${plantCode}`}
                  className="w-full border rounded px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="block text-sm text-gray-600 mb-2">{t("audit_prep.coverage_type_default_label")}</label>
                <div className="space-y-2">
                  {(["campione", "esteso", "full"] as const).map(v => (
                    <label key={v} className={`flex items-center gap-3 border rounded-lg p-3 cursor-pointer ${coverageType === v ? "border-primary-500 bg-primary-50" : "border-gray-200"}`}>
                      <input type="radio" checked={coverageType === v} onChange={() => setCoverageType(v)} />
                      <span className="text-sm">{t(`audit_prep.coverage_${v}_long`)}</span>
                    </label>
                  ))}
                </div>
                <p className="text-xs text-gray-400 mt-1">{t("audit_prep.coverage_hint")}</p>
              </div>
            </div>
          )}

          {/* STEP 2 */}
          {step === 2 && (
            <div className="space-y-4">
              <h3 className="font-medium text-gray-800">{t("audit_prep.step2_title")}</h3>
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
                  <p className="text-sm font-medium">{t("audit_prep.multi_fw_label")}</p>
                  <p className="text-xs text-gray-500">{t("audit_prep.multi_fw_hint")}</p>
                </div>
              </label>
            </div>
          )}

          {/* STEP 3 */}
          {step === 3 && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="font-medium text-gray-800">{t("audit_prep.step3_title")}</h3>
                <button onClick={loadSuggest} disabled={loadingSuggest}
                  className="px-3 py-1.5 text-xs bg-primary-600 text-white rounded hover:bg-primary-700 disabled:opacity-50">
                  {loadingSuggest ? t("audit_prep.calculating") : t("audit_prep.regenerate_plan")}
                </button>
              </div>

              {suggestedPlan.length === 0 && (
                <div className="text-center py-8">
                  <p className="text-sm text-gray-500 mb-3">{t("audit_prep.generate_plan_hint")}</p>
                  <button onClick={loadSuggest} disabled={loadingSuggest}
                    className="px-4 py-2 bg-primary-600 text-white text-sm rounded hover:bg-primary-700 disabled:opacity-50">
                    {loadingSuggest ? t("audit_prep.calculating_long") : t("audit_prep.generate_plan_btn")}
                  </button>
                </div>
              )}

              <div className="grid grid-cols-2 gap-4">
                {suggestedPlan.map(audit => {
                  const isEditing = editingQ === audit.id;
                  return (
                    <div key={audit.id} className="border border-gray-200 rounded-lg p-4">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-xs font-bold text-gray-500">Q{audit.quarter} — {quarterLabel(audit.quarter)}</span>
                        <button onClick={() => { setEditingQ(isEditing ? null : audit.id); setEditForm(audit); }}
                          className="text-xs text-primary-600 hover:underline">
                          {isEditing ? t("audit_prep.close_edit_btn") : t("audit_prep.edit_btn")}
                        </button>
                      </div>
                      {!isEditing ? (
                        <div className="space-y-1 text-xs text-gray-600">
                          <p><span className="font-medium">{t("audit_prep.date_col")}</span> {audit.planned_date}</p>
                          <p><span className="font-medium">{t("audit_prep.framework_col")}</span> {audit.framework_codes.map(fwLabel).join(", ") || "—"}</p>
                          <p><span className="font-medium">{t("audit_prep.coverage_col")}</span> {coverageLabel(audit.coverage_type)}</p>
                          <p><span className="font-medium">{t("audit_prep.domains_col")}</span> {audit.scope_domains.slice(0, 3).join(", ")}{audit.scope_domains.length > 3 ? ` +${audit.scope_domains.length - 3}` : ""}</p>
                          <p><span className="font-medium">{t("audit_prep.auditor_col")}</span> {audit.auditor_type}</p>
                        </div>
                      ) : (
                        <div className="space-y-2">
                          <input type="date" value={editForm.planned_date || ""} onChange={e => setEditForm(p => ({ ...p, planned_date: e.target.value }))}
                            className="w-full border rounded px-2 py-1 text-xs" />
                          <select value={editForm.coverage_type || "campione"} onChange={e => setEditForm(p => ({ ...p, coverage_type: e.target.value as PlannedAudit["coverage_type"] }))}
                            className="w-full border rounded px-2 py-1 text-xs">
                            <option value="campione">{t("audit_prep.coverage_sample")}</option>
                            <option value="esteso">{t("audit_prep.coverage_extended")}</option>
                            <option value="full">{t("audit_prep.coverage_full")}</option>
                          </select>
                          <select value={editForm.auditor_type || "interno"} onChange={e => setEditForm(p => ({ ...p, auditor_type: e.target.value as "interno" | "esterno" }))}
                            className="w-full border rounded px-2 py-1 text-xs">
                            <option value="interno">{t("audit_prep.internal_auditor_opt")}</option>
                            <option value="esterno">{t("audit_prep.external_auditor_opt")}</option>
                          </select>
                          <input placeholder={t("audit_prep.auditor_name_placeholder")} value={editForm.auditor_name || ""} onChange={e => setEditForm(p => ({ ...p, auditor_name: e.target.value }))}
                            className="w-full border rounded px-2 py-1 text-xs" />
                          <button onClick={() => {
                            setSuggestedPlan(prev => prev.map(a => a.id === audit.id ? { ...a, ...editForm } : a));
                            setEditingQ(null);
                          }} className="w-full py-1 bg-primary-600 text-white text-xs rounded">{t("audit_prep.save_btn")}</button>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
              {suggestedPlan.length > 0 && (
                <p className="text-xs text-gray-400 mt-2">{t("audit_prep.plan_priority_hint")}</p>
              )}
            </div>
          )}

          {/* STEP 4 */}
          {step === 4 && (
            <div className="space-y-4">
              <h3 className="font-medium text-gray-800">{t("audit_prep.step4_title")}</h3>
              <div className="bg-gray-50 rounded-lg p-4 text-sm space-y-1">
                <p><span className="text-gray-500">{t("audit_prep.year_recap")}</span> <strong>{year}</strong></p>
                <p><span className="text-gray-500">{t("audit_prep.title_recap")}</span> <strong>{title || `Programma Audit ${year} — ${plantCode}`}</strong></p>
                <p><span className="text-gray-500">{t("audit_prep.framework_recap")}</span> <strong>{selectedFwCodes.join(", ")}</strong></p>
                <p><span className="text-gray-500">{t("audit_prep.coverage_default_recap")}</span> <strong>{coverageLabel(coverageType)}</strong></p>
              </div>
              <table className="w-full text-xs border border-gray-200 rounded">
                <thead className="bg-gray-100">
                  <tr>
                    <th className="px-3 py-2 text-left">{t("audit_prep.table_q")}</th>
                    <th className="px-3 py-2 text-left">{t("audit_prep.table_date")}</th>
                    <th className="px-3 py-2 text-left">{t("audit_prep.table_framework")}</th>
                    <th className="px-3 py-2 text-left">{t("audit_prep.table_coverage")}</th>
                    <th className="px-3 py-2 text-left">{t("audit_prep.table_domains")}</th>
                    <th className="px-3 py-2 text-left">{t("audit_prep.table_auditor")}</th>
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
                <span className="text-sm">{t("audit_prep.approve_now_label")}</span>
              </label>
              {createMutation.isError && (
                <p className="text-xs text-red-600">{t("audit_prep.create_program_error")}</p>
              )}
            </div>
          )}
        </div>

        <div className="px-6 py-4 border-t border-gray-200 flex justify-between">
          <button onClick={() => step > 1 ? setStep(s => s - 1) : onClose()}
            className="px-4 py-2 border rounded text-sm text-gray-600 hover:bg-gray-50">
            {step === 1 ? t("audit_prep.cancel_btn") : t("audit_prep.back_btn")}
          </button>
          {step < 4 ? (
            <button
              disabled={step === 2 && selectedFwCodes.length === 0}
              onClick={() => { if (step === 2) loadSuggest(); setStep(s => s + 1); }}
              className="px-4 py-2 bg-primary-600 text-white text-sm rounded hover:bg-primary-700 disabled:opacity-50">
              {t("audit_prep.next_btn")}
            </button>
          ) : (
            <button onClick={() => createMutation.mutate()} disabled={createMutation.isPending}
              className="px-4 py-2 bg-green-600 text-white text-sm rounded hover:bg-green-700 disabled:opacity-50">
              {createMutation.isPending ? t("audit_prep.creating") : t("audit_prep.create_program_btn")}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── QuarterCard ──────────────────────────────────────────────────────────────

const AUDIT_STATUS_META_KEYS: Record<string, { icon: string; color: string; bg: string; labelKey: string }> = {
  planned:     { labelKey: "audit_prep.status_planned",     icon: "⏳", color: "text-gray-600",  bg: "bg-gray-100" },
  in_progress: { labelKey: "audit_prep.status_in_progress", icon: "🔵", color: "text-blue-700",  bg: "bg-blue-50"  },
  completed:   { labelKey: "audit_prep.status_completed",   icon: "✅", color: "text-green-700", bg: "bg-green-50" },
  cancelled:   { labelKey: "audit_prep.status_cancelled",   icon: "❌", color: "text-red-600",   bg: "bg-red-50"   },
};

function QuarterCard({ audit, programId, onLaunched, onEdit }: {
  audit: PlannedAudit;
  programId: string;
  onLaunched: (prepId: string) => void;
  onEdit: () => void;
}) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [confirmLaunch, setConfirmLaunch] = useState(false);
  const meta = AUDIT_STATUS_META_KEYS[audit.status] ?? AUDIT_STATUS_META_KEYS.planned;

  const coverageLabel = (c: string) => t(`audit_prep.coverage_${c}`);

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
          <span className="text-xs font-bold text-gray-500">Q{audit.quarter} — {t(`audit_prep.quarter_${audit.quarter}`)}</span>
          <span className={`text-xs font-medium ${meta.color}`}>{meta.icon} {t(meta.labelKey)}</span>
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
              <button onClick={onEdit} className="px-2 py-1 text-xs border border-gray-300 bg-white rounded hover:bg-gray-50">{t("audit_prep.edit_btn")}</button>
              <button onClick={() => setConfirmLaunch(true)} className="px-2 py-1 text-xs bg-primary-600 text-white rounded hover:bg-primary-700">{t("audit_prep.launch_audit_btn")}</button>
            </>
          )}
          {(audit.status === "in_progress") && audit.audit_prep_id && (
            <button onClick={() => onLaunched(audit.audit_prep_id!)} className="px-2 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700">{t("audit_prep.go_to_prep_btn")}</button>
          )}
          {audit.status === "completed" && (
            <span className="text-xs text-green-700">Score: {audit.audit_prep_id ? t("audit_prep.open_btn").toLowerCase() : "—"}</span>
          )}
        </div>
      </div>

      {confirmLaunch && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-sm p-6">
            <h3 className="font-semibold mb-2">{t("audit_prep.launch_audit_title", { quarter: audit.quarter })}</h3>
            <div className="text-sm text-gray-600 space-y-1 mb-4">
              <p><strong>{t("audit_prep.framework_col")}</strong> {audit.framework_codes.map(fwLabel).join(", ")}</p>
              <p><strong>{t("audit_prep.coverage_col")}</strong> {coverageLabel(audit.coverage_type)}</p>
              {audit.auditor_name && <p><strong>{t("audit_prep.auditor_col")}</strong> {audit.auditor_name}</p>}
            </div>
            {launchMutation.isError && (
              <p className="text-xs text-red-600 mb-2">
                {(launchMutation.error as { response?: { data?: { error?: string } } })?.response?.data?.error || t("audit_prep.error_generic")}
              </p>
            )}
            <div className="flex gap-2 justify-end">
              <button onClick={() => setConfirmLaunch(false)} className="px-4 py-2 border rounded text-sm">{t("audit_prep.cancel_btn")}</button>
              <button onClick={() => launchMutation.mutate()} disabled={launchMutation.isPending}
                className="px-4 py-2 bg-primary-600 text-white text-sm rounded disabled:opacity-50">
                {launchMutation.isPending ? t("audit_prep.launching") : t("audit_prep.launch_btn")}
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
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [form, setForm] = useState<Partial<PlannedAudit>>({ ...audit });

  const saveMutation = useMutation({
    mutationFn: () => auditPrepApi.updateAudit(programId, audit.id, form as Record<string, unknown>),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["audit-programs"] }); onClose(); },
  });

  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6">
        <h3 className="font-semibold mb-4">{t("audit_prep.edit_audit_title", { quarter: audit.quarter })}</h3>
        <div className="space-y-3">
          <div>
            <label className="block text-xs text-gray-600 mb-1">{t("audit_prep.planned_date_label")}</label>
            <input type="date" value={form.planned_date || ""} onChange={e => setForm(p => ({ ...p, planned_date: e.target.value }))}
              className="w-full border rounded px-3 py-2 text-sm" />
          </div>
          <div>
            <label className="block text-xs text-gray-600 mb-1">{t("audit_prep.coverage_type_edit_label")}</label>
            <select value={form.coverage_type || "campione"} onChange={e => setForm(p => ({ ...p, coverage_type: e.target.value as PlannedAudit["coverage_type"] }))}
              className="w-full border rounded px-3 py-2 text-sm">
              <option value="campione">{t("audit_prep.coverage_sample")}</option>
              <option value="esteso">{t("audit_prep.coverage_extended")}</option>
              <option value="full">{t("audit_prep.coverage_full")}</option>
            </select>
          </div>
          <div>
            <label className="block text-xs text-gray-600 mb-1">{t("audit_prep.auditor_type_label")}</label>
            <select value={form.auditor_type || "interno"} onChange={e => setForm(p => ({ ...p, auditor_type: e.target.value as "interno" | "esterno" }))}
              className="w-full border rounded px-3 py-2 text-sm">
              <option value="interno">{t("audit_prep.internal_opt")}</option>
              <option value="esterno">{t("audit_prep.external_opt")}</option>
            </select>
          </div>
          <div>
            <label className="block text-xs text-gray-600 mb-1">{t("audit_prep.auditor_label")}</label>
            <input value={form.auditor_name || ""} onChange={e => setForm(p => ({ ...p, auditor_name: e.target.value }))}
              className="w-full border rounded px-3 py-2 text-sm" />
          </div>
          <div>
            <label className="block text-xs text-gray-600 mb-1">{t("audit_prep.notes_label")}</label>
            <textarea value={form.notes || ""} rows={2} onChange={e => setForm(p => ({ ...p, notes: e.target.value }))}
              className="w-full border rounded px-3 py-2 text-sm" />
          </div>
        </div>
        <div className="flex gap-2 justify-end mt-4">
          <button onClick={onClose} className="px-4 py-2 border rounded text-sm text-gray-600">{t("audit_prep.cancel_btn")}</button>
          <button onClick={() => saveMutation.mutate()} disabled={saveMutation.isPending}
            className="px-4 py-2 bg-primary-600 text-white text-sm rounded disabled:opacity-50">
            {saveMutation.isPending ? "..." : t("audit_prep.save_changes_btn")}
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── AuditPrepCard ────────────────────────────────────────────────────────────

function AuditPrepCard({ prep, onOpen, onDelete }: { prep: AuditPrep; onOpen: () => void; onDelete: () => void }) {
  const { t } = useTranslation();
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
          <AuditTypeBadge prep={prep} />
          {prep.audit_entry_id && <span className="text-xs text-gray-400 border border-gray-200 rounded px-1.5 py-0.5">{t("audit_prep.program_tag_short")}</span>}
        </div>
        <button onClick={onDelete} className="text-gray-300 hover:text-red-500 text-sm" title={t("audit_prep.delete_btn")}>🗑</button>
      </div>
      <h3 className="font-semibold text-gray-900 mb-1">{prep.title}</h3>
      <p className="text-xs text-gray-500 mb-3">
        {fwLabel(prep.framework_code)} · {prep.auditor_name || "—"} · {prep.audit_date || "—"}
      </p>
      {usesChecklist(prep)
        ? <ReadinessBar score={prep.readiness_score} />
        : <FindingsSummary prep={prep} findings={findings} />}
      <div className="flex gap-3 mt-2 text-xs text-gray-500">
        {majorOpen > 0 && <span className="text-red-600 font-medium">⚠️ {majorOpen} Major NC</span>}
        {minorOpen > 0 && <span className="text-orange-600">{minorOpen} Minor NC</span>}
      </div>
      <div className="flex gap-2 mt-3">
        <button onClick={onOpen} className="flex-1 px-3 py-1.5 text-xs bg-primary-600 text-white rounded hover:bg-primary-700">{t("audit_prep.open_btn")}</button>
        <button onClick={() => auditPrepApi.downloadPrepReport(prep.id).then(r => downloadBlob(r.data as Blob, `AuditReport_${prep.id}.html`))}
          className="px-3 py-1.5 text-xs border border-gray-200 rounded text-gray-600 hover:bg-white">📄</button>
        {prep.status === "in_corso" && (
          <button onClick={onOpen} className="px-3 py-1.5 text-xs border border-red-200 text-red-600 rounded hover:bg-red-50">{t("audit_prep.findings_btn")}</button>
        )}
      </div>
    </div>
  );
}

// ─── NewPrepModal ─────────────────────────────────────────────────────────────

function NewPrepModal({ plants, onClose }: { plants: { id: string; code: string; name: string }[]; onClose: () => void }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [form, setForm] = useState<Partial<AuditPrep>>({ audit_type: "interno" });
  const [fwKey, setFwKey] = useState("");
  const [tisaxLevel, setTisaxLevel] = useState<"L2" | "L3">("L2");
  // Audit multi-sito (es. TISAX su 2 stabilimenti): un audit per sito, dati comuni.
  const [multi, setMulti] = useState(false);
  const [sites, setSites] = useState<string[]>([]);
  const [scopeId, setScopeId] = useState("");

  const { data: plantFws = [] } = useQuery({
    queryKey: ["plant-frameworks", form.plant],
    queryFn: () => plantsApi.plantFrameworks(form.plant!),
    enabled: !multi && !!form.plant,
  });
  const siteFws = useQueries({
    queries: sites.map(id => ({ queryKey: ["plant-frameworks", id], queryFn: () => plantsApi.plantFrameworks(id) })),
  });

  // Multi-sito: solo i framework assegnati a TUTTI i siti scelti.
  const frameworks = (() => {
    if (!multi) return plantFws.map(pf => ({ id: pf.framework, code: pf.framework_code, name: pf.framework_name }));
    if (sites.length < 2 || siteFws.some(q => !q.data)) return [];
    const [first, ...rest] = siteFws.map(q => q.data!);
    return first
      .filter(pf => rest.every(list => list.some(o => o.framework === pf.framework)))
      .map(pf => ({ id: pf.framework, code: pf.framework_code, name: pf.framework_name }));
  })();
  const siteKey = multi ? sites.join(",") : form.plant;
  useEffect(() => { setFwKey(""); setTisaxLevel("L2"); }, [siteKey]);
  const sitesReady = multi ? sites.length >= 2 : !!form.plant;

  // TISAX_PROTO è autonomo: non va raggruppato con TISAX_L2/L3 nel selettore
  const hasTisax = frameworks.some(f => f.code === "TISAX_L2" || f.code === "TISAX_L3");
  const nonTisax = frameworks.filter(f => f.code !== "TISAX_L2" && f.code !== "TISAX_L3");

  function resolvedFrameworkId(): string | null {
    if (!fwKey) return null;
    if (fwKey === "TISAX") {
      const code = tisaxLevel === "L2" ? "TISAX_L2" : "TISAX_L3";
      return frameworks.find(f => f.code === code)?.id ?? null;
    }
    return fwKey;
  }

  const mutation = useMutation({
    mutationFn: async (): Promise<unknown> => multi
      ? auditPrepApi.createGroup({
          title: form.title, plants: sites, framework: resolvedFrameworkId(),
          audit_type: form.audit_type, requesting_party: form.requesting_party ?? "",
          auditor_name: form.auditor_name ?? "", audit_date: form.audit_date ?? null, scope_id: scopeId.trim(),
        })
      : auditPrepApi.create({ ...form, framework: resolvedFrameworkId() ?? undefined }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["audit-prep"] }); onClose(); },
  });

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-lg p-6">
        <h3 className="text-lg font-semibold mb-4">{t("audit_prep.new_prep_title")}</h3>
        <div className="space-y-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("audit_prep.title_label")}</label>
            <input name="title" onChange={e => setForm(p => ({ ...p, title: e.target.value || undefined }))}
              className="w-full border rounded px-3 py-2 text-sm" />
          </div>
          <label className="flex items-center gap-2 text-sm text-gray-700">
            <input type="checkbox" checked={multi} onChange={e => { setMulti(e.target.checked); setSites([]); }} />
            {t("audit_prep.group.multi_toggle")}
          </label>
          {multi && (
            <div>
              <p className="text-xs text-gray-500 mb-1">{t("audit_prep.group.multi_hint")}</p>
              <div className="flex flex-wrap gap-x-4 gap-y-1 border rounded px-3 py-2">
                {plants.map(p => (
                  <label key={p.id} className="flex items-center gap-1.5 text-sm">
                    <input type="checkbox" checked={sites.includes(p.id)}
                      onChange={e => setSites(prev => e.target.checked ? [...prev, p.id] : prev.filter(x => x !== p.id))} />
                    {p.code} — {p.name}
                  </label>
                ))}
              </div>
            </div>
          )}
          <div className="grid grid-cols-2 gap-3">
            {!multi && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("audit_prep.site_label")}</label>
              <select name="plant" onChange={e => setForm(p => ({ ...p, plant: e.target.value || undefined }))}
                className="w-full border rounded px-3 py-2 text-sm">
                <option value="">{t("audit_prep.select_placeholder")}</option>
                {plants.map(p => <option key={p.id} value={p.id}>{p.code} — {p.name}</option>)}
              </select>
            </div>
            )}
            {multi && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">{t("audit_prep.group.scope_id_label")}</label>
                <input value={scopeId} onChange={e => setScopeId(e.target.value)}
                  placeholder={t("audit_prep.group.scope_id_placeholder")}
                  className="w-full border rounded px-3 py-2 text-sm" />
              </div>
            )}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("audit_prep.step2_title")}</label>
              <select value={fwKey} onChange={e => setFwKey(e.target.value)} disabled={!sitesReady}
                className="w-full border rounded px-3 py-2 text-sm disabled:bg-gray-50 disabled:text-gray-400">
                {!sitesReady
                  ? <option value="">{multi ? t("audit_prep.group.select_sites_first") : t("audit_prep.select_site_first")}</option>
                  : frameworks.length === 0
                    ? <option value="">{multi ? t("audit_prep.group.no_common_framework") : t("audit_prep.no_frameworks_assigned")}</option>
                    : <>
                        <option value="">{t("audit_prep.select_placeholder")}</option>
                        {hasTisax && <option value="TISAX">TISAX — VDA ISA 6.0</option>}
                        {nonTisax.map(f => <option key={f.id} value={f.id}>{f.code} — {f.name}</option>)}
                      </>
                }
              </select>
              {form.audit_type === "seconda_parte" && (
                <p className="text-xs text-gray-500 mt-0.5">{t("audit_prep.second_party.framework_hint")}</p>
              )}
            </div>
          </div>
          {fwKey === "TISAX" && (
            <div className="flex gap-3">
              {(["L2", "L3"] as const).map(l => (
                <label key={l} className={`flex-1 flex items-start gap-2 border rounded-lg px-3 py-2 cursor-pointer ${tisaxLevel === l ? "border-primary-500 bg-primary-50" : "border-gray-200"}`}>
                  <input type="radio" name="tisax_al" value={l} checked={tisaxLevel === l} onChange={() => setTisaxLevel(l)} className="mt-0.5" />
                  <div>
                    <p className="text-sm font-medium">Assessment Level {l}</p>
                    <p className="text-xs text-gray-500">{l === "L2" ? t("audit_prep.tisax_high_protection") : t("audit_prep.tisax_very_high_protection")}</p>
                  </div>
                </label>
              ))}
            </div>
          )}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("audit_prep.external.type_label")}</label>
              <select name="audit_type" value={form.audit_type} className="w-full border rounded px-3 py-2 text-sm"
                onChange={e => setForm(p => ({ ...p, audit_type: e.target.value as AuditType,
                  ...(e.target.value !== "seconda_parte" ? { requesting_party: "" } : {}) }))}>
                {AUDIT_TYPES.map(a => <option key={a} value={a}>{t(`audit_prep.audit_type.${a}`)}</option>)}
              </select>
            </div>
            {form.audit_type === "seconda_parte" && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">{t("audit_prep.external.party_label")}</label>
                <input name="requesting_party" value={form.requesting_party ?? ""}
                  onChange={e => setForm(p => ({ ...p, requesting_party: e.target.value }))}
                  placeholder={t("audit_prep.external.party_placeholder")}
                  className="w-full border rounded px-3 py-2 text-sm" />
              </div>
            )}
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("audit_prep.audit_date_label")}</label>
              <input name="audit_date" type="date" onChange={e => setForm(p => ({ ...p, audit_date: e.target.value || null }))}
                className="w-full border rounded px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {form.audit_type === "interno" ? t("audit_prep.auditor_label") : t("audit_prep.external.body_label")}
              </label>
              <input name="auditor_name" onChange={e => setForm(p => ({ ...p, auditor_name: e.target.value }))}
                className="w-full border rounded px-3 py-2 text-sm" />
            </div>
          </div>
        </div>
        {mutation.isError && (
          <p className="text-sm text-red-600 mt-2">
            {(mutation.error as { response?: { data?: { error?: string; detail?: string } } })?.response?.data?.error
              || (mutation.error as { response?: { data?: { detail?: string } } })?.response?.data?.detail
              || t("audit_prep.save_error")}
          </p>
        )}
        <div className="flex justify-end gap-2 mt-4">
          <button onClick={onClose} className="px-4 py-2 border rounded text-sm text-gray-600">{t("audit_prep.cancel_btn")}</button>
          <button onClick={() => mutation.mutate()} disabled={mutation.isPending || !form.title || (multi ? sites.length < 2 : !form.plant)}
            className="px-4 py-2 bg-primary-600 text-white rounded text-sm disabled:opacity-50">
            {mutation.isPending ? t("audit_prep.saving") : t("audit_prep.create_prep_btn")}
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────

export function AuditPrepPage() {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const selectedPlant = useAuthStore(s => s.selectedPlant);
  const [mainTab, setMainTab] = useState<"program" | "preps">("program");
  const [showWizard, setShowWizard] = useState(false);
  const [showNewPrep, setShowNewPrep] = useState(false);
  const [openPrepId, setOpenPrepId] = useState<string | null>(null);
  // Deep link dal PDCA: /audit-prep?prep=<id> apre l'audit sul tab Finding.
  const [searchParams, setSearchParams] = useSearchParams();
  const [drawerTab, setDrawerTab] = useState<"checklist" | "findings" | "info">("checklist");
  useEffect(() => {
    const linked = searchParams.get("prep");
    if (!linked) return;
    setMainTab("preps");
    setOpenPrepId(linked);
    setDrawerTab("findings");
    setSearchParams({}, { replace: true });
  }, [searchParams, setSearchParams]);
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

  const coverageLabel = (c: string) => t(`audit_prep.coverage_${c}`);

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold text-gray-900 flex items-center gap-2">
          {t("audit_prep.page_title")}
          <ModuleHelp
            title="Audit Preparation — M17"
            description={t("audit_prep.help_description")}
            steps={[
              t("audit_prep.help_step1"),
              t("audit_prep.help_step2"),
              t("audit_prep.help_step3"),
              t("audit_prep.help_step4"),
              t("audit_prep.help_step5"),
              t("audit_prep.help_step6"),
              t("audit_prep.help_step7"),
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
              {t("audit_prep.new_prep_btn")}
            </button>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-0 border-b border-gray-200 mb-6">
        {([["program", t("audit_prep.tab_program")], ["preps", t("audit_prep.tab_in_progress")]] as const).map(([key, label]) => (
          <button key={key} onClick={() => setMainTab(key)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${mainTab === key ? "border-primary-600 text-primary-600" : "border-transparent text-gray-500 hover:text-gray-700"}`}>
            {label}
          </button>
        ))}
      </div>

      {/* ── TAB PROGRAMMA ANNUALE ── */}
      {mainTab === "program" && (
        <div>
          {programsLoading && <p className="text-sm text-gray-400">{t("audit_prep.loading")}</p>}

          {!programsLoading && programs.length === 0 && (
            <div className="text-center py-16 bg-white border border-gray-200 rounded-xl">
              <div className="text-4xl mb-3">📅</div>
              <h3 className="text-lg font-semibold text-gray-800 mb-2">{t("audit_prep.no_program_title")}</h3>
              <p className="text-sm text-gray-500 mb-6 max-w-md mx-auto">
                {t("audit_prep.no_program_desc")}
              </p>
              <button onClick={() => setShowWizard(true)} disabled={!plantId}
                className="px-6 py-2.5 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50">
                {plantId ? t("audit_prep.create_annual_program_btn") : t("audit_prep.select_site_topbar")}
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
                      className="px-3 py-1.5 text-xs bg-green-600 text-white rounded hover:bg-green-700">{t("audit_prep.approve_btn")}</button>
                  )}
                  <button onClick={() => auditPrepApi.syncCompletion(prog.id).then(() => qc.invalidateQueries({ queryKey: ["audit-programs"] }))}
                    className="px-3 py-1.5 text-xs border border-gray-200 rounded text-gray-600 hover:bg-gray-50">{t("audit_prep.sync_btn")}</button>
                  <button onClick={() => auditPrepApi.downloadProgramReport(prog.id).then(r => downloadBlob(r.data as Blob, `ProgrammaAudit_${prog.year}.html`))}
                    className="px-3 py-1.5 text-xs border border-gray-200 rounded text-gray-600 hover:bg-gray-50">{t("audit_prep.report_btn")}</button>
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
                      Q{q} — {t(`audit_prep.quarter_${q}`)}<br />{t("audit_prep.not_planned")}
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
              {t("audit_prep.add_annual_program_btn")}
            </button>
          )}
        </div>
      )}

      {/* ── TAB AUDIT IN CORSO ── */}
      {mainTab === "preps" && (
        <div>
          {preps.length === 0 ? (
            <div className="text-center py-12 bg-white border border-gray-200 rounded-xl">
              <p className="text-sm text-gray-400">{t("audit_prep.no_preps")}</p>
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
      {openPrep && (
        <PrepDrawer key={openPrep.id} prep={openPrep} initialTab={drawerTab}
          onClose={() => { setOpenPrepId(null); setDrawerTab("checklist"); }} />
      )}

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
            <h3 className="font-semibold mb-2">{t("audit_prep.delete_prep_title")}</h3>
            <p className="text-sm text-gray-600 mb-4">{t("audit_prep.delete_prep_desc")}</p>
            {deletePrepMutation.isError && (
              <p className="text-xs text-red-600 mb-3">
                {(deletePrepMutation.error as { response?: { data?: { error?: string } } })?.response?.data?.error || t("audit_prep.error_generic")}
              </p>
            )}
            <div className="flex justify-end gap-2">
              <button onClick={() => setDeleteId(null)} className="px-4 py-2 border rounded text-sm">{t("audit_prep.cancel_btn")}</button>
              <button onClick={() => deletePrepMutation.mutate(deleteId)} disabled={deletePrepMutation.isPending}
                className="px-4 py-2 bg-red-600 text-white rounded text-sm disabled:opacity-50">
                {deletePrepMutation.isPending ? "..." : t("audit_prep.delete_btn")}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Conferma elimina programma */}
      {deleteProgramId && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-sm p-6">
            <h3 className="font-semibold mb-2">{t("audit_prep.delete_program_title")}</h3>
            <p className="text-sm text-gray-600 mb-4">{t("audit_prep.delete_program_desc")}</p>
            <div className="flex justify-end gap-2">
              <button onClick={() => setDeleteProgramId(null)} className="px-4 py-2 border rounded text-sm">{t("audit_prep.cancel_btn")}</button>
              <button onClick={() => deleteProgramMutation.mutate(deleteProgramId)} disabled={deleteProgramMutation.isPending}
                className="px-4 py-2 bg-red-600 text-white rounded text-sm disabled:opacity-50">
                {deleteProgramMutation.isPending ? "..." : t("audit_prep.delete_btn")}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
