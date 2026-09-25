import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { plantAccessApi, usersApi, GRC_ACCESS_ROLES, type GrcUser, type ResponsibilityGap } from "../../api/endpoints/users";
import { governanceApi, type RoleAssignment } from "../../api/endpoints/governance";
import { RoleAssignmentModal, SostituisciModal, TerminaModal } from "../governance/roleAssignmentModals";
import { todayISO } from "../../utils/dates";
import { CompetencyPanel } from "./CompetencyPanel";
import {
  Avatar, ROLE_ICON, ROLE_TONE, RoleCards, RolePermissionsPreview, ScopePicker, accessScopeText, displayName,
  emptyScope, relativeTime, respName, roleName, scopeReady, scopeToAccess, type ScopeValue,
} from "./shared";

type Tab = "profile" | "access" | "responsibilities" | "competencies" | "security";

const errText = (e: unknown, fallback: string) => {
  const data = (e as { response?: { data?: Record<string, unknown> } })?.response?.data;
  if (!data) return fallback;
  if (typeof data.detail === "string") return data.detail;
  const first = Object.values(data).flat().find(v => typeof v === "string");
  return (first as string) || fallback;
};

/** Scheda utente in un pannello laterale. `canManage` = super admin. */
export function UserDrawer({ user, users, canManage, isSelf, onClose }: {
  user: GrcUser; users: GrcUser[]; canManage: boolean; isSelf: boolean; onClose: () => void;
}) {
  const { t } = useTranslation();
  const [tab, setTab] = useState<Tab>("access");
  // "Dai accesso" da una responsabilità scoperta: editor accessi precompilato
  const [prefill, setPrefill] = useState<ResponsibilityGap | null>(null);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const tabs: Tab[] = ["access", "responsibilities", "profile", "competencies", "security"];
  const gaps = user.warnings ?? [];

  return (
    <div className="fixed inset-0 z-50 flex justify-end" role="dialog" aria-modal="true" aria-label={displayName(user)}>
      <div className="absolute inset-0 bg-black/30" onClick={onClose} />
      <aside className="relative h-full w-full max-w-2xl bg-white shadow-2xl flex flex-col">
        <header className="px-6 pt-5 pb-3 border-b border-gray-100">
          <div className="flex items-start gap-3">
            <Avatar user={user} size="lg" />
            <div className="flex-1 min-w-0">
              <h2 className="text-lg font-semibold text-gray-900 truncate">{displayName(user)}</h2>
              <p className="text-sm text-gray-500 truncate">{user.email} · {user.username}</p>
              <div className="flex flex-wrap gap-1.5 mt-1.5">
                <span className={`text-[11px] px-2 py-0.5 rounded-full ${user.is_active ? "bg-green-50 text-green-700" : "bg-gray-100 text-gray-500"}`}>
                  {user.is_active ? t("users.list.active") : t("users.list.inactive")}
                </span>
                {user.is_superuser && <span className="text-[11px] px-2 py-0.5 rounded-full bg-purple-50 text-purple-700">{t("users.list.superuser")}</span>}
                {gaps.length > 0 && (
                  <button type="button" onClick={() => setTab("responsibilities")}
                    className="text-[11px] px-2 py-0.5 rounded-full bg-amber-50 text-amber-800 hover:bg-amber-100">
                    ⚠ {t("users.list.gap_badge", { count: gaps.length })}
                  </button>
                )}
              </div>
            </div>
            <button onClick={onClose} aria-label={t("users.drawer.close")} className="text-gray-400 hover:text-gray-700 text-2xl leading-none">×</button>
          </div>
          <nav className="flex gap-1 mt-4 -mb-3 overflow-x-auto">
            {tabs.map(k => (
              <button key={k} type="button" onClick={() => setTab(k)}
                className={`px-3 py-2 text-sm whitespace-nowrap border-b-2 ${tab === k ? "border-primary-600 text-primary-700 font-medium" : "border-transparent text-gray-500 hover:text-gray-700"}`}>
                {t(`users.drawer.tabs.${k}`)}
                {k === "access" && (user.accesses?.length ?? 0) > 0 && <span className="ml-1 text-xs text-gray-400">{user.accesses!.length}</span>}
                {k === "responsibilities" && (user.responsibilities?.length ?? 0) > 0 && <span className="ml-1 text-xs text-gray-400">{user.responsibilities!.length}</span>}
              </button>
            ))}
          </nav>
        </header>
        <div className="flex-1 overflow-y-auto px-6 py-5">
          {tab === "access" && <AccessTab user={user} canManage={canManage} prefill={prefill} clearPrefill={() => setPrefill(null)} />}
          {tab === "responsibilities" && (
            <ResponsibilitiesTab user={user} users={users} canManage={canManage}
              onGiveAccess={g => { setPrefill(g); setTab("access"); }} />
          )}
          {tab === "profile" && <ProfileTab user={user} canManage={canManage} isSelf={isSelf} onDone={onClose} />}
          {tab === "competencies" && <CompetencyPanel userId={user.id} />}
          {tab === "security" && <SecurityTab user={user} canManage={canManage} />}
        </div>
      </aside>
    </div>
  );
}

// ── Accessi ──────────────────────────────────────────────────────────────────

function AccessTab({ user, canManage, prefill, clearPrefill }: {
  user: GrcUser; canManage: boolean; prefill: ResponsibilityGap | null; clearPrefill: () => void;
}) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [adding, setAdding] = useState(false);
  const [role, setRole] = useState<string>("");
  const [scope, setScope] = useState<ScopeValue>(emptyScope);
  const [confirmRevoke, setConfirmRevoke] = useState("");
  const [error, setError] = useState("");

  // Precompilazione dalla responsabilità scoperta (ruolo se coincide con un accesso)
  useEffect(() => {
    if (!prefill) return;
    setAdding(true);
    setRole((GRC_ACCESS_ROLES as readonly string[]).includes(prefill.role) ? prefill.role : "");
    setScope(prefill.scope_type === "org" ? { ...emptyScope, kind: "org" }
      : prefill.scope_type === "bu" ? { ...emptyScope, kind: "bu", bu: prefill.scope_id ?? "" }
        : { ...emptyScope, kind: "sites", sites: prefill.scope_id ? [prefill.scope_id] : [] });
    clearPrefill();
  }, [prefill, clearPrefill]);

  const refresh = () => { qc.invalidateQueries({ queryKey: ["users"] }); qc.invalidateQueries({ queryKey: ["plant-access"] }); };
  const add = useMutation({
    mutationFn: () => plantAccessApi.create({ user: user.id, role, ...scopeToAccess(scope) }),
    onSuccess: () => { setAdding(false); setRole(""); setScope(emptyScope); setError(""); refresh(); },
    onError: e => setError(errText(e, t("common.error"))),
  });
  const revoke = useMutation({
    mutationFn: (id: string) => plantAccessApi.remove(id),
    onSuccess: () => { setConfirmRevoke(""); refresh(); },
  });

  const accesses = user.accesses ?? [];
  return (
    <div className="space-y-4">
      <p className="text-sm text-gray-500">{t("users.drawer.access_intro")}</p>
      {user.is_superuser && <p className="text-sm text-purple-800 bg-purple-50 rounded-lg px-3 py-2">{t("users.drawer.superuser_note")}</p>}
      {accesses.length === 0 && !user.is_superuser && (
        <div className="rounded-xl border border-dashed border-gray-300 px-4 py-6 text-center text-sm text-gray-500">{t("users.drawer.access_empty")}</div>
      )}
      <div className="space-y-2">
        {accesses.map(a => (
          <div key={a.id} className="rounded-xl border border-gray-200 px-4 py-3">
            <div className="flex items-start gap-3">
              <span className={`w-9 h-9 rounded-lg border flex items-center justify-center ${ROLE_TONE[a.role] ?? ""}`} aria-hidden>{ROLE_ICON[a.role]}</span>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-900">{roleName(t, a.role)}</p>
                <p className="text-xs text-gray-500">📍 {accessScopeText(t, a)}</p>
              </div>
              {canManage && (confirmRevoke === a.id ? (
                <span className="flex items-center gap-2 text-xs">
                  <button onClick={() => revoke.mutate(a.id)} disabled={revoke.isPending}
                    className="px-2 py-1 rounded bg-red-600 text-white disabled:opacity-50">{t("users.drawer.revoke_confirm")}</button>
                  <button onClick={() => setConfirmRevoke("")} className="text-gray-500">{t("actions.cancel")}</button>
                </span>
              ) : (
                <button onClick={() => setConfirmRevoke(a.id)} className="text-xs text-gray-500 hover:text-red-600">{t("users.drawer.revoke")}</button>
              ))}
            </div>
            <details className="mt-2 group">
              <summary className="text-xs text-primary-700 cursor-pointer select-none">{t("users.drawer.what_can_do")}</summary>
              <div className="mt-2"><RolePermissionsPreview role={a.role} compact /></div>
            </details>
          </div>
        ))}
      </div>

      {canManage && !adding && (
        <button onClick={() => setAdding(true)}
          className="w-full rounded-xl border-2 border-dashed border-gray-200 py-3 text-sm text-gray-600 hover:border-primary-300 hover:text-primary-700">
          + {t("users.drawer.add_access")}
        </button>
      )}
      {canManage && adding && (
        <div className="rounded-xl border border-primary-200 bg-white p-4 space-y-4 shadow-sm">
          <div>
            <p className="text-sm font-medium text-gray-800 mb-2">1 · {t("users.editor.step_role")}</p>
            <RoleCards value={role} onChange={setRole} />
          </div>
          <div>
            <p className="text-sm font-medium text-gray-800 mb-2">2 · {t("users.editor.step_scope")}</p>
            <ScopePicker value={scope} onChange={setScope} />
          </div>
          {role && (
            <div>
              <p className="text-sm font-medium text-gray-800 mb-2">{t("users.editor.preview_title", { name: displayName(user) })}</p>
              <RolePermissionsPreview role={role} />
            </div>
          )}
          {error && <p className="text-sm text-red-600">{error}</p>}
          <div className="flex justify-end gap-2">
            <button onClick={() => { setAdding(false); setError(""); }} className="px-3 py-1.5 text-sm border rounded-lg text-gray-600">{t("actions.cancel")}</button>
            <button onClick={() => add.mutate()} disabled={!role || !scopeReady(scope) || add.isPending}
              className="px-3 py-1.5 text-sm rounded-lg bg-primary-600 text-white disabled:opacity-50">{t("users.editor.save")}</button>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Responsabilità (stesso flusso di Governance) ─────────────────────────────

function ResponsibilitiesTab({ user, users, canManage, onGiveAccess }: {
  user: GrcUser; users: GrcUser[]; canManage: boolean; onGiveAccess: (g: ResponsibilityGap) => void;
}) {
  const { t } = useTranslation();
  const [adding, setAdding] = useState(false);
  const [terminate, setTerminate] = useState<RoleAssignment | null>(null);
  const [replace, setReplace] = useState<RoleAssignment | null>(null);
  const { data: all = [] } = useQuery({
    queryKey: ["role-assignments", "user", user.id],
    queryFn: () => governanceApi.roleAssignments({ user: String(user.id) }),
  });
  const active = all.filter(r => r.is_active);
  const gaps = new Map((user.warnings ?? []).map(g => [g.responsibility, g]));
  const people = users.filter(u => u.is_active).map(u => ({ id: u.id, email: u.email, name: displayName(u) }));
  const scopeText = (r: RoleAssignment) =>
    r.scope_type === "org" ? t("users.scope.org") : r.scope_code ?? "—";

  return (
    <div className="space-y-4">
      <p className="text-sm text-gray-500">{t("users.drawer.resp_intro")}</p>
      {active.length === 0 && (
        <div className="rounded-xl border border-dashed border-gray-300 px-4 py-6 text-center text-sm text-gray-500">{t("users.drawer.resp_empty")}</div>
      )}
      <div className="space-y-2">
        {active.map(r => {
          const gap = gaps.get(r.id);
          return (
            <div key={r.id} className="rounded-xl border border-gray-200 px-4 py-3">
              <div className="flex items-start gap-3">
                <span className="w-9 h-9 rounded-lg border border-indigo-200 bg-indigo-50 flex items-center justify-center" aria-hidden>🛡</span>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900">{respName(t, r.role)}</p>
                  <p className="text-xs text-gray-500">
                    📍 {scopeText(r)} · {t("users.drawer.resp_since", { date: r.valid_from })}
                    {r.valid_until ? ` · ${t("users.drawer.resp_until", { date: r.valid_until })}` : ""}
                  </p>
                </div>
                {canManage && (
                  <span className="flex gap-3 text-xs">
                    <button onClick={() => setReplace(r)} className="text-gray-500 hover:text-primary-700">{t("users.drawer.resp_replace")}</button>
                    <button onClick={() => setTerminate(r)} className="text-gray-500 hover:text-red-600">{t("users.drawer.resp_terminate")}</button>
                  </span>
                )}
              </div>
              {gap && (
                <div className="mt-2 flex items-center justify-between gap-2 rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-900">
                  <span>⚠ {t("users.drawer.resp_no_access")}</span>
                  {canManage && (
                    <button onClick={() => onGiveAccess(gap)} className="shrink-0 px-2 py-1 rounded bg-amber-600 text-white hover:bg-amber-700">
                      {t("users.drawer.give_access")}
                    </button>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
      {canManage && (
        <button onClick={() => setAdding(true)}
          className="w-full rounded-xl border-2 border-dashed border-gray-200 py-3 text-sm text-gray-600 hover:border-indigo-300 hover:text-indigo-700">
          + {t("users.drawer.resp_add")}
        </button>
      )}
      {adding && (
        <RoleAssignmentModal users={people} lockUser onClose={() => setAdding(false)}
          initial={{ user: user.id, scope_type: "plant", valid_from: todayISO() }} />
      )}
      {terminate && <TerminaModal assignment={terminate} onClose={() => setTerminate(null)} onSuccess={() => {}} />}
      {replace && <SostituisciModal assignment={replace} users={people} onClose={() => setReplace(null)} onSuccess={() => {}} />}
    </div>
  );
}

// ── Profilo ──────────────────────────────────────────────────────────────────

function ProfileTab({ user, canManage, isSelf, onDone }: { user: GrcUser; canManage: boolean; isSelf: boolean; onDone: () => void }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [form, setForm] = useState({ email: user.email, first_name: user.first_name, last_name: user.last_name });
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");
  const [confirmDelete, setConfirmDelete] = useState(false);
  const dirty = form.email !== user.email || form.first_name !== user.first_name || form.last_name !== user.last_name;

  const save = useMutation({
    mutationFn: () => usersApi.update(user.id, form),
    onSuccess: () => { setSaved(true); setError(""); qc.invalidateQueries({ queryKey: ["users"] }); },
    onError: e => setError(errText(e, t("common.save_error"))),
  });
  const toggle = useMutation({
    mutationFn: () => usersApi.toggleActive(user.id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["users"] }),
  });
  const remove = useMutation({
    mutationFn: () => usersApi.remove(user.id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["users"] }); onDone(); },
    onError: e => setError(errText(e, t("common.error"))),
  });

  const field = (name: keyof typeof form, label: string, type = "text") => (
    <label className="block">
      <span className="block text-xs font-medium text-gray-600 mb-1">{label}</span>
      <input type={type} value={form[name]} disabled={!canManage}
        onChange={e => { setSaved(false); setForm(p => ({ ...p, [name]: e.target.value })); }}
        className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm disabled:bg-gray-50" />
    </label>
  );

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-3">
        {field("first_name", t("users.fields.first_name"))}
        {field("last_name", t("users.fields.last_name"))}
        <div className="col-span-2">{field("email", t("users.fields.email"), "email")}</div>
        <label className="col-span-2 block">
          <span className="block text-xs font-medium text-gray-600 mb-1">{t("users.fields.username")}</span>
          <input value={user.username} disabled className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm bg-gray-50 text-gray-500" />
        </label>
      </div>
      {canManage && (
        <div className="flex items-center gap-3">
          <button onClick={() => save.mutate()} disabled={!dirty || save.isPending}
            className="px-3 py-1.5 text-sm rounded-lg bg-primary-600 text-white disabled:opacity-50">{t("actions.save")}</button>
          {saved && <span className="text-xs text-green-700">✓ {t("users.drawer.saved")}</span>}
        </div>
      )}
      {error && <p className="text-sm text-red-600">{error}</p>}

      {canManage && !isSelf && !user.is_superuser && (
        <div className="rounded-xl border border-gray-200 divide-y">
          <div className="flex items-center justify-between gap-3 px-4 py-3">
            <div>
              <p className="text-sm font-medium text-gray-800">{user.is_active ? t("users.drawer.deactivate_title") : t("users.drawer.activate_title")}</p>
              <p className="text-xs text-gray-500">{user.is_active ? t("users.drawer.deactivate_hint") : t("users.drawer.activate_hint")}</p>
            </div>
            <button onClick={() => toggle.mutate()} disabled={toggle.isPending}
              className="px-3 py-1.5 text-sm rounded-lg border border-gray-300 text-gray-700 hover:bg-gray-50 disabled:opacity-50">
              {user.is_active ? t("users.actions.deactivate") : t("users.actions.activate")}
            </button>
          </div>
          <div className="flex items-center justify-between gap-3 px-4 py-3">
            <div>
              <p className="text-sm font-medium text-red-700">{t("users.actions.delete")}</p>
              <p className="text-xs text-gray-500">{t("users.drawer.delete_hint")}</p>
            </div>
            {confirmDelete ? (
              <span className="flex items-center gap-2 text-sm">
                <button onClick={() => remove.mutate()} disabled={remove.isPending}
                  className="px-3 py-1.5 rounded-lg bg-red-600 text-white disabled:opacity-50">{t("users.drawer.delete_confirm")}</button>
                <button onClick={() => setConfirmDelete(false)} className="text-gray-500">{t("actions.cancel")}</button>
              </span>
            ) : (
              <button onClick={() => setConfirmDelete(true)} className="px-3 py-1.5 text-sm rounded-lg border border-red-200 text-red-700 hover:bg-red-50">
                {t("users.actions.delete")}
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Sicurezza ────────────────────────────────────────────────────────────────

function SecurityTab({ user, canManage }: { user: GrcUser; canManage: boolean }) {
  const { t, i18n } = useTranslation();
  const [password, setPassword] = useState("");
  const [done, setDone] = useState(false);
  const [error, setError] = useState("");
  const reset = useMutation({
    mutationFn: () => usersApi.setPassword(user.id, password),
    onSuccess: () => { setDone(true); setPassword(""); setError(""); },
    onError: e => setError(errText(e, t("common.save_error"))),
  });
  const row = (label: string, value: React.ReactNode) => (
    <div className="flex items-center justify-between px-4 py-3 text-sm">
      <span className="text-gray-500">{label}</span><span className="text-gray-900">{value}</span>
    </div>
  );
  return (
    <div className="space-y-6">
      <div className="rounded-xl border border-gray-200 divide-y">
        {row(t("users.drawer.last_login"), relativeTime(user.last_login, i18n.language) ?? t("users.list.never_logged"))}
        {row(t("users.drawer.joined"), new Date(user.date_joined).toLocaleDateString(i18n.language))}
        {row(t("users.drawer.mfa"), user.mfa_enabled
          ? <span className="text-green-700">✓ {t("users.list.mfa_on")}</span>
          : <span className="text-amber-700">{t("users.list.mfa_off")}</span>)}
      </div>
      {!user.mfa_enabled && <p className="text-xs text-gray-500">{t("users.drawer.mfa_hint")}</p>}
      {canManage && !user.is_superuser && (
        <div className="rounded-xl border border-gray-200 p-4 space-y-2">
          <p className="text-sm font-medium text-gray-800">{t("users.actions.reset_password")}</p>
          <input type="password" value={password} onChange={e => { setDone(false); setPassword(e.target.value); }}
            aria-label={t("users.fields.password")} placeholder={t("users.fields.password_hint")}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
          {error && <p className="text-sm text-red-600">{error}</p>}
          <div className="flex items-center gap-3">
            <button onClick={() => reset.mutate()} disabled={password.length < 12 || reset.isPending}
              className="px-3 py-1.5 text-sm rounded-lg bg-primary-600 text-white disabled:opacity-50">{t("users.actions.reset_password")}</button>
            {done && <span className="text-xs text-green-700">✓ {t("users.drawer.password_done")}</span>}
          </div>
        </div>
      )}
    </div>
  );
}
