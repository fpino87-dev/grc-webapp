import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import { cockpitApi, type CockpitArea, type CockpitInsight, type InsightAction, type InsightSeverity } from "../../api/endpoints/cockpit";
import { useAuthStore } from "../../store/auth";
import { addDaysISO, todayISO } from "../../utils/dates";

const AREAS: CockpitArea[] = [
  "governance", "controls", "risk", "incidents", "supply_chain", "technical", "continuity",
];

const SEV_BADGE: Record<InsightSeverity, string> = {
  critical: "bg-red-100 text-red-700 border-red-200",
  warning: "bg-amber-100 text-amber-700 border-amber-200",
  info: "bg-sky-100 text-sky-700 border-sky-200",
};

function scoreColor(score: number): string {
  if (score >= 70) return "text-red-600";
  if (score >= 40) return "text-amber-600";
  if (score >= 15) return "text-yellow-600";
  return "text-green-600";
}
function barColor(score: number): string {
  if (score >= 70) return "bg-red-500";
  if (score >= 40) return "bg-amber-500";
  if (score >= 15) return "bg-yellow-400";
  return "bg-green-500";
}
function isoIn(days: number): string {
  return addDaysISO(todayISO(), days);
}

export function CockpitPage() {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const selectedPlant = useAuthStore(s => s.selectedPlant);
  const [areaFilter, setAreaFilter] = useState<CockpitArea | "all">("all");
  const [sevFilter, setSevFilter] = useState<InsightSeverity | "all">("all");
  const [mine, setMine] = useState(false);
  const [showSuppressed, setShowSuppressed] = useState(false);

  const plantId = selectedPlant?.id;
  const { data, isLoading, isError } = useQuery({
    queryKey: ["cockpit-insights", plantId ?? null, mine, showSuppressed],
    queryFn: () => cockpitApi.insights(plantId, { mine, includeSuppressed: showSuppressed }),
  });
  const { data: trend } = useQuery({
    queryKey: ["cockpit-trend", plantId ?? null],
    queryFn: () => cockpitApi.trend(plantId, 120),
    retry: false,
  });

  const action = useMutation({
    mutationFn: ({ fp, act, until, note }: { fp: string; act: InsightAction; until?: string; note?: string }) =>
      cockpitApi.action(fp, act, { until, note }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["cockpit-insights"] }),
  });

  const list = useMemo(() => {
    let l = data?.insights ?? [];
    if (showSuppressed && data?.suppressed) l = [...l, ...data.suppressed];
    if (areaFilter !== "all") l = l.filter(i => i.area === areaFilter);
    if (sevFilter !== "all") l = l.filter(i => i.severity === sevFilter);
    return l;
  }, [data, areaFilter, sevFilter, showSuppressed]);

  if (isLoading) return <div className="p-6 text-gray-400">{t("common.loading")}</div>;
  if (isError || !data) return <div className="p-6 text-red-600">{t("cockpit.load_error")}</div>;

  const posture = data.posture;

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-xl font-bold text-gray-900">🎛 {t("cockpit.title")}</h1>
        <p className="text-sm text-gray-500">{t("cockpit.subtitle")}</p>
      </div>

      {/* Posture Score + trend */}
      <section className="bg-white border rounded-xl p-5">
        <div className="flex items-center gap-6 flex-wrap">
          <div className="text-center">
            <div className={`text-5xl font-bold ${scoreColor(posture.total)}`}>{posture.total}</div>
            <div className="text-xs text-gray-500 uppercase mt-1">{t("cockpit.posture.score")}</div>
          </div>
          <div className="flex-1 min-w-[240px] space-y-1.5">
            {AREAS.map(area => {
              const a = posture.areas[area] ?? { score: 0 };
              return (
                <div key={area} className="flex items-center gap-2">
                  <span className="text-xs text-gray-600 w-28 shrink-0">{t(`cockpit.areas.${area}`)}</span>
                  <div className="flex-1 h-2.5 bg-gray-100 rounded">
                    <div className={`h-2.5 rounded ${barColor(a.score)}`} style={{ width: `${a.score}%` }} />
                  </div>
                  <span className="text-xs font-mono text-gray-500 w-7 text-right">{a.score}</span>
                </div>
              );
            })}
          </div>
          {trend && trend.length > 1 && (
            <div className="w-48 h-24">
              <p className="text-[11px] text-gray-400 mb-1">{t("cockpit.posture.trend")}</p>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={trend.map(p => ({ date: p.date.slice(5), total: p.total }))}>
                  <XAxis dataKey="date" tick={{ fontSize: 9 }} interval="preserveStartEnd" />
                  <YAxis domain={[0, 100]} hide />
                  <Tooltip />
                  <Line type="monotone" dataKey="total" stroke="#4f46e5" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      </section>

      {/* Chiedi a govrico */}
      <CopilotBox plantId={plantId} t={t} />

      {/* Filtri */}
      <div className="flex gap-3 items-center flex-wrap">
        <select value={areaFilter} onChange={e => setAreaFilter(e.target.value as CockpitArea | "all")}
          className="border rounded px-3 py-1.5 text-sm">
          <option value="all">{t("cockpit.filters.all_areas")}</option>
          {AREAS.map(a => <option key={a} value={a}>{t(`cockpit.areas.${a}`)}</option>)}
        </select>
        <select value={sevFilter} onChange={e => setSevFilter(e.target.value as InsightSeverity | "all")}
          className="border rounded px-3 py-1.5 text-sm">
          <option value="all">{t("cockpit.filters.all_severities")}</option>
          <option value="critical">{t("cockpit.severity.critical")}</option>
          <option value="warning">{t("cockpit.severity.warning")}</option>
          <option value="info">{t("cockpit.severity.info")}</option>
        </select>
        <label className="text-sm text-gray-600 flex items-center gap-1.5">
          <input type="checkbox" checked={mine} onChange={e => setMine(e.target.checked)} /> {t("cockpit.filters.mine")}
        </label>
        <label className="text-sm text-gray-600 flex items-center gap-1.5">
          <input type="checkbox" checked={showSuppressed} onChange={e => setShowSuppressed(e.target.checked)} />
          {t("cockpit.filters.show_suppressed")} {data.suppressed_count > 0 && `(${data.suppressed_count})`}
        </label>
        <span className="text-sm text-gray-400 ml-auto">{t("cockpit.count_shown", { n: list.length })}</span>
      </div>

      {/* Lista insight */}
      {list.length === 0 ? (
        <div className="bg-white border rounded-xl p-10 text-center text-gray-400">✅ {t("cockpit.empty")}</div>
      ) : (
        <div className="space-y-3">
          {list.map(i => (
            <InsightCard key={i.fingerprint} insight={i} t={t}
              onAction={(act, until, note) => action.mutate({ fp: i.fingerprint, act, until, note })}
              busy={action.isPending} />
          ))}
        </div>
      )}
    </div>
  );
}

function CopilotBox({ plantId, t }: { plantId?: string; t: (k: string, o?: Record<string, unknown>) => string }) {
  const [q, setQ] = useState("");
  const [answer, setAnswer] = useState<string | null>(null);
  const ask = useMutation({
    mutationFn: () => cockpitApi.assistant(q, plantId),
    onSuccess: a => setAnswer(a),
  });
  return (
    <section className="bg-white border rounded-xl p-4">
      <div className="flex items-center gap-2">
        <span className="text-lg">🤖</span>
        <input
          value={q}
          onChange={e => setQ(e.target.value)}
          onKeyDown={e => { if (e.key === "Enter" && q.trim()) ask.mutate(); }}
          placeholder={t("cockpit.ai.ask_placeholder")}
          className="flex-1 border rounded px-3 py-1.5 text-sm"
        />
        <button
          disabled={!q.trim() || ask.isPending}
          onClick={() => ask.mutate()}
          className="text-sm px-4 py-1.5 bg-indigo-600 text-white rounded hover:bg-indigo-700 disabled:opacity-50"
        >
          {ask.isPending ? t("cockpit.ai.thinking") : t("cockpit.ai.ask")}
        </button>
      </div>
      <p className="mt-2 rounded border border-sky-200 bg-sky-50 px-3 py-2 text-xs text-sky-800">
        🔒 {t("ai.cloud_pii_notice")}
      </p>
      {ask.isError && <p className="text-xs text-red-600 mt-2">{t("cockpit.ai.error")}</p>}
      {answer && (
        <div className="mt-3 bg-gray-50 border rounded-lg p-3">
          <p className="text-sm text-gray-700 whitespace-pre-wrap">{answer}</p>
          <p className="text-[10px] text-gray-400 mt-1.5">{t("cockpit.ai.disclaimer")}</p>
        </div>
      )}
    </section>
  );
}

function InsightCard({ insight, t, onAction, busy }: {
  insight: CockpitInsight;
  t: (k: string, o?: Record<string, unknown>) => string;
  onAction: (act: InsightAction, until?: string, note?: string) => void;
  busy: boolean;
}) {
  const [aiText, setAiText] = useState<string | null>(null);
  const explain = useMutation({
    mutationFn: () => cockpitApi.explain(insight.fingerprint),
    onSuccess: d => setAiText(d.text),
  });
  const title = t(`cockpit.insights.${insight.code}.title`, { ...insight.params, defaultValue: insight.code });
  const what = t(`cockpit.insights.${insight.code}.what`, { ...insight.params, defaultValue: "" });
  const act = t(`cockpit.insights.${insight.code}.action`, { ...insight.params, defaultValue: "" });
  const deepLink = insight.entity_ref?.deep_link ?? null;
  const state = insight.state;
  const suppressed = state && (state.status === "snoozed" || state.status === "accepted_risk");

  return (
    <div className={`bg-white border rounded-xl p-4 flex gap-4 items-start ${suppressed ? "opacity-60" : ""}`}>
      <span className={`text-[11px] font-semibold px-2 py-0.5 rounded border uppercase shrink-0 ${SEV_BADGE[insight.severity]}`}>
        {t(`cockpit.severity.${insight.severity}`)}
      </span>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-[11px] text-gray-400 uppercase">{t(`cockpit.areas.${insight.area}`)}</span>
          {insight.params.plant_name ? <span className="text-[11px] text-gray-500">· {String(insight.params.plant_name)}</span> : null}
          {state && state.status === "snoozed" && (
            <span className="text-[10px] bg-indigo-50 text-indigo-600 px-1.5 py-0.5 rounded">💤 {t("cockpit.state.snoozed", { date: state.snoozed_until ?? "" })}</span>
          )}
          {state && state.status === "accepted_risk" && (
            <span className="text-[10px] bg-purple-50 text-purple-600 px-1.5 py-0.5 rounded">✔ {t("cockpit.state.accepted", { date: state.accepted_until ?? "" })}</span>
          )}
        </div>
        <p className="text-sm font-medium text-gray-800 mt-0.5">{title}</p>
        {what && <p className="text-xs text-gray-500 mt-0.5">{what}</p>}
        {Array.isArray(insight.params.categories) && (insight.params.categories as Array<{ key: string; count: number }>).length > 0 && (
          <div className="flex flex-wrap gap-x-4 gap-y-1 mt-1.5">
            {(insight.params.categories as Array<{ key: string; count: number }>).map(c => (
              <span key={c.key} className="text-xs text-gray-700">
                <span className="font-semibold">{c.count}</span> {t(`cockpit.breakdown.${c.key}`, { defaultValue: c.key })}
              </span>
            ))}
          </div>
        )}
        {act && <p className="text-xs text-gray-700 mt-1">→ {act}</p>}
        <div className="flex items-center gap-2 mt-2 flex-wrap">
          {insight.compliance_refs.map((c, idx) => (
            <span key={idx} className="text-[10px] bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded">{c.framework} {c.control}</span>
          ))}
          {insight.owner_role && <span className="text-[10px] text-gray-400">{t("cockpit.owner")}: {insight.owner_role}</span>}
        </div>
        {(explain.isPending || aiText || explain.isError) && (
          <div className="mt-2 bg-indigo-50/60 border border-indigo-100 rounded-lg p-2.5">
            <div className="flex items-center justify-between mb-1">
              <span className="text-[11px] font-semibold text-indigo-700">✨ {t("cockpit.ai.draft_label")}</span>
              {aiText && <button onClick={() => setAiText(null)} className="text-[11px] text-gray-400 hover:text-gray-600">✕</button>}
            </div>
            {explain.isPending && <p className="text-xs text-gray-500">{t("cockpit.ai.thinking")}</p>}
            {explain.isError && <p className="text-xs text-red-600">{t("cockpit.ai.error")}</p>}
            {aiText && <p className="text-xs text-gray-700 whitespace-pre-wrap">{aiText}</p>}
            {aiText && <p className="text-[10px] text-gray-400 mt-1.5">{t("cockpit.ai.disclaimer")}</p>}
          </div>
        )}
      </div>
      <div className="flex flex-col gap-1 shrink-0 items-end">
        {deepLink && (
          <Link to={deepLink} className="text-xs px-3 py-1 bg-primary-600 text-white rounded hover:bg-primary-700">{t("cockpit.go")}</Link>
        )}
        <button disabled={explain.isPending} onClick={() => explain.mutate()} className="text-[11px] px-2 py-0.5 border border-indigo-200 text-indigo-600 rounded hover:bg-indigo-50 disabled:opacity-50">✨ {t("cockpit.ai.explain")}</button>
        {suppressed ? (
          <button disabled={busy} onClick={() => onAction("reopen")} className="text-[11px] px-2 py-0.5 border rounded text-gray-600 hover:bg-gray-50 disabled:opacity-50">{t("cockpit.actions.reopen")}</button>
        ) : (
          <>
            <button disabled={busy} onClick={() => onAction("snooze", isoIn(7))} className="text-[11px] px-2 py-0.5 border rounded text-gray-600 hover:bg-gray-50 disabled:opacity-50">{t("cockpit.actions.snooze")}</button>
            <button disabled={busy} onClick={() => onAction("accept", isoIn(90))} className="text-[11px] px-2 py-0.5 border rounded text-gray-600 hover:bg-gray-50 disabled:opacity-50">{t("cockpit.actions.accept")}</button>
          </>
        )}
      </div>
    </div>
  );
}
