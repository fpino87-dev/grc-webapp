import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { useQuery } from "@tanstack/react-query";
import { scheduleApi, RequiredDocItem } from "../../api/endpoints/schedule";
import { plantsApi } from "../../api/endpoints/plants";
import { controlsApi } from "../../api/endpoints/controls";

const FRAMEWORK_LABELS: Record<string, string> = {
  ISO27001: "ISO 27001",
  NIS2:     "NIS2",
  TISAX_L2: "TISAX L2",
  TISAX_L3: "TISAX L3",
};

const TRAFFIC_LIGHT_COLORS: Record<string, { bg: string; text: string }> = {
  green:  { bg: "bg-green-500",  text: "text-white" },
  yellow: { bg: "bg-yellow-400", text: "text-gray-900" },
  red:    { bg: "bg-red-500",    text: "text-white" },
};

function DocRow({ item }: { item: RequiredDocItem }) {
  const { t } = useTranslation();
  const tl = TRAFFIC_LIGHT_COLORS[item.traffic_light] ?? TRAFFIC_LIGHT_COLORS.red;
  const tlLabelKey = item.traffic_light === "green"
    ? "schedule.required_docs.traffic_present_approved"
    : item.traffic_light === "yellow"
    ? "schedule.required_docs.traffic_draft"
    : "schedule.required_docs.traffic_missing";
  const tlLabel = t(tlLabelKey);

  return (
    <tr className="hover:bg-gray-50">
      <td className="px-4 py-3">
        <div className="flex items-center gap-2">
          <span className={`inline-block w-3 h-3 rounded-full ${tl.bg}`} title={tlLabel} />
          <span className="text-sm font-medium text-gray-900">{item.description}</span>
          {item.mandatory && (
            <span className="text-xs bg-red-100 text-red-700 px-1 py-0.5 rounded">
              {t("schedule.required_docs.mandatory_badge")}
            </span>
          )}
        </div>
      </td>
      <td className="px-4 py-3 text-sm text-gray-600">{item.document_type}</td>
      <td className="px-4 py-3 text-sm text-gray-500 font-mono">{item.iso_clause}</td>
      <td className="px-4 py-3 text-sm">
        {item.document ? (
          <div>
            <span className="text-gray-800">{item.document.title}</span>
            {item.document.review_due_date && (
              <span className="block text-xs text-gray-500 mt-0.5">
                {t("schedule.required_docs.review_date", { date: item.document.review_due_date })}
              </span>
            )}
          </div>
        ) : (
          <span className="text-red-500 italic text-xs">{t("schedule.required_docs.no_doc")}</span>
        )}
      </td>
      <td className="px-4 py-3">
        <span className={`inline-flex px-2 py-0.5 rounded text-xs font-medium ${tl.bg} ${tl.text}`}>
          {tlLabel}
        </span>
      </td>
    </tr>
  );
}

export function RequiredDocumentsPage() {
  const { t } = useTranslation();
  const [plantId, setPlantId] = useState<string>("");
  const [framework, setFramework] = useState("ISO27001");
  const [filter, setFilter] = useState<"all" | "red" | "yellow" | "green">("all");

  const { data: plants } = useQuery({
    queryKey: ["plants"],
    queryFn: () => plantsApi.list(),
    retry: false,
  });

  // Carica solo framework attivi per il plant selezionato
  const { data: activeFrameworks } = useQuery({
    queryKey: ["frameworks", plantId || undefined],
    queryFn: () => controlsApi.frameworks(plantId || undefined),
    retry: false,
  });

  // Quando cambia il plant, reimposta framework se quello corrente non è attivo
  useEffect(() => {
    if (activeFrameworks && activeFrameworks.length > 0) {
      const codes = activeFrameworks.map(f => f.code);
      if (!codes.includes(framework)) {
        setFramework(codes[0]);
      }
    }
  }, [activeFrameworks]);

  const { data, isLoading } = useQuery({
    queryKey: ["required-docs-status", plantId, framework],
    queryFn: () => scheduleApi.getRequiredDocumentsStatus({
      plant: plantId || undefined,
      framework,
    }),
    retry: false,
  });

  const results = data?.results ?? [];
  const filtered = filter === "all" ? results : results.filter(r => r.traffic_light === filter);

  const statusFilterOptions = [
    { value: "all",    labelKey: "schedule.required_docs.status_all" },
    { value: "red",    labelKey: "schedule.required_docs.status_red" },
    { value: "yellow", labelKey: "schedule.required_docs.status_yellow" },
    { value: "green",  labelKey: "schedule.required_docs.status_green" },
  ] as const;

  return (
    <div>
      <h2 className="text-xl font-semibold text-gray-900 mb-6">{t("schedule.required_docs.title")}</h2>

      {/* Filters */}
      <div className="bg-white border border-gray-200 rounded-lg p-4 mb-6">
        <div className="flex flex-wrap gap-4 items-end">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">{t("schedule.required_docs.col_doc").replace("Documento", "Sito")}</label>
            <select
              value={plantId}
              onChange={e => setPlantId(e.target.value)}
              className="border border-gray-300 rounded px-2 py-1.5 text-sm"
            >
              <option value="">{t("schedule.required_docs.all_sites")}</option>
              {plants?.map(p => (
                <option key={p.id} value={p.id}>[{p.code}] {p.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Framework</label>
            {activeFrameworks && activeFrameworks.length === 0 ? (
              <p className="text-xs text-amber-600 border border-amber-300 bg-amber-50 rounded px-2 py-1">
                {t("schedule.required_docs.no_framework")}
              </p>
            ) : (
              <div className="flex gap-1 flex-wrap">
                {(activeFrameworks ?? []).map(f => (
                  <button
                    key={f.code}
                    onClick={() => setFramework(f.code)}
                    className={`px-2 py-1 text-xs rounded border ${
                      framework === f.code
                        ? "bg-blue-600 text-white border-blue-600"
                        : "text-gray-600 border-gray-300 hover:bg-gray-50"
                    }`}
                  >
                    {FRAMEWORK_LABELS[f.code] ?? f.code}
                  </button>
                ))}
              </div>
            )}
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">{t("schedule.required_docs.col_status")}</label>
            <div className="flex gap-1">
              {statusFilterOptions.map(opt => (
                <button
                  key={opt.value}
                  onClick={() => setFilter(opt.value as typeof filter)}
                  className={`px-2 py-1 text-xs rounded border ${
                    filter === opt.value
                      ? "bg-gray-700 text-white border-gray-700"
                      : "text-gray-600 border-gray-300 hover:bg-gray-50"
                  }`}
                >
                  {t(opt.labelKey)}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Summary */}
      {data && (
        <div className="grid grid-cols-3 gap-4 mb-6">
          <div className="bg-green-50 border border-green-200 rounded-lg p-4">
            <p className="text-xs font-medium text-green-700 uppercase tracking-wide">{t("schedule.required_docs.approved_label")}</p>
            <p className="text-3xl font-bold text-green-700 mt-1">{data.green}</p>
            <p className="text-xs text-green-600 mt-1">{t("schedule.required_docs.total_suffix", { total: data.total })}</p>
          </div>
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
            <p className="text-xs font-medium text-yellow-700 uppercase tracking-wide">{t("schedule.required_docs.incomplete_label")}</p>
            <p className="text-3xl font-bold text-yellow-700 mt-1">{data.yellow}</p>
          </div>
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <p className="text-xs font-medium text-red-700 uppercase tracking-wide">{t("schedule.required_docs.missing_label")}</p>
            <p className="text-3xl font-bold text-red-700 mt-1">{data.red}</p>
          </div>
        </div>
      )}

      {/* Table */}
      <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-gray-400 text-sm">{t("notification_settings.loading")}</div>
        ) : filtered.length === 0 ? (
          <div className="p-8 text-center text-gray-400 text-sm italic">
            {results.length === 0
              ? t("schedule.required_docs.no_results_framework")
              : t("schedule.required_docs.no_results_filter")}
          </div>
        ) : (
          <table className="w-full text-left">
            <thead>
              <tr className="bg-gray-50 border-b border-gray-200">
                <th className="px-4 py-3 text-xs font-semibold text-gray-600 uppercase tracking-wide">{t("schedule.required_docs.col_doc")}</th>
                <th className="px-4 py-3 text-xs font-semibold text-gray-600 uppercase tracking-wide">{t("schedule.required_docs.col_type")}</th>
                <th className="px-4 py-3 text-xs font-semibold text-gray-600 uppercase tracking-wide">{t("schedule.required_docs.col_clause")}</th>
                <th className="px-4 py-3 text-xs font-semibold text-gray-600 uppercase tracking-wide">{t("schedule.required_docs.col_present")}</th>
                <th className="px-4 py-3 text-xs font-semibold text-gray-600 uppercase tracking-wide">{t("schedule.required_docs.col_status")}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {filtered.map((item, idx) => (
                <DocRow key={`${item.document_type}-${idx}`} item={item} />
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
