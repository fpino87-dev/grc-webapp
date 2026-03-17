import { useEffect, useMemo, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "../../api/client";
import { useAuthStore } from "../../store/auth";

type EmailConfig = {
  id: string;
  name: string;
  provider: "office365" | "gmail" | "smtp_custom";
  host: string;
  port: number;
  use_tls: boolean;
  use_ssl: boolean;
  use_auth: boolean;
  username: string;
  from_email: string;
  active: boolean;
  last_test_at: string | null;
  last_test_ok: boolean | null;
  last_test_error: string;
};

type EmailConfigWrite = {
  name: string;
  provider: EmailConfig["provider"];
  host: string;
  port: number;
  use_tls: boolean;
  use_ssl: boolean;
  use_auth: boolean;
  username: string;
  password?: string;
  from_email: string;
  active: boolean;
};

type ProviderPresets = Record<
  string,
  {
    host: string;
    port: number;
    use_tls: boolean;
    use_ssl: boolean;
  }
>;

export function EmailSettingsPage() {
  const queryClient = useQueryClient();
  const userRole = useAuthStore((s) => s.user?.role);
  const [form, setForm] = useState<EmailConfigWrite>({
    name: "Configurazione principale",
    provider: "smtp_custom",
    host: "",
    port: 587,
    use_tls: true,
    use_ssl: false,
    use_auth: true,
    username: "",
    password: "",
    from_email: "GRC Platform <noreply@azienda.com>",
    active: true,
  });
  const [showPassword, setShowPassword] = useState(false);
  const [testRecipient, setTestRecipient] = useState("");
  const [banner, setBanner] = useState<{ type: "success" | "error"; message: string } | null>(null);

  const { data: presets } = useQuery<ProviderPresets>({
    queryKey: ["email-config-presets"],
    queryFn: async () => {
      const res = await apiClient.get("/notifications/email-config/presets/");
      return res.data;
    },
  });

  const { data: configs } = useQuery<EmailConfig[]>({
    queryKey: ["email-config"],
    queryFn: async () => {
      const res = await apiClient.get("/notifications/email-config/");
      const d = res.data;
      return Array.isArray(d) ? d : (d?.results ?? []);
    },
  });

  const activeConfig = useMemo(() => configs?.[0] ?? null, [configs]);

  useEffect(() => {
    if (activeConfig) {
      setForm((prev) => ({
        ...prev,
        name: activeConfig.name,
        provider: activeConfig.provider,
        host: activeConfig.host,
        port: activeConfig.port,
        use_tls: activeConfig.use_tls,
        use_ssl: activeConfig.use_ssl,
        use_auth: activeConfig.use_auth,
        username: activeConfig.username,
        password: "",
        from_email: activeConfig.from_email,
        active: activeConfig.active,
      }));
    }
  }, [activeConfig]);

  function applyPreset(provider: EmailConfig["provider"]) {
    setForm((prev) => {
      const base = { ...prev, provider };
      const preset = presets?.[provider];
      if (!preset) return base;
      return {
        ...base,
        host: preset.host,
        port: preset.port,
        use_tls: preset.use_tls,
        use_ssl: preset.use_ssl,
      };
    });
  }

  function handleChange<K extends keyof EmailConfigWrite>(key: K, value: EmailConfigWrite[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  const saveMutation = useMutation({
    mutationFn: async () => {
      const payload: EmailConfigWrite = {
        ...form,
        port: Number(form.port) || 587,
      };
      if (activeConfig) {
        // PATCH: invia solo i campi modificati; omette password se vuota
        const { password, ...rest } = payload;
        const patchData = password ? payload : rest;
        await apiClient.patch(`/notifications/email-config/${activeConfig.id}/`, patchData);
      } else {
        await apiClient.post("/notifications/email-config/", payload);
      }
    },
    onSuccess: () => {
      setBanner({ type: "success", message: "Configurazione email salvata correttamente." });
      queryClient.invalidateQueries({ queryKey: ["email-config"] });
    },
    onError: (err: any) => {
      const msg = err?.response?.data?.detail || "Errore nel salvataggio configurazione.";
      setBanner({ type: "error", message: String(msg) });
    },
  });

  const testMutation = useMutation({
    mutationFn: async () => {
      if (!activeConfig) throw new Error("Nessuna configurazione attiva da testare.");
      if (!testRecipient.trim()) throw new Error("Inserisci un indirizzo email destinatario per il test.");
      const res = await apiClient.post(`/notifications/email-config/${activeConfig.id}/test/`, {
        recipient: testRecipient.trim(),
      });
      return res.data as { ok: boolean; message?: string; error?: string };
    },
    onSuccess: (data) => {
      if (data.ok) {
        setBanner({
          type: "success",
          message: data.message || "Email di test inviata correttamente.",
        });
      } else {
        setBanner({
          type: "error",
          message: data.error || "Test configurazione fallito.",
        });
      }
      queryClient.invalidateQueries({ queryKey: ["email-config"] });
    },
    onError: (err: any) => {
      const msg = err?.response?.data?.error || "Errore durante il test configurazione.";
      setBanner({ type: "error", message: String(msg) });
    },
  });

  const statusBadge = (() => {
    if (!activeConfig || activeConfig.last_test_at === null) {
      return (
        <span className="inline-flex items-center gap-1 text-xs px-2 py-1 rounded-full bg-gray-100 text-gray-700">
          <span className="text-base">⚪</span>
          Non testato
        </span>
      );
    }
    if (activeConfig.last_test_ok) {
      return (
        <span className="inline-flex items-center gap-1 text-xs px-2 py-1 rounded-full bg-green-100 text-green-800">
          <span className="text-base">🟢</span>
          Connessione verificata
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 text-xs px-2 py-1 rounded-full bg-red-100 text-red-800">
        <span className="text-base">🔴</span>
        Ultimo test fallito
      </span>
    );
  })();

  if (userRole !== "super_admin" && userRole !== "compliance_officer") {
    return (
      <div className="p-6">
        <h2 className="text-lg font-semibold mb-2">Configurazione Email</h2>
        <p className="text-sm text-gray-600">Non hai i permessi per accedere a questa pagina.</p>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-3xl">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold">Configurazione Email</h2>
        {statusBadge}
      </div>

      {banner && (
        <div
          className={`mb-4 rounded-md px-3 py-2 text-sm ${
            banner.type === "success" ? "bg-green-50 text-green-800" : "bg-red-50 text-red-800"
          }`}
        >
          {banner.message}
        </div>
      )}

      <div className="space-y-4 bg-white rounded-lg border border-gray-200 p-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Provider</label>
            <select
              className="w-full border rounded px-3 py-2 text-sm"
              value={form.provider}
              onChange={(e) => applyPreset(e.target.value as EmailConfig["provider"])}
            >
              <option value="office365">Microsoft Office 365</option>
              <option value="gmail">Google Gmail / Workspace</option>
              <option value="smtp_custom">SMTP personalizzato</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Nome configurazione</label>
            <input
              type="text"
              className="w-full border rounded px-3 py-2 text-sm"
              value={form.name}
              onChange={(e) => handleChange("name", e.target.value)}
            />
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="md:col-span-2">
            <label className="block text-sm font-medium text-gray-700 mb-1">Host SMTP</label>
            <input
              type="text"
              className="w-full border rounded px-3 py-2 text-sm"
              value={form.host}
              onChange={(e) => handleChange("host", e.target.value)}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Porta</label>
            <input
              type="number"
              className="w-full border rounded px-3 py-2 text-sm"
              value={form.port}
              onChange={(e) => handleChange("port", Number(e.target.value))}
            />
          </div>
        </div>

        <div className="flex flex-wrap gap-4">
          <label className="inline-flex items-center gap-2 text-sm text-gray-700">
            <input
              type="checkbox"
              checked={form.use_tls}
              onChange={(e) => handleChange("use_tls", e.target.checked)}
            />
            Usa TLS
          </label>
          <label className="inline-flex items-center gap-2 text-sm text-gray-700">
            <input
              type="checkbox"
              checked={form.use_ssl}
              onChange={(e) => handleChange("use_ssl", e.target.checked)}
            />
            Usa SSL
          </label>
          <label className="inline-flex items-center gap-2 text-sm text-gray-700">
            <input
              type="checkbox"
              checked={form.use_auth}
              onChange={(e) => handleChange("use_auth", e.target.checked)}
            />
            Autenticazione SMTP
          </label>
          {!form.use_auth && (
            <span className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded px-2 py-1">
              Relay anonimo — nessun comando AUTH inviato al server
            </span>
          )}
        </div>

        {form.use_auth && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Username SMTP
              </label>
              <input
                type="text"
                className="w-full border rounded px-3 py-2 text-sm"
                value={form.username}
                onChange={(e) => handleChange("username", e.target.value)}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
              <div className="flex">
                <input
                  type={showPassword ? "text" : "password"}
                  className="w-full border rounded-l px-3 py-2 text-sm"
                  placeholder={activeConfig ? "Lascia vuoto per non modificare" : ""}
                  value={form.password ?? ""}
                  onChange={(e) => handleChange("password", e.target.value)}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((s) => !s)}
                  className="px-3 border border-l-0 rounded-r text-xs bg-gray-50 hover:bg-gray-100"
                >
                  {showPassword ? "Nascondi" : "Mostra"}
                </button>
              </div>
            </div>
          </div>
        )}

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Indirizzo mittente</label>
          <input
            type="text"
            className="w-full border rounded px-3 py-2 text-sm"
            value={form.from_email}
            onChange={(e) => handleChange("from_email", e.target.value)}
          />
          <p className="mt-1 text-xs text-gray-500">
            Questo apparirà come mittente nelle email (es. GRC Platform &lt;noreply@azienda.com&gt;).
          </p>
        </div>

        <div className="pt-4 border-t border-gray-100 space-y-3">
          <p className="text-xs text-gray-500">
            La password SMTP è cifrata con AES-256 nel database. Non viene mai mostrata dopo il salvataggio.
          </p>
          <div className="flex items-end gap-2">
            <div className="flex-1">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Destinatario email di test
              </label>
              <input
                type="email"
                className="w-full border rounded px-3 py-2 text-sm"
                placeholder="tuo@email.com"
                value={testRecipient}
                onChange={(e) => setTestRecipient(e.target.value)}
              />
            </div>
            <button
              type="button"
              onClick={() => testMutation.mutate()}
              disabled={!activeConfig || !testRecipient.trim() || testMutation.isPending}
              className="px-3 py-2 rounded-md text-sm bg-indigo-50 text-indigo-700 hover:bg-indigo-100 disabled:opacity-50 whitespace-nowrap"
            >
              {testMutation.isPending ? "Test in corso..." : "Invia email di test"}
            </button>
            <button
              type="button"
              onClick={() => saveMutation.mutate()}
              disabled={saveMutation.isPending}
              className="px-4 py-2 rounded-md text-sm bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-50 whitespace-nowrap"
            >
              {saveMutation.isPending ? "Salvataggio..." : "Salva configurazione"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

