import { useEffect, useState, useMemo } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { suppliersApi, type EvaluationConfig } from "../../api/endpoints/suppliers";
import { useAuthStore } from "../../store/auth";

type ParamKey = "impatto" | "accesso" | "dati" | "dipendenza" | "integrazione" | "compliance";
const PARAM_KEYS: ParamKey[] = ["impatto", "accesso", "dati", "dipendenza", "integrazione", "compliance"];

export function SupplierEvaluationSettingsPage() {
  const { t } = useTranslation();
  const role = useAuthStore(s => s.user?.role);
  const canEdit = role === "super_admin";
  const qc = useQueryClient();
  const [form, setForm] = useState<EvaluationConfig | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  const { data, isLoading } = useQuery<EvaluationConfig>({
    queryKey: ["suppliers", "evaluation-config"],
    queryFn: suppliersApi.getEvaluationConfig,
  });

  useEffect(() => {
    if (data && !form) setForm(data);
  }, [data, form]);

  const weightsSum = useMemo(() => {
    if (!form) return 0;
    return PARAM_KEYS.reduce((s, k) => s + (Number(form.weights[k]) || 0), 0);
  }, [form]);

  const saveMut = useMutation({
    mutationFn: (payload: Partial<EvaluationConfig>) => suppliersApi.updateEvaluationConfig(payload),
    onSuccess: (updated) => {
      setForm(updated);
      qc.invalidateQueries({ queryKey: ["suppliers", "evaluation-config"] });
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    },
    onError: (err: any) => {
      const data = err?.response?.data;
      if (data && typeof data === "object") {
        setError(Object.entries(data).map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(", ") : v}`).join(" — "));
      } else {
        setError(String(err?.message ?? "Errore"));
      }
    },
  });

  if (isLoading || !form) return <div className="p-6 text-gray-500">{t("common.loading", "Caricamento…")}</div>;

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (Math.abs(weightsSum - 1) > 0.001) {
      setError(t("suppliers.settings.weights_must_sum", "La somma dei pesi deve essere 1.00"));
      return;
    }
    saveMut.mutate({
      weights: form!.weights,
      parameter_labels: form!.parameter_labels,
      risk_thresholds: form!.risk_thresholds,
      questionnaire_validity_months: form!.questionnaire_validity_months,
      assessment_validity_months: form!.assessment_validity_months,
      nis2_concentration_bump: form!.nis2_concentration_bump,
    });
  }

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">
          {t("suppliers.settings.title", "Valutazione fornitori — Configurazione")}
        </h1>
        <p className="text-sm text-gray-600 mt-1">
          {t(
            "suppliers.settings.subtitle",
            "Pesi, label dei parametri, soglie di classificazione e validità assessment. Nessun valore è hardcoded.",
          )}
        </p>
      </div>

      {!canEdit && (
        <div className="rounded border border-amber-200 bg-amber-50 px-4 py-2 text-sm text-amber-800">
          {t("suppliers.settings.readonly", "Sola lettura — solo super_admin può modificare.")}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Pesi */}
        <section className="bg-white rounded border border-gray-200 p-4">
          <h2 className="text-base font-semibold mb-2">
            {t("suppliers.settings.weights", "Pesi parametri")}
            <span className={`ml-3 text-xs font-mono ${Math.abs(weightsSum - 1) < 0.001 ? "text-green-600" : "text-red-600"}`}>
              Σ = {weightsSum.toFixed(3)}
            </span>
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            {PARAM_KEYS.map(k => (
              <label key={k} className="text-sm">
                <span className="block text-gray-700 mb-1">
                  {form.parameter_labels[k]?.name ?? k}
                </span>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  max="1"
                  value={form.weights[k]}
                  disabled={!canEdit}
                  onChange={e =>
                    setForm(f => f && ({
                      ...f,
                      weights: { ...f.weights, [k]: parseFloat(e.target.value) || 0 },
                    }))
                  }
                  className="w-full border border-gray-300 rounded px-2 py-1 text-sm font-mono"
                />
              </label>
            ))}
          </div>
        </section>

        {/* Soglie */}
        <section className="bg-white rounded border border-gray-200 p-4">
          <h2 className="text-base font-semibold mb-2">
            {t("suppliers.settings.thresholds", "Soglie di classificazione")}
          </h2>
          <p className="text-xs text-gray-500 mb-2">
            {t(
              "suppliers.settings.thresholds_help",
              "Classe basso < soglia medio ≤ classe medio < soglia alto ≤ classe alto < soglia critico ≤ classe critico.",
            )}
          </p>
          <div className="grid grid-cols-3 gap-3">
            {(["medio", "alto", "critico"] as const).map(k => (
              <label key={k} className="text-sm">
                <span className="block text-gray-700 mb-1">≥ {k}</span>
                <input
                  type="number"
                  step="0.1"
                  min="1"
                  max="5"
                  value={form.risk_thresholds[k]}
                  disabled={!canEdit}
                  onChange={e =>
                    setForm(f => f && ({
                      ...f,
                      risk_thresholds: { ...f.risk_thresholds, [k]: parseFloat(e.target.value) || 0 },
                    }))
                  }
                  className="w-full border border-gray-300 rounded px-2 py-1 text-sm font-mono"
                />
              </label>
            ))}
          </div>
        </section>

        {/* Formula risk_adj — box informativo */}
        <section className="bg-indigo-50 rounded border border-indigo-200 p-4">
          <h2 className="text-sm font-semibold text-indigo-800 mb-2">Come viene calcolato il Rischio Adj</h2>
          <div className="text-xs text-indigo-900 space-y-1">
            <p><span className="font-mono bg-indigo-100 px-1 rounded">base = max(interno, questionario*, audit*)</span> — worst-case tra le sorgenti presenti</p>
            <p><span className="font-mono bg-indigo-100 px-1 rounded">risk_adj = base + bump</span> — dove bump = +1 classe se NIS2 rilevante e concentrazione &gt;50%</p>
            <ul className="mt-2 space-y-0.5 list-none pl-2 border-l-2 border-indigo-300">
              <li><strong>Interno</strong> — ultima valutazione interna (sempre attiva, nessuna scadenza)</li>
              <li><strong>Questionario *</strong> — ultimo questionario risposto non scaduto (validità configurabile sotto)</li>
              <li><strong>Audit terze parti *</strong> — ultimo audit approvato entro finestra configurabile</li>
            </ul>
            <p className="text-indigo-600 mt-1">* sorgente opzionale: partecipa solo se presente e valida</p>
          </div>
        </section>

        {/* Validità + Bump NIS2 */}
        <section className="bg-white rounded border border-gray-200 p-4">
          <h2 className="text-base font-semibold mb-3">
            {t("suppliers.settings.operational", "Parametri operativi")}
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            <label className="text-sm">
              <span className="block text-gray-700 font-medium mb-0.5">
                Validità questionario (mesi)
              </span>
              <span className="block text-xs text-gray-400 mb-1">
                Durata del risultato del questionario. Determina l'<span className="font-mono">expires_at</span> al momento della registrazione della risposta.
              </span>
              <input
                type="number"
                min="1"
                max="60"
                value={form.questionnaire_validity_months}
                disabled={!canEdit}
                onChange={e => setForm(f => f && ({ ...f, questionnaire_validity_months: parseInt(e.target.value) || 12 }))}
                className="w-full border border-gray-300 rounded px-2 py-1 text-sm font-mono"
              />
            </label>
            <label className="text-sm">
              <span className="block text-gray-700 font-medium mb-0.5">
                {t("suppliers.settings.validity", "Validità audit terze parti (mesi)")}
              </span>
              <span className="block text-xs text-gray-400 mb-1">
                Finestra di validità per gli audit terze parti approvati. Oltre questa soglia l'audit non partecipa al calcolo del risk_adj.
              </span>
              <input
                type="number"
                min="1"
                max="60"
                value={form.assessment_validity_months}
                disabled={!canEdit}
                onChange={e => setForm(f => f && ({ ...f, assessment_validity_months: parseInt(e.target.value) || 12 }))}
                className="w-full border border-gray-300 rounded px-2 py-1 text-sm font-mono"
              />
            </label>
          </div>
          <label className="text-sm flex items-start gap-2">
            <input
              type="checkbox"
              checked={form.nis2_concentration_bump}
              disabled={!canEdit}
              onChange={e => setForm(f => f && ({ ...f, nis2_concentration_bump: e.target.checked }))}
              className="mt-1"
            />
            <div>
              <div className="text-gray-700 font-medium">{t("suppliers.settings.bump_nis2", "Bump NIS2 + concentrazione critica")}</div>
              <div className="text-xs text-gray-500">
                Aggiunge +1 classe al risk_adj per fornitori con <span className="font-mono">nis2_relevant=True</span> e concentrazione fornitura &gt;50% (soglia TPRM "critica"). Saturazione a "critico".
              </div>
            </div>
          </label>
        </section>

        {/* Label parametri — read-only per ora, verrà mostrato in tabella */}
        <section className="bg-white rounded border border-gray-200 p-4">
          <h2 className="text-base font-semibold mb-2">
            {t("suppliers.settings.labels", "Label livelli per parametro")}
          </h2>
          <div className="space-y-3">
            {PARAM_KEYS.map(k => (
              <div key={k}>
                <div className="text-sm font-medium text-gray-700 mb-1">
                  {form.parameter_labels[k]?.name ?? k}
                </div>
                <div className="grid grid-cols-5 gap-2">
                  {[0, 1, 2, 3, 4].map(idx => (
                    <input
                      key={idx}
                      type="text"
                      value={form.parameter_labels[k]?.levels?.[idx] ?? ""}
                      disabled={!canEdit}
                      onChange={e =>
                        setForm(f => {
                          if (!f) return f;
                          const levels = [...(f.parameter_labels[k]?.levels ?? ["", "", "", "", ""])];
                          levels[idx] = e.target.value;
                          return {
                            ...f,
                            parameter_labels: {
                              ...f.parameter_labels,
                              [k]: { ...f.parameter_labels[k], levels },
                            },
                          };
                        })
                      }
                      placeholder={`Livello ${idx + 1}`}
                      className="w-full border border-gray-300 rounded px-2 py-1 text-xs"
                    />
                  ))}
                </div>
              </div>
            ))}
          </div>
        </section>

        {canEdit && (
          <div className="flex items-center justify-between">
            <div className="text-sm">
              {error && <span className="text-red-600">{error}</span>}
              {saved && <span className="text-green-600">{t("common.saved", "Salvato")}</span>}
            </div>
            <button
              type="submit"
              disabled={saveMut.isPending}
              className="px-4 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700 disabled:opacity-50"
            >
              {saveMut.isPending ? t("common.saving", "Salvataggio…") : t("common.save", "Salva")}
            </button>
          </div>
        )}
      </form>
    </div>
  );
}
