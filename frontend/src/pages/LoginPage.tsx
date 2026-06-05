import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuthStore } from "../store/auth";
import { loginApi, verifyMfaApi } from "../api/endpoints/auth";
import { useTranslation } from "react-i18next";

const DEVICE_TOKEN_KEY = "grc_device_token";

export function LoginPage() {
  const { t } = useTranslation();
  const [email, setEmail]       = useState("");
  const [password, setPassword] = useState("");
  const [error, setError]       = useState("");
  const [loading, setLoading]   = useState(false);

  // Step MFA
  const [mfaToken, setMfaToken]     = useState<string | null>(null);
  const [otpCode, setOtpCode]       = useState("");
  const [trustDevice, setTrustDevice] = useState(false);
  const otpRef = useRef<HTMLInputElement>(null);

  const { setUser } = useAuthStore();
  const navigate    = useNavigate();

  function finishLogin(access: string, refresh: string | null) {
    const payload = JSON.parse(atob(access.split(".")[1]));
    setUser(
      {
        id:       String(payload.user_id ?? payload.sub ?? ""),
        email,
        role:     payload.role ?? "user",
        language: "it",
      },
      access,
      refresh,
    );
    navigate("/");
  }

  async function handleCredentials(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const savedToken = localStorage.getItem(DEVICE_TOKEN_KEY) ?? undefined;
      const result = await loginApi(email, password, savedToken);
      if (result.mfa_required) {
        setMfaToken(result.mfa_token);
        setTimeout(() => otpRef.current?.focus(), 50);
      } else {
        finishLogin(result.access, result.refresh);
      }
    } catch {
      setError(t("auth.login.invalid_credentials"));
    } finally {
      setLoading(false);
    }
  }

  async function handleMfa(e: React.FormEvent) {
    e.preventDefault();
    if (!mfaToken) return;
    setError("");
    setLoading(true);
    try {
      const result = await verifyMfaApi(mfaToken, otpCode, trustDevice);
      if (trustDevice && result.device_token) {
        localStorage.setItem(DEVICE_TOKEN_KEY, result.device_token);
      }
      finishLogin(result.access, result.refresh);
    } catch {
      setError(t("auth.mfa.invalid_code"));
      setOtpCode("");
      otpRef.current?.focus();
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-primary-900 flex items-center justify-center">
      <div className="bg-white rounded-xl shadow-lg w-full max-w-sm p-8">
        <div className="mb-6 text-center">
          <div className="flex items-center justify-center" style={{ gap: "16px" }}>
            <svg width="56" height="56" viewBox="0 0 56 56" fill="none" aria-hidden="true">
              <rect width="56" height="56" rx="12" fill="#ffffff" />
              <rect x="14" y="14" width="11.2" height="11.2" rx="2.1" fill="#185FA5" fillOpacity="0.95" />
              <rect x="30.8" y="14" width="11.2" height="11.2" rx="2.1" fill="#185FA5" fillOpacity="0.45" />
              <rect x="14" y="30.8" width="11.2" height="11.2" rx="2.1" fill="#185FA5" fillOpacity="0.45" />
              <rect x="30.8" y="30.8" width="11.2" height="11.2" rx="2.1" fill="#185FA5" fillOpacity="0.95" />
            </svg>
            <div style={{ fontSize: "36px", letterSpacing: "-0.5px", lineHeight: 1.1, textTransform: "lowercase", WebkitFontSmoothing: "antialiased", textRendering: "optimizeLegibility" }}>
              <span style={{ color: "#1e3a5f", fontWeight: 400 }}>gov</span>
              <span style={{ color: "#185FA5", fontWeight: 500 }}>rico</span>
            </div>
          </div>
          <p className="text-sm text-gray-500 mt-1">{t("auth.login.subtitle")}</p>
        </div>

        {!mfaToken ? (
          /* ── Step 1: credenziali ── */
          <form onSubmit={handleCredentials} className="space-y-4" noValidate>
            <div>
              <label htmlFor="login-email" className="block text-sm font-medium text-gray-700 mb-1">
                {t("auth.login.email_label")}
              </label>
              <input
                id="login-email"
                type="text"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                placeholder={t("auth.login.email_placeholder")}
              />
            </div>
            <div>
              <label htmlFor="login-password" className="block text-sm font-medium text-gray-700 mb-1">
                {t("auth.login.password_label")}
              </label>
              <input
                id="login-password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>
            {error && (
              <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded">{error}</p>
            )}
            <button
              type="submit"
              disabled={loading}
              className="w-full bg-primary-600 hover:bg-primary-700 text-white font-medium py-2 rounded-md text-sm transition-colors disabled:opacity-50"
            >
              {loading ? t("auth.login.signing_in") : t("auth.login.submit")}
            </button>
          </form>
        ) : (
          /* ── Step 2: codice MFA ── */
          <form onSubmit={handleMfa} className="space-y-4">
            <div className="text-center mb-2">
              <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-primary-50 mb-3">
                <svg className="w-6 h-6 text-primary-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                </svg>
              </div>
              <p className="text-sm text-gray-600">{t("auth.mfa.prompt")}</p>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {t("auth.mfa.code_label")}
              </label>
              <input
                ref={otpRef}
                type="text"
                inputMode="numeric"
                pattern="[0-9]{6}"
                maxLength={6}
                value={otpCode}
                onChange={(e) => setOtpCode(e.target.value.replace(/\D/g, ""))}
                required
                autoComplete="one-time-code"
                className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm text-center tracking-[0.5em] text-lg font-mono focus:outline-none focus:ring-2 focus:ring-primary-500"
                placeholder="000000"
              />
            </div>
            <label className="flex items-center gap-2 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={trustDevice}
                onChange={(e) => setTrustDevice(e.target.checked)}
                className="w-4 h-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
              />
              <span className="text-sm text-gray-600">{t("auth.mfa.trust_device")}</span>
            </label>
            {error && (
              <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded">{error}</p>
            )}
            <button
              type="submit"
              disabled={loading || otpCode.length !== 6}
              className="w-full bg-primary-600 hover:bg-primary-700 text-white font-medium py-2 rounded-md text-sm transition-colors disabled:opacity-50"
            >
              {loading ? t("auth.mfa.verifying") : t("auth.mfa.verify")}
            </button>
            <button
              type="button"
              onClick={() => { setMfaToken(null); setOtpCode(""); setError(""); setTrustDevice(false); }}
              className="w-full text-sm text-gray-500 hover:text-gray-700 py-1"
            >
              {t("auth.mfa.back")}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
