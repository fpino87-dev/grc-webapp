import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { controlsApi, type ControlDetailInfo } from "../../../api/endpoints/controls";
import i18n from "../../../i18n";

export function TabCosa({ info }: { info: ControlDetailInfo }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [guidanceOpen, setGuidanceOpen] = useState(false);
  const [summaryText, setSummaryText] = useState(info.practical_summary || "");
  const [docError, setDocError] = useState("");

  const explainMut = useMutation({
    mutationFn: () => controlsApi.explainControl(info.control_uuid, i18n.language || "it"),
    onSuccess: (data) => {
      setSummaryText(data.summary);
      qc.invalidateQueries({ queryKey: ["control-detail", info.control_id] });
    },
  });

  const generateDocMut = useMutation({
    mutationFn: () => controlsApi.generateDocument(info.control_uuid, i18n.language || "it"),
    onSuccess: (blob) => {
      setDocError("");
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${info.control_id}_procedura.docx`;
      a.click();
      URL.revokeObjectURL(url);
    },
    onError: () => setDocError(t("controls.drawer.about.generate_doc_error")),
  });

  return (
    <div className="space-y-4">
      <div>
        <div className="flex flex-wrap gap-2 mb-2">
          <span className="px-2 py-0.5 text-xs font-semibold bg-blue-100 text-blue-800 rounded">{info.framework}</span>
          {info.level && <span className="px-2 py-0.5 text-xs bg-purple-100 text-purple-700 rounded">{info.level}</span>}
          {info.control_category && <span className="px-2 py-0.5 text-xs bg-teal-100 text-teal-700 rounded capitalize">{info.control_category}</span>}
          {info.domain && <span className="px-2 py-0.5 text-xs bg-gray-100 text-gray-600 rounded">{info.domain}</span>}
        </div>
        <h3 className="text-base font-semibold text-gray-900 leading-snug">{info.title}</h3>
        <p className="text-xs font-mono text-gray-400 mt-0.5">{info.control_id}</p>
      </div>

      {info.description ? (
        <div className="bg-blue-50 rounded-lg p-3 text-sm text-gray-700 leading-relaxed">
          {info.description}
        </div>
      ) : (
        <p className="text-sm text-gray-400 italic">{t("controls.drawer.about.no_description")}</p>
      )}

      {/* Requisiti normativi granulari (es. misure ACN NIS2), raggruppati per ambito */}
      {info.normative_requirements?.length > 0 && (
        <div className="border border-indigo-200 rounded-lg p-3 space-y-2">
          <p className="text-xs font-semibold text-indigo-700 uppercase tracking-wide">
            {t("controls.drawer.about.normative_requirements")}
          </p>
          {Object.entries(
            info.normative_requirements.reduce<Record<string, typeof info.normative_requirements>>((acc, r) => {
              (acc[r.ambito] ??= []).push(r);
              return acc;
            }, {}),
          ).map(([ambito, items]) => (
            <div key={ambito} className="space-y-1">
              {ambito && <p className="text-xs font-medium text-gray-500 mt-1">{ambito}</p>}
              <ul className="space-y-1">
                {items.map((r, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
                    {r.punto && <span className="text-indigo-400 font-mono text-xs shrink-0 mt-0.5">{r.punto}</span>}
                    <span>
                      {r.text}
                      {r.applies_to?.map((a) => (
                        <span key={a} className="ml-1.5 text-[10px] px-1 py-0.5 rounded bg-gray-100 text-gray-500 align-middle">
                          {t(`controls.drawer.about.applies_to.${a}`, { defaultValue: a })}
                        </span>
                      ))}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      )}

      {/* Spiegazione AI plain-language */}
      <div className="border border-purple-200 rounded-lg overflow-hidden">
        <div className="flex items-center justify-between px-3 py-2 bg-purple-50">
          <span className="text-xs font-semibold text-purple-700 flex items-center gap-1.5">
            ✨ {t("controls.drawer.about.ai_summary_title")}
          </span>
          <button
            onClick={() => explainMut.mutate()}
            disabled={explainMut.isPending}
            className="text-xs px-2 py-0.5 rounded bg-purple-600 text-white hover:bg-purple-700 disabled:opacity-50"
          >
            {explainMut.isPending
              ? t("controls.drawer.about.ai_generating")
              : summaryText
              ? t("controls.drawer.about.ai_regenerate")
              : t("controls.drawer.about.ai_generate")}
          </button>
        </div>
        {summaryText ? (
          <div className="px-3 py-2.5 text-sm text-gray-700 leading-relaxed">
            {summaryText}
          </div>
        ) : (
          <p className="px-3 py-2.5 text-xs text-gray-400 italic">
            {t("controls.drawer.about.ai_summary_empty")}
          </p>
        )}
        {explainMut.isError && (
          <p className="px-3 pb-2 text-xs text-red-600">
            {(explainMut.error as { response?: { data?: { error?: string } } })?.response?.data?.error || t("common.error")}
          </p>
        )}
      </div>

      {/* Riepilogo plain-language di cosa serve per soddisfare il controllo */}
      {(info.evidence_requirement?.documents?.length > 0 ||
        info.evidence_requirement?.evidences?.length > 0 ||
        info.evidence_requirement?.min_documents > 0 ||
        info.evidence_requirement?.min_evidences > 0) && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 space-y-2">
          <p className="text-xs font-semibold text-amber-800 uppercase tracking-wide">
            {t("controls.drawer.about.what_is_needed")}
          </p>
          <ul className="space-y-1">
            {info.evidence_requirement.documents?.filter(d => d.mandatory).map((d, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
                <span className="text-amber-500 shrink-0 mt-0.5">📄</span>
                <span>
                  <span className="font-medium">{t("controls.drawer.about.req_doc")}:</span>{" "}
                  {d.description || t(`documents.type.${d.type}`, { defaultValue: d.type })}
                </span>
              </li>
            ))}
            {info.evidence_requirement.evidences?.filter(e => e.mandatory).map((e, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
                <span className="text-amber-500 shrink-0 mt-0.5">🔬</span>
                <span>
                  <span className="font-medium">{t("controls.drawer.about.req_evidence")}:</span>{" "}
                  {e.description || t(`documents.evidence.types.${e.type}`, { defaultValue: e.type })}
                  {e.max_age_days && (
                    <span className="ml-1 text-xs text-gray-400">
                      ({t("controls.drawer.about.req_max_age", { days: e.max_age_days })})
                    </span>
                  )}
                </span>
              </li>
            ))}
            {info.evidence_requirement.min_documents > 0 && (
              <li className="flex items-start gap-2 text-sm text-gray-700">
                <span className="text-amber-500 shrink-0 mt-0.5">📌</span>
                <span>{t("controls.drawer.about.req_min_docs", { count: info.evidence_requirement.min_documents })}</span>
              </li>
            )}
            {info.evidence_requirement.min_evidences > 0 && (
              <li className="flex items-start gap-2 text-sm text-gray-700">
                <span className="text-amber-500 shrink-0 mt-0.5">📌</span>
                <span>{t("controls.drawer.about.req_min_evidences", { count: info.evidence_requirement.min_evidences })}</span>
              </li>
            )}
            {info.evidence_requirement.notes && (
              <li className="text-xs text-gray-500 italic pl-6">{info.evidence_requirement.notes}</li>
            )}
          </ul>
        </div>
      )}

      {/* Genera documento procedura */}
      <div className="border border-emerald-200 rounded-lg overflow-hidden">
        <div className="flex items-center justify-between px-3 py-2 bg-emerald-50">
          <span className="text-xs font-semibold text-emerald-700 flex items-center gap-1.5">
            📄 {t("controls.drawer.about.generate_doc_title")}
          </span>
          <button
            onClick={() => generateDocMut.mutate()}
            disabled={generateDocMut.isPending}
            className="text-xs px-2 py-0.5 rounded bg-emerald-600 text-white hover:bg-emerald-700 disabled:opacity-50 flex items-center gap-1"
          >
            {generateDocMut.isPending && (
              <svg className="animate-spin w-3 h-3" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
              </svg>
            )}
            {generateDocMut.isPending
              ? t("controls.drawer.about.generating_doc")
              : t("controls.drawer.about.generate_doc_btn")}
          </button>
        </div>
        <div className="px-3 py-2 text-xs text-gray-500">
          {t("controls.drawer.about.generate_doc_hint")}
        </div>
        {docError && (
          <p className="px-3 pb-2 text-xs text-red-600">⛔ {docError}</p>
        )}
      </div>

      {info.implementation_guidance && (
        <div className="border border-gray-200 rounded-lg">
          <button
            onClick={() => setGuidanceOpen(o => !o)}
            className="w-full flex items-center justify-between px-3 py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            <span>{t("controls.drawer.about.guidance")}</span>
            <span className="text-gray-400">{guidanceOpen ? "▲" : "▼"}</span>
          </button>
          {guidanceOpen && (
            <div className="px-3 pb-3 text-sm text-gray-600 leading-relaxed border-t border-gray-100 pt-2">
              {info.implementation_guidance}
            </div>
          )}
        </div>
      )}

      {info.evidence_examples.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">{t("controls.drawer.about.evidence_examples")}</p>
          <div className="space-y-1.5">
            {info.evidence_examples.map((ex, i) => {
              const icon = ex.toLowerCase().includes("screenshot") ? "📸"
                : ex.toLowerCase().includes("log") ? "📋"
                : ex.toLowerCase().includes("certificat") ? "🏆"
                : "📄";
              return (
                <div key={i} className="flex items-center gap-2 text-sm text-gray-700">
                  <span>{icon}</span><span>{ex}</span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {info.mappings.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">{t("controls.drawer.about.mappings")}</p>
          <div className="flex flex-wrap gap-1.5">
            {info.mappings.map((m, i) => (
              <span key={i} className="text-xs bg-indigo-50 border border-indigo-100 text-indigo-700 px-2 py-0.5 rounded">
                {m.relationship} → {m["target_control__framework__code"]} {m["target_control__external_id"]}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
