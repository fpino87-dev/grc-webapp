import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import {
  reportingApi,
  type ObjectiveKpiItem,
  type ObjectiveReportItem,
  type ObjectivesPlantRow,
} from "../../api/endpoints/reporting";
import { plantsApi } from "../../api/endpoints/plants";
import { useAuthStore } from "../../store/auth";
import { ProgressBar, TrackBadge } from "../objectives/objectiveBadges";

// Tab volutamente separato dai KPI: la soglia di un KPI è un pavimento ("siamo
// sotto il livello accettabile adesso?"), l'obiettivo è una traiettoria
// ("arriveremo al target entro la scadenza?"). Stessi numeri, domande diverse.

const KPI_STATUS_STYLE: Record<ObjectiveKpiItem["kpi_status"], string> = {
  ok: "bg-green-100 text-green-700 border-green-300",
  warning: "bg-amber-100 text-amber-800 border-amber-300",
  critical: "bg-red-100 text-red-700 border-red-300",
  no_data: "bg-gray-100 text-gray-500 border-gray-300",
};

const th = "px-3 py-2 text-left font-medium text-gray-600";
const td = "px-3 py-2.5 align-middle";

function useFmt() {
  const { i18n } = useTranslation();
  const nf = new Intl.NumberFormat(i18n.language, { maximumFractionDigits: 1 });
  return (v: number | null, unit = "") => (v === null ? "—" : `${nf.format(v)}${unit ? ` ${unit}` : ""}`);
}

function Counter({ label, value, tone }: { label: string; value: number; tone: string }) {
  return (
    <div className={`bg-white border rounded-lg p-4 ${tone}`}>
      <p className="text-xs text-gray-500 uppercase tracking-wide">{label}</p>
      <p className="text-3xl font-bold mt-1 tabular-nums">{value}</p>
    </div>
  );
}

function ObjectiveCell({ o }: { o: ObjectiveReportItem }) {
  const { t } = useTranslation();
  return (
    <td className={td}>
      <Link to={`/objectives?id=${o.id}`} className="font-medium text-primary-700 hover:underline">
        {o.title}
      </Link>
      <p className="text-xs text-gray-500">
        {o.code} · {o.plant_code ?? t("objectives.fields.plant_org")}
        {o.owner_role ? ` · ${t(`governance.roles.${o.owner_role}`)}` : ""}
      </p>
    </td>
  );
}

function PlantTable({ rows }: { rows: ObjectivesPlantRow[] }) {
  const { t } = useTranslation();
  const num = "px-3 py-2.5 text-right tabular-nums";
  const cell = (n: number, color: string) => (
    <td className={`${num} ${n > 0 ? color : "text-gray-300"}`}>{n}</td>
  );
  return (
    <div className="bg-white border border-gray-200 rounded-lg overflow-x-auto">
      <table className="w-full text-sm">
        <thead className="bg-gray-50 border-b border-gray-200 text-xs uppercase tracking-wide">
          <tr>
            <th className={th}>{t("reporting.objectives.col_scope")}</th>
            <th className={`${th} text-right`}>{t("reporting.objectives.col_active")}</th>
            <th className={`${th} text-right`}>{t("objectives.track.in_linea")}</th>
            <th className={`${th} text-right`}>{t("objectives.track.a_rischio")}</th>
            <th className={`${th} text-right`}>{t("objectives.track.mancato")}</th>
            <th className={`${th} text-right`}>{t("objectives.track.senza_misure")}</th>
            <th className={`${th} text-right`}>{t("reporting.objectives.col_in_preparation")}</th>
            <th className={`${th} text-right`}>{t("reporting.objectives.col_achieved")}</th>
            <th className={`${th} text-right`}>{t("reporting.objectives.col_not_achieved")}</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(r => (
            <tr key={r.plant_id ?? "org"} className="border-b border-gray-100">
              <td className={td}>
                {r.plant_id ? (
                  <>
                    <span className="font-medium text-gray-900">[{r.plant_code}] {r.plant_name}</span>
                    {r.bu_code && <span className="text-xs text-gray-400 ml-2">{r.bu_code}</span>}
                  </>
                ) : (
                  <span className="font-medium text-gray-900">{t("objectives.fields.plant_org")}</span>
                )}
              </td>
              <td className={`${num} font-semibold`}>{r.attivi}</td>
              {cell(r.in_linea, "text-green-700")}
              {cell(r.a_rischio, "text-amber-700 font-semibold")}
              {cell(r.mancato, "text-red-700 font-semibold")}
              {cell(r.senza_misure, "text-gray-600")}
              {cell(r.in_preparazione, "text-gray-600")}
              {cell(r.raggiunti, "text-green-700")}
              {cell(r.non_raggiunti, "text-red-700")}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function DeadlinesTable({ items }: { items: ObjectiveReportItem[] }) {
  const { t } = useTranslation();
  const fmt = useFmt();
  return (
    <div className="bg-white border border-gray-200 rounded-lg overflow-x-auto">
      <table className="w-full text-sm">
        <thead className="bg-gray-50 border-b border-gray-200 text-xs uppercase tracking-wide">
          <tr>
            <th className={th}>{t("objectives.fields.objective")}</th>
            <th className={th}>{t("objectives.fields.target_date")}</th>
            <th className={th}>{t("objectives.baseline_to_target")}</th>
            <th className={th}>{t("objectives.current_value")}</th>
            <th className={th}>{t("objectives.progress")}</th>
            <th className={th}>{t("objectives.fields.track")}</th>
          </tr>
        </thead>
        <tbody>
          {items.map(o => (
            <tr key={o.id} className="border-b border-gray-100">
              <ObjectiveCell o={o} />
              <td className={`${td} whitespace-nowrap`}>
                <span className="text-gray-700">{o.target_date}</span>
                <p className={`text-xs ${o.days_to_target < 0 ? "text-red-600 font-medium" : "text-gray-500"}`}>
                  {o.days_to_target < 0
                    ? t("reporting.objectives.overdue_days", { n: -o.days_to_target })
                    : t("reporting.objectives.days_left", { n: o.days_to_target })}
                </p>
              </td>
              <td className={`${td} whitespace-nowrap text-gray-600`}>
                {fmt(o.baseline_value)} → {fmt(o.target_value, o.unit)}
              </td>
              <td className={`${td} whitespace-nowrap font-medium`}>{fmt(o.current_value, o.unit)}</td>
              <td className={td}><ProgressBar progress={o.progress_pct} elapsed={o.elapsed_pct} /></td>
              <td className={td}><TrackBadge track={o.track} /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function KpiLinkedTable({ items }: { items: ObjectiveKpiItem[] }) {
  const { t } = useTranslation();
  const fmt = useFmt();
  return (
    <div className="bg-white border border-gray-200 rounded-lg overflow-x-auto">
      <table className="w-full text-sm">
        <thead className="bg-gray-50 border-b border-gray-200 text-xs uppercase tracking-wide">
          <tr>
            <th className={th}>{t("objectives.fields.objective")}</th>
            <th className={th}>{t("reporting.objectives.col_kpi")}</th>
            <th className={th}>{t("objectives.current_value")}</th>
            <th className={`${th} border-l border-gray-200`}>{t("reporting.objectives.col_floor")}</th>
            <th className={`${th} border-l border-gray-200`}>{t("reporting.objectives.col_trajectory")}</th>
            <th className={th}>{t("objectives.progress")}</th>
            <th className={th}>{t("objectives.fields.track")}</th>
          </tr>
        </thead>
        <tbody>
          {items.map(o => {
            const cmp = o.threshold_direction === "above" ? "≥" : "≤";
            return (
              <tr key={o.id} className="border-b border-gray-100">
                <ObjectiveCell o={o} />
                <td className={td}>
                  <p className="text-gray-800">{o.kpi_name}</p>
                  <p className="text-xs text-gray-400 font-mono">{o.kpi_code}</p>
                </td>
                <td className={`${td} whitespace-nowrap font-medium`}>
                  {fmt(o.current_value, o.unit)}
                  {o.measured_on && <p className="text-xs text-gray-400 font-normal">{o.measured_on}</p>}
                </td>
                <td className={`${td} border-l border-gray-100 whitespace-nowrap`}>
                  <span className={`inline-block px-2 py-0.5 rounded border text-xs font-medium ${KPI_STATUS_STYLE[o.kpi_status]}`}>
                    {t(`kpi.status.${o.kpi_status}`)}
                  </span>
                  <p className="text-xs text-gray-500 mt-0.5">
                    {o.threshold_warning !== null && `${t("kpi.status.warning")} ${cmp} ${fmt(o.threshold_warning)}`}
                    {o.threshold_warning !== null && o.threshold_critical !== null && " · "}
                    {o.threshold_critical !== null && `${t("kpi.status.critical")} ${cmp} ${fmt(o.threshold_critical)}`}
                  </p>
                </td>
                <td className={`${td} border-l border-gray-100 whitespace-nowrap`}>
                  <span className="text-gray-700">
                    {fmt(o.baseline_value)} → {fmt(o.target_value, o.unit)}
                  </span>
                  <p className="text-xs text-gray-500">{t("reporting.objectives.by_date", { date: o.target_date })}</p>
                  {o.weak_target && (
                    <p className="text-xs text-amber-700 mt-0.5 max-w-xs whitespace-normal">
                      ⚠ {t("reporting.objectives.weak_target_short")}
                    </p>
                  )}
                </td>
                <td className={td}><ProgressBar progress={o.progress_pct} elapsed={o.elapsed_pct} /></td>
                <td className={td}><TrackBadge track={o.track} /></td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function Empty({ text }: { text: string }) {
  return <p className="text-sm text-gray-400 italic bg-white border border-gray-200 rounded-lg px-4 py-6 text-center">{text}</p>;
}

export function TabObjectives() {
  const { t } = useTranslation();
  const selectedPlant = useAuthStore(s => s.selectedPlant);
  const [plantId, setPlantId] = useState<string>(selectedPlant?.id ?? "");

  const { data: plants } = useQuery({ queryKey: ["plants"], queryFn: () => plantsApi.list(), retry: false });
  const { data, isLoading, isError } = useQuery({
    queryKey: ["reporting-objectives", plantId],
    queryFn: () => reportingApi.objectives(plantId || undefined),
    retry: false,
  });

  const section = "text-sm font-semibold text-gray-700 mb-1";
  const hint = "text-xs text-gray-500 mb-3";

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <label className="text-xs font-medium text-gray-600">{t("reporting.kpi.plant_label")}</label>
          <select
            value={plantId}
            onChange={e => setPlantId(e.target.value)}
            className="border border-gray-300 rounded px-2 py-1.5 text-sm"
          >
            <option value="">{t("reporting.kpi.all_plants")}</option>
            {plants?.map(p => <option key={p.id} value={p.id}>[{p.code}] {p.name}</option>)}
          </select>
        </div>
        <Link to="/objectives" className="text-sm text-primary-600 hover:text-primary-800">
          {t("reporting.objectives.manage_link")} →
        </Link>
      </div>

      <p className="text-sm text-gray-600 bg-indigo-50 border border-indigo-100 rounded-lg px-4 py-3">
        {t("reporting.objectives.intro")}
      </p>

      {isLoading && <div className="text-sm text-gray-400 py-8 text-center">{t("common.loading")}</div>}
      {isError && <Empty text={t("reporting.objectives.load_error")} />}

      {data && (
        <>
          <section>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
              <Counter label={t("reporting.objectives.col_active")} value={data.totals.attivi} tone="border-indigo-200" />
              <Counter label={t("objectives.track.in_linea")} value={data.totals.in_linea} tone="border-green-300" />
              <Counter label={t("objectives.track.a_rischio")} value={data.totals.a_rischio} tone="border-amber-300" />
              <Counter label={t("objectives.track.mancato")} value={data.totals.mancato} tone="border-red-300" />
              <Counter label={t("objectives.track.senza_misure")} value={data.totals.senza_misure} tone="border-gray-300" />
            </div>
            <p className="text-xs text-gray-500 mt-2">
              {t("reporting.objectives.totals_footer", {
                preparation: data.totals.in_preparazione,
                achieved: data.totals.raggiunti,
                missed: data.totals.non_raggiunti,
                days: data.closed_window_days,
              })}
            </p>
          </section>

          <section>
            <h3 className={section}>{t("reporting.objectives.section_by_plant")}</h3>
            <p className={hint}>{t("reporting.objectives.by_plant_hint", { days: data.closed_window_days })}</p>
            {data.by_plant.length ? <PlantTable rows={data.by_plant} /> : <Empty text={t("reporting.objectives.empty")} />}
          </section>

          <section>
            <h3 className={section}>{t("reporting.objectives.section_deadlines", { days: data.horizon_days })}</h3>
            <p className={hint}>{t("reporting.objectives.deadlines_hint")}</p>
            {data.deadlines.length
              ? <DeadlinesTable items={data.deadlines} />
              : <Empty text={t("reporting.objectives.no_deadlines", { days: data.horizon_days })} />}
          </section>

          <section>
            <h3 className={section}>{t("reporting.objectives.section_kpi")}</h3>
            <p className={hint}>{t("reporting.objectives.kpi_hint")}</p>
            {data.kpi_linked.length
              ? <KpiLinkedTable items={data.kpi_linked} />
              : <Empty text={t("reporting.objectives.no_kpi_linked")} />}
          </section>
        </>
      )}
    </div>
  );
}
