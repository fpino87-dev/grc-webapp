import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { ModuleHelp } from "../../components/ui/ModuleHelp";
import {
  securityObjectivesApi,
  type SecurityObjective,
} from "../../api/endpoints/securityObjectives";
import { ObjectiveForm } from "./ObjectiveForm";
import { ObjectiveDetail } from "./ObjectiveDetail";
import { ObjectiveStatusBadge, ProgressBar, TrackBadge } from "./objectiveBadges";

const OPEN_STATUSES = ["bozza", "attivo", "sospeso"];

export function ObjectivesPage() {
  const { t } = useTranslation();
  const [showClosed, setShowClosed] = useState(false);
  const [creating, setCreating] = useState(false);
  const [editing, setEditing] = useState<SecurityObjective | null>(null);
  const [selected, setSelected] = useState<SecurityObjective | null>(null);

  const { data: objectives = [], isLoading } = useQuery({
    queryKey: ["security-objectives"],
    queryFn: () => securityObjectivesApi.list(),
  });

  const visible = objectives.filter((o) => showClosed || OPEN_STATUSES.includes(o.status));
  // Prima quelli che non stanno andando bene: è l'ordine con cui li guarda
  // la direzione, ed è lo stesso del verbale del riesame.
  const order: Record<string, number> = {
    mancato: 0, a_rischio: 1, senza_misure: 2, in_linea: 3, non_applicabile: 4,
  };
  const rows = [...visible].sort(
    (a, b) => (order[a.evaluation.track] ?? 9) - (order[b.evaluation.track] ?? 9)
      || a.target_date.localeCompare(b.target_date),
  );
  const current = selected ? objectives.find((o) => o.id === selected.id) ?? selected : null;

  const counts = {
    attivi: objectives.filter((o) => o.status === "attivo").length,
    a_rischio: visible.filter((o) => o.evaluation.track === "a_rischio").length,
    mancati: visible.filter((o) => o.evaluation.track === "mancato").length,
    raggiunti: objectives.filter((o) => o.status === "raggiunto").length,
  };

  const card = "bg-white border rounded-lg p-4";
  const th = "text-left px-3 py-2 font-medium text-gray-600";
  const td = "px-3 py-2.5 align-middle";

  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <div className="flex items-center">
          <h2 className="text-xl font-semibold text-gray-900">{t("objectives.page_title")}</h2>
          <ModuleHelp
            title={t("objectives.help.title")}
            description={t("objectives.help.description")}
            steps={[
              t("objectives.help.steps.1"),
              t("objectives.help.steps.2"),
              t("objectives.help.steps.3"),
              t("objectives.help.steps.4"),
              t("objectives.help.steps.5"),
            ]}
            connections={[
              { module: "M08 KPI", relation: t("objectives.help.connections.kpi") },
              { module: "M13", relation: t("objectives.help.connections.management_review") },
              { module: "M11 PDCA", relation: t("objectives.help.connections.pdca") },
            ]}
          />
        </div>
        <button className="px-3 py-1.5 text-sm bg-indigo-600 text-white rounded hover:bg-indigo-700"
                onClick={() => setCreating(true)}>
          {t("objectives.actions.new")}
        </button>
      </div>
      <p className="text-sm text-gray-500 mb-5">{t("objectives.page_subtitle")}</p>

      <div className="grid grid-cols-4 gap-4 mb-6">
        <div className={`${card} border-indigo-200`}>
          <p className="text-xs text-gray-500 uppercase tracking-wide">{t("objectives.counters.active")}</p>
          <p className="text-3xl font-bold text-indigo-600 mt-1">{counts.attivi}</p>
        </div>
        <div className={`${card} border-amber-300`}>
          <p className="text-xs text-gray-500 uppercase tracking-wide">{t("objectives.counters.at_risk")}</p>
          <p className="text-3xl font-bold text-amber-600 mt-1">{counts.a_rischio}</p>
        </div>
        <div className={`${card} border-red-300`}>
          <p className="text-xs text-gray-500 uppercase tracking-wide">{t("objectives.counters.missed")}</p>
          <p className="text-3xl font-bold text-red-600 mt-1">{counts.mancati}</p>
        </div>
        <div className={`${card} border-green-300`}>
          <p className="text-xs text-gray-500 uppercase tracking-wide">{t("objectives.counters.achieved")}</p>
          <p className="text-3xl font-bold text-green-600 mt-1">{counts.raggiunti}</p>
        </div>
      </div>

      <label className="flex items-center gap-2 text-sm text-gray-600 mb-3">
        <input type="checkbox" checked={showClosed} onChange={(e) => setShowClosed(e.target.checked)} />
        {t("objectives.show_closed")}
      </label>

      {isLoading ? (
        <div className="py-8 text-center text-gray-400 text-sm">{t("common.loading")}</div>
      ) : rows.length === 0 ? (
        <div className="bg-white border border-gray-200 rounded-lg py-10 text-center">
          <p className="text-gray-500 text-sm">{t("objectives.empty")}</p>
          <p className="text-gray-400 text-xs mt-1">{t("objectives.empty_hint")}</p>
        </div>
      ) : (
        <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200 text-xs uppercase tracking-wide">
              <tr>
                <th className={th}>{t("objectives.fields.objective")}</th>
                <th className={th}>{t("objectives.baseline_to_target")}</th>
                <th className={th}>{t("objectives.current_value")}</th>
                <th className={th}>{t("objectives.progress")}</th>
                <th className={th}>{t("objectives.fields.target_date")}</th>
                <th className={th}>{t("objectives.fields.track")}</th>
                <th className={th}>{t("objectives.fields.status")}</th>
                <th className={th}></th>
              </tr>
            </thead>
            <tbody>
              {rows.map((o) => (
                <tr key={o.id} className="border-b border-gray-100 hover:bg-gray-50 cursor-pointer"
                    onClick={() => setSelected(o)}>
                  <td className={td}>
                    <p className="font-medium text-gray-900">{o.title}</p>
                    <p className="text-xs text-gray-500">
                      {o.code}{o.plant_code ? ` · ${o.plant_code}` : ` · ${t("objectives.fields.plant_org")}`}
                      {o.owner_role ? ` · ${t(`governance.roles.${o.owner_role}`)}` : ""}
                    </p>
                  </td>
                  <td className={`${td} whitespace-nowrap text-gray-600`}>
                    {o.baseline_value ?? "—"} → {o.target_value} {o.evaluation.unit}
                  </td>
                  <td className={`${td} font-medium whitespace-nowrap`}>
                    {o.evaluation.current_value ?? "—"} {o.evaluation.unit}
                  </td>
                  <td className={td}>
                    <ProgressBar progress={o.evaluation.progress_pct} elapsed={o.evaluation.elapsed_pct} />
                  </td>
                  <td className={`${td} whitespace-nowrap text-gray-600`}>{o.target_date}</td>
                  <td className={td}><TrackBadge track={o.evaluation.track} /></td>
                  <td className={td}><ObjectiveStatusBadge status={o.status} /></td>
                  <td className={td}>
                    <button className="text-xs text-indigo-600 hover:text-indigo-800"
                            onClick={(e) => { e.stopPropagation(); setEditing(o); }}>
                      {t("actions.edit")}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {creating && <ObjectiveForm onClose={() => setCreating(false)} />}
      {editing && <ObjectiveForm objective={editing} onClose={() => setEditing(null)} />}
      {current && <ObjectiveDetail objective={current} onClose={() => setSelected(null)} />}
    </div>
  );
}
