import { Fragment, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "../../api/client";
import { usersApi, type GrcUser, type GrcRole } from "../../api/endpoints/users";
import { useAuthStore } from "../../store/auth";
import { useTranslation } from "react-i18next";

interface CompetencyGap {
  competency: string; role: string; required_level: number;
  current_level: number; gap: number; evidence_type: string;
}
interface CompetencyWarning { competency: string; expired_on: string; message: string; }
interface GapAnalysisResult {
  user_id: string; user_name: string; roles: string[];
  gaps: CompetencyGap[]; ok: string[]; warnings: CompetencyWarning[];
  gap_count: number;
}

function CompetencyPanel({ userId }: { userId: number }) {
  const { t } = useTranslation();
  const { data, isLoading } = useQuery({
    queryKey: ["competency-gap", userId],
    queryFn: () =>
      apiClient.get<GapAnalysisResult>(`/auth/user-competencies/gap-analysis/?user=${userId}`)
        .then(r => r.data),
    retry: false,
  });

  if (isLoading) return <p className="text-xs text-gray-400 p-4">{t("users.competency_gap.loading")}</p>;
  if (!data) return null;

  return (
    <div className="px-6 py-4 bg-gray-50 border-t border-gray-200 text-sm">
      <div className="flex items-center gap-3 mb-3">
        <h4 className="font-semibold text-gray-700">
          {t("users.competency_gap.title", { name: data.user_name })}
        </h4>
        {data.gap_count > 0 && (
          <span className="px-2 py-0.5 bg-red-100 text-red-700 text-xs rounded">
            {t("users.competency_gap.gap_count", { count: data.gap_count })}
          </span>
        )}
        {data.ok.length > 0 && !data.gap_count && (
          <span className="px-2 py-0.5 bg-green-100 text-green-700 text-xs rounded">
            {t("users.competency_gap.complete")}
          </span>
        )}
      </div>

      {data.gaps.length > 0 && (
        <div className="mb-3">
          <p className="text-xs font-medium text-red-600 mb-1">{t("users.competency_gap.to_fill")}</p>
          <div className="space-y-1">
            {data.gaps.map((g, i) => (
              <div key={i} className="flex items-center gap-2 bg-red-50 rounded px-3 py-1.5 text-xs">
                <span className="font-medium text-red-700">{g.competency}</span>
                <span className="text-gray-500">({g.role})</span>
                <span className="ml-auto text-red-600">
                  {t("users.competency_gap.level_from_to", { current: g.current_level, required: g.required_level })}
                </span>
                <span className="text-gray-400 capitalize">{g.evidence_type}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {data.warnings.length > 0 && (
        <div className="mb-3">
          <p className="text-xs font-medium text-orange-600 mb-1">{t("users.competency_gap.expired")}</p>
          <div className="space-y-1">
            {data.warnings.map((w, i) => (
              <div key={i} className="flex items-center gap-2 bg-orange-50 rounded px-3 py-1.5 text-xs">
                <span className="text-orange-700">{w.message}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {data.ok.length > 0 && (
        <div>
          <p className="text-xs font-medium text-green-600 mb-1">{t("users.competency_gap.ok")}</p>
          <div className="flex flex-wrap gap-1">
            {data.ok.map((c, i) => (
              <span key={i} className="bg-green-50 text-green-700 text-xs px-2 py-0.5 rounded">{c}</span>
            ))}
          </div>
        </div>
      )}

      {data.gaps.length === 0 && data.warnings.length === 0 && data.ok.length === 0 && (
        <p className="text-xs text-gray-400">{t("users.competency_gap.none")}</p>
      )}
    </div>
  );
}

const roleColors: Record<string, string> = {
  super_admin: "bg-purple-100 text-purple-800",
  compliance_officer: "bg-blue-100 text-blue-800",
  risk_manager: "bg-orange-100 text-orange-800",
  plant_manager: "bg-teal-100 text-teal-800",
  control_owner: "bg-green-100 text-green-800",
  internal_auditor: "bg-yellow-100 text-yellow-800",
  external_auditor: "bg-gray-100 text-gray-600",
};

function RoleBadge({ role }: { role: string | null }) {
  if (!role) return <span className="text-gray-400 text-xs">—</span>;
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${roleColors[role] ?? "bg-gray-100 text-gray-600"}`}>
      {role.replace(/_/g, " ")}
    </span>
  );
}

function NewUserModal({ roles, onClose }: { roles: GrcRole[]; onClose: () => void }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [form, setForm] = useState({ username: "", email: "", first_name: "", last_name: "", password: "", grc_role: "" });

  const mutation = useMutation({
    mutationFn: usersApi.create,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["users"] }); onClose(); },
  });

  function handleChange(e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) {
    setForm(prev => ({ ...prev, [e.target.name]: e.target.value }));
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-lg p-6">
        <h3 className="text-lg font-semibold mb-4">{t("users.new.title")}</h3>
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("users.fields.username")} *</label>
              <input name="username" value={form.username} onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("users.fields.email")} *</label>
              <input name="email" type="email" value={form.email} onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("users.fields.first_name")}</label>
              <input name="first_name" value={form.first_name} onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("users.fields.last_name")}</label>
              <input name="last_name" value={form.last_name} onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("users.fields.password")} *</label>
            <input name="password" type="password" value={form.password} onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("users.fields.grc_role")}</label>
            <select name="grc_role" value={form.grc_role} onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm">
              <option value="">{t("users.fields.grc_role_none")}</option>
              {roles.map(r => <option key={r.value} value={r.value}>{r.label}</option>)}
            </select>
          </div>
        </div>
        {mutation.isError && <p className="text-sm text-red-600 mt-2">{t("common.save_error")}</p>}
        <div className="flex justify-end gap-2 mt-4">
          <button onClick={onClose} className="px-4 py-2 border rounded text-sm text-gray-600 hover:bg-gray-50">{t("actions.cancel")}</button>
          <button
            onClick={() => mutation.mutate({ username: form.username, email: form.email, first_name: form.first_name, last_name: form.last_name, password: form.password, grc_role: form.grc_role || undefined })}
            disabled={mutation.isPending}
            className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700 disabled:opacity-50"
          >
            {mutation.isPending ? t("common.saving") : t("users.new.submit")}
          </button>
        </div>
      </div>
    </div>
  );
}

function AssignRoleInline({ user, roles }: { user: GrcUser; roles: GrcRole[] }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [role, setRole] = useState(user.grc_role ?? "");

  const mutation = useMutation({
    mutationFn: ({ id, role }: { id: number; role: string }) => usersApi.assignRole(id, role),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["users"] }); setOpen(false); },
  });

  if (!open) {
    return (
      <button onClick={() => setOpen(true)} className="text-xs text-blue-600 hover:underline border border-blue-200 rounded px-2 py-0.5">
        {t("users.actions.assign_role")}
      </button>
    );
  }

  return (
    <div className="flex items-center gap-1">
      <select value={role} onChange={e => setRole(e.target.value)} className="border rounded px-2 py-0.5 text-xs">
        <option value="">{t("users.fields.grc_role_none")}</option>
        {roles.map(r => <option key={r.value} value={r.value}>{r.label}</option>)}
      </select>
      <button
        onClick={() => mutation.mutate({ id: user.id, role })}
        disabled={mutation.isPending}
        className="text-xs bg-primary-600 text-white rounded px-2 py-0.5 hover:bg-primary-700 disabled:opacity-50"
      >
        {t("actions.confirm")}
      </button>
      <button onClick={() => setOpen(false)} className="text-xs text-gray-500 hover:text-gray-700">✕</button>
    </div>
  );
}

function ResetPasswordModal({ user, onClose }: { user: GrcUser; onClose: () => void }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  const mutation = useMutation({
    mutationFn: () => usersApi.setPassword(user.id, password),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["users"] });
      onClose();
    },
    onError: () => {
      setError(t("common.save_error"));
    },
  });

  const disabled = password.length < 8 || mutation.isPending;

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-6">
        <h3 className="text-lg font-semibold mb-3">
          {t("users.actions.reset_password")} — {user.username}
        </h3>
        <p className="text-xs text-gray-500 mb-3">
          {t("users.actions.reset_password_hint")}
        </p>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          {t("users.fields.password")} (min 8)
        </label>
        <input
          type="password"
          value={password}
          onChange={e => setPassword(e.target.value)}
          className="w-full border rounded px-3 py-2 text-sm"
        />
        {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
        <div className="flex justify-end gap-2 mt-4">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 border rounded text-sm text-gray-600 hover:bg-gray-50"
          >
            {t("actions.cancel")}
          </button>
          <button
            type="button"
            disabled={disabled}
            onClick={() => mutation.mutate()}
            className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700 disabled:opacity-50"
          >
            {mutation.isPending ? t("common.saving") : t("users.actions.reset_password")}
          </button>
        </div>
      </div>
    </div>
  );
}

function DangerZone() {
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

export function UsersPage() {
  const { t } = useTranslation();
  const [showNew, setShowNew] = useState(false);
  const [expandedCompetency, setExpandedCompetency] = useState<number | null>(null);
  const [resetUser, setResetUser] = useState<GrcUser | null>(null);
  const qc = useQueryClient();

  const { data: me } = useQuery({
    queryKey: ["users-me"],
    queryFn: usersApi.me,
    retry: false,
  });

  const { data: users = [], isLoading } = useQuery({
    queryKey: ["users"],
    queryFn: usersApi.list,
    retry: false,
  });

  const { data: roles = [] } = useQuery({
    queryKey: ["users-roles"],
    queryFn: usersApi.listRoles,
    retry: false,
  });

  const toggleMutation = useMutation({
    mutationFn: (id: number) => usersApi.toggleActive(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["users"] }),
  });

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold text-gray-900">{t("users.title")}</h2>
        <button
          onClick={() => setShowNew(true)}
          className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700"
        >
          {t("users.new.open")}
        </button>
      </div>

      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-gray-400">{t("common.loading")}</div>
        ) : users.length === 0 ? (
          <div className="p-8 text-center text-gray-400">{t("users.empty")}</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("users.table.username")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("users.table.email")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("users.table.name")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("users.table.grc_role")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("users.table.active")}</th>
                <th className="px-4 py-3 font-medium text-gray-600">{t("users.table.actions")}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {users.map(user => (
                <Fragment key={user.id}>
                  <tr className="hover:bg-gray-50 transition-colors">
                    <td className="px-4 py-3 font-medium text-gray-800">{user.username}</td>
                    <td className="px-4 py-3 text-gray-600">{user.email}</td>
                    <td className="px-4 py-3 text-gray-600">
                      {[user.first_name, user.last_name].filter(Boolean).join(" ") || t("common.none")}
                    </td>
                    <td className="px-4 py-3"><RoleBadge role={user.grc_role} /></td>
                    <td className="px-4 py-3">
                      <span className={`inline-block w-2.5 h-2.5 rounded-full ${user.is_active ? "bg-green-500" : "bg-red-400"}`} />
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2 flex-wrap">
                        <AssignRoleInline user={user} roles={roles} />
                        <button
                          onClick={() => toggleMutation.mutate(user.id)}
                          disabled={toggleMutation.isPending}
                          className={`text-xs border rounded px-2 py-0.5 disabled:opacity-50 ${user.is_active ? "text-red-600 border-red-200 hover:bg-red-50" : "text-green-600 border-green-200 hover:bg-green-50"}`}
                        >
                          {user.is_active ? t("users.actions.deactivate") : t("users.actions.activate")}
                        </button>
                        <button
                          onClick={() => setExpandedCompetency(prev => prev === user.id ? null : user.id)}
                          className="text-xs border border-indigo-200 text-indigo-600 rounded px-2 py-0.5 hover:bg-indigo-50"
                        >
                          {t("users.actions.competency")}
                        </button>
                        {me?.grc_role === "super_admin" && !user.is_superuser && (
                          <button
                            type="button"
                            onClick={() => setResetUser(user)}
                            className="text-xs border border-gray-200 text-gray-700 rounded px-2 py-0.5 hover:bg-gray-50"
                          >
                            {t("users.actions.reset_password")}
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                  {expandedCompetency === user.id && (
                    <tr>
                      <td colSpan={6} className="p-0">
                        <CompetencyPanel userId={user.id} />
                      </td>
                    </tr>
                  )}
                </Fragment>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {showNew && <NewUserModal roles={roles} onClose={() => setShowNew(false)} />}

      {resetUser && <ResetPasswordModal user={resetUser} onClose={() => setResetUser(null)} />}

      {me?.is_superuser && <DangerZone />}
    </div>
  );
}
