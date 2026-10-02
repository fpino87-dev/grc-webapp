import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { apiError, riskApi, type Cycle, type CycleKind } from "../../api/endpoints/risk";
import { governanceApi } from "../../api/endpoints/governance";
import { ErrorBox, inputCls } from "./RiskUi";
import type { RegisterId } from "./RiskPage";

function fmt(d: string | null | undefined, lang: string) {
  return d ? new Date(d).toLocaleDateString(lang) : "—";
}

/** Stato della valutazione del registro e azioni del ciclo (procedura §5, §11). */
export function CycleBar({
  registerId, registerLabel, openCycle, approvedCycle, hasLegacy, canWrite, orgScope,
}: {
  registerId: RegisterId;
  registerLabel: string;
  openCycle: Cycle | null;
  approvedCycle: Cycle | null;
  hasLegacy: boolean;
  canWrite: boolean;
  orgScope: boolean;
}) {
  const { t, i18n } = useTranslation();
  const qc = useQueryClient();
  const [dialog, setDialog] = useState<null | "start" | "submit" | "approve" | "return">(null);
  const [error, setError] = useState<string | null>(null);

  const { data: triggers = [] } = useQuery({
    queryKey: ["risk-triggers", registerId],
    queryFn: () => riskApi.triggers(registerId),
    retry: false,
  });

  const refresh = () => {
    qc.invalidateQueries({ queryKey: ["risk-cycles", registerId] });
    qc.invalidateQueries({ queryKey: ["risk-register"] });
    qc.invalidateQueries({ queryKey: ["risk-coverage", registerId] });
  };

  const close = () => { setDialog(null); setError(null); };

  let tone = "bg-amber-50 border-amber-200 text-amber-900";
  let text: string;
  if (openCycle?.status === "in_corso") {
    tone = "bg-blue-50 border-blue-200 text-blue-900";
    text = t("risk.cycle.in_progress", {
      kind: t(`risk.cycle.kinds.${openCycle.kind}`), date: fmt(openCycle.started_at, i18n.language),
    });
  } else if (openCycle?.status === "in_approvazione") {
    tone = "bg-purple-50 border-purple-200 text-purple-900";
    text = t("risk.cycle.awaiting_approval", { kind: t(`risk.cycle.kinds.${openCycle.kind}`) });
  } else if (approvedCycle) {
    tone = "bg-green-50 border-green-200 text-green-900";
    text = t("risk.cycle.approved", {
      date: fmt(approvedCycle.approved_at, i18n.language), body: approvedCycle.approved_by_body_name ?? "—",
    });
  } else {
    text = t(hasLegacy ? "risk.cycle.none_with_legacy" : "risk.cycle.none");
  }

  return (
    <div className={`rounded-lg border px-4 py-3 mb-4 ${tone}`}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="text-sm">
          <span className="font-semibold">{registerLabel}</span> · {text}
        </div>
        {canWrite && (
          <div className="flex gap-2">
            {!openCycle && (
              <button onClick={() => setDialog("start")} className="px-3 py-1.5 bg-white border rounded text-sm hover:bg-gray-50">
                {t(approvedCycle ? "risk.cycle.start_review" : "risk.cycle.start_first")}
              </button>
            )}
            {openCycle?.status === "in_corso" && (
              <button onClick={() => setDialog("submit")} className="px-3 py-1.5 bg-white border rounded text-sm hover:bg-gray-50">
                {t("risk.cycle.submit")}
              </button>
            )}
            {openCycle?.status === "in_approvazione" && (
              <>
                <button onClick={() => setDialog("return")} className="px-3 py-1.5 bg-white border rounded text-sm hover:bg-gray-50">
                  {t("risk.cycle.return")}
                </button>
                <button onClick={() => setDialog("approve")} className="px-3 py-1.5 bg-purple-600 text-white rounded text-sm hover:bg-purple-700">
                  {t("risk.cycle.approve")}
                </button>
              </>
            )}
          </div>
        )}
      </div>
      {triggers.length > 0 && (
        <ul className="mt-2 text-xs space-y-0.5">
          {triggers.map(tr => (
            <li key={tr.kind}>⚠ {t(`risk.cycle.triggers.${tr.kind}`, { count: tr.count })}</li>
          ))}
          {approvedCycle && !openCycle && <li className="text-gray-600">{t("risk.cycle.triggers_hint")}</li>}
        </ul>
      )}

      {dialog === "start" && (
        <StartDialog registerId={registerId} hasApproved={!!approvedCycle} onClose={close} onDone={() => { close(); refresh(); }} />
      )}
      {dialog === "submit" && openCycle && (
        <SubmitDialog cycle={openCycle} onClose={close} onDone={() => { close(); refresh(); }} />
      )}
      {dialog === "return" && openCycle && (
        <ReasonDialog
          title={t("risk.cycle.return")}
          label={t("risk.cycle.return_reason")}
          error={error}
          onClose={close}
          onConfirm={async reason => {
            try { await riskApi.returnCycle(openCycle.id, reason); close(); refresh(); }
            catch (e) { setError(apiError(e, t("risk.errors.generic"))); }
          }}
        />
      )}
      {dialog === "approve" && openCycle && (
        <ApproveDialog cycle={openCycle} orgScope={orgScope} onClose={close} onDone={() => { close(); refresh(); }} />
      )}
    </div>
  );
}

function Modal({ title, children, onClose }: { title: string; children: React.ReactNode; onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30" role="dialog" aria-modal="true" aria-label={title}>
      <div className="bg-white rounded-lg shadow-xl w-full max-w-lg p-5 text-gray-800">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-base font-semibold">{title}</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl leading-none">×</button>
        </div>
        {children}
      </div>
    </div>
  );
}

function StartDialog({ registerId, hasApproved, onClose, onDone }: {
  registerId: RegisterId; hasApproved: boolean; onClose: () => void; onDone: () => void;
}) {
  const { t } = useTranslation();
  const [kind, setKind] = useState<CycleKind>(hasApproved ? "periodico" : "primo");
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);
  const start = useMutation({
    mutationFn: () => riskApi.startCycle(registerId, kind, reason),
    onSuccess: onDone,
    onError: e => setError(apiError(e, t("risk.errors.generic"))),
  });
  const kinds: CycleKind[] = hasApproved ? ["periodico", "straordinario"] : ["primo"];
  return (
    <Modal title={t("risk.cycle.start_title")} onClose={onClose}>
      <div className="space-y-3 text-sm">
        {kinds.map(k => (
          <label key={k} className="flex items-start gap-2">
            <input type="radio" checked={kind === k} onChange={() => setKind(k)} className="mt-1" />
            <span>
              <span className="font-medium">{t(`risk.cycle.kinds.${k}`)}</span>
              <span className="block text-xs text-gray-500">{t(`risk.cycle.kind_hint.${k}`)}</span>
            </span>
          </label>
        ))}
        {kind === "straordinario" && (
          <textarea value={reason} onChange={e => setReason(e.target.value)} rows={3} className={inputCls}
            placeholder={t("risk.cycle.trigger_reason")} />
        )}
        <ErrorBox message={error} />
        <div className="flex justify-end gap-2">
          <button onClick={onClose} className="px-3 py-1.5 border rounded">{t("common.cancel")}</button>
          <button onClick={() => start.mutate()} disabled={start.isPending}
            className="px-3 py-1.5 bg-primary-600 text-white rounded disabled:opacity-50">{t("risk.cycle.start")}</button>
        </div>
      </div>
    </Modal>
  );
}

function SubmitDialog({ cycle, onClose, onDone }: { cycle: Cycle; onClose: () => void; onDone: () => void }) {
  const { t } = useTranslation();
  const [error, setError] = useState<string | null>(null);
  const { data: check } = useQuery({
    queryKey: ["risk-submission-check", cycle.id],
    queryFn: () => riskApi.submissionCheck(cycle.id),
    retry: false,
  });
  const submit = useMutation({
    mutationFn: () => riskApi.submitCycle(cycle.id),
    onSuccess: onDone,
    onError: e => setError(apiError(e, t("risk.errors.generic"))),
  });
  const errors = check?.errors ?? [];
  return (
    <Modal title={t("risk.cycle.submit")} onClose={onClose}>
      <div className="text-sm space-y-3">
        {errors.length > 0 ? (
          <ul className="list-disc ml-5 text-red-700">{errors.map(e => <li key={e}>{e}</li>)}</ul>
        ) : (
          <p>{t("risk.cycle.submit_ready")}</p>
        )}
        <ErrorBox message={error} />
        <div className="flex justify-end gap-2">
          <button onClick={onClose} className="px-3 py-1.5 border rounded">{t("common.cancel")}</button>
          <button onClick={() => submit.mutate()} disabled={errors.length > 0 || submit.isPending}
            className="px-3 py-1.5 bg-primary-600 text-white rounded disabled:opacity-50">{t("risk.cycle.submit")}</button>
        </div>
      </div>
    </Modal>
  );
}

function ApproveDialog({ cycle, orgScope, onClose, onDone }: {
  cycle: Cycle; orgScope: boolean; onClose: () => void; onDone: () => void;
}) {
  const { t } = useTranslation();
  const [body, setBody] = useState("");
  const [adoption, setAdoption] = useState("");
  const [error, setError] = useState<string | null>(null);
  const { data: bodies = [] } = useQuery({ queryKey: ["committees"], queryFn: () => governanceApi.committees(), retry: false });
  const approve = useMutation({
    mutationFn: () => riskApi.approveCycle(cycle.id, { body, local_adoption_ref: adoption }),
    onSuccess: onDone,
    onError: e => setError(apiError(e, t("risk.errors.generic"))),
  });
  return (
    <Modal title={t("risk.cycle.approve")} onClose={onClose}>
      <div className="text-sm space-y-3">
        <p className="text-gray-600">{t("risk.cycle.approve_hint")}</p>
        <select value={body} onChange={e => setBody(e.target.value)} className={inputCls}>
          <option value="">{t("risk.cycle.choose_body")}</option>
          {bodies.map(b => <option key={b.id} value={b.id}>{b.name}</option>)}
        </select>
        {cycle.plant && (
          <input value={adoption} onChange={e => setAdoption(e.target.value)} className={inputCls}
            placeholder={t("risk.cycle.local_adoption")} />
        )}
        {!orgScope && <p className="text-xs text-gray-500">{t("risk.cycle.approve_scope_hint")}</p>}
        <ErrorBox message={error} />
        <div className="flex justify-end gap-2">
          <button onClick={onClose} className="px-3 py-1.5 border rounded">{t("common.cancel")}</button>
          <button onClick={() => approve.mutate()} disabled={!body || approve.isPending}
            className="px-3 py-1.5 bg-purple-600 text-white rounded disabled:opacity-50">{t("risk.cycle.approve")}</button>
        </div>
      </div>
    </Modal>
  );
}

export function ReasonDialog({ title, label, error, onClose, onConfirm }: {
  title: string; label: string; error: string | null; onClose: () => void; onConfirm: (reason: string) => void;
}) {
  const { t } = useTranslation();
  const [reason, setReason] = useState("");
  return (
    <Modal title={title} onClose={onClose}>
      <div className="text-sm space-y-3">
        <textarea value={reason} onChange={e => setReason(e.target.value)} rows={3} className={inputCls} placeholder={label} />
        <ErrorBox message={error} />
        <div className="flex justify-end gap-2">
          <button onClick={onClose} className="px-3 py-1.5 border rounded">{t("common.cancel")}</button>
          <button onClick={() => onConfirm(reason)} disabled={!reason.trim()}
            className="px-3 py-1.5 bg-primary-600 text-white rounded disabled:opacity-50">{t("common.confirm")}</button>
        </div>
      </div>
    </Modal>
  );
}

export { Modal };
