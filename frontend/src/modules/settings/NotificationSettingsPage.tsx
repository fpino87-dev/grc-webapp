import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "../../api/client";
import { useAuthStore } from "../../store/auth";

type NotificationRule = {
  id: string;
  event_type: string;
  enabled: boolean;
  recipient_roles: string[];
  scope_type: "org" | "bu" | "plant";
  scope_bu: string | null;
  scope_plant: string | null;
  channel: string;
};

type Bu = { id: string; code: string; name: string };
type Plant = { id: string; code: string; name: string; bu?: string | null };

const EVENT_LABEL: Record<string, string> = {
  risk_red: "Rischio critico",
  finding_major: "Finding Major NC aperto",
  finding_minor: "Finding Minor NC aperto",
  incident_nis2: "Incidente NIS2 rilevato",
  incident_closed: "Incidente chiuso",
  task_assigned: "Task assegnato",
  task_overdue: "Task scaduto",
  evidence_expired: "Evidenza scaduta",
  document_approval: "Documento in attesa approvazione",
  role_expiring: "Ruolo normativo in scadenza",
  bcp_test_failed: "Test BCP fallito",
  pdca_blocked: "PDCA bloccato > 30 giorni",
  management_review: "Revisione direzione da approvare",
  supplier_assessment: "Assessment fornitore completato",
};

const ROLE_OPTIONS: { value: string; label: string }[] = [
  { value: "ciso", label: "CISO" },
  { value: "risk_manager", label: "Risk Manager" },
  { value: "compliance_officer", label: "Compliance Officer" },
  { value: "plant_manager", label: "Plant Manager" },
  { value: "control_owner", label: "Control Owner" },
  { value: "internal_auditor", label: "Auditor Interno" },
  { value: "external_auditor", label: "Auditor Esterno" },
];

function eventBadge(eventType: string, enabled: boolean) {
  let color = "bg-gray-100 text-gray-700";
  if (["risk_red", "finding_major", "incident_nis2", "task_overdue", "bcp_test_failed"].includes(eventType)) {
    color = enabled ? "bg-red-100 text-red-800" : "bg-red-50 text-red-400";
  } else if (["finding_minor", "evidence_expired", "pdca_blocked"].includes(eventType)) {
    color = enabled ? "bg-amber-100 text-amber-800" : "bg-amber-50 text-amber-400";
  }
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${color}`}>
      {EVENT_LABEL[eventType] || eventType}
    </span>
  );
}

function scopeBadge(rule: NotificationRule, buMap: Record<string, Bu>, plantMap: Record<string, Plant>) {
  if (rule.scope_type === "org") {
    return <span className="px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 text-xs">Organizzazione</span>;
  }
  if (rule.scope_type === "bu" && rule.scope_bu && buMap[rule.scope_bu]) {
    const bu = buMap[rule.scope_bu];
    return (
      <span className="px-2 py-0.5 rounded-full bg-indigo-50 text-indigo-700 text-xs">
        BU: {bu.code} — {bu.name}
      </span>
    );
  }
  if (rule.scope_type === "plant" && rule.scope_plant && plantMap[rule.scope_plant]) {
    const p = plantMap[rule.scope_plant];
    return (
      <span className="px-2 py-0.5 rounded-full bg-green-50 text-green-700 text-xs">
        Plant: {p.code} — {p.name}
      </span>
    );
  }
  return <span className="px-2 py-0.5 rounded-full bg-gray-50 text-gray-500 text-xs">Non configurato</span>;
}

function rolesBadges(roles: string[]) {
  if (!roles.length) return <span className="text-xs text-gray-400">Nessun ruolo</span>;
  return (
    <div className="flex flex-wrap gap-1">
      {roles.map((r) => {
        const label = ROLE_OPTIONS.find((o) => o.value === r)?.label || r;
        return (
          <span
            key={r}
            className="px-2 py-0.5 rounded-full bg-purple-50 text-purple-700 text-[11px] font-medium"
          >
            {label}
          </span>
        );
      })}
    </div>
  );
}

type RuleForm = {
  id?: string;
  event_type: string;
  enabled: boolean;
  recipient_roles: string[];
  scope_type: "org" | "bu" | "plant";
  scope_bu: string | null;
  scope_plant: string | null;
};

export function NotificationSettingsPage() {
  const userRole = useAuthStore((s) => s.user?.role);
  const qc = useQueryClient();
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<RuleForm | null>(null);
  const [error, setError] = useState("");

  const { data: rules } = useQuery<NotificationRule[]>({
    queryKey: ["notification-rules"],
    queryFn: async () => {
      const res = await apiClient.get("/notifications/rules/");
      return res.data;
    },
  });

  const { data: bus } = useQuery<Bu[]>({
    queryKey: ["business-units"],
    queryFn: async () => {
      const res = await apiClient.get("/plants/business-units/");
      return res.data.results || res.data;
    },
  });

  const { data: plants } = useQuery<Plant[]>({
    queryKey: ["plants-all"],
    queryFn: async () => {
      const res = await apiClient.get("/plants/");
      return res.data.results || res.data;
    },
  });

  const buMap = Object.fromEntries((bus || []).map((b) => [b.id, b]));
  const plantMap = Object.fromEntries((plants || []).map((p) => [p.id, p]));

  const saveMutation = useMutation({
    mutationFn: async (form: RuleForm) => {
      const payload = {
        event_type: form.event_type,
        enabled: form.enabled,
        recipient_roles: form.recipient_roles,
        scope_type: form.scope_type,
        scope_bu: form.scope_type === "bu" ? form.scope_bu : null,
        scope_plant: form.scope_type === "plant" ? form.scope_plant : null,
        channel: "email",
      };
      if (form.id) {
        await apiClient.put(`/notifications/rules/${form.id}/`, payload);
      } else {
        await apiClient.post("/notifications/rules/", payload);
      }
    },
    onSuccess: () => {
      setModalOpen(false);
      setEditing(null);
      setError("");
      qc.invalidateQueries({ queryKey: ["notification-rules"] });
    },
    onError: (e: any) => {
      const msg = e?.response?.data?.detail || "Errore nel salvataggio regola.";
      setError(String(msg));
    },
  });

  const toggleMutation = useMutation({
    mutationFn: async (rule: NotificationRule) => {
      await apiClient.patch(`/notifications/rules/${rule.id}/`, {
        enabled: !rule.enabled,
      });
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["notification-rules"] });
    },
  });

  function openNew() {
    setEditing({
      event_type: "risk_red",
      enabled: true,
      recipient_roles: [],
      scope_type: "org",
      scope_bu: null,
      scope_plant: null,
    });
    setError("");
    setModalOpen(true);
  }

  function openEdit(rule: NotificationRule) {
    setEditing({
      id: rule.id,
      event_type: rule.event_type,
      enabled: rule.enabled,
      recipient_roles: rule.recipient_roles,
      scope_type: rule.scope_type,
      scope_bu: rule.scope_bu,
      scope_plant: rule.scope_plant,
    });
    setError("");
    setModalOpen(true);
  }

  function toggleRole(value: string) {
    if (!editing) return;
    const has = editing.recipient_roles.includes(value);
    setEditing({
      ...editing,
      recipient_roles: has
        ? editing.recipient_roles.filter((r) => r !== value)
        : [...editing.recipient_roles, value],
    });
  }

  if (userRole !== "super_admin" && userRole !== "compliance_officer") {
    return (
      <div className="p-6">
        <h2 className="text-lg font-semibold mb-2">Regole di Notifica</h2>
        <p className="text-sm text-gray-600">Non hai i permessi per accedere a questa pagina.</p>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-xl font-semibold">Regole di Notifica</h2>
          <p className="text-xs text-gray-500 mt-1">
            Le notifiche vengono inviate agli utenti che hanno il ruolo selezionato e accesso al sito
            dell&apos;evento. Configura prima l&apos;email in Impostazioni → Configurazione Email.
          </p>
        </div>
        <button
          type="button"
          onClick={openNew}
          className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700"
        >
          + Nuova regola
        </button>
      </div>

      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Evento</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Ruoli destinatari</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Scope</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Canale</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Attivo</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Azioni</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {(rules || []).map((rule) => (
              <tr key={rule.id} className="hover:bg-gray-50">
                <td className="px-4 py-3">{eventBadge(rule.event_type, rule.enabled)}</td>
                <td className="px-4 py-3">{rolesBadges(rule.recipient_roles)}</td>
                <td className="px-4 py-3">{scopeBadge(rule, buMap, plantMap)}</td>
                <td className="px-4 py-3 text-xs text-gray-600">Email</td>
                <td className="px-4 py-3">
                  <button
                    type="button"
                    onClick={() => toggleMutation.mutate(rule)}
                    className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                      rule.enabled
                        ? "bg-green-100 text-green-800"
                        : "bg-gray-100 text-gray-500"
                    }`}
                  >
                    {rule.enabled ? "Attiva" : "Disattiva"}
                  </button>
                </td>
                <td className="px-4 py-3">
                  <button
                    type="button"
                    onClick={() => openEdit(rule)}
                    className="text-xs text-primary-600 hover:underline"
                  >
                    Modifica
                  </button>
                </td>
              </tr>
            ))}
            {!rules?.length && (
              <tr>
                <td className="px-4 py-6 text-center text-gray-400 text-sm" colSpan={6}>
                  Nessuna regola di notifica configurata.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {modalOpen && editing && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-xl p-6">
            <h3 className="text-lg font-semibold mb-4">
              {editing.id ? "Modifica regola" : "Nuova regola di notifica"}
            </h3>
            <div className="space-y-4 text-sm">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Evento</label>
                <select
                  className="w-full border rounded px-3 py-2 text-sm"
                  value={editing.event_type}
                  onChange={(e) => setEditing({ ...editing, event_type: e.target.value })}
                >
                  {Object.keys(EVENT_LABEL).map((k) => (
                    <option key={k} value={k}>
                      {EVENT_LABEL[k]}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Ruoli destinatari
                </label>
                <div className="grid grid-cols-2 gap-2">
                  {ROLE_OPTIONS.map((opt) => (
                    <label key={opt.value} className="inline-flex items-center gap-2 text-xs">
                      <input
                        type="checkbox"
                        checked={editing.recipient_roles.includes(opt.value)}
                        onChange={() => toggleRole(opt.value)}
                      />
                      {opt.label}
                    </label>
                  ))}
                </div>
              </div>
              <div className="grid grid-cols-3 gap-3">
                <div className="col-span-1">
                  <label className="block text-sm font-medium text-gray-700 mb-1">Scope</label>
                  <select
                    className="w-full border rounded px-3 py-2 text-sm"
                    value={editing.scope_type}
                    onChange={(e) =>
                      setEditing({
                        ...editing,
                        scope_type: e.target.value as any,
                        scope_bu: null,
                        scope_plant: null,
                      })
                    }
                  >
                    <option value="org">Organizzazione</option>
                    <option value="bu">Business Unit</option>
                    <option value="plant">Sito</option>
                  </select>
                </div>
                {editing.scope_type === "bu" && (
                  <div className="col-span-2">
                    <label className="block text-sm font-medium text-gray-700 mb-1">Business Unit</label>
                    <select
                      className="w-full border rounded px-3 py-2 text-sm"
                      value={editing.scope_bu ?? ""}
                      onChange={(e) =>
                        setEditing({
                          ...editing,
                          scope_bu: e.target.value || null,
                        })
                      }
                    >
                      <option value="">— seleziona BU —</option>
                      {(bus || []).map((b) => (
                        <option key={b.id} value={b.id}>
                          {b.code} — {b.name}
                        </option>
                      ))}
                    </select>
                  </div>
                )}
                {editing.scope_type === "plant" && (
                  <div className="col-span-2">
                    <label className="block text-sm font-medium text-gray-700 mb-1">Sito</label>
                    <select
                      className="w-full border rounded px-3 py-2 text-sm"
                      value={editing.scope_plant ?? ""}
                      onChange={(e) =>
                        setEditing({
                          ...editing,
                          scope_plant: e.target.value || null,
                        })
                      }
                    >
                      <option value="">— seleziona sito —</option>
                      {(plants || []).map((p) => (
                        <option key={p.id} value={p.id}>
                          {p.code} — {p.name}
                        </option>
                      ))}
                    </select>
                  </div>
                )}
              </div>
              {error && <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded">{error}</p>}
            </div>
            <div className="flex justify-end gap-2 mt-4">
              <button
                type="button"
                onClick={() => {
                  setModalOpen(false);
                  setEditing(null);
                  setError("");
                }}
                className="px-4 py-2 border rounded text-sm text-gray-600 hover:bg-gray-50"
              >
                Annulla
              </button>
              <button
                type="button"
                onClick={() => editing && saveMutation.mutate(editing)}
                disabled={saveMutation.isPending}
                className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700 disabled:opacity-50"
              >
                {saveMutation.isPending ? "Salvataggio..." : "Salva regola"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

