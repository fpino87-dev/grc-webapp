import { useEffect, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { incidentsApi, type NIS2Configuration } from "../../api/endpoints/incidents";
import { useTranslation } from "react-i18next";

export const CSIRT_BY_COUNTRY: Record<string, { name: string; portal: string }> = {
  IT: {
    name: "ACN — Agenzia Cybersicurezza Nazionale",
    portal: "https://www.acn.gov.it/portale/nis/notifica-incidenti",
  },
  DE: {
    name: "BSI — Bundesamt fur Sicherheit in der Informationstechnik",
    portal: "https://www.bsi.bund.de/EN/Topics/KRITIS/NIS2/nis2_node.html",
  },
  FR: { name: "ANSSI", portal: "https://www.ssi.gouv.fr/en/" },
};

export function Nis2ConfigPanel({ plantId, plantCountry }: { plantId: string; plantCountry: string }) {
  const { t } = useTranslation();
  const qc = useQueryClient();

  const { data: configData } = useQuery({
    queryKey: ["nis2-config", plantId],
    queryFn: () => incidentsApi.listConfig(plantId),
    enabled: !!plantId,
  });
  const currentConfig = configData?.[0];

  const [configForm, setConfigForm] = useState<Partial<NIS2Configuration>>({
    threshold_users: 100,
    threshold_hours: 4,
    threshold_financial: 100000,
    multiplier_medium: 2,
    multiplier_high: 3,
    ptnr_threshold: 4,
    recurrence_window_days: 90,
    recurrence_score_bonus: 2,
  });

  const configMutation = useMutation({
    mutationFn: () => {
      const payload = { ...configForm, plant: plantId } as NIS2Configuration;
      if (currentConfig?.id) return incidentsApi.updateConfig(currentConfig.id, payload);
      return incidentsApi.createConfig(payload);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["nis2-config", plantId] }),
  });

  useEffect(() => {
    if (!currentConfig) return;
    setConfigForm({
      threshold_users: currentConfig.threshold_users,
      threshold_hours: currentConfig.threshold_hours,
      threshold_financial: currentConfig.threshold_financial,
      multiplier_medium: currentConfig.multiplier_medium ?? 2,
      multiplier_high: currentConfig.multiplier_high ?? 3,
      ptnr_threshold: currentConfig.ptnr_threshold ?? 4,
      recurrence_window_days: currentConfig.recurrence_window_days ?? 90,
      recurrence_score_bonus: currentConfig.recurrence_score_bonus ?? 2,
    });
  }, [currentConfig]);

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4 space-y-3 max-w-4xl">
      <div className="text-sm font-semibold">{t("incidents.nis2_classification.config.calc_title")}</div>
      <p className="text-xs text-gray-500 bg-blue-50 border border-blue-100 rounded p-2">{t("incidents.nis2_classification.config.ptnr_note")}</p>
      <p className="text-xs text-gray-600">{t("incidents.nis2_config_plant_note")}</p>
      <div className="text-xs font-semibold text-gray-700 pt-1">{t("incidents.nis2_classification.config.base_title")}</div>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <div className="space-y-1">
          <label className="text-xs font-medium text-gray-600">{t("incidents.nis2_config_labels.threshold_users")}</label>
          <input
            className="w-full border rounded px-2 py-1.5 text-sm"
            type="number"
            value={configForm.threshold_users ?? currentConfig?.threshold_users ?? 100}
            onChange={(e) => setConfigForm((f) => ({ ...f, threshold_users: Number(e.target.value) }))}
          />
        </div>
        <div className="space-y-1">
          <label className="text-xs font-medium text-gray-600">{t("incidents.nis2_config_labels.threshold_hours")}</label>
          <input
            className="w-full border rounded px-2 py-1.5 text-sm"
            type="number"
            step="0.01"
            value={configForm.threshold_hours ?? currentConfig?.threshold_hours ?? 4}
            onChange={(e) => setConfigForm((f) => ({ ...f, threshold_hours: Number(e.target.value) }))}
          />
        </div>
        <div className="space-y-1">
          <label className="text-xs font-medium text-gray-600">{t("incidents.nis2_config_labels.threshold_financial")}</label>
          <input
            className="w-full border rounded px-2 py-1.5 text-sm"
            type="number"
            value={configForm.threshold_financial ?? currentConfig?.threshold_financial ?? 100000}
            onChange={(e) => setConfigForm((f) => ({ ...f, threshold_financial: Number(e.target.value) }))}
          />
        </div>
      </div>
      <div className="text-xs font-semibold text-gray-700 pt-2">{t("incidents.nis2_classification.config.multiplier_title")}</div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div className="space-y-1">
          <label className="text-xs font-medium text-gray-600">{t("incidents.nis2_classification.config.multiplier_m")}</label>
          <input
            className="w-full border rounded px-2 py-1.5 text-sm"
            type="number"
            step="0.01"
            value={configForm.multiplier_medium ?? currentConfig?.multiplier_medium ?? 2}
            onChange={(e) => setConfigForm((f) => ({ ...f, multiplier_medium: Number(e.target.value) }))}
          />
        </div>
        <div className="space-y-1">
          <label className="text-xs font-medium text-gray-600">{t("incidents.nis2_classification.config.multiplier_h")}</label>
          <input
            className="w-full border rounded px-2 py-1.5 text-sm"
            type="number"
            step="0.01"
            value={configForm.multiplier_high ?? currentConfig?.multiplier_high ?? 3}
            onChange={(e) => setConfigForm((f) => ({ ...f, multiplier_high: Number(e.target.value) }))}
          />
        </div>
      </div>
      <p className="text-xs text-gray-500">{t("incidents.nis2_classification.config.multiplier_note")}</p>
      <div className="text-xs font-semibold text-gray-700 pt-2">{t("incidents.nis2_classification.config.rule_title")}</div>
      <div className="max-w-xs space-y-1">
        <label className="text-xs font-medium text-gray-600">{t("incidents.nis2_classification.config.ptnr_threshold")}</label>
        <input
          className="w-full border rounded px-2 py-1.5 text-sm"
          type="number"
          value={configForm.ptnr_threshold ?? currentConfig?.ptnr_threshold ?? 4}
          onChange={(e) => setConfigForm((f) => ({ ...f, ptnr_threshold: Number(e.target.value) }))}
        />
      </div>
      <div className="text-xs font-semibold text-gray-700 pt-2">{t("incidents.nis2_classification.config.recurrence_title")}</div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div className="space-y-1">
          <label className="text-xs font-medium text-gray-600">{t("incidents.nis2_classification.config.recurrence_window")}</label>
          <input
            className="w-full border rounded px-2 py-1.5 text-sm"
            type="number"
            value={configForm.recurrence_window_days ?? currentConfig?.recurrence_window_days ?? 90}
            onChange={(e) => setConfigForm((f) => ({ ...f, recurrence_window_days: Number(e.target.value) }))}
          />
        </div>
        <div className="space-y-1">
          <label className="text-xs font-medium text-gray-600">{t("incidents.nis2_classification.config.recurrence_bonus")}</label>
          <input
            className="w-full border rounded px-2 py-1.5 text-sm"
            type="number"
            value={configForm.recurrence_score_bonus ?? currentConfig?.recurrence_score_bonus ?? 2}
            onChange={(e) => setConfigForm((f) => ({ ...f, recurrence_score_bonus: Number(e.target.value) }))}
          />
        </div>
      </div>
      <p className="text-xs text-gray-500">{t("incidents.nis2_classification.config.recurrence_note")}</p>
      <button
        type="button"
        onClick={() => configMutation.mutate()}
        className="px-3 py-2 text-xs bg-primary-600 text-white rounded"
      >
        {t("incidents.nis2_config_save")}
      </button>
      <div className="text-xs text-gray-600 border rounded p-2 bg-gray-50">
        {t("incidents.config_extra.csirt_label")}: <strong>{CSIRT_BY_COUNTRY[plantCountry]?.name ?? t("incidents.config_extra.csirt_fallback")}</strong>
        <br />
        {t("incidents.config_extra.portal_label")}: {CSIRT_BY_COUNTRY[plantCountry]?.portal ?? "—"}
      </div>
    </div>
  );
}
