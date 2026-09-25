import { useState } from "react";
import { useTranslation } from "react-i18next";
import { GRC_ACCESS_ROLES, type GrcUser } from "../../api/endpoints/users";
import { ROLE_ICON, ROLE_TONE, roleName, useRoleMatrix } from "./shared";

const CELL: Record<string, { icon: string; cls: string }> = {
  W: { icon: "✎", cls: "bg-green-50 text-green-700" },
  R: { icon: "👁", cls: "text-gray-500" },
  "-": { icon: "·", cls: "text-gray-300" },
};

/** Catalogo dei ruoli: descrizione, quante persone lo hanno e cosa può fare
 *  in ogni area (matrice letta dai permessi reali del codice). */
export function RolesCatalog({ users }: { users: GrcUser[] }) {
  const { t } = useTranslation();
  const { data, isLoading } = useRoleMatrix();
  const [focus, setFocus] = useState<string>("");
  const count = (role: string) => users.filter(u => u.is_active && (u.accesses ?? []).some(a => a.role === role)).length;

  return (
    <div className="space-y-6">
      <p className="text-sm text-gray-500 max-w-3xl">{t("users.roles_catalog.intro")}</p>
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
        {GRC_ACCESS_ROLES.map(r => (
          <button key={r} type="button" onClick={() => setFocus(focus === r ? "" : r)} aria-pressed={focus === r}
            className={`text-left rounded-xl border p-4 transition-shadow ${focus === r ? "border-primary-500 ring-2 ring-primary-100" : "border-gray-200 hover:shadow-sm"} bg-white`}>
            <div className="flex items-center gap-3">
              <span className={`w-10 h-10 rounded-lg border flex items-center justify-center text-lg ${ROLE_TONE[r]}`} aria-hidden>{ROLE_ICON[r]}</span>
              <div className="flex-1">
                <p className="text-sm font-semibold text-gray-900">{roleName(t, r)}</p>
                <p className="text-xs text-gray-400">{t("users.roles_catalog.people", { count: count(r) })}</p>
              </div>
            </div>
            <p className="text-xs text-gray-600 mt-2 leading-snug">{t(`users.role.${r}.desc`)}</p>
          </button>
        ))}
      </div>

      <div className="rounded-xl border border-gray-200 bg-white overflow-x-auto">
        <div className="flex flex-wrap items-center gap-4 px-4 py-3 border-b border-gray-100 text-xs text-gray-500">
          <span className="font-medium text-gray-700">{t("users.roles_catalog.matrix_title")}</span>
          <span><span className="text-green-700">✎</span> {t("users.roles_catalog.legend_write")}</span>
          <span>👁 {t("users.roles_catalog.legend_read")}</span>
          <span className="text-gray-300">·</span><span>{t("users.roles_catalog.legend_none")}</span>
        </div>
        {isLoading || !data ? (
          <p className="p-6 text-sm text-gray-400">{t("common.loading")}</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-xs text-gray-500">
                <th className="text-left font-medium px-4 py-2 sticky left-0 bg-white">{t("users.roles_catalog.area_col")}</th>
                {data.roles.map(r => (
                  <th key={r} className={`px-2 py-2 font-medium text-center whitespace-nowrap ${focus === r ? "bg-primary-50 text-primary-800" : ""}`}>
                    <span aria-hidden>{ROLE_ICON[r]}</span> {roleName(t, r)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {data.areas.map(a => (
                <tr key={a.key} className="hover:bg-gray-50/60">
                  <td className="px-4 py-1.5 text-gray-700 sticky left-0 bg-white">{t(`users.areas.${a.key}`)}</td>
                  {data.roles.map(r => {
                    const c = CELL[a.perms[r]] ?? CELL["-"];
                    return (
                      <td key={r} className={`px-2 py-1.5 text-center ${focus === r ? "bg-primary-50/60" : ""}`}
                        title={`${roleName(t, r)} · ${t(`users.areas.${a.key}`)}: ${t(`users.roles_catalog.cell_${a.perms[r] === "W" ? "write" : a.perms[r] === "R" ? "read" : "none"}`)}`}>
                        <span className={`inline-flex w-6 h-6 items-center justify-center rounded ${c.cls}`}>{c.icon}</span>
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
      <p className="text-xs text-gray-400">{t("users.roles_catalog.footnote")}</p>
    </div>
  );
}
