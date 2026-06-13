import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { controlsApi, type GapAnalysisResult, type GapCrossLink, type GapItem, type GapState } from "../../api/endpoints/controls";
import { useAuthStore } from "../../store/auth";
import { useTranslation } from "react-i18next";
import i18n from "../../i18n";
import { toCsv } from "../../utils/csv";

const TARGETS = [
  { code: "ISO27001", label: "ISO 27001:2022" },
  { code: "NIS2", label: "NIS2 (art. 21)" },
  { code: "ACN_NIS2", label: "ACN NIS2 (Det. 379907/2025)" },
  { code: "TISAX", label: "TISAX (VDA ISA 6.0)" },
];

const STATE_STYLE: Record<GapState, { badge: string; bar: string; icon: string }> = {
  coperto:        { badge: "bg-green-100 text-green-800",   bar: "bg-green-500",  icon: "🟢" },
  coperto_riuso:  { badge: "bg-teal-100 text-teal-800",     bar: "bg-teal-400",   icon: "♻️" },
  parziale:       { badge: "bg-yellow-100 text-yellow-800", bar: "bg-yellow-400", icon: "🟡" },
  parziale_riuso: { badge: "bg-amber-100 text-amber-800",   bar: "bg-amber-300",  icon: "♻️" },
  scoperto:       { badge: "bg-red-100 text-red-700",       bar: "bg-red-500",    icon: "🔴" },
  escluso:        { badge: "bg-gray-100 text-gray-500",     bar: "bg-gray-300",   icon: "⚪" },
};

const STATE_ORDER: GapState[] = ["scoperto", "parziale", "parziale_riuso", "coperto_riuso", "coperto", "escluso"];

const REL_ICON: Record<string, string> = { equivalente: "≡", parziale: "≈", correlato: "~" };

function StateBadge({ state }: { state: GapState }) {
  const { t } = useTranslation();
  const s = STATE_STYLE[state];
  return (
    <span className={`inline-flex items-center gap-1 text-xs px-1.5 py-0.5 rounded whitespace-nowrap ${s.badge}`}>
      {s.icon} {t(`gap_analysis.states.${state}`)}
    </span>
  );
}

function CrossChips({ cross }: { cross: GapCrossLink[] }) {
  const { t } = useTranslation();
  if (cross.length === 0) return <span className="text-xs text-gray-300">—</span>;
  return (
    <div className="flex flex-wrap gap-1">
      {cross.map((c, i) => {
        const compliant = c.status === "compliant";
        return (
          <span
            key={i}
            title={
              `${c.title}` +
              (c.via ? ` · ${t("gap_analysis.items.via", { id: c.via })}` : "") +
              ` · ${t(`gap_analysis.relationships.${c.relationship}`)}` +
              (compliant ? ` · ${t("gap_analysis.items.reuse_hint")}` : "")
            }
            className={`inline-flex items-center gap-1 text-[11px] px-1.5 py-0.5 rounded border whitespace-nowrap ${
              compliant
                ? "bg-green-50 border-green-300 text-green-800"
                : "bg-gray-50 border-gray-200 text-gray-500"
            }`}
          >
            <span className="font-bold">{REL_ICON[c.relationship]}</span>
            <span className="font-mono">{c.external_id}</span>
            {compliant ? <span>✓</span> : c.status ? (
              <span className="text-gray-400">({t(`status.${c.status}`, { defaultValue: c.status })})</span>
            ) : null}
          </span>
        );
      })}
    </div>
  );
}

function AcnRequirements({ item }: { item: GapItem }) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  if (!item.requirements?.length) return null;
  return (
    <div className="mt-1">
      <button onClick={() => setOpen(o => !o)} className="text-[11px] text-indigo-600 hover:text-indigo-800">
        {open ? "▲" : "▼"} {t("gap_analysis.items.requirements", { count: item.requirements.length })}
      </button>
      {open && (
        <ul className="mt-1 space-y-1">
          {item.requirements.map((r, i) => (
            <li key={i} className="flex items-start gap-2 text-xs text-gray-600">
              <span className="text-indigo-400 font-mono shrink-0">{r.punto}</span>
              <span>
                {r.text}
                {r.applies_to.map(a => (
                  <span key={a} className="ml-1 text-[10px] px-1 rounded bg-gray-100 text-gray-500">
                    {t(`controls.drawer.about.applies_to.${a}`, { defaultValue: a })}
                  </span>
                ))}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function exportCsv(result: GapAnalysisResult, t: (key: string, opts?: Record<string, unknown>) => string) {
  const rows: string[][] = [[
    t("gap_analysis.export.columns.state"),
    t("gap_analysis.export.columns.id"),
    t("gap_analysis.export.columns.title"),
    t("gap_analysis.export.columns.domain"),
    t("gap_analysis.export.columns.direct_status"),
    t("gap_analysis.export.columns.cross"),
  ]];
  for (const item of result.items) {
    rows.push([
      t(`gap_analysis.states.${item.state}`),
      item.external_id,
      item.title,
      item.domain,
      item.direct_status ?? "",
      item.cross.map(c =>
        `${c.relationship} ${c.framework} ${c.external_id}${c.status === "compliant" ? " ✓" : ""}`
      ).join("; "),
    ]);
  }
  const blob = new Blob([toCsv(rows)], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `gap-analysis-${result.target}${result.profile ? `-${result.profile}` : ""}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

export function GapAnalysisPage() {
  const { t } = useTranslation();
  const selectedPlant = useAuthStore(s => s.selectedPlant);
  const [target, setTarget] = useState("");
  const [acnProfile, setAcnProfile] = useState("");      // "" = auto dal sito
  const [tisaxProfile, setTisaxProfile] = useState("AL3");
  const [proto, setProto] = useState(false);
  const [onlyGaps, setOnlyGaps] = useState(true);
  const [triggered, setTriggered] = useState(false);

  const profile = target === "ACN_NIS2" ? acnProfile : target === "TISAX" ? tisaxProfile : "";

  const { data: result, isLoading, error } = useQuery({
    queryKey: ["gap-analysis", target, profile, proto, selectedPlant?.id, i18n.language],
    queryFn: () => controlsApi.gapAnalysis(target, selectedPlant!.id, {
      profile: profile || undefined,
      proto: target === "TISAX" ? proto : undefined,
      lang: i18n.language,
    }),
    enabled: triggered && !!target && !!selectedPlant?.id,
    retry: false,
  });

  const visibleItems = (result?.items ?? []).filter(
    item => !onlyGaps || (item.state !== "coperto" && item.state !== "escluso"),
  ).sort((a, b) => STATE_ORDER.indexOf(a.state) - STATE_ORDER.indexOf(b.state));

  const isAcn = result?.target === "ACN_NIS2";

  return (
    <div>
      <h2 className="text-xl font-semibold text-gray-900 mb-1">{t("gap_analysis.title")}</h2>
      <p className="text-sm text-gray-500 mb-4">{t("gap_analysis.subtitle")}</p>

      {!selectedPlant && (
        <div className="p-4 bg-yellow-50 border border-yellow-200 rounded text-sm text-yellow-800">
          {t("gap_analysis.errors.select_plant")}
        </div>
      )}

      {selectedPlant && (
        <div className="bg-white border border-gray-200 rounded-lg p-4 mb-6">
          <div className="flex flex-wrap items-end gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {t("gap_analysis.target_framework")}
              </label>
              <select
                value={target}
                onChange={e => { setTarget(e.target.value); setTriggered(false); }}
                className="border rounded px-3 py-2 text-sm min-w-[220px]"
              >
                <option value="">{t("common.select")}</option>
                {TARGETS.map(f => <option key={f.code} value={f.code}>{f.label}</option>)}
              </select>
            </div>

            {target === "ACN_NIS2" && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">{t("gap_analysis.profile")}</label>
                <select
                  value={acnProfile}
                  onChange={e => { setAcnProfile(e.target.value); setTriggered(false); }}
                  className="border rounded px-3 py-2 text-sm"
                >
                  <option value="">{t("gap_analysis.profile_auto")}</option>
                  <option value="importante">{t("gap_analysis.profile_importante")}</option>
                  <option value="essenziale">{t("gap_analysis.profile_essenziale")}</option>
                </select>
              </div>
            )}

            {target === "TISAX" && (
              <>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">{t("gap_analysis.profile")}</label>
                  <select
                    value={tisaxProfile}
                    onChange={e => { setTisaxProfile(e.target.value); setTriggered(false); }}
                    className="border rounded px-3 py-2 text-sm"
                  >
                    <option value="AL2">AL2</option>
                    <option value="AL3">AL3</option>
                  </select>
                </div>
                <label className="flex items-center gap-1.5 text-sm text-gray-700 pb-2">
                  <input
                    type="checkbox"
                    checked={proto}
                    onChange={e => { setProto(e.target.checked); setTriggered(false); }}
                    className="accent-violet-600"
                  />
                  {t("gap_analysis.include_proto")}
                </label>
              </>
            )}

            <button
              onClick={() => setTriggered(true)}
              disabled={!target}
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
        </div>
      )}

      {isLoading && <div className="p-8 text-center text-gray-400">{t("gap_analysis.loading")}</div>}
      {error && <div className="p-4 text-red-600 bg-red-50 rounded">{t("gap_analysis.errors.load_failed")}</div>}

      {result && (
        <div className="space-y-4">
          {/* Copertura diretta / assistita */}
          <div className="bg-white border border-gray-200 rounded-lg p-4">
            <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
              <span className="text-sm font-medium text-gray-700">
                {t("gap_analysis.summary.scope", {
                  plant: selectedPlant?.name,
                  target: TARGETS.find(f => f.code === result.target)?.label ?? result.target,
                })}
                {result.profile && (
                  <span className="ml-1.5 text-xs bg-indigo-50 text-indigo-700 px-1.5 py-0.5 rounded">
                    {t("gap_analysis.summary.profile_badge", { profile: result.profile })}
                  </span>
                )}
              </span>
              <div className="flex items-center gap-5">
                <div className="text-right">
                  <p className="text-xs text-gray-400">{t("gap_analysis.summary.direct")}</p>
                  <p className="text-xl font-bold text-green-700">{result.coverage.direct_pct}%</p>
                </div>
                <div className="text-right" title={t("gap_analysis.summary.assisted_hint")}>
                  <p className="text-xs text-gray-400">{t("gap_analysis.summary.assisted")} ♻️</p>
                  <p className="text-xl font-bold text-teal-600">{result.coverage.assisted_pct}%</p>
                </div>
              </div>
            </div>

            <div className="flex rounded overflow-hidden h-4 bg-gray-100">
              {STATE_ORDER.filter(s => s !== "escluso").map(s => (
                result.counts[s] > 0 && result.coverage.applicable > 0 && (
                  <div
                    key={s}
                    className={STATE_STYLE[s].bar}
                    style={{ width: `${result.counts[s] / result.coverage.applicable * 100}%` }}
                    title={`${t(`gap_analysis.states.${s}`)}: ${result.counts[s]}`}
                  />
                )
              ))}
            </div>

            <div className="flex flex-wrap gap-3 mt-2 text-xs text-gray-500">
              {STATE_ORDER.map(s => (
                <span key={s} className="flex items-center gap-1">
                  <span className={`w-2 h-2 rounded-full inline-block ${STATE_STYLE[s].bar}`} />
                  {t(`gap_analysis.states.${s}`)}: {result.counts[s]}
                </span>
              ))}
              <span className="ml-auto text-gray-400">
                {isAcn
                  ? t("gap_analysis.summary.applicable_requirements", { count: result.coverage.applicable })
                  : t("gap_analysis.summary.applicable_controls", { count: result.coverage.applicable })}
              </span>
            </div>
            <p className="text-[11px] text-gray-400 mt-2">♻️ {t("gap_analysis.reuse_disclaimer")}</p>
          </div>

          {/* Copertura per dominio */}
          {result.coverage_by_domain.length > 1 && (
            <div className="bg-white border border-gray-200 rounded-lg p-4">
              <p className="text-sm font-medium text-gray-700 mb-2">{t("gap_analysis.domains.title")}</p>
              <div className="space-y-1.5">
                {result.coverage_by_domain.map(d => (
                  <div key={d.code} className="flex items-center gap-3 text-xs">
                    <span className="w-28 shrink-0 font-mono text-gray-500 truncate" title={d.name}>{d.code}</span>
                    <div className="flex-1 flex rounded overflow-hidden h-2.5 bg-gray-100">
                      {STATE_ORDER.filter(s => s !== "escluso").map(s => (
                        d[s] > 0 && d.applicable > 0 && (
                          <div key={s} className={STATE_STYLE[s].bar} style={{ width: `${d[s] / d.applicable * 100}%` }} />
                        )
                      ))}
                    </div>
                    <span className="w-24 text-right text-gray-500">
                      {d.direct_pct}% <span className="text-teal-600">({d.assisted_pct}%)</span>
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Tabella elementi */}
          <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
            <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100">
              <p className="text-sm font-medium text-gray-700">
                {t("gap_analysis.items.title", { count: visibleItems.length })}
              </p>
              <label className="flex items-center gap-1.5 text-xs text-gray-500">
                <input type="checkbox" checked={onlyGaps} onChange={e => setOnlyGaps(e.target.checked)} />
                {t("gap_analysis.items.only_gaps")}
              </label>
            </div>
            {visibleItems.length === 0 ? (
              <p className="px-4 py-6 text-sm text-gray-400 text-center">{t("gap_analysis.items.empty")}</p>
            ) : (
              <table className="w-full text-sm">
                <thead className="bg-gray-50 text-xs text-gray-500">
                  <tr>
                    <th className="text-left px-4 py-2 font-medium">{t("gap_analysis.items.state")}</th>
                    <th className="text-left px-4 py-2 font-medium">{t("gap_analysis.items.control")}</th>
                    <th className="text-left px-4 py-2 font-medium">{t("gap_analysis.items.cross")}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {visibleItems.map(item => (
                    <tr key={item.id} className="hover:bg-gray-50 align-top">
                      <td className="px-4 py-2 w-36"><StateBadge state={item.state} /></td>
                      <td className="px-4 py-2">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-xs text-gray-500">{item.external_id}</span>
                          {result.frameworks.length > 1 && (
                            <span className="text-[10px] bg-blue-50 text-blue-700 px-1 rounded">{item.framework}</span>
                          )}
                        </div>
                        <p className="text-gray-700 text-xs mt-0.5">{item.title}</p>
                        <AcnRequirements item={item} />
                      </td>
                      <td className="px-4 py-2 w-2/5"><CrossChips cross={item.cross} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
