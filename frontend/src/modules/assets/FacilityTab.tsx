import { Fragment, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { assetsApi, type AssetFacility } from "../../api/endpoints/assets";
import { CriticalityBadge } from "./AssetBadges";

const RESULT_STYLES: Record<string, string> = {
  superata: "bg-green-100 text-green-700",
  con_riserve: "bg-amber-100 text-amber-700",
  fallita: "bg-red-100 text-red-700",
};

/** Impianti di supporto: continuità elettrica, antincendio, climatizzazione,
 *  sicurezza fisica. La colonna che conta è la prossima manutenzione. */
export function FacilityTab({ search }: { search: string }) {
  const { t, i18n } = useTranslation();
  const qc = useQueryClient();
  const [recordingId, setRecordingId] = useState<string | null>(null);
  const [result, setResult] = useState("superata");
  const [notes, setNotes] = useState("");

  const { data, isLoading } = useQuery({
    queryKey: ["assets-facility"],
    queryFn: () => assetsApi.listFacility(),
    retry: false,
  });

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["assets-facility"] });
    qc.invalidateQueries({ queryKey: ["schedule"] });
  };

  const deleteMutation = useMutation({
    mutationFn: (id: string) => assetsApi.deleteFacility(id),
    onSuccess: invalidate,
  });

  const recordMutation = useMutation({
    mutationFn: (id: string) =>
      assetsApi.recordMaintenance("facility", id, { result, notes }),
    onSuccess: () => {
      invalidate();
      setRecordingId(null);
      setNotes("");
      setResult("superata");
    },
  });

  const assets: AssetFacility[] = (data?.results ?? []).filter(
    (a) =>
      !search ||
      a.name.toLowerCase().includes(search.toLowerCase()) ||
      a.location.toLowerCase().includes(search.toLowerCase()) ||
      a.vendor.toLowerCase().includes(search.toLowerCase())
  );

  if (isLoading) {
    return <div className="p-8 text-center text-gray-400">{t("common.loading")}</div>;
  }

  const fmt = (d: string | null) =>
    d ? new Date(d).toLocaleDateString(i18n.language || "it") : "—";

  return (
    <table className="w-full text-sm">
      <thead className="bg-gray-50 border-b border-gray-200">
        <tr>
          <th className="text-left px-4 py-3 font-medium text-gray-600">{t("plants.fields.name")}</th>
          <th className="text-left px-4 py-3 font-medium text-gray-600">{t("assets.cols.category")}</th>
          <th className="text-left px-4 py-3 font-medium text-gray-600">{t("assets.facility.location")}</th>
          <th className="text-left px-4 py-3 font-medium text-gray-600">{t("assets.cols.criticality")}</th>
          <th className="text-left px-4 py-3 font-medium text-gray-600">{t("assets.maintenance.last")}</th>
          <th className="text-left px-4 py-3 font-medium text-gray-600">{t("assets.maintenance.next")}</th>
          <th className="px-4 py-3"></th>
        </tr>
      </thead>
      <tbody className="divide-y divide-gray-100">
        {assets.length === 0 ? (
          <tr>
            <td colSpan={7} className="px-4 py-8 text-center text-gray-400">
              {t("assets.facility.empty")}
            </td>
          </tr>
        ) : (
          assets.map((a) => (
            <Fragment key={a.id}>
              <tr className="hover:bg-gray-50 transition-colors">
                <td className="px-4 py-3 font-medium text-gray-800">
                  {a.name}
                  {a.rated_autonomy_minutes ? (
                    <span className="ml-2 text-xs text-gray-400">
                      {t("assets.facility.rated_autonomy_short", { minutes: a.rated_autonomy_minutes })}
                    </span>
                  ) : null}
                </td>
                <td className="px-4 py-3">
                  <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800">
                    {t(`assets.facility.categories.${a.category}`)}
                  </span>
                </td>
                <td className="px-4 py-3 text-gray-600">{a.location || "—"}</td>
                <td className="px-4 py-3"><CriticalityBadge value={a.criticality} /></td>
                <td className="px-4 py-3 text-gray-600">
                  {fmt(a.last_maintenance_date)}
                  {a.last_maintenance_result && (
                    <span className={`ml-2 inline-flex px-1.5 py-0.5 rounded text-[11px] font-medium ${RESULT_STYLES[a.last_maintenance_result] ?? ""}`}>
                      {t(`assets.maintenance.results.${a.last_maintenance_result}`)}
                    </span>
                  )}
                </td>
                <td className="px-4 py-3">
                  {a.next_maintenance_date ? (
                    <span className={a.maintenance_is_overdue ? "text-red-600 font-medium" : "text-gray-600"}>
                      {fmt(a.next_maintenance_date)}
                      {a.maintenance_is_overdue && ` — ${t("assets.maintenance.overdue")}`}
                    </span>
                  ) : (
                    <span className="text-gray-400">{t("assets.maintenance.not_planned")}</span>
                  )}
                </td>
                <td className="px-4 py-3 whitespace-nowrap text-right">
                  <button
                    onClick={() => setRecordingId(recordingId === a.id ? null : a.id)}
                    disabled={!a.maintenance_frequency_months}
                    title={
                      a.maintenance_frequency_months
                        ? t("assets.maintenance.record")
                        : t("assets.maintenance.no_cadence_hint")
                    }
                    className="text-xs text-blue-600 hover:underline border border-blue-200 rounded px-2 py-0.5 disabled:opacity-40 disabled:no-underline"
                  >
                    {recordingId === a.id ? t("common.close") : t("assets.maintenance.record")}
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      if (!window.confirm(t("assets.actions.delete_confirm", { name: a.name }))) return;
                      deleteMutation.mutate(a.id);
                    }}
                    disabled={deleteMutation.isPending}
                    className="ml-2 text-xs text-red-600 border border-red-200 rounded px-2 py-0.5 hover:bg-red-50 disabled:opacity-50"
                  >
                    🗑
                  </button>
                </td>
              </tr>
              {recordingId === a.id && (
                <tr>
                  <td colSpan={7} className="px-4 pb-4">
                    <div className="border border-blue-200 bg-blue-50/40 rounded-lg p-3">
                      <p className="text-sm font-medium text-gray-700 mb-2">
                        {t("assets.maintenance.record_title", { name: a.name })}
                      </p>
                      <div className="flex flex-wrap items-end gap-2">
                        <label className="text-xs text-gray-600">
                          {t("assets.maintenance.result")}
                          <select
                            value={result}
                            onChange={(e) => setResult(e.target.value)}
                            className="block border rounded px-2 py-1 text-sm mt-0.5"
                          >
                            {["superata", "con_riserve", "fallita"].map((r) => (
                              <option key={r} value={r}>{t(`assets.maintenance.results.${r}`)}</option>
                            ))}
                          </select>
                        </label>
                        <label className="flex-1 min-w-[16rem] text-xs text-gray-600">
                          {t("assets.maintenance.notes")}
                          <input
                            value={notes}
                            onChange={(e) => setNotes(e.target.value)}
                            placeholder={t("assets.maintenance.notes_placeholder")}
                            className="block w-full border rounded px-2 py-1 text-sm mt-0.5"
                          />
                        </label>
                        <button
                          onClick={() => recordMutation.mutate(a.id)}
                          disabled={recordMutation.isPending}
                          className="px-3 py-1.5 bg-primary-600 text-white rounded text-sm hover:bg-primary-700 disabled:opacity-50"
                        >
                          {recordMutation.isPending ? t("common.saving") : t("actions.save")}
                        </button>
                      </div>
                      <p className="text-xs text-gray-500 mt-2">
                        {t("assets.maintenance.record_hint", {
                          months: a.maintenance_frequency_months ?? 0,
                        })}
                      </p>
                    </div>
                  </td>
                </tr>
              )}
            </Fragment>
          ))
        )}
      </tbody>
    </table>
  );
}
