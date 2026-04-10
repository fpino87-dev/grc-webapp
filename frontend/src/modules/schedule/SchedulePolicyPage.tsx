import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { scheduleApi, SchedulePolicy, ScheduleRule } from "../../api/endpoints/schedule";
import { plantsApi } from "../../api/endpoints/plants";

const CATEGORIES: Record<string, string[]> = {
  "Controlli":  ["control_review", "control_audit"],
  "Documenti":  ["document_policy", "document_procedure", "document_record"],
  "Rischi":     ["risk_assessment", "risk_treatment"],
  "BCP":        ["bcp_test", "bcp_review"],
  "Incidenti":  ["incident_review"],
  "Fornitori":  ["supplier_assessment", "supplier_contract_review"],
  "Formazione": ["training_mandatory", "training_refresh"],
  "Governance": ["management_review", "security_committee"],
  "Audit":      ["finding_minor", "finding_major", "finding_observation"],
  "PDCA":       ["pdca_cycle"],
  "Reporting":  ["kpi_review", "isms_review"],
};

function RuleRow({
  rule,
  policyId,
  onUpdated,
}: {
  rule: ScheduleRule;
  policyId: string;
  onUpdated: () => void;
}) {
  const { t } = useTranslation();
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState({
    frequency_value: rule.frequency_value,
    frequency_unit: rule.frequency_unit,
    alert_days_before: rule.alert_days_before,
    enabled: rule.enabled,
  });

  const mutation = useMutation({
    mutationFn: () => scheduleApi.updateRule(policyId, { rule_type: rule.rule_type, ...form }),
    onSuccess: () => { setEditing(false); onUpdated(); },
  });

  if (!editing) {
    return (
      <tr className="hover:bg-gray-50">
        <td className="px-4 py-2 text-sm text-gray-900">{rule.rule_type_label}</td>
        <td className="px-4 py-2 text-sm text-gray-700">
          {rule.frequency_value} {t(`schedule.units.${rule.frequency_unit}`, rule.frequency_unit)}
        </td>
        <td className="px-4 py-2 text-sm text-gray-700">{rule.alert_days_before} {t("schedule.policy.days_before")}</td>
        <td className="px-4 py-2">
          <span className={`inline-block w-2 h-2 rounded-full ${rule.enabled ? "bg-green-500" : "bg-gray-400"}`} />
        </td>
        <td className="px-4 py-2">
          <button
            onClick={() => setEditing(true)}
            className="text-xs text-blue-600 hover:underline"
          >
            {t("actions.edit")}
          </button>
        </td>
      </tr>
    );
  }

  return (
    <tr className="bg-blue-50">
      <td className="px-4 py-2 text-sm font-medium text-gray-900">{rule.rule_type_label}</td>
      <td className="px-4 py-2">
        <div className="flex items-center gap-1">
          <input
            type="number"
            min={1}
            value={form.frequency_value}
            onChange={e => setForm(f => ({ ...f, frequency_value: parseInt(e.target.value) || 1 }))}
            className="border rounded px-2 py-1 text-sm w-16"
          />
          <select
            value={form.frequency_unit}
            onChange={e => setForm(f => ({ ...f, frequency_unit: e.target.value as ScheduleRule["frequency_unit"] }))}
            className="border rounded px-2 py-1 text-sm"
          >
            {(["days", "weeks", "months", "years"] as const).map(v => (
              <option key={v} value={v}>{t(`schedule.units.${v}`)}</option>
            ))}
          </select>
        </div>
      </td>
      <td className="px-4 py-2">
        <div className="flex items-center gap-1">
          <input
            type="number"
            min={0}
            value={form.alert_days_before}
            onChange={e => setForm(f => ({ ...f, alert_days_before: parseInt(e.target.value) || 0 }))}
            className="border rounded px-2 py-1 text-sm w-16"
          />
          <span className="text-xs text-gray-500">{t("schedule.policy.days_before")}</span>
        </div>
      </td>
      <td className="px-4 py-2">
        <input
          type="checkbox"
          checked={form.enabled}
          onChange={e => setForm(f => ({ ...f, enabled: e.target.checked }))}
        />
      </td>
      <td className="px-4 py-2">
        <div className="flex gap-2">
          <button
            onClick={() => mutation.mutate()}
            disabled={mutation.isPending}
            className="text-xs bg-blue-600 text-white px-2 py-1 rounded hover:bg-blue-700 disabled:opacity-50"
          >
            {t("actions.save")}
          </button>
          <button
            onClick={() => { setEditing(false); setForm({ frequency_value: rule.frequency_value, frequency_unit: rule.frequency_unit, alert_days_before: rule.alert_days_before, enabled: rule.enabled }); }}
            className="text-xs text-gray-500 hover:text-gray-700"
          >
            {t("actions.cancel")}
          </button>
        </div>
      </td>
    </tr>
  );
}

function PolicyDetail({ policy, onUpdated }: { policy: SchedulePolicy; onUpdated: () => void }) {
  const { t } = useTranslation();
  // Group rules by category
  const rulesByType = Object.fromEntries(policy.rules.map(r => [r.rule_type, r]));

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="font-semibold text-gray-900">{policy.name}</h3>
          <p className="text-xs text-gray-500">
            {policy.plant_name ?? t("schedule.policy.global")} · {policy.valid_from} ·{" "}
            {policy.is_active ? <span className="text-green-600 font-medium">{t("status.attivo")}</span> : <span className="text-gray-400">{t("status.chiuso")}</span>}
          </p>
        </div>
      </div>

      {Object.entries(CATEGORIES).map(([cat, ruleTypes]) => {
        const catRules = ruleTypes.map(rt => rulesByType[rt]).filter(Boolean);
        if (catRules.length === 0) return null;
        return (
          <div key={cat} className="mb-6">
            <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2 px-4">{t(`schedule.categories.${cat}`, cat)}</h4>
            <table className="w-full text-left">
              <thead>
                <tr className="bg-gray-50 border-y border-gray-200">
                  <th className="px-4 py-2 text-xs font-semibold text-gray-500 uppercase tracking-wide">{t("schedule.policy.col_rule")}</th>
                  <th className="px-4 py-2 text-xs font-semibold text-gray-500 uppercase tracking-wide">{t("schedule.policy.col_frequency")}</th>
                  <th className="px-4 py-2 text-xs font-semibold text-gray-500 uppercase tracking-wide">{t("schedule.policy.col_alert")}</th>
                  <th className="px-4 py-2 text-xs font-semibold text-gray-500 uppercase tracking-wide">{t("schedule.policy.col_active")}</th>
                  <th className="px-4 py-2" />
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {catRules.map(rule => (
                  <RuleRow key={rule.rule_type} rule={rule} policyId={policy.id} onUpdated={onUpdated} />
                ))}
              </tbody>
            </table>
          </div>
        );
      })}
    </div>
  );
}

export function SchedulePolicyPage() {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [plantId, setPlantId] = useState<string>("");
  const [selectedPolicyId, setSelectedPolicyId] = useState<string>("");
  const [showCreate, setShowCreate] = useState(false);
  const [newPolicyName, setNewPolicyName] = useState("");

  const { data: plants } = useQuery({
    queryKey: ["plants"],
    queryFn: () => plantsApi.list(),
    retry: false,
  });

  const { data, isLoading, refetch } = useQuery({
    queryKey: ["schedule-policies", plantId],
    queryFn: () => scheduleApi.listPolicies(plantId || undefined),
    retry: false,
  });

  const policies = data?.results ?? [];
  const selectedPolicy = policies.find(p => p.id === selectedPolicyId) ?? policies[0];

  const createMutation = useMutation({
    mutationFn: () => scheduleApi.createDefaultPolicy({
      plant_id: plantId || undefined,
      name: newPolicyName,
    }),
    onSuccess: (p) => {
      qc.invalidateQueries({ queryKey: ["schedule-policies"] });
      setSelectedPolicyId(p.id);
      setShowCreate(false);
      setNewPolicyName("");
    },
  });

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-semibold text-gray-900">{t("schedule.policy.title")}</h2>
        <button
          onClick={() => setShowCreate(true)}
          className="bg-blue-600 text-white text-sm px-3 py-1.5 rounded hover:bg-blue-700"
        >
          {t("schedule.policy.new_policy")}
        </button>
      </div>

      {/* Create form */}
      {showCreate && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
          <h3 className="font-medium text-blue-800 mb-3">{t("schedule.policy.create_title")}</h3>
          <div className="flex gap-3 items-end">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">{t("schedule.policy.site_optional")}</label>
              <select
                value={plantId}
                onChange={e => setPlantId(e.target.value)}
                className="border border-gray-300 rounded px-2 py-1.5 text-sm"
              >
                <option value="">{t("schedule.policy.global")}</option>
                {plants?.map(p => (
                  <option key={p.id} value={p.id}>[{p.code}] {p.name}</option>
                ))}
              </select>
            </div>
            <div className="flex-1">
              <label className="block text-xs font-medium text-gray-600 mb-1">{t("schedule.policy.policy_name")}</label>
              <input
                value={newPolicyName}
                onChange={e => setNewPolicyName(e.target.value)}
                className="border border-gray-300 rounded px-2 py-1.5 text-sm w-full"
              />
            </div>
            <button
              onClick={() => createMutation.mutate()}
              disabled={createMutation.isPending}
              className="bg-blue-600 text-white text-sm px-3 py-1.5 rounded hover:bg-blue-700 disabled:opacity-50"
            >
              {t("schedule.policy.create_btn")}
            </button>
            <button onClick={() => setShowCreate(false)} className="text-sm text-gray-500 hover:text-gray-700">
              {t("actions.cancel")}
            </button>
          </div>
          {createMutation.isError && (
            <p className="text-red-600 text-xs mt-2">{t("schedule.policy.create_error")}</p>
          )}
        </div>
      )}

      {/* Filters */}
      <div className="bg-white border border-gray-200 rounded-lg p-4 mb-6">
        <div className="flex gap-4 items-end">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">{t("schedule.policy.site_label")}</label>
            <select
              value={plantId}
              onChange={e => setPlantId(e.target.value)}
              className="border border-gray-300 rounded px-2 py-1.5 text-sm"
            >
              <option value="">{t("schedule.policy.all")}</option>
              {plants?.map(p => (
                <option key={p.id} value={p.id}>[{p.code}] {p.name}</option>
              ))}
            </select>
          </div>
          {policies.length > 1 && (
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">{t("schedule.policy.policy_label")}</label>
              <select
                value={selectedPolicy?.id ?? ""}
                onChange={e => setSelectedPolicyId(e.target.value)}
                className="border border-gray-300 rounded px-2 py-1.5 text-sm"
              >
                {policies.map(p => (
                  <option key={p.id} value={p.id}>
                    {p.name} {p.is_active ? t("schedule.policy.active_suffix") : ""}
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>
      </div>

      {/* Policy detail */}
      {isLoading ? (
        <div className="p-8 text-center text-gray-400 text-sm">{t("notification_settings.loading")}</div>
      ) : !selectedPolicy ? (
        <div className="p-8 text-center text-gray-400 text-sm italic">
          {t("schedule.policy.no_policy")}
        </div>
      ) : (
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <PolicyDetail policy={selectedPolicy} onUpdated={refetch} />
        </div>
      )}
    </div>
  );
}
