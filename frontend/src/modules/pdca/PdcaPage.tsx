import { useState, Fragment } from "react";
import { useTranslation } from "react-i18next";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { pdcaApi, type PdcaCycle, type PdcaLinkedFinding, type PdcaPhase } from "../../api/endpoints/pdca";
import { auditPrepApi } from "../../api/endpoints/auditPrep";
import { useNavigate, useSearchParams } from "react-router-dom";
import { plantsApi } from "../../api/endpoints/plants";
import { useAuthStore } from "../../store/auth";
import { apiClient } from "../../api/client";
import i18n from "../../i18n";

type TFn = (key: string, opts?: Record<string, unknown>) => string;

// I codici sono enum del backend: se ne arriva uno non mappato (nuovo trigger
// non ancora tradotto) si mostra il codice grezzo invece della chiave i18n.
const TRIGGER_CODES = [
  "audit", "incident", "management_review", "risk", "manual",
  "pdca_ko", "gap_controllo", "risk_rosso",
  "finding_major", "finding_minor", "finding_observation", "finding_opportunity",
  "incidente", "bcp_test_fallito", "bcp_rto_sforato", "checklist_incompleta",
];
// Categorie del filtro "origine": il backend le espande nei codici (TRIGGER_GROUPS).
const TRIGGER_FILTERS = [
  "audit", "incident", "management_review", "risk", "controls", "bcp", "checklist", "pdca_ko", "manual",
];
const SCOPE_CODES = ["plant", "org", "process"];
const AUDIT_SUBTYPE_CODES = ["interno", "seconda_parte", "terza_parte"];

// In elenco e scheda i PDCA aperti da un finding sono "Audit" come quelli
// creati a mano: il tipo di finding è già nel titolo ([OBSERVATION] …).
const triggerLabel = (t: TFn, code: string) =>
  code.startsWith("finding_") ? t("pdca.trigger.audit")
    : TRIGGER_CODES.includes(code) ? t(`pdca.trigger.${code}`) : code;
// Valore dei select "Sito" per il ciclo di organizzazione (plant = null).
const ORG_VALUE = "__org__";

const scopeLabel = (t: TFn, code: string) =>
  SCOPE_CODES.includes(code) ? t(`pdca.scope.${code}`) : code;
const auditSubtypeLabel = (t: TFn, code: string) =>
  AUDIT_SUBTYPE_CODES.includes(code) ? t(`pdca.audit_subtype.${code}`) : code;

function DeleteCycleButton({ cycle }: { cycle: PdcaCycle }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState("");
  const [error, setError] = useState("");

  const deleteMutation = useMutation({
    mutationFn: () => pdcaApi.remove(cycle.id, reason.trim()),
    onSuccess: () => {
      setOpen(false);
      setReason("");
      setError("");
      qc.invalidateQueries({ queryKey: ["pdca"] });
    },
    onError: (e: unknown) => {
      const msg =
        (e as { response?: { data?: { error?: string } } })?.response?.data?.error
        || t("pdca.delete.error_generic");
      setError(String(msg));
    },
  });

  if (cycle.fase_corrente === "chiuso") return null;

  return (
    <>
      <button
        type="button"
        onClick={() => { setError(""); setOpen(true); }}
        title={t("pdca.delete.tooltip")}
        className="px-2 py-1 text-[11px] rounded-md text-red-600 hover:bg-red-50 border border-transparent hover:border-red-200"
      >
        🗑
      </button>
      {open && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-6">
            <h3 className="text-lg font-semibold mb-2">{t("pdca.delete.modal_title")}</h3>
            <p className="text-sm text-gray-600 mb-3">{t("pdca.delete.modal_intro", { title: cycle.title })}</p>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {t("pdca.delete.reason_label")}
            </label>
            <textarea
              className="w-full border rounded px-3 py-2 text-sm min-h-[80px]"
              value={reason}
              onChange={e => setReason(e.target.value)}
              placeholder={t("pdca.delete.reason_placeholder")}
            />
            {error && (
              <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded mt-2">{error}</p>
            )}
            <div className="flex justify-end gap-2 mt-4">
              <button
                type="button"
                onClick={() => { setOpen(false); setError(""); }}
                className="px-4 py-2 border rounded text-sm text-gray-600 hover:bg-gray-50"
              >
                {t("pdca.delete.cancel_btn")}
              </button>
              <button
                type="button"
                onClick={() => deleteMutation.mutate()}
                disabled={reason.trim().length < 10 || deleteMutation.isPending}
                className="px-4 py-2 bg-red-600 text-white rounded text-sm hover:bg-red-700 disabled:opacity-50"
              >
                {deleteMutation.isPending ? t("pdca.delete.in_progress") : t("pdca.delete.confirm_btn")}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

function EditCycleModal({ cycle, onClose }: { cycle: PdcaCycle; onClose: () => void }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [form, setForm] = useState({
    title: cycle.title,
    descrizione: cycle.descrizione ?? "",
    trigger_type: cycle.trigger_type,
    audit_subtype: cycle.audit_subtype ?? "",
    riferimento_finding: cycle.riferimento_finding ?? "",
    scope_type: cycle.scope_type,
  });
  const [error, setError] = useState("");

  const mutation = useMutation({
    mutationFn: () => {
      const payload: Partial<PdcaCycle> = {
        title: form.title,
        descrizione: form.descrizione,
        trigger_type: form.trigger_type,
        scope_type: form.scope_type,
        audit_subtype: form.trigger_type === "audit" ? form.audit_subtype || undefined : undefined,
        riferimento_finding: form.trigger_type === "audit" ? form.riferimento_finding : "",
      };
      return pdcaApi.update(cycle.id, payload);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["pdca"] });
      onClose();
    },
    onError: (e: unknown) => {
      const msg =
        (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        t("common.save_error");
      setError(String(msg));
    },
  });

  function handleChange(e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) {
    const { name, value } = e.target;
    setForm(prev => ({ ...prev, [name]: value }));
  }

  const isAudit = form.trigger_type === "audit";

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-lg p-6 max-h-[90vh] overflow-y-auto">
        <h3 className="text-lg font-semibold mb-4">{t("pdca.form.edit_title")}</h3>
        <div className="space-y-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("pdca.form.title_label")}</label>
            <input
              name="title"
              value={form.title}
              onChange={handleChange}
              className="w-full border rounded px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("pdca.form.desc_label")}</label>
            <textarea
              name="descrizione"
              value={form.descrizione}
              onChange={handleChange}
              rows={4}
              className="w-full border rounded px-3 py-2 text-sm"
              placeholder={t("pdca.form.desc_placeholder_edit")}
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("pdca.form.trigger_label")}</label>
              <select name="trigger_type" value={form.trigger_type} onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm">
                {/* origine automatica (es. finding di audit): resta selezionata */}
                {form.trigger_type && !["audit", "incident", "management_review", "risk", "manual"].includes(form.trigger_type) && (
                  <option value={form.trigger_type}>{TRIGGER_CODES.includes(form.trigger_type) ? t(`pdca.trigger.${form.trigger_type}`) : form.trigger_type}</option>
                )}
                <option value="audit">{t("pdca.trigger.audit")}</option>
                <option value="incident">{t("pdca.trigger.incident")}</option>
                <option value="management_review">{t("pdca.trigger.management_review")}</option>
                <option value="risk">{t("pdca.trigger.risk")}</option>
                <option value="manual">{t("pdca.trigger.manual")}</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("pdca.form.scope_label")}</label>
              <select name="scope_type" value={form.scope_type} onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm">
                <option value="plant">{t("pdca.scope.plant")}</option>
                <option value="org">{t("pdca.scope.org")}</option>
                <option value="process">{t("pdca.scope.process")}</option>
              </select>
            </div>
          </div>
          {isAudit && (
            <>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">{t("pdca.form.audit_subtype_label")}</label>
                <select name="audit_subtype" value={form.audit_subtype} onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm">
                  <option value="">{t("common.select")}</option>
                  <option value="interno">{t("pdca.audit_subtype.interno_full")}</option>
                  <option value="seconda_parte">{t("pdca.audit_subtype.seconda_parte_full")}</option>
                  <option value="terza_parte">{t("pdca.audit_subtype.terza_parte_full")}</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">{t("pdca.form.finding_label")}</label>
                <input
                  name="riferimento_finding"
                  value={form.riferimento_finding}
                  onChange={handleChange}
                  className="w-full border rounded px-3 py-2 text-sm"
                  placeholder={t("pdca.form.finding_placeholder_edit")}
                />
              </div>
            </>
          )}
        </div>
        {error && <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded mt-3">{error}</p>}
        <div className="flex justify-end gap-2 mt-4">
          <button onClick={onClose} className="px-4 py-2 border rounded text-sm text-gray-600 hover:bg-gray-50">
            {t("pdca.form.cancel")}
          </button>
          <button
            onClick={() => mutation.mutate()}
            disabled={mutation.isPending || !form.title.trim()}
            className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700 disabled:opacity-50"
          >
            {mutation.isPending ? t("common.saving") : t("pdca.form.save_btn")}
          </button>
        </div>
      </div>
    </div>
  );
}

function EditCycleButton({ cycle }: { cycle: PdcaCycle }) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        title={t("pdca.form.edit_tooltip")}
        className="px-2 py-1 text-[11px] rounded-md text-gray-600 hover:bg-gray-100 border border-transparent hover:border-gray-200"
      >
        ✏️
      </button>
      {open && <EditCycleModal cycle={cycle} onClose={() => setOpen(false)} />}
    </>
  );
}

function ArchiviaCycleButton({ cycle }: { cycle: PdcaCycle }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [motivo, setMotivo] = useState("");
  const [error, setError] = useState("");

  const mutation = useMutation({
    mutationFn: () => pdcaApi.archivia(cycle.id, motivo.trim()),
    onSuccess: () => {
      setOpen(false);
      setMotivo("");
      setError("");
      qc.invalidateQueries({ queryKey: ["pdca"] });
    },
    onError: (e: unknown) => {
      const msg =
        (e as { response?: { data?: { error?: string } } })?.response?.data?.error ||
        t("pdca.archive.error_generic");
      setError(String(msg));
    },
  });

  if (cycle.fase_corrente === "chiuso" || cycle.fase_corrente === "archiviato") return null;

  return (
    <>
      <button
        type="button"
        onClick={() => { setError(""); setOpen(true); }}
        title={t("pdca.archive.tooltip")}
        className="px-2 py-1 text-[11px] rounded-md text-amber-700 hover:bg-amber-50 border border-transparent hover:border-amber-200"
      >
        📦
      </button>
      {open && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-6">
            <h3 className="text-lg font-semibold mb-2">{t("pdca.archive.modal_title")}</h3>
            <p className="text-sm text-gray-600 mb-1">
              <strong>{cycle.title}</strong>
            </p>
            <p className="text-sm text-gray-500 mb-3">{t("pdca.archive.intro")}</p>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {t("pdca.archive.reason_label")}
            </label>
            <textarea
              className="w-full border rounded px-3 py-2 text-sm min-h-[100px]"
              value={motivo}
              onChange={e => setMotivo(e.target.value)}
              placeholder={t("pdca.archive.reason_placeholder")}
            />
            <p className="text-xs text-gray-400 mt-0.5">
              {t("pdca.archive.min_chars", { n: motivo.trim().length })}
            </p>
            {error && (
              <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded mt-2">{error}</p>
            )}
            <div className="flex justify-end gap-2 mt-4">
              <button
                type="button"
                onClick={() => { setOpen(false); setError(""); }}
                className="px-4 py-2 border rounded text-sm text-gray-600 hover:bg-gray-50"
              >
                {t("pdca.form.cancel")}
              </button>
              <button
                type="button"
                onClick={() => mutation.mutate()}
                disabled={motivo.trim().length < 20 || mutation.isPending}
                className="px-4 py-2 bg-amber-600 text-white rounded text-sm hover:bg-amber-700 disabled:opacity-50"
              >
                {mutation.isPending ? t("pdca.archive.in_progress") : t("pdca.archive.confirm_btn")}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

// ─── Collegamento a un finding di audit ───────────────────────────────────────

/** Scelta audit → finding. Con `plant` gli audit sono limitati a quel sito
 *  (collegamento da un ciclo esistente). Di default solo i finding senza PDCA;
 *  con `allowReplace` tutti i finding dell'audit, aperti e chiusi: quelli con
 *  già un PDCA riportano il ciclo e si scelgono per sostituirlo. */
function AuditFindingPicker({
  plant, prepId, findingId, onChange, allowReplace = false, excludeCycle, commonKey,
}: {
  plant?: string | null;
  prepId: string;
  findingId: string;
  onChange: (v: { prepId: string; findingId: string; prepPlant: string | null; currentPdca: string | null }) => void;
  allowReplace?: boolean;
  /** ciclo da cui si collega: i suoi finding non si ripropongono */
  excludeCycle?: string;
  /** ciclo di organizzazione: solo audit multi-sito e rilievi comuni
   *  (`null` = qualunque rilievo comune, stringa = solo quel rilievo) */
  commonKey?: string | null;
}) {
  const { t } = useTranslation();
  const { data: preps = [] } = useQuery({
    queryKey: ["pdca-audit-preps", plant ?? "all", allowReplace],
    queryFn: () => auditPrepApi.list(plant ? { plant } : undefined)
      .then(r => (allowReplace ? r.results : r.results.filter(p => p.status !== "archiviato"))
        .filter(p => commonKey === undefined || !!p.group)),
  });
  const { data: allFindings = [] } = useQuery({
    queryKey: ["pdca-linkable-findings", prepId, allowReplace],
    queryFn: () => auditPrepApi.findings(prepId, allowReplace ? undefined : { without_pdca: "true" }),
    enabled: !!prepId,
  });
  const findings = allFindings
    .filter(f => !excludeCycle || f.pdca_cycle !== excludeCycle)
    .filter(f => commonKey === undefined || (!!f.common_key && (commonKey === null || f.common_key === commonKey)));
  const isClosedFinding = (s: string) => s === "closed" || s === "accepted_by_auditor";
  const prepPlant = (id: string) => preps.find(p => p.id === id)?.plant ?? null;
  const currentPdca = (id: string) => findings.find(f => f.id === id)?.pdca_cycle ?? null;
  return (
    <div className="grid grid-cols-2 gap-3">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">{t("pdca.link.audit_label")}</label>
        <select value={prepId} onChange={e => onChange({ prepId: e.target.value, findingId: "", prepPlant: prepPlant(e.target.value), currentPdca: null })}
          className="w-full border rounded px-3 py-2 text-sm">
          <option value="">{preps.length ? t("pdca.link.audit_select") : t("pdca.link.no_audits")}</option>
          {preps.map(p => (
            <option key={p.id} value={p.id}>
              {p.title}{p.audit_date ? ` (${p.audit_date})` : ""}{p.status === "archiviato" ? ` — ${t("pdca.link.archived_suffix")}` : ""}
            </option>
          ))}
        </select>
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">{t("pdca.link.finding_label")}</label>
        <select value={findingId} disabled={!prepId}
          onChange={e => onChange({ prepId, findingId: e.target.value, prepPlant: prepPlant(prepId), currentPdca: currentPdca(e.target.value) })}
          className="w-full border rounded px-3 py-2 text-sm disabled:bg-gray-50">
          <option value="">
            {prepId && !findings.length
              ? (allowReplace ? t("pdca.link.no_findings_any") : t("pdca.link.no_findings"))
              : t("pdca.link.finding_select")}
          </option>
          {findings.map(f => (
            <option key={f.id} value={f.id}>
              [{f.finding_type.replace("_", " ").toUpperCase()}] {f.title}
              {isClosedFinding(f.status) ? ` (${t("pdca.link.closed_suffix")})` : ""}
              {f.pdca_cycle ? ` — ${t("pdca.link.has_pdca", { title: f.pdca_title ?? "" })}` : ""}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}

const FINDING_STATUS_CHIP: Record<string, string> = {
  open: "bg-amber-50 text-amber-800 border-amber-200",
  in_response: "bg-blue-50 text-blue-800 border-blue-200",
  closed: "bg-green-50 text-green-800 border-green-200",
  accepted_by_auditor: "bg-green-50 text-green-800 border-green-200",
};

/** Finding collegati al ciclo, con rimando all'audit. I finding di un rilievo
 *  comune (stesso common_key) stanno su una riga sola, con un chip per sito;
 *  il titolo del finding si ripete solo se diverso da quello del ciclo. */
function LinkedFindings({ findings, cycleTitle }: { findings: PdcaLinkedFinding[]; cycleTitle: string }) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  if (!findings.length) return null;
  const groups: PdcaLinkedFinding[][] = [];
  const byKey: Record<string, PdcaLinkedFinding[]> = {};
  for (const f of findings) {
    const key = f.common_key ?? f.id;
    if (!byKey[key]) { byKey[key] = []; groups.push(byKey[key]); }
    byKey[key].push(f);
  }
  return (
    <div className="mt-1 space-y-1">
      {groups.map(g => {
        const f = g[0];
        const showTitle = !cycleTitle.includes(f.title);
        const audit = f.group_title ?? f.audit_title;
        return (
          <div key={f.id} className="text-[11px] text-gray-600">
            {showTitle && <div className="text-teal-800">[{f.finding_type.replace("_", " ").toUpperCase()}] {f.title}</div>}
            <div className="flex flex-wrap items-center gap-1">
              <span>🔗 {audit}
                {f.audit_type !== "interno" ? ` (${t(`pdca.audit_subtype.${f.audit_type}`)}${f.requesting_party ? ` — ${f.requesting_party}` : ""})` : ""}
              </span>
              {g.map(s => (
                <button key={s.id} type="button" onClick={() => navigate(`/audit-prep?prep=${s.audit_prep}`)}
                  title={`${s.plant_code} — ${t(`pdca.link.finding_status.${s.status}`, { defaultValue: s.status })}`}
                  className={`font-mono border rounded px-1 hover:underline ${FINDING_STATUS_CHIP[s.status] ?? "bg-gray-50 text-gray-700 border-gray-200"}`}>
                  {s.plant_code}
                </button>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function LinkFindingButton({ cycle }: { cycle: PdcaCycle }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [pick, setPick] = useState({ prepId: "", findingId: "", currentPdca: null as string | null });
  const [replaceReason, setReplaceReason] = useState("");
  const [unlinkId, setUnlinkId] = useState("");
  const [reason, setReason] = useState("");
  const [error, setError] = useState("");
  const errMsg = (e: unknown) =>
    (e as { response?: { data?: { error?: string; detail?: string } } })?.response?.data?.error
    || (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || t("common.save_error");
  const refresh = () => { setError(""); setPick({ prepId: "", findingId: "", currentPdca: null }); setUnlinkId(""); setReason(""); setReplaceReason("");
    qc.invalidateQueries({ queryKey: ["pdca"] }); qc.invalidateQueries({ queryKey: ["pdca-linkable-findings"] }); };
  // Finding con già un PDCA (es. quello automatico della NC): sostituzione con motivo.
  const replacing = !!pick.currentPdca;
  const linkMut = useMutation({
    mutationFn: () => pdcaApi.linkFinding(cycle.id, pick.findingId, replacing ? replaceReason : undefined),
    onSuccess: refresh, onError: e => setError(errMsg(e)),
  });
  const unlinkMut = useMutation({ mutationFn: () => pdcaApi.unlinkFinding(cycle.id, unlinkId, reason), onSuccess: refresh, onError: e => setError(errMsg(e)) });
  const linked = cycle.findings ?? [];
  // Opzione A: più finding solo dello stesso audit → il picker resta sull'audit già collegato.
  const lockedPrep = linked[0]?.audit_prep ?? "";
  // Ciclo di organizzazione: solo rilievi comuni (collegati su tutti i siti).
  const isOrg = cycle.plant === null;

  return (
    <>
      <button type="button" onClick={() => setOpen(true)} title={t("pdca.link.btn_title")}
        className="px-2 py-1 text-[11px] rounded-md border border-teal-200 text-teal-700 hover:bg-teal-50">
        🔗 {t("pdca.link.btn")}
      </button>
      {open && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-xl p-6 space-y-4">
            <h3 className="text-lg font-semibold">{t("pdca.link.modal_title")}</h3>
            <p className="text-xs text-gray-500">{t(isOrg ? "pdca.link.org_rule_hint" : "pdca.link.rule_hint")}</p>
            {linked.length > 0 && (
              <div className="space-y-1">
                {linked.map(f => (
                  <div key={f.id} className="flex items-center justify-between gap-2 text-sm border rounded px-2 py-1">
                    <span>[{f.finding_type.replace("_", " ").toUpperCase()}] {f.title} <span className="text-gray-500">— {f.audit_title}</span></span>
                    <button type="button" onClick={() => setUnlinkId(unlinkId === f.id ? "" : f.id)} className="text-xs text-red-600 underline">
                      {t("pdca.link.unlink")}
                    </button>
                  </div>
                ))}
                {unlinkId && (
                  <div className="flex gap-2">
                    <input value={reason} onChange={e => setReason(e.target.value)} placeholder={t("pdca.link.unlink_reason")}
                      className="flex-1 border rounded px-2 py-1 text-sm" />
                    <button onClick={() => unlinkMut.mutate()} disabled={reason.trim().length < 10 || unlinkMut.isPending}
                      className="px-3 py-1 text-xs border border-red-300 text-red-700 rounded disabled:opacity-50">{t("pdca.link.unlink_confirm")}</button>
                  </div>
                )}
              </div>
            )}
            <AuditFindingPicker plant={cycle.plant} prepId={lockedPrep || pick.prepId} findingId={pick.findingId}
              allowReplace excludeCycle={cycle.id}
              commonKey={isOrg ? (linked[0]?.common_key ?? null) : undefined}
              onChange={v => setPick({ prepId: lockedPrep || v.prepId, findingId: v.findingId, currentPdca: v.currentPdca })} />
            {replacing && (
              <div className="space-y-1">
                <p className="text-xs text-amber-800 bg-amber-50 border border-amber-200 rounded px-2 py-1">{t("pdca.link.replace_hint")}</p>
                <input value={replaceReason} onChange={e => setReplaceReason(e.target.value)} placeholder={t("pdca.link.replace_reason")}
                  className="w-full border rounded px-2 py-1 text-sm" />
              </div>
            )}
            {error && <p className="text-sm text-red-600">{error}</p>}
            <div className="flex justify-end gap-2">
              <button onClick={() => { setOpen(false); setError(""); }} className="px-4 py-2 border rounded text-sm text-gray-600">{t("pdca.form.cancel")}</button>
              <button onClick={() => linkMut.mutate()}
                disabled={!pick.findingId || linkMut.isPending || (replacing && replaceReason.trim().length < 10)}
                className="px-4 py-2 bg-primary-600 text-white rounded text-sm disabled:opacity-50">{t("pdca.link.link_btn")}</button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

function NewCycleModal({ plants, onClose }: { plants: { id: string; code: string; name: string }[]; onClose: () => void }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const selectedPlant = useAuthStore(s => s.selectedPlant);
  const [form, setForm] = useState<Partial<PdcaCycle>>({
    trigger_type: "audit",
    scope_type: "plant",
    // Precompila con il sito attivo in barra: evita di creare cicli sul sito
    // sbagliato quando si sta lavorando su uno stabilimento specifico.
    ...(selectedPlant?.id ? { plant: selectedPlant.id } : {}),
  });
  const [error, setError] = useState("");
  // Il ciclo di organizzazione (senza sito) è riservato a chi ha accesso a
  // tutta l'organizzazione; il backend ricontrolla comunque.
  const { data: caps } = useQuery({ queryKey: ["pdca-capabilities"], queryFn: pdcaApi.capabilities });
  const isOrg = form.plant === null;
  // Origine "Audit": collegamento a un finding registrato (sito e tipo di audit dal finding).
  const [link, setLink] = useState({ prepId: "", findingId: "" });
  const linkedToFinding = form.trigger_type === "audit" && !!link.findingId;

  const mutation = useMutation({
    mutationFn: (data: Partial<PdcaCycle> & { finding?: string }) => pdcaApi.create(data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["pdca"] }); onClose(); },
    onError: (e: any) => setError(e?.response?.data?.detail || t("common.save_error")),
  });

  function handleChange(e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) {
    const { name, value } = e.target;
    setForm(prev => {
      const next: Partial<PdcaCycle> = { ...prev, [name]: value };
      if (name === "plant") {
        if (value === ORG_VALUE) {
          next.plant = null;
          next.scope_type = "org";
        } else {
          if (value === "") delete next.plant;
          if (prev.plant === null) next.scope_type = "plant";
        }
      }
      if (name === "trigger_type" && value !== "audit") {
        delete next.audit_subtype;
        delete next.riferimento_finding;
      }
      return next;
    });
  }

  const isAudit = form.trigger_type === "audit";

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-lg p-6 max-h-[90vh] overflow-y-auto">
        <h3 className="text-lg font-semibold mb-4">{t("pdca.form.new_title")}</h3>
        <div className="space-y-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("pdca.form.plant_label")}</label>
            <select name="plant" value={isOrg ? ORG_VALUE : form.plant ?? ""} onChange={handleChange} disabled={linkedToFinding}
              className="w-full border rounded px-3 py-2 text-sm disabled:bg-gray-50">
              <option value="">{t("common.select")}</option>
              <option value={ORG_VALUE} disabled={!caps?.can_manage_org}>{t("pdca.form.plant_org_option")}</option>
              {plants.map(p => <option key={p.id} value={p.id}>{p.code} — {p.name}</option>)}
            </select>
            <p className="text-xs text-gray-400 mt-0.5">
              {caps?.can_manage_org ? t("pdca.form.plant_org_hint") : t("pdca.form.plant_org_denied")}
            </p>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("pdca.form.title_label")}</label>
            <input name="title" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" placeholder={t("pdca.form.title_placeholder")} />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("pdca.form.desc_label")}</label>
            <textarea
              name="descrizione"
              onChange={e => setForm(prev => ({ ...prev, descrizione: e.target.value }))}
              rows={3}
              className="w-full border rounded px-3 py-2 text-sm"
              placeholder={t("pdca.form.desc_placeholder")}
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("pdca.form.trigger_label")}</label>
              <select name="trigger_type" value={form.trigger_type} onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm">
                <option value="audit">{t("pdca.trigger.audit")}</option>
                <option value="incident">{t("pdca.trigger.incident")}</option>
                <option value="management_review">{t("pdca.trigger.management_review")}</option>
                <option value="risk">{t("pdca.trigger.risk")}</option>
                <option value="manual">{t("pdca.trigger.manual")}</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("pdca.form.scope_label")}</label>
              {/* Ambito "Organizzazione" = ciclo senza sito: si sceglie dal campo Sito. */}
              <select name="scope_type" value={form.scope_type} disabled={isOrg} onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm disabled:bg-gray-50">
                {isOrg
                  ? <option value="org">{t("pdca.scope.org")}</option>
                  : <>
                      <option value="plant">{t("pdca.scope.plant")}</option>
                      <option value="process">{t("pdca.scope.process")}</option>
                    </>}
              </select>
            </div>
          </div>

          {isAudit && (
            <div className="border border-teal-200 bg-teal-50/40 rounded p-3 space-y-2">
              <p className="text-xs text-gray-600">{t("pdca.link.new_hint")}</p>
              <AuditFindingPicker prepId={link.prepId} findingId={link.findingId}
                onChange={v => {
                  setLink({ prepId: v.prepId, findingId: v.findingId });
                  // il sito del ciclo è quello dell'audit
                  if (v.findingId && v.prepPlant) setForm(prev => ({ ...prev, plant: v.prepPlant, scope_type: "plant" }));
                }} />
            </div>
          )}
          {isAudit && !linkedToFinding && (
            <>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">{t("pdca.form.audit_subtype_label")}</label>
                <select name="audit_subtype" value={form.audit_subtype ?? ""} onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm">
                  <option value="">{t("common.select")}</option>
                  <option value="interno">{t("pdca.audit_subtype.interno_full")}</option>
                  <option value="seconda_parte">{t("pdca.audit_subtype.seconda_parte_full")}</option>
                  <option value="terza_parte">{t("pdca.audit_subtype.terza_parte_full")}</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">{t("pdca.form.finding_label")}</label>
                <input
                  name="riferimento_finding"
                  value={form.riferimento_finding ?? ""}
                  onChange={handleChange}
                  className="w-full border rounded px-3 py-2 text-sm"
                  placeholder={t("pdca.form.finding_placeholder")}
                />
                <p className="text-xs text-gray-400 mt-0.5">{t("pdca.form.finding_hint")}</p>
              </div>
            </>
          )}
        </div>
        {error && <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded mt-3">{error}</p>}
        <div className="flex justify-end gap-2 mt-4">
          <button onClick={onClose} className="px-4 py-2 border rounded text-sm text-gray-600 hover:bg-gray-50">{t("pdca.form.cancel")}</button>
          <button
            onClick={() => mutation.mutate(linkedToFinding ? { ...form, finding: link.findingId } : form)}
            disabled={mutation.isPending || (form.plant === undefined && !linkedToFinding) || !form.title}
            className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700 disabled:opacity-50"
          >
            {mutation.isPending ? t("common.saving") : t("pdca.form.create_btn")}
          </button>
        </div>
      </div>
    </div>
  );
}

type Evidence = { id: string; title: string };

function PhaseStepper({ cycle }: { cycle: PdcaCycle & { reopened_as?: string | null } }) {
  const { t } = useTranslation();
  const phases = ["plan", "do", "check", "act"] as const;
  const labels: Record<(typeof phases)[number], string> = {
    plan: t("pdca.phase.plan"),
    do: t("pdca.phase.do"),
    check: t("pdca.phase.check"),
    act: t("pdca.phase.act"),
  };
  const currentIndex = phases.indexOf((cycle.fase_corrente || "plan") as any);

  if (cycle.fase_corrente === "chiuso" || cycle.fase_corrente === "archiviato") {
    const isArchiviato = cycle.fase_corrente === "archiviato";
    return (
      <div className="flex items-center gap-2 text-xs">
        {phases.map((p) => (
          <span key={p} className="px-2 py-0.5 rounded-full bg-gray-100 text-gray-500">
            {labels[p]}
          </span>
        ))}
        <span className={`ml-2 inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold ${isArchiviato ? "bg-amber-100 text-amber-800" : "bg-gray-800 text-white"}`}>
          {isArchiviato ? t("pdca.status.archiviato") : t("pdca.status.chiuso")}
        </span>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-2 text-xs">
      {phases.map((p, idx) => {
        const isDone = idx < currentIndex;
        const isCurrent = idx === currentIndex;
        return (
          <Fragment key={p}>
            <span
              className={`px-2 py-0.5 rounded-full border text-[11px] font-medium ${
                isCurrent
                  ? "bg-primary-600 text-white border-primary-600"
                  : isDone
                  ? "bg-green-100 text-green-800 border-green-200"
                  : "bg-gray-50 text-gray-500 border-gray-200"
              }`}
            >
              {isDone ? "✓ " : ""}
              {labels[p]}
            </span>
            {idx < phases.length - 1 && <span className="text-gray-400 text-[10px]">→</span>}
          </Fragment>
        );
      })}
    </div>
  );
}

const OUTCOME_BADGE: Record<string, { labelKey: string; cls: string }> = {
  ok: { labelKey: "pdca.outcome.ok", cls: "bg-green-100 text-green-800 border-green-200" },
  partial: { labelKey: "pdca.outcome.partial", cls: "bg-amber-100 text-amber-800 border-amber-200" },
  ko: { labelKey: "pdca.outcome.ko", cls: "bg-red-100 text-red-800 border-red-200" },
};

const DOSSIER_PHASES: { key: PdcaPhase["phase"]; labelKey: string; contentKey: string }[] = [
  { key: "plan", labelKey: "pdca.dossier.plan_label", contentKey: "pdca.dossier.plan_content" },
  { key: "do", labelKey: "pdca.dossier.do_label", contentKey: "pdca.dossier.do_content" },
  { key: "check", labelKey: "pdca.dossier.check_label", contentKey: "pdca.dossier.check_content" },
  { key: "act", labelKey: "pdca.dossier.act_label", contentKey: "pdca.dossier.act_content" },
];

function fmtDateTime(d?: string | null): string {
  if (!d) return "—";
  return new Date(d).toLocaleString(i18n.language || "it");
}

function CycleDossierModal({ cycle, onClose }: { cycle: PdcaCycle; onClose: () => void }) {
  const { t } = useTranslation();
  const phases = cycle.phases ?? [];
  const byPhase = (p: string) => phases.find((ph) => ph.phase === p);

  return (
    <div className="fixed inset-0 bg-black/40 flex items-start justify-center z-50 p-4 overflow-y-auto">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-3xl my-6">
        {/* Toolbar (non stampata) */}
        <div className="no-print flex items-center justify-between px-6 py-3 border-b border-gray-200 sticky top-0 bg-white rounded-t-lg">
          <h3 className="text-base font-semibold text-gray-900">{t("pdca.dossier.modal_title")}</h3>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => window.print()}
              className="px-3 py-1.5 text-sm rounded bg-primary-600 text-white hover:bg-primary-700"
            >
              {t("pdca.dossier.print_btn")}
            </button>
            <button
              type="button"
              onClick={onClose}
              className="px-3 py-1.5 text-sm rounded border border-gray-300 text-gray-600 hover:bg-gray-50"
            >
              {t("common.close")}
            </button>
          </div>
        </div>

        {/* Contenuto stampabile */}
        <div id="pdca-dossier-print" className="px-6 py-5">
          <header className="border-b border-gray-200 pb-4 mb-4">
            <h1 className="text-lg font-bold text-gray-900">{cycle.title}</h1>
            {cycle.descrizione && (
              <p className="mt-1 text-sm text-gray-600 whitespace-pre-wrap">{cycle.descrizione}</p>
            )}
            <dl className="mt-3 grid grid-cols-2 gap-x-6 gap-y-1.5 text-xs">
              <div className="flex gap-2">
                <dt className="text-gray-500">{t("pdca.dossier.meta_trigger")}</dt>
                <dd className="text-gray-800 font-medium">{triggerLabel(t, cycle.trigger_type)}</dd>
              </div>
              {cycle.riferimento_finding && (
                <div className="flex gap-2">
                  <dt className="text-gray-500">{t("pdca.dossier.meta_finding")}</dt>
                  <dd className="text-gray-800 font-mono">{cycle.riferimento_finding}</dd>
                </div>
              )}
              <div className="flex gap-2">
                <dt className="text-gray-500">{t("pdca.dossier.meta_scope")}</dt>
                <dd className="text-gray-800">{scopeLabel(t, cycle.scope_type)}</dd>
              </div>
              <div className="flex gap-2">
                <dt className="text-gray-500">{t("pdca.dossier.meta_status")}</dt>
                <dd className="text-gray-800 font-medium uppercase">
                  {t(`pdca.phase.${cycle.fase_corrente}`, { defaultValue: cycle.fase_corrente })}
                </dd>
              </div>
              <div className="flex gap-2">
                <dt className="text-gray-500">{t("pdca.dossier.meta_created")}</dt>
                <dd className="text-gray-800">{fmtDateTime(cycle.created_at)}</dd>
              </div>
              {cycle.closed_at && (
                <div className="flex gap-2">
                  <dt className="text-gray-500">{t("pdca.dossier.meta_closed")}</dt>
                  <dd className="text-gray-800">{fmtDateTime(cycle.closed_at)}</dd>
                </div>
              )}
            </dl>
          </header>

          <ol className="space-y-3">
            {DOSSIER_PHASES.map(({ key, labelKey, contentKey }) => {
              const ph = byPhase(key);
              const done = !!ph?.completed_at;
              // ACT: la standardizzazione è registrata sul ciclo alla chiusura.
              const notes = key === "act" ? (cycle.act_description || ph?.notes || "") : (ph?.notes || "");
              return (
                <li
                  key={key}
                  className={`rounded-lg border p-4 ${done ? "border-gray-200 bg-white" : "border-dashed border-gray-200 bg-gray-50"}`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-semibold text-gray-900">
                      {done ? "✓ " : ""}{t(labelKey)}
                    </span>
                    {ph?.completed_at && (
                      <span className="text-[11px] text-gray-500">
                        {ph.completed_by_username ? `${ph.completed_by_username} · ` : ""}{fmtDateTime(ph.completed_at)}
                      </span>
                    )}
                  </div>

                  {notes ? (
                    <div className="text-xs">
                      <div className="text-gray-500 mb-0.5">{t(contentKey)}</div>
                      <p className="text-gray-800 whitespace-pre-wrap leading-relaxed">{notes}</p>
                    </div>
                  ) : (
                    <p className="text-xs text-gray-400 italic">{t("pdca.dossier.phase_incomplete")}</p>
                  )}

                  {key === "check" && ph?.outcome && OUTCOME_BADGE[ph.outcome] && (
                    <div className="mt-2">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded-full border text-[11px] font-semibold ${OUTCOME_BADGE[ph.outcome].cls}`}>
                        {t("pdca.dossier.outcome_prefix", { outcome: t(OUTCOME_BADGE[ph.outcome].labelKey) })}
                      </span>
                    </div>
                  )}

                  {ph?.evidence && (
                    <div className="mt-2 text-xs">
                      <div className="text-gray-500 mb-0.5">{t("pdca.dossier.evidence_label")}</div>
                      {ph.evidence.file_url ? (
                        <a
                          href={ph.evidence.file_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="print-url inline-flex items-center gap-1 text-primary-700 hover:underline break-all"
                        >
                          📎 {ph.evidence.title}
                        </a>
                      ) : (
                        <span className="text-gray-800">📎 {ph.evidence.title} <span className="text-gray-400">{t("pdca.dossier.no_file")}</span></span>
                      )}
                    </div>
                  )}
                </li>
              );
            })}
          </ol>

          {cycle.motivo_archiviazione && (
            <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-4 text-xs">
              <div className="font-semibold text-amber-800 mb-0.5">{t("pdca.dossier.archived_reason")}</div>
              <p className="text-amber-900 whitespace-pre-wrap">{cycle.motivo_archiviazione}</p>
            </div>
          )}
          {cycle.reopened_as && (
            <p className="mt-3 text-[11px] text-blue-700">{t("pdca.dossier.reopened")}</p>
          )}

          <p className="no-print mt-4 text-[10px] text-gray-400">{t("pdca.dossier.footer_note")}</p>
        </div>
      </div>

      <style>{`
        @media print {
          body * { visibility: hidden !important; }
          #pdca-dossier-print, #pdca-dossier-print * { visibility: visible !important; }
          #pdca-dossier-print {
            position: absolute !important;
            left: 0; top: 0; width: 100%;
            padding: 0 !important;
            -webkit-print-color-adjust: exact; print-color-adjust: exact;
          }
          .no-print { display: none !important; }
          .print-url::after { content: " — " attr(href); font-size: 9px; color: #555; word-break: break-all; }
          @page { margin: 1.5cm; }
        }
      `}</style>
    </div>
  );
}

function CycleDossierButton({ cycle }: { cycle: PdcaCycle }) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        title={t("pdca.dossier.tooltip")}
        className="px-2 py-1 text-[11px] rounded-md text-gray-600 hover:bg-gray-100 border border-transparent hover:border-gray-200"
      >
        📄
      </button>
      {open && <CycleDossierModal cycle={cycle} onClose={() => setOpen(false)} />}
    </>
  );
}

function AdvanceButtons({
  cycle,
  onUpdated,
}: {
  cycle: PdcaCycle & { reopened_as?: string | null };
  onUpdated: () => void;
}) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [open, setOpen] = useState<"plan" | "do" | "check" | "act" | null>(null);
  const [notes, setNotes] = useState("");
  const [outcome, setOutcome] = useState<"" | "ok" | "partial" | "ko">("");
  const [evidenceId, setEvidenceId] = useState("");
  // DO → CHECK: evidenza esistente oppure file caricato qui (stessa richiesta).
  const [evidenceMode, setEvidenceMode] = useState<"existing" | "upload">("existing");
  const [evidenceFile, setEvidenceFile] = useState<File | null>(null);
  const [evidenceTitle, setEvidenceTitle] = useState("");
  const [error, setError] = useState("");
  const { data: evidences } = useQuery<Evidence[]>({
    queryKey: ["pdca-evidences", cycle.plant],
    enabled: open === "do",
    queryFn: async () => {
      // Ciclo di sito: evidenze del sito + di organizzazione. Ciclo di
      // organizzazione: tutte le evidenze visibili (di qualunque sito).
      const res = await apiClient.get("/documents/evidences/", {
        params: { ...(cycle.plant ? { plant: cycle.plant } : {}), page_size: 1000 },
      });
      return res.data.results || res.data;
    },
  });

  const advanceMutation = useMutation({
    mutationFn: async () => {
      if (open === "do" && evidenceMode === "upload" && evidenceFile) {
        const fd = new FormData();
        fd.append("notes", notes);
        fd.append("file", evidenceFile);
        if (evidenceTitle.trim()) fd.append("evidence_title", evidenceTitle.trim());
        const res = await apiClient.post(`/pdca/cycles/${cycle.id}/advance/`, fd, {
          headers: { "Content-Type": "multipart/form-data" },
        });
        return res.data;
      }
      const payload: any = { notes };
      if (open === "do") payload.evidence_id = evidenceId || undefined;
      if (open === "check") payload.outcome = outcome;
      const res = await apiClient.post(`/pdca/cycles/${cycle.id}/advance/`, payload);
      return res.data;
    },
    onSuccess: () => {
      setOpen(null);
      setNotes("");
      setOutcome("");
      setEvidenceId("");
      setEvidenceMode("existing");
      setEvidenceFile(null);
      setEvidenceTitle("");
      setError("");
      qc.invalidateQueries({ queryKey: ["pdca-evidences"] });
      qc.invalidateQueries({ queryKey: ["pdca"] });
      onUpdated();
    },
    onError: (e: any) => {
      const msg = e?.response?.data?.error || t("pdca.advance.error_advance");
      setError(String(msg));
    },
  });

  const closeMutation = useMutation({
    mutationFn: async () => {
      const res = await apiClient.post(`/pdca/cycles/${cycle.id}/close/`, {
        act_description: notes,
      });
      return res.data;
    },
    onSuccess: () => {
      setOpen(null);
      setNotes("");
      setError("");
      qc.invalidateQueries({ queryKey: ["pdca"] });
      onUpdated();
    },
    onError: (e: any) => {
      const msg = e?.response?.data?.error || t("pdca.advance.error_close");
      setError(String(msg));
    },
  });

  const fase = cycle.fase_corrente;

  function renderModal() {
    if (!open) return null;
    const titleMap: Record<string, string> = {
      plan: t("pdca.advance.to_do"),
      do: t("pdca.advance.to_check"),
      check: t("pdca.advance.to_act"),
      act: t("pdca.advance.close"),
    };
    return (
      <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg shadow-xl w-full max-w-lg p-6">
          <h3 className="text-lg font-semibold mb-4">{titleMap[open]}</h3>
          <div className="space-y-4">
            {open === "plan" && (
              <>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  {t("pdca.advance.plan_label")}
                </label>
                <textarea
                  className="w-full border rounded px-3 py-2 text-sm min-h-[100px]"
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder={t("pdca.advance.min_20")}
                />
              </>
            )}
            {open === "do" && (
              <>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  {t("pdca.advance.do_notes_label")}
                </label>
                <textarea
                  className="w-full border rounded px-3 py-2 text-sm min-h-[80px]"
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                />
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    {t("pdca.advance.do_evidence_label")}
                  </label>
                  <div className="flex gap-4 mb-2 text-sm">
                    <label className="flex items-center gap-1.5">
                      <input type="radio" name="evidence_mode" checked={evidenceMode === "existing"}
                             onChange={() => setEvidenceMode("existing")} />
                      {t("pdca.advance.evidence_mode_existing")}
                    </label>
                    <label className="flex items-center gap-1.5">
                      <input type="radio" name="evidence_mode" checked={evidenceMode === "upload"}
                             onChange={() => setEvidenceMode("upload")} />
                      {t("pdca.advance.evidence_mode_upload")}
                    </label>
                  </div>
                  {evidenceMode === "existing" ? (
                    <select
                      className="w-full border rounded px-3 py-2 text-sm"
                      value={evidenceId}
                      onChange={(e) => setEvidenceId(e.target.value)}
                    >
                      <option value="">{t("pdca.advance.evidence_placeholder")}</option>
                      {(evidences || []).map((ev) => (
                        <option key={ev.id} value={ev.id}>
                          {ev.title}
                        </option>
                      ))}
                    </select>
                  ) : (
                    <div className="space-y-2">
                      <input
                        type="file"
                        aria-label={t("pdca.advance.evidence_file_label")}
                        onChange={(e) => setEvidenceFile(e.target.files?.[0] ?? null)}
                        className="w-full text-sm"
                      />
                      <input
                        type="text"
                        value={evidenceTitle}
                        onChange={(e) => setEvidenceTitle(e.target.value)}
                        placeholder={t("pdca.advance.evidence_title_placeholder")}
                        className="w-full border rounded px-3 py-2 text-sm"
                      />
                      <p className="text-xs text-gray-500">{t("pdca.advance.evidence_upload_hint")}</p>
                    </div>
                  )}
                </div>
              </>
            )}
            {open === "check" && (
              <>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  {t("pdca.advance.check_label")}
                </label>
                <textarea
                  className="w-full border rounded px-3 py-2 text-sm min-h-[80px]"
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder={t("pdca.advance.min_10")}
                />
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    {t("pdca.advance.outcome_label")}
                  </label>
                  <select
                    className="w-full border rounded px-3 py-2 text-sm"
                    value={outcome}
                    onChange={(e) => setOutcome(e.target.value as any)}
                  >
                    <option value="">{t("pdca.advance.outcome_placeholder")}</option>
                    <option value="ok">{t("pdca.advance.outcome_ok")}</option>
                    <option value="partial">{t("pdca.advance.outcome_partial")}</option>
                    <option value="ko">{t("pdca.advance.outcome_ko")}</option>
                  </select>
                </div>
                {outcome === "ko" && (
                  <p className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded px-3 py-2">
                    {t("pdca.advance.ko_warning")}
                  </p>
                )}
              </>
            )}
            {open === "act" && (
              <>
                {(cycle.findings?.length ?? 0) > 0 && (
                  <p className="text-xs text-teal-800 bg-teal-50 border border-teal-200 rounded px-2 py-1.5">
                    {t("pdca.advance.findings_close_hint", { count: cycle.findings!.length })}
                  </p>
                )}
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  {t("pdca.advance.act_label")}
                </label>
                <textarea
                  className="w-full border rounded px-3 py-2 text-sm min-h-[100px]"
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder={t("pdca.advance.act_placeholder")}
                />
              </>
            )}
            {error && <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded">{error}</p>}
          </div>
          <div className="flex justify-end gap-2 mt-4">
            <button
              type="button"
              onClick={() => {
                setOpen(null);
                setError("");
              }}
              className="px-4 py-2 border rounded text-sm text-gray-600 hover:bg-gray-50"
            >
              {t("pdca.form.cancel")}
            </button>
            {open === "act" ? (
              <button
                type="button"
                onClick={() => closeMutation.mutate()}
                disabled={closeMutation.isPending}
                className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700 disabled:opacity-50"
              >
                {closeMutation.isPending ? t("pdca.advance.closing") : t("pdca.advance.close")}
              </button>
            ) : (
              <button
                type="button"
                onClick={() => advanceMutation.mutate()}
                disabled={advanceMutation.isPending}
                className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700 disabled:opacity-50"
              >
                {advanceMutation.isPending ? t("pdca.advance.in_progress") : t("pdca.advance.confirm")}
              </button>
            )}
          </div>
        </div>
      </div>
    );
  }

  if (fase === "chiuso" || fase === "archiviato") {
    const isArchiviato = fase === "archiviato";
    return (
      <>
        <p className="text-xs text-gray-500">
          {t(isArchiviato ? "pdca.status.archived_on" : "pdca.status.closed_on", {
            date: new Date(
              cycle.closed_at || cycle.updated_at || cycle.created_at,
            ).toLocaleDateString(i18n.language || "it"),
          })}
        </p>
        {isArchiviato && (cycle as any).motivo_archiviazione && (
          <p className="mt-1 text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded px-2 py-1 whitespace-pre-wrap">
            {(cycle as any).motivo_archiviazione}
          </p>
        )}
        {!isArchiviato && cycle.act_description && (
          <p className="mt-1 text-xs text-gray-700 whitespace-pre-wrap">{cycle.act_description}</p>
        )}
      </>
    );
  }

  const advanceConfig: Record<string, { label: string; title: string }> = {
    plan:  { label: t("pdca.advance.btn_do"),    title: t("pdca.advance.to_do") },
    do:    { label: t("pdca.advance.btn_check"), title: t("pdca.advance.to_check") },
    check: { label: t("pdca.advance.btn_act"),   title: t("pdca.advance.to_act") },
    act:   { label: t("pdca.advance.btn_close"), title: t("pdca.advance.close") },
  };
  const cfg = advanceConfig[fase as string];

  const onClick = () => {
    if (fase === "plan" || fase === "do" || fase === "check" || fase === "act") {
      setOpen(fase as any);
    }
  };

  return (
    <>
      <button
        type="button"
        onClick={onClick}
        title={cfg?.title}
        className="px-2 py-1 text-[11px] font-semibold rounded-md bg-primary-50 text-primary-700 hover:bg-primary-100 border border-primary-200"
      >
        {cfg?.label}
      </button>
      {cycle.reopened_as && (
        <div className="mt-2 text-[11px] text-blue-700 bg-blue-50 border border-blue-200 rounded px-2 py-1">
          {t("pdca.advance.reopened_note")}
        </div>
      )}
      {renderModal()}
    </>
  );
}

function TitleCell({ cycle }: { cycle: PdcaCycle }) {
  const { t } = useTranslation();
  const [expanded, setExpanded] = useState(false);
  const hasDesc = !!cycle.descrizione;

  return (
    <div>
      <div className="flex items-start gap-1">
        <span className="font-medium text-gray-800 leading-snug">{cycle.title}</span>
        {hasDesc && (
          <button
            type="button"
            onClick={() => setExpanded(v => !v)}
            title={expanded ? t("pdca.title_cell.hide_desc") : t("pdca.title_cell.show_desc")}
            className="mt-0.5 flex-shrink-0 text-gray-400 hover:text-primary-600 transition-colors"
          >
            <svg
              className={`w-4 h-4 transition-transform duration-150 ${expanded ? "rotate-180" : ""}`}
              fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
            </svg>
          </button>
        )}
      </div>

      {hasDesc && expanded && (
        <p className="mt-1.5 text-xs font-normal text-gray-600 bg-gray-50 border border-gray-200 rounded px-2.5 py-2 whitespace-pre-wrap leading-relaxed">
          {cycle.descrizione}
        </p>
      )}

      <div className="mt-1 flex flex-wrap gap-1">
        {/* riferimento testuale (storico): superfluo se c'è il finding collegato */}
        {cycle.riferimento_finding && !(cycle.findings ?? []).length && (
          <span className="text-[11px] text-indigo-700 font-mono bg-indigo-50 border border-indigo-200 rounded px-1.5 py-0.5">
            {cycle.riferimento_finding}
          </span>
        )}
        {cycle.reopened_as && (
          <span className="text-[11px] text-blue-700 bg-blue-50 border border-blue-200 rounded px-2 py-0.5">
            {t("pdca.title_cell.recycle_badge")}
          </span>
        )}
      </div>
    </div>
  );
}

export function PdcaPage() {
  const { t } = useTranslation();
  const selectedPlant = useAuthStore(s => s.selectedPlant);
  const [showNew, setShowNew] = useState(false);
  const [filterTrigger, setFilterTrigger] = useState("");
  const [filterPlant, setFilterPlant] = useState("");
  // Stato: "open" = in corso (PLAN…ACT), oppure una fase / chiuso / archiviato.
  const [filterStatus, setFilterStatus] = useState("");

  // Il sito scelto nella barra in alto vale come filtro di default; il select
  // locale lo sovrascrive solo se valorizzato esplicitamente.
  const effectivePlant = filterPlant || selectedPlant?.id || "";

  // Deep link dal finding di audit: /pdca?cycle=<id> mostra solo quel ciclo.
  const [searchParams, setSearchParams] = useSearchParams();
  const onlyCycle = searchParams.get("cycle") ?? "";
  const params: Record<string, string> = {};
  if (onlyCycle) params.id = onlyCycle;
  if (filterTrigger) params.trigger_type = filterTrigger;
  if (filterStatus === "open") params.open = "true";
  else if (filterStatus) params.fase_corrente = filterStatus;
  // Filtro per sito: cicli del sito + cicli di organizzazione (valgono anche lì).
  if (onlyCycle) { /* ciclo singolo: nessun altro filtro */ }
  else if (effectivePlant === ORG_VALUE) params.org = "true";
  else if (effectivePlant) params.site = effectivePlant;

  const { data, isLoading } = useQuery({
    queryKey: ["pdca", filterTrigger, effectivePlant, filterStatus, onlyCycle],
    queryFn: () => pdcaApi.list(params),
    retry: false,
  });

  const { data: plants } = useQuery({
    queryKey: ["plants"],
    queryFn: () => plantsApi.list(),
    retry: false,
  });

  const cycles = data?.results ?? [];

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold text-gray-900">{t("pdca.title")}</h2>
        <button onClick={() => setShowNew(true)} className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700">
          {t("pdca.new_btn")}
        </button>
      </div>

      <div className="mb-3 flex items-center gap-3">
        <label className="text-sm text-gray-600 font-medium">{t("pdca.filters.trigger_label")}</label>
        <select
          value={filterTrigger}
          onChange={e => setFilterTrigger(e.target.value)}
          className="border rounded px-3 py-1.5 text-sm text-gray-700 bg-white"
        >
          <option value="">{t("pdca.filters.all_triggers")}</option>
          {TRIGGER_FILTERS.map(code => <option key={code} value={code}>{t(`pdca.trigger_filter.${code}`)}</option>)}
        </select>
        <label className="text-sm text-gray-600 font-medium ml-2">{t("pdca.filters.plant_label")}</label>
        <select
          value={filterPlant}
          onChange={e => setFilterPlant(e.target.value)}
          className="border rounded px-3 py-1.5 text-sm text-gray-700 bg-white"
        >
          <option value="">
            {selectedPlant?.id
              ? t("pdca.filters.from_topbar", { plant: selectedPlant.code || selectedPlant.name })
              : t("pdca.filters.all_plants")}
          </option>
          <option value={ORG_VALUE}>{t("pdca.filters.only_org")}</option>
          {(plants ?? []).map(p => (
            <option key={p.id} value={p.id}>{p.code} — {p.name}</option>
          ))}
        </select>
        <label className="text-sm text-gray-600 font-medium ml-2">{t("pdca.filters.status_label")}</label>
        <select
          value={filterStatus}
          onChange={e => setFilterStatus(e.target.value)}
          className="border rounded px-3 py-1.5 text-sm text-gray-700 bg-white"
        >
          <option value="">{t("pdca.filters.all_statuses")}</option>
          <option value="open">{t("pdca.filters.only_open")}</option>
          {(["plan", "do", "check", "act", "chiuso", "archiviato"] as const).map(p => (
            <option key={p} value={p}>{t(`pdca.phase.${p}`)}</option>
          ))}
        </select>
        {(filterTrigger || filterPlant || filterStatus) && (
          <button
            onClick={() => { setFilterTrigger(""); setFilterPlant(""); setFilterStatus(""); }}
            className="text-xs text-gray-500 hover:text-gray-700 underline"
          >
            {t("pdca.filters.clear")}
          </button>
        )}
      </div>

      {onlyCycle && (
        <div className="mb-3 flex items-center gap-3 text-sm bg-primary-50 border border-primary-200 rounded px-3 py-2">
          <span>{t("pdca.link.single_cycle")}</span>
          <button onClick={() => setSearchParams({})} className="text-primary-700 underline">{t("pdca.link.show_all")}</button>
        </div>
      )}
      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-gray-400">{t("common.loading")}</div>
        ) : cycles.length === 0 ? (
          <div className="p-8 text-center">
            <p className="text-gray-400 mb-2">{t("pdca.empty")}</p>
            <button onClick={() => setShowNew(true)} className="text-sm text-primary-600 hover:underline">{t("pdca.empty_cta")}</button>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("pdca.table.title")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("pdca.table.trigger")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("pdca.table.plant")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("pdca.table.scope")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("pdca.table.phases")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("pdca.table.action")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("pdca.table.created_at")}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {cycles.map((c) => (
                <tr key={c.id} className="hover:bg-gray-50 transition-colors align-top">
                  <td className="px-4 py-3 font-medium text-gray-800 max-w-sm">
                    <TitleCell cycle={c} />
                    <LinkedFindings findings={c.findings ?? []} cycleTitle={c.title} />
                  </td>
                  <td className="px-4 py-3 text-gray-600 text-xs">
                    <span className="font-medium">{triggerLabel(t, c.trigger_type)}</span>
                    {c.audit_subtype && (
                      <div className="mt-0.5 text-[11px] text-gray-400">
                        {auditSubtypeLabel(t, c.audit_subtype)}
                      </div>
                    )}
                  </td>
                  <td className="px-4 py-3 text-gray-600 text-xs">
                    {c.plant === null ? (
                      <span className="text-[11px] font-medium text-purple-700 bg-purple-50 border border-purple-200 rounded px-1.5 py-0.5">
                        {t("pdca.scope.org")}
                      </span>
                    ) : (
                      <>
                        {c.plant_code ? <span className="font-mono">{c.plant_code}</span> : null}
                        {c.plant_name ? <div className="text-[11px] text-gray-400">{c.plant_name}</div> : null}
                        {!c.plant_code && !c.plant_name ? "—" : null}
                      </>
                    )}
                  </td>
                  {/* ciclo di organizzazione: l'ambito è già nella colonna Sito */}
                  <td className="px-4 py-3 text-gray-600 text-xs">{c.plant === null && c.scope_type === "org" ? "" : scopeLabel(t, c.scope_type)}</td>
                  <td className="px-4 py-3">
                    <PhaseStepper cycle={c as any} />
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex flex-row flex-wrap gap-1 items-center">
                      {c.can_manage === false ? (
                        <>
                          <CycleDossierButton cycle={c} />
                          <span className="text-[11px] text-gray-400" title={t("pdca.read_only_org_title")}>
                            {t("pdca.read_only_org")}
                          </span>
                        </>
                      ) : (
                        <>
                          <AdvanceButtons cycle={c as any} onUpdated={() => {}} />
                          <CycleDossierButton cycle={c} />
                          <EditCycleButton cycle={c} />
                          <LinkFindingButton cycle={c} />
                          <ArchiviaCycleButton cycle={c} />
                          <DeleteCycleButton cycle={c} />
                        </>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-gray-500 text-xs">
                    {new Date(c.created_at).toLocaleDateString(i18n.language || "it")}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {showNew && plants && <NewCycleModal plants={plants} onClose={() => setShowNew(false)} />}
    </div>
  );
}
