import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "../../api/client";

// ── Tipi ────────────────────────────────────────────────────────────────────

type RoleProfile = {
  id: string;
  grc_role: string;
  profile: string;
  profile_label: string;
  custom_events: string[];
  enabled: boolean;
  active_events: string[];
};

type ProfilesCatalog = {
  profiles: Record<string, { label: string; description: string; events: string[] }>;
  event_labels: Record<string, string>;
};

// ── Costanti ────────────────────────────────────────────────────────────────

const ROLE_LABELS: Record<string, string> = {
  ciso:               "CISO",
  compliance_officer: "Compliance Officer",
  risk_manager:       "Risk Manager",
  plant_manager:      "Plant Manager",
  control_owner:      "Control Owner",
  internal_auditor:   "Auditor Interno",
  external_auditor:   "Auditor Esterno",
  nis2_contact:       "Contatto NIS2",
  isms_manager:       "ISMS Manager",
  dpo:                "DPO",
};

const PROFILE_OPTIONS = [
  { value: "silenzioso", label: "Silenzioso" },
  { value: "essenziale", label: "Essenziale" },
  { value: "standard",   label: "Standard" },
  { value: "completo",   label: "Completo" },
  { value: "custom",     label: "Personalizzato" },
];

const PROFILE_COLOR: Record<string, string> = {
  silenzioso: "bg-gray-100 text-gray-600",
  essenziale: "bg-yellow-100 text-yellow-800",
  standard:   "bg-blue-100 text-blue-800",
  completo:   "bg-green-100 text-green-800",
  custom:     "bg-purple-100 text-purple-800",
};

// Gruppi eventi per il modal personalizzazione
const EVENT_GROUPS = [
  {
    label: "Rischi e Sicurezza",
    events: ["risk_red", "finding_major", "finding_minor", "incident_nis2", "incident_closed"],
  },
  {
    label: "Operatività",
    events: ["task_assigned", "task_overdue", "evidence_expired", "document_approval", "bcp_test_failed"],
  },
  {
    label: "Governance",
    events: ["role_expiring", "role_vacant", "pdca_blocked", "management_review"],
  },
  {
    label: "Fornitori e Rischio",
    events: ["supplier_assessment", "risk_accepted"],
  },
];

// ── Modal personalizzazione ──────────────────────────────────────────────────

function CustomModal({
  rp,
  eventLabels,
  onClose,
}: {
  rp: RoleProfile;
  eventLabels: Record<string, string>;
  onClose: () => void;
}) {
  const qc = useQueryClient();
  const [selected, setSelected] = useState<string[]>(
    rp.profile === "custom" ? rp.custom_events : rp.active_events
  );
  const [error, setError] = useState("");

  const saveMutation = useMutation({
    mutationFn: async () => {
      await apiClient.post(`/notifications/role-profiles/${rp.id}/set-custom/`, { events: selected });
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["notification-role-profiles"] });
      onClose();
    },
    onError: (e: any) => {
      setError(e?.response?.data?.error || "Errore nel salvataggio.");
    },
  });

  const resetMutation = useMutation({
    mutationFn: async () => {
      await apiClient.patch(`/notifications/role-profiles/${rp.id}/`, { profile: "standard" });
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["notification-role-profiles"] });
      onClose();
    },
  });

  function toggle(ev: string) {
    setSelected((s) =>
      s.includes(ev) ? s.filter((x) => x !== ev) : [...s, ev]
    );
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-lg p-6 max-h-[90vh] overflow-y-auto">
        <h3 className="text-lg font-semibold mb-1">
          Personalizza notifiche — {ROLE_LABELS[rp.grc_role] ?? rp.grc_role}
        </h3>
        <p className="text-xs text-gray-500 mb-4">
          Seleziona esattamente quali eventi vuoi ricevere per questo ruolo.
        </p>

        <div className="space-y-4">
          {EVENT_GROUPS.map((group) => (
            <div key={group.label}>
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
                {group.label}
              </p>
              <div className="space-y-1.5">
                {group.events.map((ev) => {
                  const label = eventLabels[ev] ?? ev;
                  return (
                    <label key={ev} className="flex items-center gap-2 text-sm cursor-pointer">
                      <input
                        type="checkbox"
                        checked={selected.includes(ev)}
                        onChange={() => toggle(ev)}
                        className="rounded"
                      />
                      <span className="text-gray-700">{label}</span>
                    </label>
                  );
                })}
              </div>
            </div>
          ))}
        </div>

        {error && (
          <p className="mt-3 text-sm text-red-600 bg-red-50 px-3 py-2 rounded">{error}</p>
        )}

        <div className="flex justify-between items-center mt-5 pt-4 border-t border-gray-100">
          <button
            type="button"
            onClick={() => resetMutation.mutate()}
            disabled={resetMutation.isPending}
            className="text-xs text-gray-500 hover:text-gray-700 underline"
          >
            Ripristina profilo Standard
          </button>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={onClose}
              className="px-3 py-1.5 border rounded text-sm text-gray-600 hover:bg-gray-50"
            >
              Annulla
            </button>
            <button
              type="button"
              onClick={() => saveMutation.mutate()}
              disabled={saveMutation.isPending}
              className="px-3 py-1.5 bg-primary-600 text-white rounded text-sm hover:bg-primary-700 disabled:opacity-50"
            >
              {saveMutation.isPending ? "Salvataggio..." : "Salva personalizzazione"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Accordion profili ────────────────────────────────────────────────────────

const ALL_EVENTS_ORDERED = [
  "risk_red", "finding_major", "incident_nis2", "role_expiring", "role_vacant",
  "finding_minor", "incident_closed", "task_assigned", "task_overdue",
  "evidence_expired", "bcp_test_failed", "document_approval",
  "pdca_blocked", "supplier_assessment", "management_review", "risk_accepted",
];

function ProfilesAccordion({ catalog }: { catalog: ProfilesCatalog }) {
  const [open, setOpen] = useState(false);
  const profiles = ["essenziale", "standard", "completo"];

  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden mb-6">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between px-4 py-3 bg-gray-50 hover:bg-gray-100 text-sm font-medium text-gray-700"
      >
        <span>Cosa include ogni profilo?</span>
        <span className="text-gray-400">{open ? "▲" : "▼"}</span>
      </button>
      {open && (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-white border-b border-gray-100">
                <th className="text-left px-4 py-2 text-xs text-gray-500 font-medium">Evento</th>
                {profiles.map((p) => (
                  <th key={p} className="px-4 py-2 text-xs font-medium text-center">
                    <span className={`px-2 py-0.5 rounded-full ${PROFILE_COLOR[p]}`}>
                      {catalog.profiles[p]?.label ?? p}
                    </span>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {ALL_EVENTS_ORDERED.map((ev) => (
                <tr key={ev} className="hover:bg-gray-50">
                  <td className="px-4 py-2 text-gray-700">{catalog.event_labels[ev] ?? ev}</td>
                  {profiles.map((p) => {
                    const has = catalog.profiles[p]?.events.includes(ev);
                    return (
                      <td key={p} className="px-4 py-2 text-center">
                        {has ? (
                          <span className="text-green-600 font-bold">✓</span>
                        ) : (
                          <span className="text-gray-300">—</span>
                        )}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ── Pagina principale ────────────────────────────────────────────────────────

export function NotificationSettingsPage() {
  const qc = useQueryClient();
  const [customModal, setCustomModal] = useState<RoleProfile | null>(null);
  const [confirmReset, setConfirmReset] = useState(false);

  const { data: profiles, isLoading } = useQuery<RoleProfile[]>({
    queryKey: ["notification-role-profiles"],
    queryFn: async () => {
      const res = await apiClient.get("/notifications/role-profiles/");
      const d = res.data;
      return Array.isArray(d) ? d : (d?.results ?? []);
    },
    retry: false,
  });

  const { data: catalog } = useQuery<ProfilesCatalog>({
    queryKey: ["notification-profiles-catalog"],
    queryFn: async () => {
      const res = await apiClient.get("/notifications/role-profiles/profiles-catalog/");
      return res.data;
    },
    retry: false,
  });

  const { data: emailConfig } = useQuery({
    queryKey: ["email-config-check"],
    queryFn: async () => {
      const res = await apiClient.get("/notifications/email-config/");
      const d = res.data;
      return Array.isArray(d) ? d : (d?.results ?? []);
    },
    retry: false,
  });

  const patchMutation = useMutation({
    mutationFn: async ({ id, data }: { id: string; data: Record<string, unknown> }) => {
      await apiClient.patch(`/notifications/role-profiles/${id}/`, data);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["notification-role-profiles"] }),
  });

  const resetAllMutation = useMutation({
    mutationFn: async () => {
      await apiClient.post("/notifications/role-profiles/reset-defaults/");
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["notification-role-profiles"] });
      setConfirmReset(false);
    },
  });

  function handleProfileChange(rp: RoleProfile, newProfile: string) {
    if (newProfile === "custom") {
      setCustomModal(rp);
      return;
    }
    patchMutation.mutate({ id: rp.id, data: { profile: newProfile } });
  }

  const hasEmailConfig = Array.isArray(emailConfig) && emailConfig.length > 0;

  return (
    <div>
      <div className="flex items-start justify-between mb-6">
        <div>
          <h2 className="text-xl font-semibold text-gray-900">Profili di Notifica Email</h2>
          <p className="text-sm text-gray-500 mt-1">
            Scegli quanti avvisi riceve ogni ruolo. Le notifiche vengono inviate agli utenti
            con quel ruolo e accesso al sito dell&apos;evento.
          </p>
        </div>
        <button
          type="button"
          onClick={() => setConfirmReset(true)}
          className="px-3 py-1.5 border border-gray-300 text-sm text-gray-600 rounded hover:bg-gray-50"
        >
          Reimposta tutti i default
        </button>
      </div>

      {/* Banner email non configurata */}
      {!hasEmailConfig && (
        <div className="mb-4 flex items-center gap-3 bg-amber-50 border border-amber-200 rounded-lg px-4 py-3 text-sm text-amber-800">
          <span>⚠</span>
          <span>
            Server email non configurato — le notifiche non verranno inviate.{" "}
            <a href="/settings/email" className="underline font-medium">
              Configura email →
            </a>
          </span>
        </div>
      )}

      {/* Accordion */}
      {catalog && <ProfilesAccordion catalog={catalog} />}

      {/* Tabella ruoli */}
      <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Ruolo GRC</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Profilo</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Stato</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">
                <span className="sr-only">Personalizza</span>
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {isLoading && (
              <tr>
                <td colSpan={4} className="px-4 py-8 text-center text-gray-400 text-sm">
                  Caricamento...
                </td>
              </tr>
            )}
            {(profiles ?? []).map((rp) => (
              <tr key={rp.id} className="hover:bg-gray-50">
                <td className="px-4 py-3 font-medium text-gray-800">
                  {ROLE_LABELS[rp.grc_role] ?? rp.grc_role}
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <select
                      value={rp.profile}
                      onChange={(e) => handleProfileChange(rp, e.target.value)}
                      className="border border-gray-300 rounded px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-primary-500"
                    >
                      {PROFILE_OPTIONS.map((opt) => (
                        <option key={opt.value} value={opt.value}>
                          {opt.label}
                        </option>
                      ))}
                    </select>
                    {rp.profile !== "silenzioso" && (
                      <span className="text-xs text-gray-400">
                        {rp.active_events.length} eventi
                      </span>
                    )}
                  </div>
                </td>
                <td className="px-4 py-3">
                  <button
                    type="button"
                    onClick={() => patchMutation.mutate({ id: rp.id, data: { enabled: !rp.enabled } })}
                    className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${
                      rp.enabled
                        ? "bg-green-100 text-green-800"
                        : "bg-gray-100 text-gray-500"
                    }`}
                  >
                    <span className={`w-1.5 h-1.5 rounded-full ${rp.enabled ? "bg-green-500" : "bg-gray-400"}`} />
                    {rp.enabled ? "On" : "Off"}
                  </button>
                </td>
                <td className="px-4 py-3">
                  <button
                    type="button"
                    onClick={() => setCustomModal(rp)}
                    className={`px-2.5 py-1 rounded text-xs font-medium border ${
                      rp.profile === "custom"
                        ? "border-purple-300 text-purple-700 bg-purple-50 hover:bg-purple-100"
                        : "border-gray-200 text-gray-500 hover:bg-gray-50"
                    }`}
                  >
                    Personalizza
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Modal personalizzazione */}
      {customModal && catalog && (
        <CustomModal
          rp={customModal}
          eventLabels={catalog.event_labels}
          onClose={() => setCustomModal(null)}
        />
      )}

      {/* Conferma reset */}
      {confirmReset && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-sm p-6">
            <h3 className="text-base font-semibold mb-2">Sei sicuro?</h3>
            <p className="text-sm text-gray-600 mb-4">
              Tutti i profili personalizzati verranno persi e reimpostati ai valori default.
            </p>
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setConfirmReset(false)}
                className="px-4 py-2 border rounded text-sm text-gray-600 hover:bg-gray-50"
              >
                Annulla
              </button>
              <button
                type="button"
                onClick={() => resetAllMutation.mutate()}
                disabled={resetAllMutation.isPending}
                className="px-4 py-2 bg-red-600 text-white rounded text-sm hover:bg-red-700 disabled:opacity-50"
              >
                {resetAllMutation.isPending ? "..." : "Reimposta"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
