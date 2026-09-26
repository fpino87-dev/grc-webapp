import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useQuery } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router-dom";
import { LineChart, Line, ResponsiveContainer, YAxis, Tooltip } from "recharts";
import {
  reportingApi,
  type ComplianceCounts,
  type ComplianceFramework,
  type ComplianceOverview,
} from "../../api/endpoints/reporting";
import { plantsApi } from "../../api/endpoints/plants";
import { useAuthStore } from "../../store/auth";

// Stati che entrano nel denominatore, nell'ordine in cui compaiono nelle barre.
const STATUSES = ["compliant", "parziale", "gap", "non_valutato"] as const;
type Status = typeof STATUSES[number];

const STATUS_BG: Record<Status, string> = {
  compliant: "bg-green-500",
  parziale: "bg-yellow-400",
  gap: "bg-red-500",
  non_valutato: "bg-gray-300",
};

const STATUS_TEXT: Record<Status, string> = {
  compliant: "text-green-700",
  parziale: "text-yellow-700",
  gap: "text-red-600",
  non_valutato: "text-gray-500",
};

// Soglie di colore della percentuale: stesse per schede e confronto siti.
function pctClasses(pct: number): string {
  if (pct >= 80) return "bg-green-50 text-green-800 border-green-200";
  if (pct >= 50) return "bg-yellow-50 text-yellow-800 border-yellow-200";
  return "bg-red-50 text-red-700 border-red-200";
}

function controlsLink(framework: string, opts: { status?: string; domain?: string } = {}): string {
  const p = new URLSearchParams({ framework });
  if (opts.status) p.set("status", opts.status);
  if (opts.domain) p.set("domain", opts.domain);
  return `/controls?${p.toString()}`;
}

function StatusBar({ counts, height = "h-2.5" }: { counts: ComplianceCounts; height?: string }) {
  const { t } = useTranslation();
  if (counts.total === 0) return <div className={`${height} rounded bg-gray-100`} />;
  return (
    <div className={`flex ${height} rounded overflow-hidden bg-gray-100`}>
      {STATUSES.map(s => {
        const n = counts[s];
        if (!n) return null;
        return (
          <div
            key={s}
            className={STATUS_BG[s]}
            style={{ width: `${(n / counts.total) * 100}%` }}
            title={`${t(`status.${s}`)}: ${n}`}
          />
        );
      })}
    </div>
  );
}

function Delta({ delta }: { delta: number | null }) {
  const { t } = useTranslation();
  if (delta === null) return null;
  const cls = delta > 0 ? "text-green-700" : delta < 0 ? "text-red-600" : "text-gray-500";
  const sign = delta > 0 ? "▲ +" : delta < 0 ? "▼ " : "= ";
  return (
    <span className={`text-xs font-medium ${cls}`} title={t("reporting.compliance.delta_hint")}>
      {sign}{delta}
    </span>
  );
}

function Sparkline({ fw }: { fw: ComplianceFramework }) {
  const { t } = useTranslation();
  // Due serie: i punti calcolati con la regola precedente in grigio, gli altri
  // colorati. Il primo punto con la regola attuale compare in entrambe così la
  // linea resta continua.
  const firstCurrent = fw.trend.findIndex(p => !p.legacy);
  const data = fw.trend.map((p, i) => ({
    date: p.date,
    live: p.live,
    legacy: p.legacy || i === firstCurrent ? p.pct_compliant : null,
    current: p.legacy ? null : p.pct_compliant,
  }));
  if (data.length < 2) return <div className="h-10" />;
  return (
    <ResponsiveContainer width="100%" height={40}>
      <LineChart data={data} margin={{ top: 4, right: 2, left: 2, bottom: 2 }}>
        <YAxis hide domain={[0, 100]} />
        <Tooltip
          formatter={(v) => [`${v}%`, ""]}
          labelFormatter={(_, payload) => {
            const p = payload?.[0]?.payload as { date: string; live: boolean } | undefined;
            if (!p) return "";
            return p.live ? t("reporting.compliance.today") : p.date;
          }}
        />
        <Line type="monotone" dataKey="legacy" stroke="#9ca3af" strokeDasharray="3 3" dot={false} isAnimationActive={false} connectNulls />
        <Line type="monotone" dataKey="current" stroke="#4f46e5" strokeWidth={2} dot={false} isAnimationActive={false} connectNulls />
      </LineChart>
    </ResponsiveContainer>
  );
}

function FrameworkCard({ fw, selected, onDetail }: { fw: ComplianceFramework; selected: boolean; onDetail: () => void }) {
  const { t } = useTranslation();
  return (
    <div className={`bg-white rounded-lg border p-4 flex flex-col gap-2 ${selected ? "border-primary-400 ring-1 ring-primary-200" : "border-gray-200"}`}>
      <div className="flex items-start justify-between gap-2">
        <span className="text-sm font-semibold text-gray-800">{fw.name}</span>
        <Delta delta={fw.delta} />
      </div>
      <div className="flex items-baseline gap-2">
        <span className="text-3xl font-bold text-gray-900">{fw.total ? `${fw.pct_compliant}%` : "—"}</span>
        <span className="text-xs text-gray-400">{t("reporting.compliance.compliant_of", { compliant: fw.compliant, total: fw.total })}</span>
      </div>
      <Sparkline fw={fw} />
      <StatusBar counts={fw} />
      <div className="flex flex-wrap gap-x-3 gap-y-0.5 text-xs">
        {(["gap", "parziale", "non_valutato"] as const).map(s => (
          fw[s] > 0 ? (
            <Link key={s} to={controlsLink(fw.code, { status: s })} className={`${STATUS_TEXT[s]} hover:underline`}>
              {t(`status.${s}`)} {fw[s]}
            </Link>
          ) : null
        ))}
      </div>
      {(fw.superseded_by_extender > 0 || fw.na_excluded > 0) && (
        <p className="text-xs text-gray-400">
          {fw.superseded_by_extender > 0 && t("reporting.compliance.superseded", { count: fw.superseded_by_extender })}
          {fw.superseded_by_extender > 0 && fw.na_excluded > 0 && " · "}
          {fw.na_excluded > 0 && t("reporting.compliance.na_excluded", { count: fw.na_excluded })}
        </p>
      )}
      <button onClick={onDetail} className="mt-auto self-start text-xs font-medium text-primary-600 hover:underline">
        {t("reporting.compliance.see_detail")} ↓
      </button>
    </div>
  );
}

function PlantsMatrix({ overview }: { overview: ComplianceOverview }) {
  const { t } = useTranslation();
  const setPlant = useAuthStore(s => s.setPlant);
  const { data: plants } = useQuery({ queryKey: ["plants"], queryFn: () => plantsApi.list(), retry: false });
  if (!overview.plants || overview.plants.length === 0) return null;

  const selectPlant = (id: string) => {
    const p = plants?.find(pl => pl.id === id);
    if (p) setPlant(p);
  };

  return (
    <section>
      <h3 className="text-sm font-semibold text-gray-700 mb-1">{t("reporting.compliance.plants_title")}</h3>
      <p className="text-xs text-gray-400 mb-3">{t("reporting.compliance.plants_hint")}</p>
      <div className="bg-white rounded-lg border border-gray-200 overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th className="text-left px-4 py-2 font-medium text-gray-600">{t("reporting.compliance.col_plant")}</th>
              {overview.frameworks.map(fw => (
                <th key={fw.code} className="text-center px-3 py-2 font-medium text-gray-600 whitespace-nowrap">{fw.name}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {overview.plants.map(p => (
              <tr key={p.id}>
                <td className="px-4 py-2">
                  <span className="font-medium text-gray-800">[{p.code}]</span>{" "}
                  <span className="text-gray-600">{p.name}</span>
                </td>
                {overview.frameworks.map(fw => {
                  const cell = p.cells[fw.code];
                  if (!cell || cell.total === 0) {
                    return <td key={fw.code} className="px-3 py-2 text-center text-gray-300">—</td>;
                  }
                  const open = cell.gap + cell.parziale + cell.non_valutato;
                  return (
                    <td key={fw.code} className="px-3 py-2 text-center">
                      <button
                        onClick={() => selectPlant(p.id)}
                        className={`inline-block min-w-[4.5rem] px-2 py-1 rounded border text-sm font-semibold hover:opacity-80 ${pctClasses(cell.pct_compliant)}`}
                        title={t("reporting.compliance.cell_hint", { open, gap: cell.gap })}
                      >
                        {cell.pct_compliant}%
                      </button>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function DomainDetail({ frameworks, framework, onFramework }: {
  frameworks: ComplianceFramework[];
  framework: string;
  onFramework: (code: string) => void;
}) {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const selectedPlant = useAuthStore(s => s.selectedPlant);
  const { data, isLoading } = useQuery({
    queryKey: ["reporting-compliance-domains", framework, selectedPlant?.id, i18n.language],
    queryFn: () => reportingApi.complianceDomains(framework, selectedPlant?.id),
    enabled: !!framework,
    retry: false,
  });

  return (
    <section>
      <div className="flex items-center justify-between gap-3 flex-wrap mb-3">
        <div>
          <h3 className="text-sm font-semibold text-gray-700">{t("reporting.compliance.domains_title")}</h3>
          <p className="text-xs text-gray-400">{t("reporting.compliance.domains_hint")}</p>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <select
            value={framework}
            onChange={e => onFramework(e.target.value)}
            className="border border-gray-300 rounded px-2 py-1.5 text-sm"
            aria-label={t("reporting.compliance.framework_label")}
          >
            {frameworks.map(fw => <option key={fw.code} value={fw.code}>{fw.name}</option>)}
          </select>
          <button
            onClick={() => navigate("/gap-analysis")}
            className="text-xs font-medium text-gray-600 border border-gray-300 rounded px-3 py-1.5 hover:bg-gray-50"
          >
            {t("reporting.compliance.gap_analysis")} →
          </button>
          <button
            onClick={() => reportingApi.exportComplianceOpenControlsCsv(framework, selectedPlant?.id)}
            className="text-xs font-medium text-gray-600 border border-gray-300 rounded px-3 py-1.5 hover:bg-gray-50"
            title={t("reporting.compliance.export_hint")}
          >
            ⬇ {t("reporting.compliance.export_csv")}
          </button>
        </div>
      </div>

      <div className="bg-white rounded-lg border border-gray-200 overflow-x-auto">
        {isLoading ? (
          <p className="p-6 text-center text-gray-400 text-sm">{t("reporting.loading")}</p>
        ) : !data || data.domains.length === 0 ? (
          <p className="p-6 text-center text-gray-400 text-sm">{t("reporting.no_data")}</p>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-4 py-2 font-medium text-gray-600">{t("reporting.compliance.col_domain")}</th>
                <th className="text-left px-3 py-2 font-medium text-gray-600 w-1/4">{t("reporting.compliance.col_distribution")}</th>
                <th className="text-right px-3 py-2 font-medium text-red-600">{t("status.gap")}</th>
                <th className="text-right px-3 py-2 font-medium text-yellow-700">{t("status.parziale")}</th>
                <th className="text-right px-3 py-2 font-medium text-gray-500">{t("status.non_valutato")}</th>
                <th className="text-right px-3 py-2 font-medium text-gray-600">%</th>
                <th className="px-3 py-2" />
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {data.domains.map(d => (
                <tr key={d.code || "none"} className="hover:bg-gray-50">
                  <td className="px-4 py-2">
                    <span className="font-mono text-xs text-gray-500 mr-2">{d.code || "—"}</span>
                    <span className="text-gray-800">{d.name || t("reporting.compliance.no_domain")}</span>
                  </td>
                  <td className="px-3 py-2"><StatusBar counts={d} height="h-2" /></td>
                  {(["gap", "parziale", "non_valutato"] as const).map(s => (
                    <td key={s} className={`px-3 py-2 text-right tabular-nums ${d[s] ? `font-semibold ${STATUS_TEXT[s]}` : "text-gray-300"}`}>
                      {d[s] && d.code ? (
                        <Link to={controlsLink(framework, { status: s, domain: d.code })} className="hover:underline">{d[s]}</Link>
                      ) : (d[s] || "—")}
                    </td>
                  ))}
                  <td className="px-3 py-2 text-right tabular-nums font-medium text-gray-700">
                    {d.total ? `${d.pct_compliant}%` : "—"}
                  </td>
                  <td className="px-3 py-2 text-right">
                    {d.code && (
                      <Link to={controlsLink(framework, { domain: d.code })} className="text-xs text-primary-600 hover:underline whitespace-nowrap">
                        {t("reporting.compliance.open_controls")} →
                      </Link>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </section>
  );
}

export function TabCompliance() {
  const { t } = useTranslation();
  const selectedPlant = useAuthStore(s => s.selectedPlant);
  const [detailFw, setDetailFw] = useState("");

  const { data, isLoading } = useQuery({
    queryKey: ["reporting-compliance-overview", selectedPlant?.id],
    queryFn: () => reportingApi.complianceOverview(selectedPlant?.id),
    retry: false,
  });

  const frameworks = data?.frameworks ?? [];
  // Framework del dettaglio: quello scelto dall'utente se esiste nel perimetro,
  // altrimenti il primo con più controlli aperti.
  const worst = [...frameworks].sort(
    (a, b) => (b.gap + b.parziale + b.non_valutato) - (a.gap + a.parziale + a.non_valutato),
  )[0];
  const activeFw = frameworks.some(f => f.code === detailFw) ? detailFw : (worst?.code ?? "");

  if (isLoading) return <div className="p-8 text-center text-gray-400">{t("reporting.loading_compliance")}</div>;
  if (!data || frameworks.length === 0) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-8 text-center text-gray-400">
        {t("reporting.no_compliance_data")}
      </div>
    );
  }

  const hasLegacy = frameworks.some(f => f.trend.some(p => p.legacy));

  const showDetail = (code: string) => {
    setDetailFw(code);
    document.getElementById("compliance-domains")?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  return (
    <div className="space-y-8">
      <section>
        <div className="flex items-baseline justify-between gap-3 flex-wrap mb-3">
          <h3 className="text-sm font-semibold text-gray-700">
            {selectedPlant
              ? t("reporting.compliance.summary_title_plant", { plant: `[${selectedPlant.code}] ${selectedPlant.name}` })
              : t("reporting.compliance.summary_title_org")}
          </h3>
          <span className="text-xs text-gray-400">{t("reporting.compliance.rule_hint")}</span>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
          {frameworks.map(fw => (
            <FrameworkCard key={fw.code} fw={fw} selected={fw.code === activeFw} onDetail={() => showDetail(fw.code)} />
          ))}
        </div>
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 mt-3 text-xs text-gray-500">
          {STATUSES.map(s => (
            <span key={s} className="flex items-center gap-1.5">
              <span className={`w-3 h-3 rounded-sm inline-block ${STATUS_BG[s]}`} />
              {t(`status.${s}`)}
            </span>
          ))}
        </div>
        {hasLegacy && (
          <p className="text-xs text-gray-400 mt-2">{t("reporting.compliance.legacy_note")}</p>
        )}
      </section>

      {!selectedPlant && <PlantsMatrix overview={data} />}

      <div id="compliance-domains">
        {activeFw && <DomainDetail frameworks={frameworks} framework={activeFw} onFramework={setDetailFw} />}
      </div>
    </div>
  );
}
