import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import {
  osintApi, classifyScore, scoreBadgeColor, deltaArrow, deltaColor,
  type OsintEntity, type AlertSeverity,
} from "../../api/endpoints/osint";
import { OsintEntityDrawer } from "./OsintEntityDrawer";
import { OsintAiPanel } from "./OsintAiPanel";

type FilterType = "all" | "my_domain" | "supplier" | "asset";
type FilterAlert = "all" | "critical" | "warning";

function ScoreBadge({ score }: { score: number | undefined | null }) {
  if (score == null) return <span className="text-gray-400 text-xs">—</span>;
  const cls = classifyScore(score);
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-sm font-semibold ${scoreBadgeColor(cls)}`}>
      {score}
    </span>
  );
}

function SubScoreIcon({ value, threshold = 40 }: { value: number | undefined | null; threshold?: number }) {
  if (value == null) return <span className="text-gray-300">—</span>;
  if (value === 0) return <span title="OK">✅</span>;
  if (value < threshold) return <span title="Attenzione">⚠️</span>;
  return <span title="Critico">❌</span>;
}

export function OsintDashboard() {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [filterType, setFilterType] = useState<FilterType>("all");
  const [filterAlert, setFilterAlert] = useState<FilterAlert>("all");
  const [search, setSearch] = useState("");
  const [sortByScore, setSortByScore] = useState(true);
  const [selectedEntityId, setSelectedEntityId] = useState<string | null>(null);
  const [showAiPanel, setShowAiPanel] = useState(false);
  const [aiType, setAiType] = useState<"attack_surface" | "suppliers_nis2" | "board_report">("attack_surface");

  const { data: summary } = useQuery({
    queryKey: ["osint-summary"],
    queryFn: osintApi.dashboardSummary,
    refetchInterval: 60_000,
  });

  const { data: entities = [], isLoading } = useQuery({
    queryKey: ["osint-entities"],
    queryFn: () => osintApi.entities(),
  });

  const { data: pending = [] } = useQuery({
    queryKey: ["osint-subdomains-pending"],
    queryFn: osintApi.pendingSubdomains,
  });

  // Filtro locale
  const filtered = entities
    .filter(e => {
      if (filterType !== "all" && e.entity_type !== filterType) return false;
      if (filterAlert !== "all") {
        const s = e.last_scan?.score_total;
        if (s == null) return false;
        const cls = classifyScore(s);
        if (filterAlert === "critical" && cls !== "critical") return false;
        if (filterAlert === "warning" && cls !== "warning") return false;
      }
      if (search && !e.display_name.toLowerCase().includes(search.toLowerCase()) &&
          !e.domain.toLowerCase().includes(search.toLowerCase())) return false;
      return true;
    })
    .sort((a, b) => {
      if (!sortByScore) return a.display_name.localeCompare(b.display_name);
      const sa = a.last_scan?.score_total ?? 0;
      const sb = b.last_scan?.score_total ?? 0;
      return sb - sa;
    });

  function openAi(type: typeof aiType) {
    setAiType(type);
    setShowAiPanel(true);
  }

  return (
    <div className="p-4 sm:p-6 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">{t("osint.title")}</h1>
          <p className="text-sm text-gray-500">{t("osint.subtitle")}</p>
        </div>
        <Link to="/osint/settings" className="px-3 py-1.5 text-sm border rounded hover:bg-gray-50">
          ⚙ {t("osint.settings.title")}
        </Link>
      </div>

      {/* KPI cards */}
      {summary && (
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
          <KpiCard label={t("osint.kpi.entities")} value={summary.total_entities} />
          <KpiCard label={t("osint.kpi.critical")} value={summary.critical_count} valueClass="text-red-600" icon="🔴" />
          <KpiCard label={t("osint.kpi.warning")} value={summary.warning_count} valueClass="text-orange-600" icon="🟠" />
          <KpiCard
            label={t("osint.kpi.last_scan")}
            value={summary.last_scan_date ? new Date(summary.last_scan_date).toLocaleDateString("it-IT") : "—"}
          />
          <KpiCard label={t("osint.kpi.pending_subdomains")} value={summary.pending_subdomains} />
        </div>
      )}

      {/* Banner sottodomini pending */}
      {pending.length > 0 && (
        <div className="flex items-center gap-3 px-4 py-2 bg-yellow-50 border border-yellow-200 rounded-lg">
          <span>⚠️</span>
          <span className="text-sm text-yellow-800">
            {t("osint.subdomains.pending_banner", { count: pending.length })}
          </span>
          <Link to="/osint/subdomains" className="ml-auto text-xs text-yellow-700 hover:underline font-medium">
            {t("osint.subdomains.view_arrow")}
          </Link>
        </div>
      )}

      {/* Filtri e ricerca */}
      <div className="flex flex-wrap items-center gap-2">
        {(["all", "my_domain", "supplier"] as FilterType[]).map(ft => (
          <button
            key={ft}
            onClick={() => setFilterType(ft)}
            className={`px-3 py-1 rounded-full text-sm border ${filterType === ft ? "bg-primary-600 text-white border-primary-600" : "bg-white text-gray-600 border-gray-300 hover:bg-gray-50"}`}
          >
            {t(`osint.filters.${ft}`)}
          </button>
        ))}
        <button
          onClick={() => setFilterAlert(filterAlert === "critical" ? "all" : "critical")}
          className={`px-3 py-1 rounded-full text-sm border ${filterAlert === "critical" ? "bg-red-600 text-white border-red-600" : "bg-white text-gray-600 border-gray-300"}`}
        >
          {t("osint.filters.with_alert")}
        </button>
        <input
          value={search}
          onChange={e => setSearch(e.target.value)}
          placeholder={t("osint.search_placeholder")}
          className="ml-auto px-3 py-1.5 border rounded text-sm w-48"
        />
        <button
          onClick={() => setSortByScore(!sortByScore)}
          className="text-xs text-gray-500 hover:text-gray-700"
        >
          {t("osint.sort_by")}: {sortByScore ? t("osint.sort.score") : t("osint.sort.name")} ▼
        </button>
      </div>

      {/* Tabella entità */}
      <div className="overflow-x-auto border rounded-lg bg-white">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t("osint.table.entity")}</th>
              <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t("osint.table.type")}</th>
              <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t("osint.table.score")}</th>
              <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase">Δ</th>
              <th className="px-3 py-3 text-center text-xs font-medium text-gray-500 uppercase">SSL</th>
              <th className="px-3 py-3 text-center text-xs font-medium text-gray-500 uppercase">DNS</th>
              <th className="px-3 py-3 text-center text-xs font-medium text-gray-500 uppercase">{t("osint.table.reputation")}</th>
              <th className="px-3 py-3 text-center text-xs font-medium text-gray-500 uppercase">⚡</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {isLoading && (
              <tr><td colSpan={8} className="px-4 py-8 text-center text-gray-400">{t("common.loading")}</td></tr>
            )}
            {!isLoading && filtered.length === 0 && (
              <tr><td colSpan={8} className="px-4 py-8 text-center text-gray-400">{t("osint.table.no_entities")}</td></tr>
            )}
            {filtered.map(entity => (
              <EntityRow
                key={entity.id}
                entity={entity}
                onClick={() => setSelectedEntityId(entity.id)}
              />
            ))}
          </tbody>
        </table>
      </div>

      {/* Sezione AI */}
      <div className="border rounded-lg bg-white p-4">
        <div className="flex items-center gap-2 mb-3">
          <span className="text-lg">🤖</span>
          <h3 className="font-semibold text-gray-900">{t("osint.ai.title")}</h3>
        </div>
        <div className="flex flex-wrap gap-2">
          <button onClick={() => openAi("attack_surface")} className="px-4 py-2 border rounded text-sm hover:bg-gray-50">
            {t("osint.ai.attack_surface")}
          </button>
          <button onClick={() => openAi("suppliers_nis2")} className="px-4 py-2 border rounded text-sm hover:bg-gray-50">
            {t("osint.ai.suppliers_nis2")}
          </button>
          <button onClick={() => openAi("board_report")} className="px-4 py-2 border rounded text-sm hover:bg-gray-50">
            {t("osint.ai.board_report")}
          </button>
        </div>
      </div>

      {/* Drawer dettaglio entità */}
      {selectedEntityId && (
        <OsintEntityDrawer
          entityId={selectedEntityId}
          onClose={() => setSelectedEntityId(null)}
        />
      )}

      {/* Pannello AI */}
      {showAiPanel && (
        <OsintAiPanel type={aiType} onClose={() => setShowAiPanel(false)} />
      )}
    </div>
  );
}

function KpiCard({ label, value, valueClass = "text-gray-900", icon = "" }: {
  label: string; value: number | string; valueClass?: string; icon?: string;
}) {
  return (
    <div className="bg-white border rounded-lg p-3 text-center">
      <div className={`text-2xl font-bold ${valueClass}`}>{icon} {value}</div>
      <div className="text-xs text-gray-500 mt-0.5">{label}</div>
    </div>
  );
}

function EntityRow({ entity, onClick }: { entity: OsintEntity; onClick: () => void }) {
  const { t } = useTranslation();
  const scan = entity.last_scan;
  const delta = entity.delta;

  return (
    <tr
      className="hover:bg-gray-50 cursor-pointer transition-colors"
      onClick={onClick}
    >
      <td className="px-4 py-3">
        <div className="font-medium text-sm text-gray-900 truncate max-w-[200px]">{entity.display_name}</div>
        <div className="text-xs text-gray-400 truncate">{entity.domain}</div>
      </td>
      <td className="px-3 py-3">
        <span className="text-xs text-gray-600">
          {entity.entity_type === "my_domain" ? t("osint.entity_type.my_domain") :
           entity.entity_type === "supplier" ? t("osint.entity_type.supplier") : t("osint.entity_type.asset")}
          {entity.is_nis2_critical && <span className="ml-1 text-orange-500" title="NIS2 critico">★</span>}
        </span>
      </td>
      <td className="px-3 py-3">
        {scan ? <ScoreBadge score={scan.score_total} /> : <span className="text-gray-400 text-xs">—</span>}
      </td>
      <td className="px-3 py-3">
        <span className={`text-xs font-medium ${deltaColor(delta)}`}>
          {deltaArrow(delta)}
        </span>
      </td>
      <td className="px-3 py-3 text-center">
        <SubScoreIcon value={scan?.score_ssl} />
      </td>
      <td className="px-3 py-3 text-center">
        <SubScoreIcon value={scan?.score_dns} />
      </td>
      <td className="px-3 py-3 text-center">
        <SubScoreIcon value={scan?.score_reputation} />
      </td>
      <td className="px-3 py-3 text-center">
        {entity.active_alerts_count > 0 ? (
          <span className="text-xs font-bold text-red-600">{entity.active_alerts_count}</span>
        ) : (
          <span className="text-gray-300">0</span>
        )}
      </td>
    </tr>
  );
}
