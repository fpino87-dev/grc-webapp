import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { riskApi, type RiskAssessment, type SuggestResidualResult } from "../../api/endpoints/risk";
import { useTranslation } from "react-i18next";
import i18n from "../../i18n";

export function SuggestResidualPanel({ assessment }: { assessment: RiskAssessment }) {
  const { t } = useTranslation();
  const [suggestion, setSuggestion] = useState<SuggestResidualResult | null>(null);

  const { refetch, isFetching } = useQuery({
    queryKey: ["suggest-residual", assessment.id],
    queryFn: () => riskApi.suggestResidual(assessment.id),
    enabled: false,
  });

  async function handleSuggest() {
    const { data } = await refetch();
    if (data) setSuggestion(data);
  }

  return (
    <div className="px-6 py-3 border-t border-gray-100">
      <div className="flex items-center gap-3">
        <button
          onClick={handleSuggest}
          disabled={isFetching}
          className="text-xs px-3 py-1.5 border border-indigo-300 text-indigo-600 rounded hover:bg-indigo-50 disabled:opacity-50"
        >
          {isFetching ? t("common.loading") : t("risk.suggest_residual")}
        </button>
        {suggestion && (
          <span className="text-xs text-gray-600">{suggestion.reason}</span>
        )}
      </div>
      {suggestion && (
        <div className="mt-2 flex flex-wrap items-center gap-2">
          <span className="text-xs text-green-700 bg-green-50 border border-green-200 px-2 py-1 rounded">
            {t("risk.controls_reduction")} {suggestion.reduction_pct ?? 0}%
          </span>
          <span className="text-xs text-green-800 bg-green-50 border border-green-200 px-2 py-1 rounded">
            {t("risk.bcp_extra")} {suggestion.bcp_extra_pct ?? 0}%
          </span>
          <span className="text-xs text-gray-700 bg-gray-50 border border-gray-200 px-2 py-1 rounded">
            {t("risk.total_label")} {Math.min(70, (suggestion.reduction_pct ?? 0) + (suggestion.bcp_extra_pct ?? 0))}%
          </span>
          <span className="text-xs text-gray-500">{t("risk.suggest_hint")}</span>
        </div>
      )}
    </div>
  );
}

export function FormalAcceptancePanel({ assessment }: { assessment: RiskAssessment }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [renewOpen, setRenewOpen] = useState(false);
  const [note, setNote] = useState("");
  // Default: +1 anno da oggi (ISO 27001 — revisione annuale accettazione rischio)
  const defaultExpiry = new Date(new Date().setFullYear(new Date().getFullYear() + 1)).toISOString().slice(0, 10);
  const [expiry, setExpiry] = useState(defaultExpiry);
  const [renewExpiry, setRenewExpiry] = useState(defaultExpiry);
  const [err, setErr] = useState("");

  const mutation = useMutation({
    mutationFn: () => riskApi.acceptRisk(assessment.id, note, expiry || undefined),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["risk-assessments"] }); setOpen(false); },
    onError: (e: unknown) => {
      const msg = (e as { response?: { data?: { error?: string } } })?.response?.data?.error ?? t("risk.error_generic");
      setErr(msg);
    },
  });

  const renewMutation = useMutation({
    mutationFn: () => riskApi.renewAcceptance(assessment.id, renewExpiry),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["risk-assessments"] }); setRenewOpen(false); },
    onError: (e: unknown) => {
      const msg = (e as { response?: { data?: { error?: string } } })?.response?.data?.error ?? t("risk.error_generic");
      setErr(msg);
    },
  });

  const resetMutation = useMutation({
    mutationFn: () => riskApi.resetAcceptance(assessment.id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["risk-assessments"] }); },
    onError: (e: unknown) => {
      const msg = (e as { response?: { data?: { error?: string } } })?.response?.data?.error ?? t("risk.error_generic");
      setErr(msg);
    },
  });

  if (assessment.risk_level === "verde" && !assessment.risk_accepted_formally) return null;

  if (assessment.risk_accepted_formally) {
    const expiryStr = assessment.risk_acceptance_expiry ?? null;
    const todayStr = new Date().toISOString().slice(0, 10);
    const expired = expiryStr ? expiryStr < todayStr : false;
    const expiryDisplay = expiryStr ? new Date(expiryStr + "T12:00:00").toLocaleDateString(i18n.language || "it") : null;
    return (
      <div className="px-6 py-3 border-t border-gray-100 space-y-2">
        <div className={`flex items-center gap-2 text-xs px-3 py-2 rounded-lg ${expired ? "bg-red-50 text-red-700" : "bg-green-50 text-green-700"}`}>
          <span>{expired ? "⚠️" : "✅"}</span>
          <span>
            {t("risk.accepted_by_on", { name: assessment.accepted_by_name ?? "—", date: assessment.risk_accepted_at ? new Date(assessment.risk_accepted_at).toLocaleDateString(i18n.language || "it") : "—" })}
            {expiryDisplay && <> — {expired ? t("risk.expired_on") : t("risk.expires_on")} <strong>{expiryDisplay}</strong></>}
          </span>
        </div>
        {assessment.risk_acceptance_note && (
          <p className="text-xs text-gray-500 italic px-1">"{assessment.risk_acceptance_note}"</p>
        )}
        <div className="flex gap-2 flex-wrap">
          {!renewOpen ? (
            <button onClick={() => setRenewOpen(true)}
              className="text-xs px-3 py-1.5 border border-blue-300 text-blue-700 rounded hover:bg-blue-50">
              {t("risk.renew_acceptance")}
            </button>
          ) : (
            <div className="flex items-center gap-2">
              <input type="date" value={renewExpiry} min={todayStr}
                onChange={e => setRenewExpiry(e.target.value)}
                className="border rounded px-2 py-1 text-xs" />
              <button onClick={() => renewMutation.mutate()} disabled={renewMutation.isPending}
                className="text-xs px-3 py-1.5 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50">
                {renewMutation.isPending ? t("common.saving") : t("risk.renew_confirm")}
              </button>
              <button onClick={() => setRenewOpen(false)} className="text-xs px-2 py-1.5 border rounded text-gray-600 hover:bg-gray-50">
                {t("actions.cancel")}
              </button>
            </div>
          )}
          <button
            onClick={() => { if (window.confirm(t("risk.reset_acceptance_confirm"))) resetMutation.mutate(); }}
            disabled={resetMutation.isPending}
            className="text-xs px-3 py-1.5 border border-orange-300 text-orange-700 rounded hover:bg-orange-50 disabled:opacity-50">
            {t("risk.reset_acceptance")}
          </button>
        </div>
        {err && <p className="text-xs text-red-600">⛔ {err}</p>}
      </div>
    );
  }

  return (
    <div className="px-6 py-3 border-t border-gray-100">
      {!open ? (
        <button
          onClick={() => setOpen(true)}
          className="text-xs px-3 py-1.5 border border-yellow-300 text-yellow-700 rounded hover:bg-yellow-50"
        >
          {t("risk.accept_risk_prompt")}
        </button>
      ) : (
        <div className="space-y-2 max-w-lg">
          <p className="text-xs font-medium text-gray-700">{t("risk.accept_risk_title")}</p>
          <textarea
            value={note}
            onChange={e => { setNote(e.target.value); setErr(""); }}
            placeholder={`${t("risk.accept_note_label")}${assessment.risk_level === "rosso" ? ` ${t("risk.accept_note_critical_hint")}` : ""}`}
            className="w-full border rounded px-2 py-1.5 text-xs resize-none"
            rows={3}
          />
          <input
            type="date"
            value={expiry}
            onChange={e => setExpiry(e.target.value)}
            className="border rounded px-2 py-1.5 text-xs w-full"
            placeholder={t("risk.acceptance_expiry_placeholder")}
          />
          {err && <p className="text-xs text-red-600">⛔ {err}</p>}
          <div className="flex gap-2">
            <button
              onClick={() => mutation.mutate()}
              disabled={mutation.isPending}
              className="px-3 py-1.5 bg-yellow-600 text-white text-xs rounded hover:bg-yellow-700 disabled:opacity-50"
            >
              {mutation.isPending ? t("common.saving") : t("risk.confirm_acceptance")}
            </button>
            <button onClick={() => setOpen(false)} className="px-3 py-1.5 border rounded text-xs text-gray-600 hover:bg-gray-50">
              {t("actions.cancel")}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
