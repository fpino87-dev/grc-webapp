import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { usersApi, GRC_ACCESS_ROLES } from "../../api/endpoints/users";
import { plantsApi } from "../../api/endpoints/plants";
import { NewUserWizard } from "./NewUserWizard";
import { RolesCatalog } from "./RolesCatalog";
import { UserDrawer } from "./UserDrawer";
import { Avatar, ROLE_ICON, ROLE_TONE, accessScopeText, displayName, relativeTime, respName, roleName } from "./shared";

type Status = "active" | "inactive" | "all";

export function UsersPage() {
  const { t, i18n } = useTranslation();
  const [view, setView] = useState<"users" | "roles">("users");
  const [status, setStatus] = useState<Status>("active");
  const [search, setSearch] = useState("");
  const [site, setSite] = useState("");
  const [role, setRole] = useState("");
  const [openId, setOpenId] = useState<number | null>(null);
  const [showNew, setShowNew] = useState(false);

  const { data: me } = useQuery({ queryKey: ["users-me"], queryFn: usersApi.me, retry: false });
  const { data: users = [], isLoading } = useQuery({
    queryKey: ["users", "admin", status],
    queryFn: () => usersApi.listForAdmin(status),
    retry: false,
  });
  // per il catalogo ruoli e la sostituzione delle responsabilità servono gli attivi
  const { data: activeUsers = [] } = useQuery({
    queryKey: ["users", "admin", "active"],
    queryFn: () => usersApi.listForAdmin("active"),
    retry: false,
  });
  const { data: plants = [] } = useQuery({ queryKey: ["plants"], queryFn: () => plantsApi.list() });
  const { data: bus = [] } = useQuery({ queryKey: ["business-units"], queryFn: () => plantsApi.businessUnits() });
  const canManage = me?.grc_role === "super_admin" || !!me?.is_superuser;

  const sitePlant = plants.find(p => p.id === site);
  const siteCode = sitePlant?.code;
  const siteBuCode = bus.find(b => b.id === sitePlant?.bu)?.code;
  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return users.filter(u => {
      if (q && ![u.username, u.email, u.first_name, u.last_name].join(" ").toLowerCase().includes(q)) return false;
      const acc = u.accesses ?? [];
      if (role && !acc.some(a => a.role === role)) return false;
      if (siteCode && !u.is_superuser && !acc.some(a => a.scope_type === "org" || a.scope_plant_codes.includes(siteCode)
        || (a.scope_type === "bu" && !!siteBuCode && a.scope_bu_code === siteBuCode))) return false;
      return true;
    });
  }, [users, search, role, siteCode, siteBuCode]);
  const opened = users.find(u => u.id === openId) ?? activeUsers.find(u => u.id === openId) ?? null;
  const gapsTotal = users.reduce((n, u) => n + (u.warnings?.length ?? 0), 0);

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="text-xl font-semibold text-gray-900">{t("users.page_title")}</h2>
          <p className="text-sm text-gray-500">{t("users.page_subtitle")}</p>
        </div>
        <div className="flex items-center gap-2">
          <Link to="/reporting?tab=access_matrix" className="text-sm text-gray-600 hover:text-primary-700 px-3 py-2">
            {t("users.access_review_link")} →
          </Link>
          {canManage && (
            <button onClick={() => setShowNew(true)} className="px-4 py-2 rounded-lg bg-primary-600 text-white text-sm hover:bg-primary-700 shadow-sm">
              + {t("users.wizard.open")}
            </button>
          )}
        </div>
      </div>

      <nav className="flex gap-1 border-b border-gray-200">
        {(["users", "roles"] as const).map(v => (
          <button key={v} onClick={() => setView(v)}
            className={`px-4 py-2 text-sm border-b-2 -mb-px ${view === v ? "border-primary-600 text-primary-700 font-medium" : "border-transparent text-gray-500 hover:text-gray-700"}`}>
            {t(`users.tabs.${v}`)}
          </button>
        ))}
      </nav>

      {view === "roles" ? <RolesCatalog users={activeUsers} /> : (
        <>
          <div className="flex flex-wrap items-center gap-2">
            <input type="search" value={search} onChange={e => setSearch(e.target.value)}
              placeholder={t("users.search_placeholder")} aria-label={t("users.search_placeholder")}
              className="border border-gray-300 rounded-lg px-3 py-2 text-sm w-72" />
            <select value={site} onChange={e => setSite(e.target.value)} aria-label={t("users.filters.site")}
              className="border border-gray-300 rounded-lg px-3 py-2 text-sm bg-white">
              <option value="">{t("users.filters.all_sites")}</option>
              {plants.map(p => <option key={p.id} value={p.id}>{p.code} — {p.name}</option>)}
            </select>
            <select value={role} onChange={e => setRole(e.target.value)} aria-label={t("users.filters.role")}
              className="border border-gray-300 rounded-lg px-3 py-2 text-sm bg-white">
              <option value="">{t("users.filters.all_roles")}</option>
              {GRC_ACCESS_ROLES.map(r => <option key={r} value={r}>{roleName(t, r)}</option>)}
            </select>
            <div className="inline-flex rounded-lg border border-gray-200 bg-gray-50 p-0.5 ml-auto" role="radiogroup" aria-label={t("users.filters.status")}>
              {(["active", "inactive", "all"] as const).map(s => (
                <button key={s} role="radio" aria-checked={status === s} onClick={() => setStatus(s)}
                  className={`px-3 py-1.5 text-sm rounded-md ${status === s ? "bg-white shadow-sm text-gray-900 font-medium" : "text-gray-500"}`}>
                  {t(`users.filters.status_${s}`)}
                </button>
              ))}
            </div>
          </div>

          {gapsTotal > 0 && (
            <p className="text-sm text-amber-900 bg-amber-50 border border-amber-100 rounded-lg px-3 py-2">
              ⚠ {t("users.list.gaps_summary", { count: gapsTotal })}
            </p>
          )}

          <div className="bg-white rounded-xl border border-gray-200 divide-y divide-gray-100">
            {isLoading ? (
              <p className="p-8 text-center text-gray-400">{t("common.loading")}</p>
            ) : filtered.length === 0 ? (
              <p className="p-8 text-center text-gray-400">{t("users.empty")}</p>
            ) : filtered.map(u => (
              <button key={u.id} type="button" onClick={() => setOpenId(u.id)}
                className="w-full text-left flex flex-wrap md:flex-nowrap items-center gap-4 px-4 py-3 hover:bg-gray-50 focus:bg-gray-50 focus:outline-none">
                <Avatar user={u} />
                <div className="w-56 min-w-0">
                  <p className={`text-sm font-medium truncate ${u.is_active ? "text-gray-900" : "text-gray-400"}`}>{displayName(u)}</p>
                  <p className="text-xs text-gray-500 truncate">{u.email}</p>
                </div>
                <div className="flex-1 min-w-0 flex flex-wrap gap-1.5">
                  {u.is_superuser && <span className="text-xs px-2 py-0.5 rounded-full border bg-purple-50 text-purple-800 border-purple-200">🛠 {t("users.list.superuser")}</span>}
                  {(u.accesses ?? []).map(a => (
                    <span key={a.id} className={`text-xs px-2 py-0.5 rounded-full border ${ROLE_TONE[a.role] ?? "bg-gray-50 text-gray-700 border-gray-200"}`}>
                      <span aria-hidden>{ROLE_ICON[a.role]}</span> {roleName(t, a.role)} · {accessScopeText(t, a)}
                    </span>
                  ))}
                  {!u.is_superuser && (u.accesses ?? []).length === 0 && <span className="text-xs text-gray-400 italic">{t("users.list.no_access")}</span>}
                  {(u.responsibilities ?? []).map(r => (
                    <span key={r.id} className="text-xs px-2 py-0.5 rounded-full bg-indigo-50 text-indigo-700">
                      🛡 {respName(t, r.role)}{r.scope_code ? ` · ${r.scope_code}` : ""}
                    </span>
                  ))}
                  {(u.warnings?.length ?? 0) > 0 && (
                    <span className="text-xs px-2 py-0.5 rounded-full bg-amber-50 text-amber-800">⚠ {t("users.list.gap_badge", { count: u.warnings!.length })}</span>
                  )}
                </div>
                <div className="w-44 text-right text-xs text-gray-500 space-y-0.5 shrink-0">
                  <p>
                    <span className={`inline-block w-2 h-2 rounded-full mr-1 ${u.is_active ? "bg-green-500" : "bg-gray-300"}`} />
                    {u.is_active ? t("users.list.active") : t("users.list.inactive")}
                    {" · "}{u.mfa_enabled ? <span className="text-green-700">MFA ✓</span> : <span className="text-gray-400">MFA —</span>}
                  </p>
                  <p>{u.last_login ? t("users.list.last_login", { when: relativeTime(u.last_login, i18n.language) }) : t("users.list.never_logged")}</p>
                </div>
              </button>
            ))}
          </div>
        </>
      )}

      {opened && (
        <UserDrawer user={opened} users={activeUsers} canManage={canManage} isSelf={me?.id === opened.id}
          onClose={() => setOpenId(null)} />
      )}
      {showNew && (
        <NewUserWizard onClose={() => setShowNew(false)}
          onCreated={id => { setShowNew(false); setStatus("active"); setOpenId(id); }} />
      )}
    </div>
  );
}
