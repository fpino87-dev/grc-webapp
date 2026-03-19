import { useEffect, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { governanceApi, type RoleAssignment, type SecurityCommittee } from "../../api/endpoints/governance";
import { usersApi } from "../../api/endpoints/users";
import { plantsApi } from "../../api/endpoints/plants";
import { apiClient } from "../../api/client";
import { ModuleHelp } from "../../components/ui/ModuleHelp";
import { DocumentWorkflowSection } from "./DocumentWorkflowPage";
import { FrameworkGovernanceTab } from "./FrameworkGovernanceTab";
import { RiskAppetiteGovernanceTab } from "./RiskAppetiteGovernanceTab";
import { useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";

const ROLE_KEYS: Record<string, string> = {
  ciso:                   "ciso",
  compliance_officer:     "compliance_officer",
  risk_manager:           "risk_manager",
  internal_auditor:       "internal_auditor",
  external_auditor:       "external_auditor",
  plant_manager:          "plant_manager",
  control_owner:          "control_owner",
  plant_security_officer: "plant_security_officer",
  nis2_contact:           "nis2_contact",
  dpo:                    "dpo",
  isms_manager:           "isms_manager",
  comitato_membro:        "comitato_membro",
  bu_referente:           "bu_referente",
  raci_responsible:       "raci_responsible",
  raci_accountable:       "raci_accountable",
};

const TODAY = new Date().toISOString().slice(0, 10);

// ── Helpers ───────────────────────────────────────────────────────────────────

function scopeBadge(a: RoleAssignment) {
  if (a.scope_label) {
    const colors: Record<string, string> = {
      Globale: "bg-blue-50 text-blue-700 border-blue-200",
    };
    const isGlobal = a.scope_type === "org";
    const isBu = a.scope_type === "bu";
    const cls = isGlobal
      ? "bg-blue-50 text-blue-700 border-blue-200"
      : isBu
      ? "bg-indigo-50 text-indigo-700 border-indigo-200"
      : "bg-green-50 text-green-700 border-green-200";
    return (
      <span className={`text-xs px-1.5 py-0.5 rounded border ${cls}`}>
        {a.scope_label}
      </span>
    );
  }
  return null;
}

function roleBadge(a: RoleAssignment, t: (k: string, opts?: any) => string) {
  if (!a.valid_until) {
    return (
      <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full">
        {t("status.attivo")}
      </span>
    );
  }
  const days = Math.ceil((new Date(a.valid_until).getTime() - Date.now()) / 86400000);
  if (days < 0) {
    return (
      <span className="text-xs bg-red-100 text-red-700 px-2 py-0.5 rounded-full">
        {t("status.scaduto")}
      </span>
    );
  }
  if (days <= 30) {
    return (
      <span className="text-xs bg-amber-100 text-amber-700 px-2 py-0.5 rounded-full">
        {t("governance.badges.expires_in_days", { days })}
      </span>
    );
  }
  return (
    <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full">
      {t("status.attivo")}
    </span>
  );
}

// ── Toast ─────────────────────────────────────────────────────────────────────

function Toast({ msg, onClose }: { msg: string; onClose: () => void }) {
  return (
    <div className="fixed bottom-6 right-6 z-50 bg-green-600 text-white px-5 py-3 rounded-lg shadow-lg flex items-center gap-3 max-w-sm">
      <span className="text-sm">{msg}</span>
      <button onClick={onClose} className="text-white/80 hover:text-white text-lg leading-none">×</button>
    </div>
  );
}

// ── Modal: Nuova assegnazione ─────────────────────────────────────────────────

function RoleAssignmentModal({
  users,
  onClose,
}: { users: { id: number; email: string; name: string }[]; onClose: () => void }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [form, setForm] = useState<Record<string, any>>({
    scope_type: "org",
    valid_from: TODAY,
  });
  const [error, setError] = useState("");

  const { data: plants } = useQuery({
    queryKey: ["plants"],
    queryFn: () => plantsApi.list(),
    retry: false,
  });
  const { data: busData } = useQuery({
    queryKey: ["business-units"],
    queryFn: async () => {
      const res = await apiClient.get("/plants/business-units/");
      const d = res.data;
      return Array.isArray(d) ? d : (d?.results ?? []);
    },
    retry: false,
  });

  const mutation = useMutation({
    mutationFn: () => governanceApi.createRoleAssignment(form as any),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["role-assignments"] }); onClose(); },
    onError: (e: any) => setError(e?.response?.data?.detail || JSON.stringify(e?.response?.data) || t("common.error")),
  });

  function handleChange(e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) {
    const val = e.target.value || null;
    if (e.target.name === "scope_type") {
      setForm(prev => ({ ...prev, scope_type: val, scope_id: null }));
    } else {
      setForm(prev => ({ ...prev, [e.target.name]: val }));
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-6">
        <h3 className="text-lg font-semibold mb-4">{t("governance.roles_assign.modal_title")}</h3>
        <div className="space-y-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("governance.roles_assign.user")} *</label>
            <select name="user" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm">
              <option value="">{t("common.select")}</option>
              {users.map(u => <option key={u.id} value={u.id}>{u.name || u.email}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("governance.roles_assign.role")} *</label>
            <select name="role" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm">
              <option value="">{t("common.select")}</option>
              {Object.keys(ROLE_KEYS).map((k) => (
                <option key={k} value={k}>{t(`governance.roles.${ROLE_KEYS[k]}`)}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("governance.roles_assign.scope")}</label>
            <select name="scope_type" defaultValue="org" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm">
              <option value="org">{t("governance.scopes.org")}</option>
              <option value="bu">{t("governance.scopes.bu")}</option>
              <option value="plant">{t("governance.scopes.plant")}</option>
            </select>
          </div>
          {form.scope_type === "bu" && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("governance.roles_assign.business_unit")} *</label>
              <select name="scope_id" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm">
                <option value="">{t("governance.roles_assign.select_bu")}</option>
                {(busData ?? []).map((b: any) => (
                  <option key={b.id} value={b.id}>{b.code} — {b.name}</option>
                ))}
              </select>
            </div>
          )}
          {form.scope_type === "plant" && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("governance.roles_assign.plant")} *</label>
              <select name="scope_id" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm">
                <option value="">{t("governance.roles_assign.select_plant")}</option>
                {(plants ?? []).map((p) => (
                  <option key={p.id} value={p.id}>[{p.code}] {p.name}</option>
                ))}
              </select>
            </div>
          )}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("governance.roles_assign.valid_from")} *</label>
              <input type="date" name="valid_from" defaultValue={TODAY} onChange={handleChange}
                className="w-full border rounded px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("governance.roles_assign.valid_until")}</label>
              <input type="date" name="valid_until" onChange={handleChange}
                className="w-full border rounded px-3 py-2 text-sm" />
            </div>
          </div>
        </div>
        {error && <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded mt-3">{error}</p>}
        <div className="flex justify-end gap-2 mt-4">
          <button onClick={onClose} className="px-4 py-2 border rounded text-sm text-gray-600 hover:bg-gray-50">{t("actions.cancel")}</button>
          <button
            onClick={() => mutation.mutate()}
            disabled={
              mutation.isPending || !form.user || !form.role || !form.valid_from ||
              (form.scope_type !== "org" && !form.scope_id)
            }
            className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700 disabled:opacity-50"
          >
            {mutation.isPending ? t("common.saving") : t("governance.roles_assign.submit")}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Modal: Termina ruolo ──────────────────────────────────────────────────────

function TerminaModal({
  assignment,
  onClose,
  onSuccess,
}: { assignment: RoleAssignment; onClose: () => void; onSuccess: (msg: string) => void }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [reason, setReason] = useState("");
  const [date, setDate] = useState(TODAY);
  const [error, setError] = useState("");

  function roleLabel(role: string) {
    const key = ROLE_KEYS[role] ?? role;
    return t(`governance.roles.${key}`, { defaultValue: role });
  }

  const mutation = useMutation({
    mutationFn: () => governanceApi.terminaRole(assignment.id, { reason, termination_date: date }),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ["role-assignments"] });
      qc.invalidateQueries({ queryKey: ["governance-vacanti"] });
      qc.invalidateQueries({ queryKey: ["governance-in-scadenza"] });
      onSuccess(data.message);
      onClose();
    },
    onError: (e: any) => setError(e?.response?.data?.error || t("governance.terminate.error")),
  });

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-6 space-y-4">
        <h3 className="text-lg font-semibold">{t("governance.terminate.title")}</h3>
        <p className="text-sm text-gray-600">
          {t("governance.terminate.body", {
            role: roleLabel(assignment.role),
            user: assignment.user_name ?? assignment.user_email,
          })}
        </p>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">{t("governance.terminate.end_date")}</label>
          <input type="date" value={date} onChange={e => setDate(e.target.value)}
            className="w-full border rounded px-3 py-2 text-sm" />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">{t("governance.terminate.reason")} *</label>
          <textarea
            value={reason}
            onChange={e => setReason(e.target.value)}
            rows={3}
            placeholder={t("governance.terminate.reason_placeholder")}
            className="w-full border rounded px-3 py-2 text-sm"
          />
        </div>
        {error && <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded">{error}</p>}
        <div className="flex justify-end gap-2">
          <button onClick={onClose} className="px-4 py-2 border rounded text-sm text-gray-600 hover:bg-gray-50">{t("actions.cancel")}</button>
          <button
            onClick={() => mutation.mutate()}
            disabled={mutation.isPending || reason.trim().length < 5}
            className="px-4 py-2 bg-orange-600 text-white rounded text-sm hover:bg-orange-700 disabled:opacity-50"
          >
            {mutation.isPending ? t("governance.terminate.pending") : t("governance.terminate.confirm")}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Modal: Sostituisci ruolo ──────────────────────────────────────────────────

function SostituisciModal({
  assignment,
  users,
  onClose,
  onSuccess,
}: {
  assignment: RoleAssignment;
  users: { id: number; email: string; name: string }[];
  onClose: () => void;
  onSuccess: (msg: string) => void;
}) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [newUserId, setNewUserId] = useState<number | "">("");
  const [reason, setReason] = useState("");
  const [date, setDate] = useState(TODAY);
  const [error, setError] = useState("");

  function roleLabel(role: string) {
    const key = ROLE_KEYS[role] ?? role;
    return t(`governance.roles.${key}`, { defaultValue: role });
  }

  const mutation = useMutation({
    mutationFn: () =>
      governanceApi.sostituisciRole(assignment.id, {
        new_user_id: newUserId as number,
        reason,
        handover_date: date,
      }),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ["role-assignments"] });
      qc.invalidateQueries({ queryKey: ["governance-vacanti"] });
      qc.invalidateQueries({ queryKey: ["governance-in-scadenza"] });
      onSuccess(data.message);
      onClose();
    },
    onError: (e: any) => setError(e?.response?.data?.error || t("governance.replace.error")),
  });

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-6 space-y-4">
        <h3 className="text-lg font-semibold">{t("governance.replace.title")}</h3>
        <p className="text-sm text-gray-600">
          {t("governance.replace.body", {
            role: roleLabel(assignment.role),
            user: assignment.user_name ?? assignment.user_email,
          })}
        </p>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">{t("governance.replace.new_owner")} *</label>
          <select
            value={newUserId}
            onChange={e => setNewUserId(Number(e.target.value))}
            className="w-full border rounded px-3 py-2 text-sm"
          >
            <option value="">{t("common.select")}</option>
            {users.filter(u => u.id !== assignment.user).map(u => (
              <option key={u.id} value={u.id}>{u.name || u.email}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">{t("governance.replace.handover_date")}</label>
          <input type="date" value={date} onChange={e => setDate(e.target.value)}
            className="w-full border rounded px-3 py-2 text-sm" />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">{t("governance.replace.reason")}</label>
          <textarea
            value={reason}
            onChange={e => setReason(e.target.value)}
            rows={2}
            placeholder={t("common.optional")}
            className="w-full border rounded px-3 py-2 text-sm"
          />
        </div>
        {error && <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded">{error}</p>}
        <div className="flex justify-end gap-2">
          <button onClick={onClose} className="px-4 py-2 border rounded text-sm text-gray-600 hover:bg-gray-50">{t("actions.cancel")}</button>
          <button
            onClick={() => mutation.mutate()}
            disabled={mutation.isPending || !newUserId}
            className="px-4 py-2 bg-blue-600 text-white rounded text-sm hover:bg-blue-700 disabled:opacity-50"
          >
            {mutation.isPending ? t("governance.replace.pending") : t("governance.replace.confirm")}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Modal: Comitato ───────────────────────────────────────────────────────────

function CommitteeModal({ onClose }: { onClose: () => void }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [form, setForm] = useState<Partial<SecurityCommittee>>({ committee_type: "centrale", frequency: "trimestrale" });
  const [error, setError] = useState("");

  const mutation = useMutation({
    mutationFn: governanceApi.createCommittee,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["committees"] }); onClose(); },
    onError: (e: any) => setError(e?.response?.data?.detail || t("common.error")),
  });

  function handleChange(e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) {
    setForm(prev => ({ ...prev, [e.target.name]: e.target.value || null }));
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-6">
        <h3 className="text-lg font-semibold mb-4">{t("governance.committees.new.title")}</h3>
        <div className="space-y-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("governance.committees.fields.name")} *</label>
            <input name="name" onChange={handleChange}
              className="w-full border rounded px-3 py-2 text-sm"
              placeholder={t("governance.committees.placeholders.name")} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("governance.committees.fields.type")}</label>
              <select name="committee_type" defaultValue="centrale" onChange={handleChange}
                className="w-full border rounded px-3 py-2 text-sm">
                <option value="centrale">{t("governance.committees.types.centrale")}</option>
                <option value="bu">{t("governance.committees.types.bu")}</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("governance.committees.fields.frequency")}</label>
              <select name="frequency" defaultValue="trimestrale" onChange={handleChange}
                className="w-full border rounded px-3 py-2 text-sm">
                <option value="mensile">{t("governance.committees.frequencies.mensile")}</option>
                <option value="trimestrale">{t("governance.committees.frequencies.trimestrale")}</option>
                <option value="semestrale">{t("governance.committees.frequencies.semestrale")}</option>
              </select>
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("governance.committees.fields.next_meeting")}</label>
            <input type="datetime-local" name="next_meeting_at" onChange={handleChange}
              className="w-full border rounded px-3 py-2 text-sm" />
          </div>
        </div>
        {error && <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded mt-3">{error}</p>}
        <div className="flex justify-end gap-2 mt-4">
          <button onClick={onClose} className="px-4 py-2 border rounded text-sm text-gray-600 hover:bg-gray-50">{t("actions.cancel")}</button>
          <button
            onClick={() => mutation.mutate(form)}
            disabled={mutation.isPending || !form.name}
            className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700 disabled:opacity-50"
          >
            {mutation.isPending ? t("common.saving") : t("governance.committees.new.submit")}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export function GovernancePage() {
  const { t, i18n } = useTranslation();
  const [searchParams, setSearchParams] = useSearchParams();
  const tabParam = searchParams.get("tab");
  const initialTab =
    tabParam === "workflow"
      ? "workflow"
      : tabParam === "frameworks"
      ? "frameworks"
      : tabParam === "risk-appetite"
      ? "risk-appetite"
      : "roles";
  const [tab, setTab] = useState<"roles" | "workflow" | "frameworks" | "risk-appetite">(initialTab);

  useEffect(() => {
    const tabParam = searchParams.get("tab");
    const next =
      tabParam === "workflow"
        ? "workflow"
        : tabParam === "frameworks"
        ? "frameworks"
        : tabParam === "risk-appetite"
        ? "risk-appetite"
        : "roles";
    setTab(next);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams]);

  const [showRoleModal, setShowRoleModal]         = useState(false);
  const [showCommitteeModal, setShowCommitteeModal] = useState(false);
  const [terminaTarget, setTerminaTarget]         = useState<RoleAssignment | null>(null);
  const [sostituisciTarget, setSostituisciTarget] = useState<RoleAssignment | null>(null);
  const [toast, setToast]                         = useState<string | null>(null);

  const { data: assignments, isLoading: loadingAssign } = useQuery({
    queryKey: ["role-assignments"],
    queryFn: () => governanceApi.roleAssignments(),
    retry: false,
  });

  const { data: committees, isLoading: loadingComm } = useQuery({
    queryKey: ["committees"],
    queryFn: () => governanceApi.committees(),
    retry: false,
  });

  const { data: users } = useQuery({
    queryKey: ["users"],
    queryFn: () => usersApi.list(),
    retry: false,
  });

  const { data: vacanti } = useQuery({
    queryKey: ["governance-vacanti"],
    queryFn: () => governanceApi.vacanti(),
    retry: false,
  });

  const { data: inScadenza } = useQuery({
    queryKey: ["governance-in-scadenza"],
    queryFn: () => governanceApi.inScadenza(30),
    retry: false,
  });

  const userList = (users ?? []).map(u => ({
    id:    u.id,
    email: u.email,
    name:  `${u.first_name} ${u.last_name}`.trim() || u.username || u.email,
  }));

  function roleLabel(role: string) {
    const key = ROLE_KEYS[role] ?? role;
    return t(`governance.roles.${key}`, { defaultValue: role });
  }

  function formatDate(dateStr: string) {
    return new Date(dateStr).toLocaleDateString(i18n.language);
  }

  function showToast(msg: string) {
    setToast(msg);
    setTimeout(() => setToast(null), 4000);
  }

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">{t("governance.title")}</h2>
          <p className="text-sm text-gray-500 mt-1">{t("governance.subtitle")}</p>
        </div>
        <ModuleHelp
          title={t("governance.help.title")}
          description={t("governance.help.description")}
          steps={[
            t("governance.help.steps.assign_role"),
            t("governance.help.steps.replace_role"),
            t("governance.help.steps.terminate_role"),
            t("governance.help.steps.vacant_roles_alert"),
            t("governance.help.steps.link_nomination_doc"),
          ]}
          connections={[
            { module: "M02 RBAC",              relation: t("governance.help.connections.rbac") },
            { module: "M13 Management Review", relation: t("governance.help.connections.management_review") },
          ]}
          configNeeded={[t("governance.help.config.create_users_m02")]}
        />
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex gap-6">
          <button
            type="button"
            onClick={() => {
              setTab("roles");
              setSearchParams((prev) => {
                const next = new URLSearchParams(prev);
                next.delete("tab");
                return next;
              });
            }}
            className={
              tab === "roles"
                ? "border-primary-600 text-primary-700 whitespace-nowrap py-2 px-1 border-b-2 font-medium text-sm"
                : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 whitespace-nowrap py-2 px-1 border-b-2 font-medium text-sm"
            }
          >
            {t("governance.tabs.roles")}
          </button>
          <button
            type="button"
            onClick={() => {
              setTab("workflow");
              setSearchParams((prev) => {
                const next = new URLSearchParams(prev);
                next.set("tab", "workflow");
                return next;
              });
            }}
            className={
              tab === "workflow"
                ? "border-primary-600 text-primary-700 whitespace-nowrap py-2 px-1 border-b-2 font-medium text-sm"
                : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 whitespace-nowrap py-2 px-1 border-b-2 font-medium text-sm"
            }
          >
            {t("governance.tabs.workflow")}
          </button>
          <button
            type="button"
            onClick={() => {
              setTab("frameworks");
              setSearchParams((prev) => {
                const next = new URLSearchParams(prev);
                next.set("tab", "frameworks");
                return next;
              });
            }}
            className={
              tab === "frameworks"
                ? "border-primary-600 text-primary-700 whitespace-nowrap py-2 px-1 border-b-2 font-medium text-sm"
                : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 whitespace-nowrap py-2 px-1 border-b-2 font-medium text-sm"
            }
          >
            {t("governance.tabs.frameworks")}
          </button>
          <button
            type="button"
            onClick={() => {
              setTab("risk-appetite");
              setSearchParams((prev) => {
                const next = new URLSearchParams(prev);
                next.set("tab", "risk-appetite");
                return next;
              });
            }}
            className={
              tab === "risk-appetite"
                ? "border-primary-600 text-primary-700 whitespace-nowrap py-2 px-1 border-b-2 font-medium text-sm"
                : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 whitespace-nowrap py-2 px-1 border-b-2 font-medium text-sm"
            }
          >
            {t("governance.tabs.risk_appetite", { defaultValue: "Risk Appetite" })}
          </button>
        </nav>
      </div>

      {tab === "frameworks" ? (
        <FrameworkGovernanceTab />
      ) : tab === "workflow" ? (
        <div className="space-y-4">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h3 className="text-lg font-semibold text-gray-900">{t("governance.workflow.title")}</h3>
              <p className="text-sm text-gray-500 mt-1">
                {t("governance.workflow.subtitle")}
              </p>
            </div>
            <ModuleHelp
                title={t("governance.workflow.help.title")}
                description={t("governance.workflow.help.description")}
                steps={[
                  t("governance.workflow.help.steps.choose_type_and_scope"),
                  t("governance.workflow.help.steps.assign_creators"),
                  t("governance.workflow.help.steps.assign_reviewers"),
                  t("governance.workflow.help.steps.assign_approvers"),
                ]}
                connections={[
                  { module: "M07 Documenti", relation: t("governance.workflow.help.connections.documents") },
                  { module: "M00 Governance", relation: t("governance.workflow.help.connections.governance") },
                ]}
            />
          </div>
          <DocumentWorkflowSection embedded />
        </div>
      ) : tab === "risk-appetite" ? (
        <RiskAppetiteGovernanceTab />
      ) : (
        <>
          {/* Alert: ruoli vacanti */}
          {(vacanti?.count ?? 0) > 0 && (
            <div className="border border-red-300 bg-red-50 rounded-lg p-4">
              <p className="font-semibold text-red-700">
                {t("governance.alerts.vacant_roles", { count: vacanti!.count })}
              </p>
              <ul className="mt-2 text-sm text-red-600 space-y-0.5">
                {vacanti!.vacant_roles.map((r) => (
                  <li key={r}>• {roleLabel(r)}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Alert: ruoli in scadenza */}
          {(inScadenza?.expiring?.length ?? 0) > 0 && (
            <div className="border border-amber-300 bg-amber-50 rounded-lg p-4">
              <p className="font-semibold text-amber-700">
                {t("governance.alerts.expiring_roles", { count: inScadenza!.expiring.length })}
              </p>
              <ul className="mt-2 text-sm text-amber-600 space-y-0.5">
                {inScadenza!.expiring.map((r) => (
                  <li key={r.id}>
                    • {roleLabel(r.role)} — {r.user} ({t("governance.expires_on", { date: formatDate(r.valid_until) })})
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Ruoli normativi */}
            <div className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold text-gray-700">{t("governance.sections.roles")}</h3>
            <button
              onClick={() => setShowRoleModal(true)}
              className="text-xs px-2 py-1 bg-primary-600 text-white rounded hover:bg-primary-700"
            >
              {t("governance.roles_assign.open")}
            </button>
          </div>

          {loadingAssign ? (
            <p className="text-sm text-gray-400">{t("common.loading")}</p>
          ) : !assignments?.length ? (
            <p className="text-sm text-gray-400 italic">{t("governance.empty.roles")}</p>
          ) : (
            <div className="space-y-1">
              {assignments.map((a) => (
                <div key={a.id} className="flex items-start justify-between py-2 border-b border-gray-50 last:border-0 gap-2">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-medium text-gray-800 text-sm">
                        {roleLabel(a.role)}
                      </span>
                      {roleBadge(a, t)}
                      {scopeBadge(a)}
                    </div>
                    <div className="text-xs text-gray-500 mt-0.5">
                      {a.user_name ?? a.user_email ?? String(a.user)}
                      {a.valid_until && (
                        <span className="ml-2 text-gray-400">
                          {t("governance.valid_until", { date: formatDate(a.valid_until) })}
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="flex gap-1 flex-shrink-0 mt-0.5">
                    <button
                      onClick={() => setSostituisciTarget(a)}
                      className="text-xs px-2 py-1 bg-blue-50 text-blue-700 rounded hover:bg-blue-100 border border-blue-200"
                    >
                      {t("governance.actions.replace")}
                    </button>
                    <button
                      onClick={() => setTerminaTarget(a)}
                      className="text-xs px-2 py-1 bg-orange-50 text-orange-700 rounded hover:bg-orange-100 border border-orange-200"
                    >
                      {t("governance.actions.terminate")}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Comitati */}
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold text-gray-700">{t("governance.sections.committees")}</h3>
            <button
              onClick={() => setShowCommitteeModal(true)}
              className="text-xs px-2 py-1 bg-primary-600 text-white rounded hover:bg-primary-700"
            >
              {t("governance.committees.new.open")}
            </button>
          </div>
          {loadingComm ? (
            <p className="text-sm text-gray-400">{t("common.loading")}</p>
          ) : !committees?.length ? (
            <p className="text-sm text-gray-400 italic">{t("governance.empty.committees")}</p>
          ) : (
            <div className="space-y-3">
              {committees.map((c) => (
                <div key={c.id} className="border border-gray-100 rounded p-3">
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-gray-800 text-sm">{c.name}</span>
                    <span className="text-xs bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded">
                      {c.committee_type}
                    </span>
                  </div>
                  <div className="text-xs text-gray-500 mt-1">
                    {t("governance.committees.frequency", { value: c.frequency })}
                    {c.next_meeting_at && (
                      <> — {t("governance.committees.next_meeting")}{" "}
                        <span className="font-medium">
                          {new Date(c.next_meeting_at).toLocaleDateString(i18n.language)}
                        </span>
                      </>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
            </div>
          </div>

          {/* Modali */}
          {showRoleModal && (
            <RoleAssignmentModal users={userList} onClose={() => setShowRoleModal(false)} />
          )}
          {showCommitteeModal && (
            <CommitteeModal onClose={() => setShowCommitteeModal(false)} />
          )}
          {terminaTarget && (
            <TerminaModal
              assignment={terminaTarget}
              onClose={() => setTerminaTarget(null)}
              onSuccess={showToast}
            />
          )}
          {sostituisciTarget && (
            <SostituisciModal
              assignment={sostituisciTarget}
              users={userList}
              onClose={() => setSostituisciTarget(null)}
              onSuccess={showToast}
            />
          )}

          {toast && <Toast msg={toast} onClose={() => setToast(null)} />}
        </>
      )}
    </div>
  );
}
