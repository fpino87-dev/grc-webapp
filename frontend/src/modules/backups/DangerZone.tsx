import { useState } from "react";
import { useTranslation } from "react-i18next";
import { usersApi } from "../../api/endpoints/users";
import { useAuthStore } from "../../store/auth";

/** Reset del database di test: solo superuser, spostato da Gestione utenti
 *  (operazione di sistema, non di gestione delle persone). */
export function DangerZone() {
  const { t } = useTranslation();
  const logout = useAuthStore(s => s.logout);
  const [showConfirm, setShowConfirm] = useState(false);
  const [confirmText, setConfirmText] = useState("");
  const [isResetting, setIsResetting] = useState(false);
  const [result, setResult] = useState<{ ok: boolean; msg: string } | null>(null);

  async function handleReset() {
    setIsResetting(true);
    setResult(null);
    try {
      await usersApi.resetTestDb();
      setResult({ ok: true, msg: t("users.danger.reset_success") });
      setTimeout(() => {
        logout();
        window.location.href = "/login";
      }, 2000);
    } catch (e: any) {
      const msg = e?.response?.data?.error || t("users.danger.reset_error");
      setResult({ ok: false, msg });
    } finally {
      setIsResetting(false);
    }
  }

  return (
    <div className="mt-12 border-2 border-red-300 rounded-lg p-6 bg-red-50">
      <h3 className="text-red-700 font-bold text-lg mb-2">
        {t("users.danger.title")}
      </h3>
      <p className="text-sm text-red-600 mb-4">
        {t("users.danger.body")}
      </p>

      {result && (
        <div className={`mb-4 px-4 py-3 rounded text-sm ${result.ok ? "bg-green-100 text-green-800 border border-green-300" : "bg-red-100 text-red-800 border border-red-400"}`}>
          {result.msg}
        </div>
      )}

      {!showConfirm ? (
        <button
          onClick={() => setShowConfirm(true)}
          className="px-4 py-2 bg-red-600 text-white rounded font-medium hover:bg-red-700"
        >
          {t("users.danger.open")}
        </button>
      ) : (
        <div className="bg-white border border-red-400 rounded p-4">
          <p className="font-semibold text-red-700 mb-3">
            {t("users.danger.confirm_body")}
          </p>
          <input
            placeholder={t("users.danger.confirm_placeholder")}
            value={confirmText}
            onChange={e => setConfirmText(e.target.value)}
            className="border rounded px-3 py-2 text-sm w-full mb-3"
          />
          <div className="flex gap-3">
            <button
              onClick={handleReset}
              disabled={confirmText !== "RESET" || isResetting}
              className="px-4 py-2 bg-red-700 text-white rounded disabled:opacity-40 font-medium"
            >
              {isResetting ? t("users.danger.resetting") : t("users.danger.confirm")}
            </button>
            <button
              onClick={() => { setShowConfirm(false); setConfirmText(""); }}
              className="px-4 py-2 border rounded text-gray-600"
            >
              {t("actions.cancel")}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

