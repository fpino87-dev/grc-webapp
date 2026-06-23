import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import {
  governanceApi,
  type CoverageCell,
  type CoverageStatus,
  type CoveragePlant,
} from "../../api/endpoints/governance";

export interface AssignPrefill {
  role: string;
  scope_type: "org" | "plant";
  scope_id?: string | null;
}

interface Props {
  onAssign: (prefill: AssignPrefill) => void;
  onReplace: (holder: { id: string; role: string; user_name?: string | null }) => void;
  onTerminate: (holder: { id: string; role: string; user_name?: string | null }) => void;
}

const STATUS_DOT: Record<CoverageStatus, string> = {
  covered: "bg-green-500",
  covered_via_org: "bg-emerald-400",
  expiring: "bg-amber-400",
  vacant: "bg-red-500",
  na: "bg-gray-200",
};

const STATUS_CELL: Record<CoverageStatus, string> = {
  covered: "bg-green-50 border-green-200 text-green-800",
  covered_via_org: "bg-emerald-50 border-emerald-200 text-emerald-800",
  expiring: "bg-amber-50 border-amber-200 text-amber-800",
  vacant: "bg-red-50 border-red-200 text-red-700",
  na: "bg-gray-50 border-gray-100 text-gray-300",
};

export function RoleCoverageMatrix({ onAssign, onReplace, onTerminate }: Props) {
  const { t } = useTranslation();
  const [buFilter, setBuFilter] = useState<string>("");
  const [onlyGaps, setOnlyGaps] = useState(false);
  const [search, setSearch] = useState("");
  const [openCell, setOpenCell] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["governance-coverage-matrix"],
    queryFn: () => governanceApi.coverageMatrix(),
  });

  function roleLabel(role: string) {
    return t(`governance.roles.${role}`, { defaultValue: role });
  }
  function statusLabel(s: CoverageStatus) {
    return t(`governance.coverage.status.${s}`);
  }

  const plants = useMemo<CoveragePlant[]>(() => {
    let list = data?.plants ?? [];
    if (buFilter) list = list.filter((p) => p.bu_id === buFilter);
    if (search.trim()) {
      const q = search.trim().toLowerCase();
      list = list.filter(
        (p) => p.code.toLowerCase().includes(q) || p.name.toLowerCase().includes(q),
      );
    }
    return list;
  }, [data, buFilter, search]);

  const businessUnits = useMemo(() => {
    const map = new Map<string, string>();
    (data?.plants ?? []).forEach((p) => {
      if (p.bu_id) map.set(p.bu_id, `${p.bu_code} — ${p.bu_name}`);
    });
    return Array.from(map.entries());
  }, [data]);

  if (isLoading) {
    return <p className="text-sm text-gray-400">{t("common.loading")}</p>;
  }
  if (!data) return null;

  const isGap = (s: CoverageStatus) => s === "vacant" || s === "expiring";

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h3 className="text-sm font-semibold text-gray-700">{t("governance.coverage.title")}</h3>
          <p className="text-xs text-gray-500 mt-0.5">{t("governance.coverage.subtitle")}</p>
        </div>
        {/* Legenda */}
        <div className="flex items-center gap-3 text-xs text-gray-600 flex-wrap">
          {(["covered", "covered_via_org", "expiring", "vacant", "na"] as CoverageStatus[]).map((s) => (
            <span key={s} className="inline-flex items-center gap-1">
              <span className={`inline-block w-2.5 h-2.5 rounded-full ${STATUS_DOT[s]}`} />
              {statusLabel(s)}
            </span>
          ))}
        </div>
      </div>

      {/* Ruoli org-level */}
      <div>
        <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
          {t("governance.coverage.org_section")}
        </h4>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
          {data.org_roles.map((r) => (
            <div
              key={r.role}
              className={`flex items-center justify-between border rounded px-3 py-2 ${STATUS_CELL[r.status]}`}
            >
              <div className="min-w-0">
                <div className="text-sm font-medium truncate">{roleLabel(r.role)}</div>
                <div className="text-xs truncate">
                  {r.holders.length
                    ? r.holders.map((h) => h.user).join(", ")
                    : t("governance.coverage.holder_none")}
                </div>
              </div>
              {r.status === "vacant" ? (
                <button
                  onClick={() => onAssign({ role: r.role, scope_type: "org" })}
                  className="text-xs px-2 py-1 bg-white/70 border rounded hover:bg-white shrink-0"
                >
                  {t("governance.coverage.assign")}
                </button>
              ) : (
                <span className="text-xs font-medium shrink-0">{statusLabel(r.status)}</span>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Ruoli per-sito */}
      <div>
        <div className="flex items-center justify-between gap-3 flex-wrap mb-2">
          <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
            {t("governance.coverage.sites_section")}
          </h4>
          <div className="flex items-center gap-2 flex-wrap">
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder={t("governance.coverage.filters.search_plant")}
              className="border rounded px-2 py-1 text-xs"
            />
            <select
              value={buFilter}
              onChange={(e) => setBuFilter(e.target.value)}
              className="border rounded px-2 py-1 text-xs"
            >
              <option value="">{t("governance.coverage.filters.all_bu")}</option>
              {businessUnits.map(([id, label]) => (
                <option key={id} value={id}>{label}</option>
              ))}
            </select>
            <label className="inline-flex items-center gap-1 text-xs text-gray-600">
              <input type="checkbox" checked={onlyGaps} onChange={(e) => setOnlyGaps(e.target.checked)} />
              {t("governance.coverage.filters.only_gaps")}
            </label>
          </div>
        </div>

        {plants.length === 0 ? (
          <p className="text-sm text-gray-400 italic">{t("governance.coverage.no_plants")}</p>
        ) : (
          // Trasposta: siti in riga (tutti visibili, niente scroll orizzontale),
          // ruoli per-sito in colonna (pochi → ci stanno sempre in larghezza).
          <div className="border border-gray-200 rounded">
            <table className="w-full text-sm border-collapse table-fixed">
              <thead>
                <tr className="bg-gray-50">
                  <th className="text-left px-3 py-2 font-medium text-gray-600 border-b border-r border-gray-200">
                    {t("governance.coverage.site_column")}
                  </th>
                  {data.plant_roles.map((r) => (
                    <th key={r.role} className="px-2 py-2 font-medium text-gray-600 border-b border-gray-200 text-center">
                      <div>{roleLabel(r.role)}</div>
                      {r.applies_to === "nis2_only" && (
                        <div className="text-[10px] text-gray-400 font-normal">
                          {t("governance.coverage.applies_nis2_only")}
                        </div>
                      )}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {plants.map((p) => {
                  const rowCells = data.plant_roles.map((r) => ({ r, cell: r.cells[p.id] as CoverageCell | undefined }));
                  if (onlyGaps && !rowCells.some(({ cell }) => cell && isGap(cell.status))) {
                    return null;
                  }
                  return (
                    <tr key={p.id} className="border-b border-gray-100 last:border-0">
                      <td className="px-3 py-2 text-gray-800 border-r border-gray-200">
                        <span className="font-medium">{p.code}</span>
                        <span className="text-gray-500"> — {p.name}</span>
                        {p.is_nis2 && (
                          <span className="ml-1 text-[10px] text-blue-600">NIS2</span>
                        )}
                      </td>
                      {rowCells.map(({ r, cell }) => {
                        const status = cell?.status ?? "na";
                        const key = `${p.id}:${r.role}`;
                        const isOpen = openCell === key;
                        return (
                          <td key={r.role} className="px-1 py-1 text-center align-middle relative">
                            <button
                              onClick={() => setOpenCell(isOpen ? null : key)}
                              disabled={status === "na"}
                              className={`w-full h-8 rounded border text-xs ${STATUS_CELL[status]} ${status === "na" ? "cursor-default" : "hover:brightness-95"}`}
                              title={statusLabel(status)}
                            >
                              {status === "covered" && "✓"}
                              {status === "covered_via_org" && "↑"}
                              {status === "expiring" && "!"}
                              {status === "vacant" && "—"}
                            </button>
                            {isOpen && status !== "na" && (
                              <div className="absolute z-20 mt-1 left-1/2 -translate-x-1/2 bg-white border border-gray-200 rounded shadow-lg p-2 w-56 text-left">
                                <div className="text-xs font-semibold text-gray-700 mb-1">
                                  {roleLabel(r.role)} — {p.code}
                                </div>
                                {cell?.via_org && (
                                  <div className="text-[11px] text-emerald-600 mb-1">
                                    {t("governance.coverage.via_org_hint")}
                                  </div>
                                )}
                                {cell?.holders?.length ? (
                                  <ul className="text-xs text-gray-600 space-y-0.5 mb-2">
                                    {cell.holders.map((h) => (
                                      <li key={h.id}>
                                        {h.user}
                                        {h.valid_until && (
                                          <span className="text-gray-400"> · {h.valid_until}</span>
                                        )}
                                      </li>
                                    ))}
                                  </ul>
                                ) : (
                                  <div className="text-xs text-gray-400 italic mb-2">
                                    {t("governance.coverage.holder_none")}
                                  </div>
                                )}
                                <div className="flex flex-wrap gap-1">
                                  <button
                                    onClick={() => {
                                      setOpenCell(null);
                                      onAssign({ role: r.role, scope_type: "plant", scope_id: p.id });
                                    }}
                                    className="text-xs px-2 py-1 bg-primary-600 text-white rounded hover:bg-primary-700"
                                  >
                                    {t("governance.coverage.assign")}
                                  </button>
                                  {/* sostituisci/termina solo su titolari specifici del sito (non sul fallback org) */}
                                  {!cell?.via_org && cell?.holders?.map((h) => (
                                    <span key={h.id} className="flex gap-1">
                                      <button
                                        onClick={() => {
                                          setOpenCell(null);
                                          onReplace({ id: h.id, role: r.role, user_name: h.user });
                                        }}
                                        className="text-xs px-2 py-1 bg-blue-50 text-blue-700 border border-blue-200 rounded hover:bg-blue-100"
                                      >
                                        {t("governance.coverage.replace")}
                                      </button>
                                      <button
                                        onClick={() => {
                                          setOpenCell(null);
                                          onTerminate({ id: h.id, role: r.role, user_name: h.user });
                                        }}
                                        className="text-xs px-2 py-1 bg-orange-50 text-orange-700 border border-orange-200 rounded hover:bg-orange-100"
                                      >
                                        {t("governance.coverage.terminate")}
                                      </button>
                                    </span>
                                  ))}
                                </div>
                              </div>
                            )}
                          </td>
                        );
                      })}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
