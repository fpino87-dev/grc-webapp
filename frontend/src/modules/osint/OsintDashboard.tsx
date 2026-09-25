import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { osintApi, type OsintEntity, type OsintFinding } from "../../api/endpoints/osint";
import { OsintEntityDrawer } from "./OsintEntityDrawer";
import { OsintAiPanel } from "./OsintAiPanel";
import { GradeBadge, ReportToSupplierDialog, Sparkline, findingTitle } from "./shared";

type Tab = "my_domain" | "supplier" | "asset";
type AiType = "attack_surface" | "suppliers_nis2" | "board_report";

const SEV_DOT: Record<string, string> = { critical: "bg-red-600", warning: "bg-orange-500", info: "bg-gray-400" };

function daysSince(iso: string) {
  return Math.max(0, Math.floor((Date.now() - new Date(iso).getTime()) / 86400000));
}

/** Barra di una dimensione (SSL/DNS/Reputazione): più piena = più sicura. */
function DimBar({ risk }: { risk: number | null | undefined }) {
  if (risk == null) return <span className="text-xs text-gray-300">—</span>;
  const sec = Math.max(0, 100 - risk);
  const tone = risk >= 70 ? "bg-red-500" : risk >= 50 ? "bg-orange-400" : risk >= 30 ? "bg-yellow-400" : "bg-emerald-500";
  return (
    <span className="inline-block w-12 h-1.5 rounded-full bg-gray-100 overflow-hidden align-middle" title={`${sec}/100`}>
      <span className={`block h-full ${tone}`} style={{ width: `${sec}%` }} />
    </span>
  );
}

export function OsintDashboard() {
  const { t, i18n } = useTranslation();
  const [tab, setTab] = useState<Tab>("my_domain");
  const [search, setSearch] = useState("");
  const [sortBy, setSortBy] = useState<"risk" | "name">("risk");
  const [selectedEntityId, setSelectedEntityId] = useState<string | null>(null);
  const [reporting, setReporting] = useState<OsintFinding | null>(null);
  const [aiType, setAiType] = useState<AiType | null>(null);
  const [aiMenu, setAiMenu] = useState(false);

  const { data: posture } = useQuery({ queryKey: ["osint-posture"], queryFn: osintApi.posture, refetchInterval: 5 * 60_000 });
  const { data: changes } = useQuery({ queryKey: ["osint-changes"], queryFn: () => osintApi.changes(7) });
  const { data: summary } = useQuery({ queryKey: ["osint-summary"], queryFn: osintApi.dashboardSummary });
  const { data: entities = [], isLoading } = useQuery({ queryKey: ["osint-entities"], queryFn: () => osintApi.entities() });
  const { data: ownOpen = [] } = useQuery({
    queryKey: ["osint-findings", "own", "critical-queue"],
    queryFn: () => osintApi.findings({ ownership: "own", open_only: "1", severity: "critical" }),
  });
  const { data: supplierQueue = [] } = useQuery({
    queryKey: ["osint-supplier-queue"],
    queryFn: () => osintApi.findings({ ownership: "supplier", open_only: "1", severity: "critical" }),
  });

  const todo = [...ownOpen].sort((a, b) => a.first_seen.localeCompare(b.first_seen)).slice(0, 5);
  // Da segnalare: non ancora segnalati, poi i segnalati da sollecitare.
  const toReport = supplierQueue.filter(f => f.status !== "reported" || f.report_overdue)
    .sort((a, b) => Number(a.status === "reported") - Number(b.status === "reported"));

  const counts = useMemo(() => {
    const c: Record<Tab, number> = { my_domain: 0, supplier: 0, asset: 0 };
    entities.forEach(e => { c[e.entity_type as Tab] += 1; });
    return c;
  }, [entities]);
  const rows = useMemo(() => entities
    .filter(e => e.entity_type === tab)
    .filter(e => !search || `${e.display_name} ${e.domain}`.toLowerCase().includes(search.toLowerCase()))
    .sort((a, b) => sortBy === "name"
      ? a.display_name.localeCompare(b.display_name)
      : (a.security ?? 101) - (b.security ?? 101)), [entities, tab, search, sortBy]);

  const supplierStatus = (e: OsintEntity) => {
    const mine = supplierQueue.filter(f => f.entity === e.id);
    if (!mine.length) return null;
    const pending = mine.filter(f => f.status !== "reported").length;
    return pending ? { tone: "bg-red-50 text-red-700", text: t("osint.dash.sup_to_report", { count: pending }) }
      : { tone: "bg-gray-100 text-gray-600", text: t("osint.dash.sup_reported", { count: mine.length }) };
  };

  return (
    <div className="p-4 sm:p-6 space-y-5">
      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-gray-900">{t("osint.title")}</h1>
          <p className="text-sm text-gray-500">{t("osint.dash.subtitle")}</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Link to="/osint/remediation" className="px-3 py-1.5 text-sm border rounded-lg hover:bg-gray-50">
            🛠 {t("osint.dash.to_fix_link")}
          </Link>
          <Link to="/osint/subdomains" className="relative px-3 py-1.5 text-sm border rounded-lg hover:bg-gray-50">
            🌐 {t("osint.subdomains.title")}
            {(summary?.pending_subdomains ?? 0) > 0 && (
              <span className="absolute -top-1.5 -right-1.5 bg-yellow-500 text-white text-[10px] rounded-full min-w-4 h-4 px-1 flex items-center justify-center font-bold">
                {summary!.pending_subdomains}
              </span>
            )}
          </Link>
          <div className="relative">
            <button onClick={() => setAiMenu(v => !v)} className="px-3 py-1.5 text-sm border rounded-lg hover:bg-gray-50">
              🤖 {t("osint.dash.generate_report")} ▾
            </button>
            {aiMenu && (
              <div className="absolute right-0 mt-1 w-64 bg-white border rounded-lg shadow-lg z-20 text-sm overflow-hidden">
                {(["attack_surface", "suppliers_nis2", "board_report"] as AiType[]).map(k => (
                  <button key={k} onClick={() => { setAiType(k); setAiMenu(false); }} className="w-full text-left px-3 py-2 hover:bg-gray-50">
                    {t(`osint.ai.${k}`)}
                  </button>
                ))}
              </div>
            )}
          </div>
          <Link to="/osint/settings" className="px-3 py-1.5 text-sm border rounded-lg hover:bg-gray-50" aria-label={t("osint.settings.title")}>⚙</Link>
        </div>
      </div>

      {/* Postura esterna + code di lavoro */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        <section className="rounded-2xl border border-gray-200 bg-white p-5">
          <p className="text-xs font-medium uppercase tracking-wide text-gray-500">{t("osint.dash.posture_title")}</p>
          <div className="flex items-center gap-4 mt-3">
            <GradeBadge grade={posture?.grade} security={posture?.security} size="xl" />
            <div className="flex-1 min-w-0">
              <Sparkline values={(posture?.trend ?? []).map(p => p.security)} width={180} height={40} />
              <p className="text-[11px] text-gray-400 mt-1">{t("osint.dash.trend_weeks", { count: 12 })}</p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2 mt-4 text-xs">
            <span className="px-2 py-1 rounded-full bg-red-50 text-red-700">● {t("osint.dash.critical", { count: posture?.own.critical ?? 0 })}</span>
            <span className="px-2 py-1 rounded-full bg-orange-50 text-orange-700">● {t("osint.dash.warning", { count: posture?.own.warning ?? 0 })}</span>
            <span className="px-2 py-1 rounded-full bg-green-50 text-green-700">✓ {t("osint.dash.resolved_week", { count: posture?.own.resolved_week ?? 0 })}</span>
          </div>
          <p className="text-[11px] text-gray-400 mt-3">{t("osint.dash.posture_hint")}</p>
        </section>

        <section className="rounded-2xl border border-gray-200 bg-white p-5">
          <div className="flex items-center justify-between">
            <p className="text-xs font-medium uppercase tracking-wide text-gray-500">🛠 {t("osint.dash.todo_title")}</p>
            <Link to="/osint/remediation" className="text-xs text-primary-700 hover:underline">{t("osint.dash.see_all")}</Link>
          </div>
          {todo.length === 0 ? (
            <p className="mt-6 text-sm text-gray-400 text-center">✓ {t("osint.dash.todo_empty")}</p>
          ) : (
            <ul className="mt-3 space-y-2">
              {todo.map(f => (
                <li key={f.id}>
                  <button onClick={() => setSelectedEntityId(f.entity)} className="w-full text-left rounded-lg px-3 py-2 hover:bg-gray-50 border border-gray-100">
                    <p className="text-sm font-medium text-gray-900">🔴 {findingTitle(t, f)}</p>
                    <p className="text-xs text-gray-500">{f.entity_domain} · {t("osint.dash.since_days", { count: daysSince(f.first_seen) })}</p>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="rounded-2xl border border-gray-200 bg-white p-5">
          <p className="text-xs font-medium uppercase tracking-wide text-gray-500">📣 {t("osint.dash.report_title")}</p>
          <p className="text-[11px] text-gray-400 mt-0.5">{t("osint.dash.report_hint")}</p>
          {toReport.length === 0 ? (
            <p className="mt-6 text-sm text-gray-400 text-center">✓ {t("osint.dash.report_empty")}</p>
          ) : (
            <ul className="mt-3 space-y-2">
              {toReport.slice(0, 5).map(f => (
                <li key={f.id} className="flex items-center gap-2 rounded-lg px-3 py-2 border border-gray-100">
                  <button onClick={() => setSelectedEntityId(f.entity)} className="flex-1 min-w-0 text-left">
                    <p className="text-sm font-medium text-gray-900 truncate">{f.entity_display_name}</p>
                    <p className="text-xs text-gray-500 truncate">
                      {findingTitle(t, f)}
                      {f.report_overdue && f.reported_at && ` · ${t("osint.dash.reported_ago", { count: daysSince(f.reported_at) })}`}
                    </p>
                  </button>
                  <button onClick={() => setReporting(f)}
                    className={`shrink-0 px-2 py-1 text-xs rounded-lg ${f.report_overdue ? "bg-amber-500 text-white" : "bg-gray-900 text-white"}`}>
                    {f.report_overdue ? t("osint.dash.remind") : t("osint.dash.report_btn")}
                  </button>
                </li>
              ))}
            </ul>
          )}
          {(posture?.suppliers.reported_open ?? 0) > 0 && (
            <p className="text-[11px] text-gray-500 mt-3">{t("osint.dash.reported_open", { count: posture!.suppliers.reported_open })}</p>
          )}
        </section>
      </div>

      {/* Cosa è cambiato */}
      {changes && (
        <section className="rounded-2xl border border-gray-200 bg-white px-5 py-3 flex flex-wrap items-center gap-x-5 gap-y-2 text-sm">
          <span className="text-xs font-medium uppercase tracking-wide text-gray-500">{t("osint.dash.changes_title")}</span>
          <span>🆕 {t("osint.dash.ch_new", { count: changes.new_own.count })}</span>
          <span className="text-green-700">✓ {t("osint.dash.ch_resolved", { count: changes.resolved_own })}</span>
          <span>📣 {t("osint.dash.ch_supplier", { count: changes.new_supplier_critical.count })}</span>
          {changes.score_changes.slice(0, 3).map(c => (
            <button key={c.entity} onClick={() => setSelectedEntityId(c.entity)} className={`hover:underline ${c.delta < 0 ? "text-red-700" : "text-green-700"}`}>
              {c.delta < 0 ? "▼" : "▲"} {c.name} {c.grade ? `(${c.grade})` : ""}
            </button>
          ))}
          {changes.pending_subdomains > 0 && (
            <Link to="/osint/subdomains" className="text-yellow-800 hover:underline">🌐 {t("osint.dash.ch_subdomains", { count: changes.pending_subdomains })}</Link>
          )}
        </section>
      )}

      {/* Entità per tipo */}
      <section className="rounded-2xl border border-gray-200 bg-white">
        <div className="flex flex-wrap items-center gap-2 px-4 pt-3 border-b border-gray-100">
          {(["my_domain", "supplier", "asset"] as Tab[]).map(k => (
            <button key={k} onClick={() => setTab(k)}
              className={`px-3 py-2 text-sm border-b-2 -mb-px ${tab === k ? "border-primary-600 text-primary-700 font-medium" : "border-transparent text-gray-500 hover:text-gray-700"}`}>
              {t(`osint.dash.tab_${k}`)} <span className="text-xs text-gray-400">{counts[k]}</span>
            </button>
          ))}
          <div className="ml-auto flex items-center gap-2 pb-2">
            <input type="search" value={search} onChange={e => setSearch(e.target.value)} placeholder={t("osint.search_placeholder")}
              aria-label={t("osint.search_placeholder")} className="px-3 py-1.5 border rounded-lg text-sm w-52" />
            <select value={sortBy} onChange={e => setSortBy(e.target.value as "risk" | "name")} aria-label={t("osint.sort_by")}
              className="px-2 py-1.5 border rounded-lg text-sm bg-white">
              <option value="risk">{t("osint.dash.sort_risk")}</option>
              <option value="name">{t("osint.sort.name")}</option>
            </select>
          </div>
        </div>
        {tab === "supplier" && <p className="px-4 pt-3 text-xs text-gray-500">{t("osint.dash.supplier_tab_hint")}</p>}
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="text-xs text-gray-500">
                <th className="text-left font-medium px-4 py-2">{t("osint.table.entity")}</th>
                <th className="text-left font-medium px-3 py-2">{t("osint.dash.col_grade")}</th>
                <th className="text-left font-medium px-3 py-2">{t("osint.dash.col_trend")}</th>
                {tab !== "supplier" ? (
                  <>
                    <th className="font-medium px-2 py-2">SSL</th>
                    <th className="font-medium px-2 py-2">DNS</th>
                    <th className="font-medium px-2 py-2">{t("osint.table.reputation")}</th>
                    <th className="text-left font-medium px-3 py-2">{t("osint.dash.col_problems")}</th>
                  </>
                ) : (
                  <th className="text-left font-medium px-3 py-2">{t("osint.dash.col_critical")}</th>
                )}
                <th className="text-right font-medium px-4 py-2">{t("osint.dash.col_last_scan")}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {isLoading && <tr><td colSpan={8} className="px-4 py-8 text-center text-gray-400">{t("common.loading")}</td></tr>}
              {!isLoading && rows.length === 0 && <tr><td colSpan={8} className="px-4 py-8 text-center text-gray-400">{t("osint.table.no_entities")}</td></tr>}
              {rows.map(e => {
                const of = e.open_findings ?? { critical: 0, warning: 0, info: 0 };
                const sup = tab === "supplier" ? supplierStatus(e) : null;
                return (
                  <tr key={e.id} onClick={() => setSelectedEntityId(e.id)} className="hover:bg-gray-50 cursor-pointer">
                    <td className="px-4 py-2.5">
                      <p className="font-medium text-gray-900 truncate max-w-[16rem]">
                        {e.display_name}
                        {e.is_nis2_critical && <span className="ml-1 text-[10px] px-1.5 py-0.5 rounded bg-orange-50 text-orange-700" title={t("osint.dash.nis2_critical")}>NIS2</span>}
                        {tab === "supplier" && e.deep_monitoring && (
                          <span className="ml-1 text-[10px] px-1.5 py-0.5 rounded bg-indigo-50 text-indigo-700" title={t("osint.chain.deep_hint")}>{t("osint.chain.deep_badge")}</span>
                        )}
                      </p>
                      <p className="text-xs text-gray-400 truncate max-w-[16rem]">{e.domain}</p>
                    </td>
                    <td className="px-3 py-2.5"><GradeBadge grade={e.grade} security={e.security} /></td>
                    <td className="px-3 py-2.5"><Sparkline values={e.trend ?? []} /></td>
                    {tab !== "supplier" ? (
                      <>
                        <td className="px-2 py-2.5 text-center"><DimBar risk={e.last_scan?.score_ssl} /></td>
                        <td className="px-2 py-2.5 text-center"><DimBar risk={e.last_scan?.score_dns} /></td>
                        <td className="px-2 py-2.5 text-center"><DimBar risk={e.last_scan?.score_reputation} /></td>
                        <td className="px-3 py-2.5">
                          <span className="flex gap-1.5 text-xs">
                            {(["critical", "warning", "info"] as const).map(s => of[s] > 0 && (
                              <span key={s} className="inline-flex items-center gap-1 text-gray-700"><span className={`w-2 h-2 rounded-full ${SEV_DOT[s]}`} />{of[s]}</span>
                            ))}
                            {of.critical + of.warning + of.info === 0 && <span className="text-green-700">✓</span>}
                          </span>
                        </td>
                      </>
                    ) : (
                      <td className="px-3 py-2.5">
                        {sup ? <span className={`text-xs px-2 py-0.5 rounded-full ${sup.tone}`}>{sup.text}</span> : <span className="text-xs text-green-700">✓</span>}
                      </td>
                    )}
                    <td className="px-4 py-2.5 text-right text-xs text-gray-500">
                      {e.last_scan?.scan_date ? new Date(e.last_scan.scan_date).toLocaleDateString(i18n.language) : "—"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>

      {selectedEntityId && <OsintEntityDrawer entityId={selectedEntityId} onClose={() => setSelectedEntityId(null)} />}
      {reporting && <ReportToSupplierDialog finding={reporting} onClose={() => setReporting(null)} />}
      {aiType && <OsintAiPanel type={aiType} onClose={() => setAiType(null)} />}
    </div>
  );
}

