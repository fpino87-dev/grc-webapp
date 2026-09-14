import { useTranslation } from "react-i18next";
import i18n from "../../i18n";
import type { EvaluationConfig } from "../../api/endpoints/suppliers";

type LabelsByParam = EvaluationConfig["parameter_labels"];
type ParamLabels = LabelsByParam[keyof LabelsByParam] | undefined;

/**
 * Etichette dei parametri della valutazione interna nella lingua dell'utente.
 *
 * Nomi e livelli vivono in `SupplierEvaluationConfig.parameter_labels` (DB) e
 * nascono dai default italiani del backend, che l'amministratore può
 * modificare dalle Impostazioni. Un testo ancora uguale al default italiano
 * viene tradotto; uno personalizzato è mostrato così come è stato scritto,
 * perché non esiste una sua traduzione.
 */
export function useEvaluationLabels() {
  const { t } = useTranslation();

  function localize(path: string, stored: string | undefined): string | undefined {
    if (!stored) return stored;
    const key = `suppliers.evaluation.params.${path}`;
    const italianDefault = i18n.getResource("it", "common", key);
    return stored === italianDefault ? t(key) : stored;
  }

  return {
    paramName: (key: string, labels: ParamLabels): string =>
      localize(`${key}.name`, labels?.name) ?? key,
    levelLabel: (key: string, labels: ParamLabels, score: number): string | undefined =>
      localize(`${key}.levels.${score}`, labels?.levels?.[score - 1]),
  };
}
