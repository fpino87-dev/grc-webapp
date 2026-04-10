import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { controlsApi, type GapEntry, type GapAnalysisResult } from "../../api/endpoints/controls";
import { useAuthStore } from "../../store/auth";
import { useTranslation } from "react-i18next";

function Section({
  icon, label, color, items, emptyText, defaultOpen,
}: {
  icon: string; label: string; color: string; items: GapEntry[]; emptyText: string; defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(!!defaultOpen);
  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden">
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between px-4 py-3 bg-gray-50 hover:bg-gray-100 transition-colors"
      >
        <div className="flex items-center gap-2">
          <span>{icon}</span>
          <span className={`font-medium text-sm ${color}`}>{label}</span>
          <span className="ml-1 text-xs bg-gray-200 text-gray-600 px-2 py-0.5 rounded-full">{items.length}</span>
        </div>
        <span className="text-gray-400 text-xs">{open ? "▲" : "▼"}</span>
      </button>
      {open && items.length > 0 && (
        <table className="w-full text-sm">
          <tbody className="divide-y divide-gray-100">
            {items.map((e) => (
              <tr key={e.id} className="hover:bg-gray-50">
                <td className="px-4 py-2 font-mono text-xs text-gray-500 w-24">{e.external_id}</td>
                <td className="px-4 py-2 text-gray-700">{e.title}</td>
                <td className="px-4 py-2 text-gray-400 text-xs">{e.domain}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {open && items.length === 0 && (
        <p className="px-4 py-3 text-sm text-gray-400">
          {emptyText}
        </p>
      )}
    </div>
  );
}

function exportCsv(result: GapAnalysisResult, t: (key: string, opts?: any) => string) {
  const rows: string[][] = [[
    t("gap_analysis.export.columns.category"),
    t("gap_analysis.export.columns.id"),
    t("gap_analysis.export.columns.title"),
    t("gap_analysis.export.columns.domain"),
    t("gap_analysis.export.columns.source_status"),
  ]];
  const add = (cat: string, items: GapEntry[]) =>
    items.forEach(e => rows.push([cat, e.external_id, e.title, e.domain, e.source_status ?? ""]));
  add(t("gap_analysis.sections.covered"), result.covered);
  add(t("gap_analysis.sections.partial"), result.partial);
  add(t("gap_analysis.sections.gap"), result.gap);
  add(t("gap_analysis.sections.not_mapped"), result.not_mapped);
  const csv = rows.map(r => r.map(c => `"${c.replace(/"/g, '""')}"`).join(",")).join("\n");
  const blob = new Blob([csv], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `gap-analysis-${result.source_framework}-vs-${result.target_framework}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

export function GapAnalysisPage() {
  const { t } = useTranslation();
  const [source, setSource] = useState("");
  const [target, setTarget] = useState("");
  const [triggered, setTriggered] = useState(false);
  const selectedPlant = useAuthStore(s => s.selectedPlant);

  const { data: frameworks } = useQuery({
    queryKey: ["frameworks", selectedPlant?.id],
    queryFn: () => controlsApi.frameworks(selectedPlant?.id),
    retry: false,
  });

  const { data: result, isLoading, error } = useQuery({
    queryKey: ["gap-analysis", source, target, selectedPlant?.id],
    queryFn: () => controlsApi.gapAnalysis(source, target, selectedPlant?.id),
    enabled: triggered && !!source && !!target && source !== target,
    retry: false,
  });

  function handleAnalyze() {
    setTriggered(true);
  }

  return (
    <div>
      <h2 className="text-xl font-semibold text-gray-900 mb-4">{t("gap_analysis.title")}</h2>

      {/* Selettori */}
      <div className="bg-white border border-gray-200 rounded-lg p-4 mb-6">
        <div className="flex flex-wrap items-end gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {t("gap_analysis.source_framework")}
            </label>
            <select
              value={source}
              onChange={e => { setSource(e.target.value); setTriggered(false); }}
              className="border rounded px-3 py-2 text-sm min-w-[180px]"
            >
              <option value="">{t("common.select")}</option>
              {frameworks?.map(f => (
                <option key={f.id} value={f.code}>{f.code} — {f.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {t("gap_analysis.target_framework")}
            </label>
            <select
              value={target}
              onChange={e => { setTarget(e.target.value); setTriggered(false); }}
              className="border rounded px-3 py-2 text-sm min-w-[180px]"
            >
              <option value="">{t("common.select")}</option>
              {frameworks?.map(f => (
                <option key={f.id} value={f.code}>{f.code} — {f.name}</option>
              ))}
            </select>
          </div>
          <button
            onClick={handleAnalyze}
            disabled={!source || !target || source === target}
            className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700 disabled:opacity-50"
          >
            {t("gap_analysis.actions.analyze")}
          </button>
          {result && (
            <button
              onClick={() => exportCsv(result, t)}
              className="px-4 py-2 border border-gray-300 rounded text-sm text-gray-600 hover:bg-gray-50"
            >
              {t("gap_analysis.actions.download_report")}
            </button>
          )}
        </div>
        {source === target && source && (
          <p className="text-sm text-red-500 mt-2">{t("gap_analysis.errors.same_framework")}</p>
        )}
      </div>

      {isLoading && <div className="p-8 text-center text-gray-400">{t("gap_analysis.loading")}</div>}
      {error && <div className="p-4 text-red-600 bg-red-50 rounded">{t("gap_analysis.errors.load_failed")}</div>}

      {result && (
        <div className="space-y-4">
          {/* Progress bar */}
          <div className="bg-white border border-gray-200 rounded-lg p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-gray-700">
                {t("gap_analysis.summary.controls_from_to", { source: result.source_framework, target: result.target_framework })}
              </span>
              <span className="text-lg font-bold text-primary-600">
                {t("gap_analysis.summary.pct_covered", { pct: result.summary.pct_ready })}
              </span>
            </div>
            <div className="flex rounded overflow-hidden h-4 bg-gray-100">
              {result.summary.total > 0 && (
                <>
                  <div
                    className="bg-green-500"
                    style={{ width: `${result.summary.covered / result.summary.total * 100}%` }}
                    title={`Coperti: ${result.summary.covered}`}
                  />
                  <div
                    className="bg-yellow-400"
                    style={{ width: `${result.summary.partial / result.summary.total * 100}%` }}
                    title={`Parziali: ${result.summary.partial}`}
                  />
                  <div
                    className="bg-red-500"
                    style={{ width: `${result.summary.gap / result.summary.total * 100}%` }}
                    title={`Gap: ${result.summary.gap}`}
                  />
                  <div
                    className="bg-gray-300"
                    style={{ width: `${result.summary.not_mapped / result.summary.total * 100}%` }}
                    title={`Non mappati: ${result.summary.not_mapped}`}
                  />
                </>
              )}
            </div>
            <div className="flex gap-4 mt-2 text-xs text-gray-500">
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-green-500 inline-block" />
                {t("gap_analysis.summary.covered_count", { count: result.summary.covered })}
              </span>
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-yellow-400 inline-block" />
                {t("gap_analysis.summary.partial_count", { count: result.summary.partial })}
              </span>
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-red-500 inline-block" />
                {t("gap_analysis.summary.gap_count", { count: result.summary.gap })}
              </span>
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-gray-300 inline-block" />
                {t("gap_analysis.summary.not_mapped_count", { count: result.summary.not_mapped })}
              </span>
            </div>
          </div>

          {/* Sezioni collassabili */}
          <Section
            icon="✅"
            label={t("gap_analysis.sections.covered")}
            color="text-green-700"
            items={result.covered}
            emptyText={t("gap_analysis.empty_category")}
            defaultOpen
          />
          <Section
            icon="🟡"
            label={t("gap_analysis.sections.partial")}
            color="text-yellow-700"
            items={result.partial}
            emptyText={t("gap_analysis.empty_category")}
          />
          <Section
            icon="🔴"
            label={t("gap_analysis.sections.gap")}
            color="text-red-700"
            items={result.gap}
            emptyText={t("gap_analysis.empty_category")}
          />
          <Section
            icon="⬜"
            label={t("gap_analysis.sections.not_mapped")}
            color="text-gray-600"
            items={result.not_mapped}
            emptyText={t("gap_analysis.empty_category")}
          />
        </div>
      )}
    </div>
  );
}
