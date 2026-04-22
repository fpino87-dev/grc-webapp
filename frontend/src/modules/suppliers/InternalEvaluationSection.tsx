import { useState, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import {
  suppliersApi,
  type InternalEvaluation,
  type EvaluationConfig,
} from "../../api/endpoints/suppliers";

type ParamKey = "impatto" | "accesso" | "dati" | "dipendenza" | "integrazione" | "compliance";
const PARAM_KEYS: ParamKey[] = ["impatto", "accesso", "dati", "dipendenza", "integrazione", "compliance"];

function riskClassClasses(cls: string): string {
  switch (cls) {
    case "basso": return "bg-green-100 text-green-800";
    case "medio": return "bg-yellow-100 text-yellow-800";
    case "alto": return "bg-orange-100 text-orange-800";
    case "critico": return "bg-red-100 text-red-800";
    default: return "bg-gray-100 text-gray-700";
  }
}

function formatWeightedScore(value: string | number): string {
  const n = typeof value === "string" ? parseFloat(value) : value;
  return Number.isFinite(n) ? n.toFixed(2) : String(value);
}

export function InternalEvaluationSection({ supplierId }: { supplierId: string }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);

  const { data: config } = useQuery<EvaluationConfig>({
    queryKey: ["suppliers", "evaluation-config"],
    queryFn: suppliersApi.getEvaluationConfig,
    staleTime: 5 * 60 * 1000,
  });

  const { data: current, isLoading } = useQuery<InternalEvaluation | null>({
    queryKey: ["suppliers", supplierId, "internal-evaluation", "current"],
    queryFn: () => suppliersApi.getCurrentEvaluation(supplierId),
  });

  const { data: history } = useQuery({
    queryKey: ["suppliers", supplierId, "internal-evaluation", "history"],
    queryFn: () => suppliersApi.listEvaluationHistory(supplierId),
  });

  if (isLoading || !config) {
    return <div className="p-6 text-sm text-gray-500">{t("common.loading", "Caricamento…")}</div>;
  }

  return (
    <div className="p-4 space-y-4">
      {current ? (
        <CurrentEvaluationCard evaluation={current} config={config} />
      ) : (
        <div className="rounded border border-dashed border-gray-300 p-4 text-sm text-gray-600">
          {t("suppliers.evaluation.no_current", "Nessuna valutazione interna registrata.")}
        </div>
      )}

      <div className="flex items-center justify-between">
        <h4 className="text-sm font-semibold text-gray-700">
          {t("suppliers.evaluation.title", "Valutazione interna del rischio")}
        </h4>
        <button
          onClick={() => setShowForm(v => !v)}
          className="px-3 py-1.5 text-xs font-medium rounded bg-indigo-600 text-white hover:bg-indigo-700"
        >
          {showForm
            ? t("common.cancel", "Annulla")
            : current
              ? t("suppliers.evaluation.new", "Nuova valutazione")
              : t("suppliers.evaluation.start", "Avvia valutazione")}
        </button>
      </div>

      {showForm && (
        <EvaluationForm
          config={config}
          onSubmit={async (scores, notes) => {
            await suppliersApi.createEvaluation(supplierId, scores, notes);
            await qc.invalidateQueries({ queryKey: ["suppliers", supplierId, "internal-evaluation"] });
            await qc.invalidateQueries({ queryKey: ["suppliers"] });
            setShowForm(false);
          }}
        />
      )}

      {history && history.results.length > 1 && (
        <EvaluationHistoryTable history={history.results} />
      )}
    </div>
  );
}

function CurrentEvaluationCard({
  evaluation,
  config,
}: {
  evaluation: InternalEvaluation;
  config: EvaluationConfig;
}) {
  const { t } = useTranslation();
  const scores: Record<ParamKey, number> = {
    impatto: evaluation.score_impatto,
    accesso: evaluation.score_accesso,
    dati: evaluation.score_dati,
    dipendenza: evaluation.score_dipendenza,
    integrazione: evaluation.score_integrazione,
    compliance: evaluation.score_compliance,
  };
  return (
    <div className="rounded border border-gray-200 bg-white p-4">
      <div className="flex items-center justify-between mb-3">
        <div>
          <div className="text-xs uppercase tracking-wide text-gray-500">
            {t("suppliers.evaluation.current", "Valutazione corrente")}
          </div>
          <div className="text-sm text-gray-700">
            {new Date(evaluation.evaluated_at).toLocaleDateString()}
            {evaluation.evaluated_by_display && <> — {evaluation.evaluated_by_display}</>}
          </div>
        </div>
        <div className="flex items-center gap-3">
          <div className="text-right">
            <div className="text-xs text-gray-500">{t("suppliers.evaluation.weighted", "Weighted score")}</div>
            <div className="text-lg font-semibold">{formatWeightedScore(evaluation.weighted_score)}</div>
          </div>
          <span className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold ${riskClassClasses(evaluation.risk_class)}`}>
            {t(`suppliers.risk.${evaluation.risk_class}`, evaluation.risk_class)}
          </span>
        </div>
      </div>
      <table className="w-full text-xs">
        <thead className="text-gray-500">
          <tr>
            <th className="text-left font-medium py-1">{t("suppliers.evaluation.param", "Parametro")}</th>
            <th className="text-center font-medium py-1">{t("suppliers.evaluation.score", "Score")}</th>
            <th className="text-center font-medium py-1">{t("suppliers.evaluation.weight", "Peso")}</th>
            <th className="text-left font-medium py-1">{t("suppliers.evaluation.level", "Livello")}</th>
          </tr>
        </thead>
        <tbody>
          {PARAM_KEYS.map(key => {
            const score = scores[key];
            const weight = evaluation.weights_snapshot?.[key] ?? config.weights[key];
            const labels = config.parameter_labels[key];
            return (
              <tr key={key} className="border-t border-gray-100">
                <td className="py-1 text-gray-700">{labels?.name ?? key}</td>
                <td className="py-1 text-center font-mono">{score}</td>
                <td className="py-1 text-center text-gray-500">{(weight * 100).toFixed(0)}%</td>
                <td className="py-1 text-gray-600">{labels?.levels?.[score - 1] ?? "—"}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
      {evaluation.notes && (
        <div className="mt-3 text-xs text-gray-600 italic border-t pt-2">
          {evaluation.notes}
        </div>
      )}
    </div>
  );
}

function EvaluationForm({
  config,
  onSubmit,
}: {
  config: EvaluationConfig;
  onSubmit: (
    scores: {
      score_impatto: number;
      score_accesso: number;
      score_dati: number;
      score_dipendenza: number;
      score_integrazione: number;
      score_compliance: number;
    },
    notes: string,
  ) => void | Promise<void>;
}) {
  const { t } = useTranslation();
  const [scores, setScores] = useState<Record<ParamKey, number>>({
    impatto: 3, accesso: 3, dati: 3, dipendenza: 3, integrazione: 3, compliance: 3,
  });
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const weighted = useMemo(
    () => PARAM_KEYS.reduce((sum, k) => sum + scores[k] * config.weights[k], 0),
    [scores, config.weights],
  );
  const previewClass = useMemo(() => {
    const thr = config.risk_thresholds;
    if (weighted >= thr.critico) return "critico";
    if (weighted >= thr.alto) return "alto";
    if (weighted >= thr.medio) return "medio";
    return "basso";
  }, [weighted, config.risk_thresholds]);

  const submitMut = useMutation({
    mutationFn: async () => {
      await onSubmit(
        {
          score_impatto: scores.impatto,
          score_accesso: scores.accesso,
          score_dati: scores.dati,
          score_dipendenza: scores.dipendenza,
          score_integrazione: scores.integrazione,
          score_compliance: scores.compliance,
        },
        notes,
      );
    },
    onError: (err: any) => {
      const msg = err?.response?.data?.error ?? err?.message ?? "Errore";
      setError(Array.isArray(msg) ? msg.join(", ") : String(msg));
    },
  });

  return (
    <form
      onSubmit={e => {
        e.preventDefault();
        setError(null);
        setSubmitting(true);
        submitMut.mutate(undefined, {
          onSettled: () => setSubmitting(false),
        });
      }}
      className="rounded border border-indigo-200 bg-indigo-50/40 p-4 space-y-3"
    >
      <div className="text-xs text-gray-600">
        {t(
          "suppliers.evaluation.form_help",
          "Valuta ciascun parametro su scala 1–5 (1 = rischio minimo, 5 = rischio massimo). Il peso è configurabile in Impostazioni.",
        )}
      </div>
      {PARAM_KEYS.map(key => {
        const labels = config.parameter_labels[key];
        return (
          <div key={key} className="grid grid-cols-12 gap-2 items-center">
            <label className="col-span-3 text-sm text-gray-700" title={labels?.name}>
              {labels?.name ?? key}
              <span className="ml-1 text-xs text-gray-400">({(config.weights[key] * 100).toFixed(0)}%)</span>
            </label>
            <div className="col-span-5 flex gap-1">
              {[1, 2, 3, 4, 5].map(n => (
                <button
                  key={n}
                  type="button"
                  onClick={() => setScores(s => ({ ...s, [key]: n }))}
                  className={`flex-1 py-1 text-sm font-medium rounded border ${
                    scores[key] === n
                      ? "bg-indigo-600 text-white border-indigo-600"
                      : "bg-white text-gray-700 border-gray-300 hover:border-indigo-400"
                  }`}
                >
                  {n}
                </button>
              ))}
            </div>
            <div className="col-span-4 text-xs text-gray-600 truncate" title={labels?.levels?.[scores[key] - 1]}>
              {labels?.levels?.[scores[key] - 1] ?? "—"}
            </div>
          </div>
        );
      })}
      <div>
        <label className="block text-sm text-gray-700 mb-1">{t("common.notes", "Note")}</label>
        <textarea
          value={notes}
          onChange={e => setNotes(e.target.value)}
          rows={2}
          className="w-full border border-gray-300 rounded px-2 py-1 text-sm"
        />
      </div>
      <div className="flex items-center justify-between border-t border-indigo-200 pt-3">
        <div className="text-sm">
          <span className="text-gray-600">{t("suppliers.evaluation.preview", "Anteprima")}: </span>
          <span className="font-mono">{weighted.toFixed(2)}</span>
          <span className={`ml-3 inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold ${riskClassClasses(previewClass)}`}>
            {t(`suppliers.risk.${previewClass}`, previewClass)}
          </span>
        </div>
        <button
          type="submit"
          disabled={submitting}
          className="px-4 py-1.5 text-sm font-medium rounded bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-50"
        >
          {submitting ? t("common.saving", "Salvataggio…") : t("common.save", "Salva")}
        </button>
      </div>
      {error && <div className="text-sm text-red-600">{error}</div>}
    </form>
  );
}

function EvaluationHistoryTable({ history }: { history: InternalEvaluation[] }) {
  const { t } = useTranslation();
  return (
    <div>
      <h5 className="text-xs uppercase tracking-wide text-gray-500 mb-2">
        {t("suppliers.evaluation.history", "Storico valutazioni")}
      </h5>
      <table className="w-full text-xs">
        <thead className="bg-gray-50 text-gray-600">
          <tr>
            <th className="text-left px-2 py-1">{t("common.date", "Data")}</th>
            <th className="text-left px-2 py-1">{t("common.user", "Utente")}</th>
            <th className="text-center px-2 py-1">{t("suppliers.evaluation.weighted", "Score")}</th>
            <th className="text-left px-2 py-1">{t("suppliers.evaluation.class", "Classe")}</th>
            <th className="text-left px-2 py-1">{t("common.notes", "Note")}</th>
          </tr>
        </thead>
        <tbody>
          {history.map(h => (
            <tr key={h.id} className={`border-t border-gray-100 ${h.is_current ? "bg-indigo-50/40" : ""}`}>
              <td className="px-2 py-1">{new Date(h.evaluated_at).toLocaleDateString()}</td>
              <td className="px-2 py-1 text-gray-600">{h.evaluated_by_display ?? "—"}</td>
              <td className="px-2 py-1 text-center font-mono">{formatWeightedScore(h.weighted_score)}</td>
              <td className="px-2 py-1">
                <span className={`inline-flex items-center px-2 py-0.5 rounded-full ${riskClassClasses(h.risk_class)}`}>
                  {t(`suppliers.risk.${h.risk_class}`, h.risk_class)}
                </span>
                {h.is_current && <span className="ml-2 text-[10px] uppercase text-indigo-700">{t("common.current", "Corrente")}</span>}
              </td>
              <td className="px-2 py-1 text-gray-600 truncate max-w-[250px]" title={h.notes}>{h.notes || "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
