import type { TFunction } from "i18next";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { usersApi, GRC_ACCESS_ROLES, type AccessScopeType, type GrcUser, type RoleMatrix, type UserAccess } from "../../api/endpoints/users";
import { plantsApi } from "../../api/endpoints/plants";

export type AccessRole = (typeof GRC_ACCESS_ROLES)[number];

/** Colore d'accento per ruolo: avatar delle card, chip degli accessi. */
export const ROLE_TONE: Record<string, string> = {
  super_admin: "bg-purple-50 text-purple-800 border-purple-200",
  compliance_officer: "bg-blue-50 text-blue-800 border-blue-200",
  risk_manager: "bg-orange-50 text-orange-800 border-orange-200",
  plant_manager: "bg-teal-50 text-teal-800 border-teal-200",
  control_owner: "bg-green-50 text-green-800 border-green-200",
  internal_auditor: "bg-amber-50 text-amber-800 border-amber-200",
  external_auditor: "bg-slate-50 text-slate-700 border-slate-200",
};

export const ROLE_ICON: Record<string, string> = {
  super_admin: "🛠", compliance_officer: "🧭", risk_manager: "⚖️", plant_manager: "🏭",
  control_owner: "✅", internal_auditor: "🔎", external_auditor: "🧾",
};

export const roleName = (t: TFunction, role: string) => t(`users.role.${role}.name`, { defaultValue: role });
export const respName = (t: TFunction, role: string) => t(`governance.roles.${role}`, { defaultValue: role.replace(/_/g, " ") });

export function displayName(u: Pick<GrcUser, "first_name" | "last_name" | "username">) {
  return [u.first_name, u.last_name].filter(Boolean).join(" ") || u.username;
}

export function initials(u: Pick<GrcUser, "first_name" | "last_name" | "username">) {
  const parts = [u.first_name, u.last_name].filter(Boolean);
  const src = parts.length ? parts : [u.username];
  return src.map(p => p.trim()[0] ?? "").join("").slice(0, 2).toUpperCase();
}

export function Avatar({ user, size = "md" }: { user: GrcUser; size?: "md" | "lg" }) {
  const tone = ROLE_TONE[user.accesses?.[0]?.role ?? ""] ?? "bg-gray-100 text-gray-600 border-gray-200";
  const dim = size === "lg" ? "w-12 h-12 text-base" : "w-9 h-9 text-xs";
  return (
    <span className={`inline-flex items-center justify-center rounded-full border font-semibold shrink-0 ${dim} ${tone} ${user.is_active ? "" : "opacity-50"}`}>
      {initials(user)}
    </span>
  );
}

/** Perimetro di un accesso in parole: "Tutta l'organizzazione", "BU NORD", "TA, TB". */
export function accessScopeText(t: TFunction, a: Pick<UserAccess, "scope_type" | "scope_bu_code" | "scope_plant_codes">) {
  if (a.scope_type === "org") return t("users.scope.org");
  if (a.scope_type === "bu") return t("users.scope.bu_named", { code: a.scope_bu_code ?? "—" });
  return a.scope_plant_codes.join(", ") || t("users.scope.none");
}

export function relativeTime(iso: string | null | undefined, lang: string): string | null {
  if (!iso) return null;
  const diff = (new Date(iso).getTime() - Date.now()) / 1000;
  const fmt = new Intl.RelativeTimeFormat(lang, { numeric: "auto" });
  const abs = Math.abs(diff);
  if (abs < 3600) return fmt.format(Math.round(diff / 60), "minute");
  if (abs < 86400) return fmt.format(Math.round(diff / 3600), "hour");
  if (abs < 86400 * 30) return fmt.format(Math.round(diff / 86400), "day");
  if (abs < 86400 * 365) return fmt.format(Math.round(diff / (86400 * 30)), "month");
  return fmt.format(Math.round(diff / (86400 * 365)), "year");
}

export function useRoleMatrix() {
  return useQuery<RoleMatrix>({ queryKey: ["role-matrix"], queryFn: usersApi.roleMatrix, staleTime: Infinity });
}

// ── Scelta del ruolo a card ──────────────────────────────────────────────────

export function RoleCards({ value, onChange }: { value: string; onChange: (role: AccessRole) => void }) {
  const { t } = useTranslation();
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
      {GRC_ACCESS_ROLES.map(r => (
        <button key={r} type="button" onClick={() => onChange(r)} aria-pressed={value === r}
          className={`text-left rounded-xl border px-3 py-2.5 transition-shadow ${value === r
            ? "border-primary-500 ring-2 ring-primary-100 bg-primary-50/40" : "border-gray-200 hover:border-gray-300 hover:shadow-sm bg-white"}`}>
          <span className="flex items-center gap-2 text-sm font-medium text-gray-900">
            <span aria-hidden>{ROLE_ICON[r]}</span>{roleName(t, r)}
          </span>
          <span className="block text-xs text-gray-500 mt-0.5 leading-snug">{t(`users.role.${r}.desc`)}</span>
        </button>
      ))}
    </div>
  );
}

// ── Scelta del perimetro ─────────────────────────────────────────────────────

export interface ScopeValue { kind: "org" | "bu" | "sites"; bu: string; sites: string[] }

export const emptyScope: ScopeValue = { kind: "sites", bu: "", sites: [] };

export function scopeToAccess(s: ScopeValue): { scope_type: AccessScopeType; scope_plants?: string[]; scope_bu?: string | null } {
  if (s.kind === "org") return { scope_type: "org" };
  if (s.kind === "bu") return { scope_type: "bu", scope_bu: s.bu || null };
  return { scope_type: s.sites.length === 1 ? "single_plant" : "plant_list", scope_plants: s.sites };
}

export const scopeReady = (s: ScopeValue) =>
  s.kind === "org" || (s.kind === "bu" ? !!s.bu : s.sites.length > 0);

export function ScopePicker({ value, onChange }: { value: ScopeValue; onChange: (v: ScopeValue) => void }) {
  const { t } = useTranslation();
  const { data: plants = [] } = useQuery({ queryKey: ["plants"], queryFn: () => plantsApi.list() });
  const { data: bus = [] } = useQuery({ queryKey: ["business-units"], queryFn: () => plantsApi.businessUnits() });
  const kinds: ScopeValue["kind"][] = ["sites", "bu", "org"];
  return (
    <div className="space-y-3">
      <div className="inline-flex rounded-lg border border-gray-200 bg-gray-50 p-0.5" role="radiogroup">
        {kinds.map(k => (
          <button key={k} type="button" role="radio" aria-checked={value.kind === k}
            onClick={() => onChange({ ...value, kind: k })}
            className={`px-3 py-1.5 text-sm rounded-md ${value.kind === k ? "bg-white shadow-sm text-gray-900 font-medium" : "text-gray-500 hover:text-gray-700"}`}>
            {t(`users.scope.kind_${k}`)}
          </button>
        ))}
      </div>
      {value.kind === "sites" && (
        <div className="flex flex-wrap gap-1.5">
          {plants.map(p => {
            const on = value.sites.includes(p.id);
            return (
              <button key={p.id} type="button" aria-pressed={on} title={p.name}
                onClick={() => onChange({ ...value, sites: on ? value.sites.filter(x => x !== p.id) : [...value.sites, p.id] })}
                className={`text-xs px-2.5 py-1 rounded-full border ${on ? "bg-gray-900 text-white border-gray-900" : "bg-white text-gray-700 border-gray-300 hover:border-gray-400"}`}>
                {p.code}
              </button>
            );
          })}
        </div>
      )}
      {value.kind === "bu" && (
        <div className="flex flex-wrap gap-1.5">
          {bus.map(b => (
            <button key={b.id} type="button" aria-pressed={value.bu === b.id} onClick={() => onChange({ ...value, bu: b.id })}
              className={`text-xs px-2.5 py-1 rounded-full border ${value.bu === b.id ? "bg-gray-900 text-white border-gray-900" : "bg-white text-gray-700 border-gray-300 hover:border-gray-400"}`}>
              {b.code} — {b.name}
            </button>
          ))}
          {bus.length === 0 && <p className="text-xs text-gray-400">{t("users.scope.no_bu")}</p>}
        </div>
      )}
      {value.kind === "org" && <p className="text-xs text-gray-500">{t("users.scope.org_hint")}</p>}
    </div>
  );
}

// ── Cosa potrà fare: riepilogo dai permessi reali ────────────────────────────

export function RolePermissionsPreview({ role, compact = false }: { role: string; compact?: boolean }) {
  const { t } = useTranslation();
  const { data } = useRoleMatrix();
  if (!data || !role) return null;
  const write = data.areas.filter(a => a.perms[role] === "W");
  const read = data.areas.filter(a => a.perms[role] === "R");
  const chip = (k: string, tone: string) => (
    <span key={k} className={`text-[11px] px-2 py-0.5 rounded-full border ${tone}`}>{t(`users.areas.${k}`)}</span>
  );
  return (
    <div className={`space-y-2 ${compact ? "" : "rounded-xl border border-gray-200 bg-gray-50/60 p-3"}`}>
      {write.length > 0 && (
        <div>
          <p className="text-xs font-medium text-gray-700 mb-1">✎ {t("users.editor.can_edit")}</p>
          <div className="flex flex-wrap gap-1">{write.map(a => chip(a.key, "bg-green-50 text-green-800 border-green-200"))}</div>
        </div>
      )}
      {read.length > 0 && (
        <div>
          <p className="text-xs font-medium text-gray-700 mb-1">👁 {t("users.editor.can_view")}</p>
          <div className="flex flex-wrap gap-1">{read.map(a => chip(a.key, "bg-white text-gray-600 border-gray-200"))}</div>
        </div>
      )}
    </div>
  );
}
