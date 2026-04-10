import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getMfaStatusApi,
  getMfaSetupApi,
  confirmMfaApi,
  disableMfaApi,
} from "../../api/endpoints/auth";

type Step = "idle" | "setup" | "confirm" | "disable";

export function MfaSettingsPage() {
  const { t } = useTranslation();
  const qc = useQueryClient();

  const [step, setStep]       = useState<Step>("idle");
  const [code, setCode]       = useState("");
  const [error, setError]     = useState("");
  const [success, setSuccess] = useState("");

  const { data: status, isLoading } = useQuery({
    queryKey: ["mfa-status"],
    queryFn: getMfaStatusApi,
  });

  const { data: setupData, isLoading: loadingQr } = useQuery({
    queryKey: ["mfa-setup"],
    queryFn: getMfaSetupApi,
    enabled: step === "setup",
  });

  const confirmMutation = useMutation({
    mutationFn: () => confirmMfaApi(code),
    onSuccess: () => {
      setSuccess(t("auth.mfa.setup_success"));
      setStep("idle");
      setCode("");
      qc.invalidateQueries({ queryKey: ["mfa-status"] });
    },
    onError: () => setError(t("auth.mfa.invalid_code")),
  });

  const disableMutation = useMutation({
    mutationFn: () => disableMfaApi(code),
    onSuccess: () => {
      setSuccess(t("auth.mfa.disable_success"));
      setStep("idle");
      setCode("");
      qc.invalidateQueries({ queryKey: ["mfa-status"] });
    },
    onError: () => setError(t("auth.mfa.invalid_code")),
  });

  function handleAction(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    if (step === "confirm") confirmMutation.mutate();
    else if (step === "disable") disableMutation.mutate();
  }

  if (isLoading) return <div className="p-6 text-gray-400">{t("actions.loading")}</div>;

  const enabled = status?.enabled ?? false;

  return (
    <div className="max-w-lg mx-auto p-6 space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-gray-900">{t("auth.mfa.title")}</h2>
        <p className="text-sm text-gray-500 mt-1">{t("auth.mfa.description")}</p>
      </div>

      {/* Stato corrente */}
      <div className="flex items-center gap-3 p-4 rounded-lg border border-gray-200 bg-gray-50">
        <span className={`inline-block w-3 h-3 rounded-full ${enabled ? "bg-green-500" : "bg-gray-300"}`} />
        <span className="text-sm font-medium text-gray-700">
          {enabled ? t("auth.mfa.status_active") : t("auth.mfa.status_inactive")}
        </span>
        {!enabled && step === "idle" && (
          <button
            onClick={() => { setStep("setup"); setError(""); setSuccess(""); }}
            className="ml-auto text-sm font-medium text-primary-600 hover:text-primary-700"
          >
            {t("auth.mfa.enable")}
          </button>
        )}
        {enabled && step === "idle" && (
          <button
            onClick={() => { setStep("disable"); setError(""); setSuccess(""); }}
            className="ml-auto text-sm font-medium text-red-600 hover:text-red-700"
          >
            {t("auth.mfa.disable")}
          </button>
        )}
      </div>

      {success && (
        <p className="text-sm text-green-700 bg-green-50 border border-green-200 px-3 py-2 rounded">
          {success}
        </p>
      )}

      {/* Setup QR */}
      {step === "setup" && (
        <div className="space-y-4">
          <p className="text-sm text-gray-600">{t("auth.mfa.setup_instructions")}</p>
          {loadingQr ? (
            <div className="h-48 flex items-center justify-center text-gray-400">{t("actions.loading")}</div>
          ) : setupData ? (
            <>
              <div className="flex justify-center">
                <img
                  src={`data:image/png;base64,${setupData.qr_png}`}
                  alt="QR Code MFA"
                  className="w-48 h-48 border border-gray-200 rounded-lg"
                />
              </div>
              <p className="text-xs text-center text-gray-500 font-mono break-all">{setupData.secret}</p>
              <button
                onClick={() => setStep("confirm")}
                className="w-full bg-primary-600 hover:bg-primary-700 text-white font-medium py-2 rounded-md text-sm"
              >
                {t("auth.mfa.scanned")}
              </button>
            </>
          ) : null}
          <button
            onClick={() => setStep("idle")}
            className="w-full text-sm text-gray-500 hover:text-gray-700 py-1"
          >
            {t("actions.cancel")}
          </button>
        </div>
      )}

      {/* Conferma codice */}
      {(step === "confirm" || step === "disable") && (
        <form onSubmit={handleAction} className="space-y-4">
          <p className="text-sm text-gray-600">
            {step === "confirm" ? t("auth.mfa.enter_first_code") : t("auth.mfa.enter_code_to_disable")}
          </p>
          <input
            type="text"
            inputMode="numeric"
            pattern="[0-9]{6}"
            maxLength={6}
            value={code}
            onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
            required
            autoFocus
            autoComplete="one-time-code"
            className="w-full border border-gray-300 rounded-md px-3 py-2 text-center tracking-[0.5em] text-lg font-mono focus:outline-none focus:ring-2 focus:ring-primary-500"
            placeholder="000000"
          />
          {error && (
            <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded">{error}</p>
          )}
          <button
            type="submit"
            disabled={code.length !== 6 || confirmMutation.isPending || disableMutation.isPending}
            className={`w-full font-medium py-2 rounded-md text-sm text-white disabled:opacity-50 ${
              step === "disable"
                ? "bg-red-600 hover:bg-red-700"
                : "bg-primary-600 hover:bg-primary-700"
            }`}
          >
            {step === "confirm" ? t("auth.mfa.activate") : t("auth.mfa.disable")}
          </button>
          <button
            type="button"
            onClick={() => { setStep(enabled ? "idle" : "setup"); setCode(""); setError(""); }}
            className="w-full text-sm text-gray-500 hover:text-gray-700 py-1"
          >
            {t("actions.cancel")}
          </button>
        </form>
      )}
    </div>
  );
}
