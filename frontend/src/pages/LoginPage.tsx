import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuthStore } from "../store/auth";
import { loginApi } from "../api/endpoints/auth";
import { useTranslation } from "react-i18next";

export function LoginPage() {
  const { t } = useTranslation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const { setUser } = useAuthStore();
  const navigate = useNavigate();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const { access } = await loginApi(email, password);
      // Decode basic user info from JWT payload
      const payload = JSON.parse(atob(access.split(".")[1]));
      setUser(
        {
          id: String(payload.user_id ?? payload.sub ?? ""),
          email,
          role: payload.role ?? "user",
          language: "it",
        },
        access
      );
      navigate("/");
    } catch {
      setError(t("auth.login.invalid_credentials"));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-primary-900 flex items-center justify-center">
      <div className="bg-white rounded-xl shadow-lg w-full max-w-sm p-8">
        <div className="mb-6 text-center">
          <h1 className="text-2xl font-bold text-gray-900">{t("app.name")}</h1>
          <p className="text-sm text-gray-500 mt-1">{t("auth.login.subtitle")}</p>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {t("auth.login.email_label")}
            </label>
            <input
              type="text"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
              placeholder={t("auth.login.email_placeholder")}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {t("auth.login.password_label")}
            </label>
            <input
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
      </div>
    </div>
  );
}
