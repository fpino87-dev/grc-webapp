import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import {
  securityObjectivesApi,
  type SecurityObjective,
} from "../../api/endpoints/securityObjectives";
import { ObjectiveStatusBadge, ProgressBar, TrackBadge } from "./objectiveBadges";

/** Andamento delle misure: una spark-line in SVG, senza librerie. Serve a
 *  vedere se la curva sale verso il target o è piatta, non a leggere valori
 *  precisi — quelli sono in tabella. */
function Sparkline({ points, target, baseline }: {
  points: { date: string; value: number }[];
  target: number;
  baseline: number | null;
}) {
  if (points.length < 2) return null;
  const values = [...points.map((p) => p.value), target, ...(baseline !== null ? [baseline] : [])];
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const w = 320;
  const h = 70;
  const x = (i: number) => (i / (points.length - 1)) * w;
  const y = (v: number) => h - ((v - min) / span) * h;
  const path = points.map((p, i) => `${i === 0 ? "M" : "L"}${x(i).toFixed(1)},${y(p.value).toFixed(1)}`).join(" ");
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="w-full h-20" preserveAspectRatio="none">
      <line x1="0" y1={y(target)} x2={w} y2={y(target)} stroke="#16a34a" strokeDasharray="4 3" strokeWidth="1" />
      {baseline !== null && (
        <line x1="0" y1={y(baseline)} x2={w} y2={y(baseline)} stroke="#9ca3af" strokeDasharray="2 3" strokeWidth="1" />
      )}
      <path d={path} fill="none" stroke="#4f46e5" strokeWidth="2" />
    </svg>
  );
}

export function ObjectiveDetail({ objective, onClose }: { objective: SecurityObjective; onClose: () => void }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [value, setValue] = useState("");
  const [note, setNote] = useState("");
  const [error, setError] = useState("");

  const { data: series = [] } = useQuery({
    queryKey: ["objective-series", objective.id],
    queryFn: () => securityObjectivesApi.series(objective.id),
  });

  const refresh = () => {
    qc.invalidateQueries({ queryKey: ["security-objectives"] });
    qc.invalidateQueries({ queryKey: ["objective-series", objective.id] });
  };
  const onError = (e: { response?: { data?: Record<string, string[] | string> | string } }) => {
    const data = e.response?.data;
    if (typeof data === "string") return setError(data);
    const first = Object.entries(data ?? {})[0];
    setError(first ? [first[1]].flat().join(" ") : t("common.error"));
  };

  const activate = useMutation({
    mutationFn: () => securityObjectivesApi.activate(objective.id),
    onSuccess: refresh, onError,
  });
  const suspend = useMutation({
    mutationFn: () => securityObjectivesApi.suspend(objective.id),
    onSuccess: refresh, onError,
  });
  const close = useMutation({
    mutationFn: (outcome: "raggiunto" | "non_raggiunto") =>
      securityObjectivesApi.close(objective.id, outcome, note),
    onSuccess: refresh, onError,
  });
  const measure = useMutation({
    mutationFn: () => securityObjectivesApi.measure(objective.id, Number(value), undefined, note),
    onSuccess: () => { setValue(""); setNote(""); refresh(); },
    onError,
  });

  const ev = objective.evaluation;
  const open = ["bozza", "attivo", "sospeso"].includes(objective.status);
  const row = "flex justify-between py-1.5 border-b border-gray-100 text-sm";

  return (
    <div className="fixed inset-0 bg-black/40 flex items-start justify-center z-50 overflow-y-auto py-8">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl p-6 mx-4">
        <div className="flex items-start justify-between mb-4">
          <div>
            <p className="text-xs text-gray-500">{objective.code}{objective.plant_code ? ` · ${objective.plant_code}` : ` · ${t("objectives.fields.plant_org")}`}</p>
            <h3 className="text-lg font-semibold">{objective.title}</h3>
            <div className="flex gap-2 mt-1.5">
              <ObjectiveStatusBadge status={objective.status} />
              <TrackBadge track={ev.track} />
            </div>
          </div>
          <button className="text-gray-400 hover:text-gray-600 text-xl leading-none" onClick={onClose}>×</button>
        </div>

        {ev.weak_target && (
          <div className="bg-amber-50 border border-amber-200 rounded p-2.5 mb-4 text-xs text-amber-800">
            {t("objectives.weak_target_warning")}
          </div>
        )}

        <div className="grid grid-cols-2 gap-x-6 mb-4">
          <div className={row}>
            <span className="text-gray-500">{t("objectives.fields.baseline_value")}</span>
            <span>{objective.baseline_value ?? "—"} {ev.unit}</span>
          </div>
          <div className={row}>
            <span className="text-gray-500">{t("objectives.fields.target_value")}</span>
            <span className="font-medium">{objective.target_value} {ev.unit}</span>
          </div>
          <div className={row}>
            <span className="text-gray-500">{t("objectives.current_value")}</span>
            <span className="font-medium">{ev.current_value ?? "—"} {ev.unit}</span>
          </div>
          <div className={row}>
            <span className="text-gray-500">{t("objectives.fields.target_date")}</span>
            <span>{objective.target_date} ({t("objectives.days_left", { n: ev.days_to_target })})</span>
          </div>
          <div className={row}>
            <span className="text-gray-500">{t("objectives.progress")}</span>
            <ProgressBar progress={ev.progress_pct} elapsed={ev.elapsed_pct} />
          </div>
          <div className={row}>
            <span className="text-gray-500">{t("objectives.fields.measure_source")}</span>
            <span>
              {objective.measure_source === "kpi"
                ? `KPI ${objective.kpi_code ?? ""}`
                : t("objectives.measure_source.manual")}
            </span>
          </div>
        </div>

        {series.length > 1 && (
          <div className="mb-4">
            <p className="text-xs font-medium text-gray-600 mb-1">{t("objectives.trend")}</p>
            <Sparkline points={series} target={objective.target_value} baseline={objective.baseline_value} />
          </div>
        )}

        {(objective.resources || objective.evaluation_method) && (
          <div className="bg-gray-50 rounded p-3 mb-4 text-sm space-y-2">
            {objective.resources && (
              <p><span className="text-gray-500">{t("objectives.fields.resources")}: </span>{objective.resources}</p>
            )}
            {objective.evaluation_method && (
              <p><span className="text-gray-500">{t("objectives.fields.evaluation_method")}: </span>{objective.evaluation_method}</p>
            )}
          </div>
        )}

        {objective.measure_source === "manual" && open && (
          <div className="border-t pt-4 mb-4">
            <p className="text-xs font-medium text-gray-600 mb-2">{t("objectives.record_measure")}</p>
            <div className="flex gap-2">
              <input type="number" step="any" className="border border-gray-300 rounded px-2 py-1.5 text-sm w-28"
                     placeholder={ev.unit || t("objectives.fields.value")} value={value}
                     onChange={(e) => setValue(e.target.value)} />
              <input className="border border-gray-300 rounded px-2 py-1.5 text-sm flex-1"
                     placeholder={t("objectives.fields.note")} value={note}
                     onChange={(e) => setNote(e.target.value)} />
              <button className="px-3 py-1.5 text-sm bg-indigo-600 text-white rounded hover:bg-indigo-700 disabled:opacity-50"
                      disabled={!value || measure.isPending}
                      onClick={() => { setError(""); measure.mutate(); }}>
                {t("actions.save")}
              </button>
            </div>
          </div>
        )}

        {objective.measure_source === "kpi" && (
          <p className="text-xs text-gray-500 mb-4">{t("objectives.kpi_measured_hint")}</p>
        )}

        {error && <p className="text-sm text-red-600 mb-3">{error}</p>}

        <div className="flex flex-wrap gap-2 border-t pt-4">
          {(objective.status === "bozza" || objective.status === "sospeso") && (
            <button className="px-3 py-1.5 text-sm bg-indigo-600 text-white rounded hover:bg-indigo-700"
                    onClick={() => { setError(""); activate.mutate(); }}>
              {t("objectives.actions.activate")}
            </button>
          )}
          {objective.status === "attivo" && (
            <>
              <button className="px-3 py-1.5 text-sm border border-gray-300 rounded hover:bg-gray-50"
                      onClick={() => { setError(""); suspend.mutate(); }}>
                {t("objectives.actions.suspend")}
              </button>
              <button className="px-3 py-1.5 text-sm bg-green-600 text-white rounded hover:bg-green-700"
                      onClick={() => { setError(""); close.mutate("raggiunto"); }}>
                {t("objectives.actions.close_reached")}
              </button>
              <button className="px-3 py-1.5 text-sm bg-red-600 text-white rounded hover:bg-red-700"
                      onClick={() => { setError(""); close.mutate("non_raggiunto"); }}>
                {t("objectives.actions.close_missed")}
              </button>
            </>
          )}
          {!open && objective.closure_note && (
            <p className="text-xs text-gray-500">{objective.closure_note}</p>
          )}
        </div>
      </div>
    </div>
  );
}
