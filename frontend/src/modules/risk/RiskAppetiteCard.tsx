import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "../../api/client";
import { riskApi, type AppetitePolicyFull } from "../../api/endpoints/risk";
import { usersApi } from "../../api/endpoints/users";
import { useTranslation } from "react-i18next";
import { addYearsISO, usePlantToday } from "../../utils/dates";

function expiryBadge(valid_until: string | null, today: string, t: (k: string) => string, lang: string) {
  if (!valid_until) return null;
  const diffDays = Math.floor((new Date(valid_until).getTime() - new Date(today).getTime()) / 86400000);
  if (diffDays < 0)
    return <span className="px-2 py-0.5 rounded-full text-xs font-semibold bg-red-100 text-red-700">⚠ {t("risk.appetite_expired")}</span>;
  if (diffDays <= 30)
    return <span className="px-2 py-0.5 rounded-full text-xs font-semibold bg-amber-100 text-amber-700">⚠ {t("risk.appetite_expiry_warning")}</span>;
  return <span className="text-sm font-medium text-gray-800">{new Date(valid_until + "T12:00:00").toLocaleDateString(lang)}</span>;
}

export function RiskAppetiteCard({ plantId }: { plantId?: string }) {
  const { t, i18n } = useTranslation();
  const qc = useQueryClient();
  const [editing, setEditing] = useState(false);
  const today = usePlantToday();
  const defaultUntil = addYearsISO(today, 1);

  const emptyForm = {
    max_acceptable_score: 14,
    max_red_risks_count: 3,
    valid_from: today,
    valid_until: defaultUntil as string | null,
    approved_by: null as number | null,
    approved_at: today as string | null,
    notes: "",
  };
  const [form, setForm] = useState(emptyForm);
  const [saveError, setSaveError] = useState("");

  const { data: policy, isLoading, isError } = useQuery({
    queryKey: ["risk-appetite", plantId],
    queryFn: () => {
      const params = new URLSearchParams();
      if (plantId) params.set("plant", plantId);
      return apiClient.get<AppetitePolicyFull>(
        `/risk/appetite-policies/active/?${params.toString()}`
      ).then(r => r.data);
    },
    retry: false,
  });

  const { data: users } = useQuery({
    queryKey: ["users-list"],
    queryFn: () => usersApi.list(),
    enabled: editing,
  });

  const saveMutation = useMutation({
    mutationFn: (data: typeof form) => {
      const payload = { ...data, plant: plantId ?? null };
      return policy
        ? riskApi.updateAppetite(policy.id, payload)
        : riskApi.createAppetite(payload);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["risk-appetite"] });
      setEditing(false);
      setSaveError("");
    },
    onError: () => setSaveError(t("risk.error_generic")),
  });

  function openEdit() {
    if (policy) {
      setForm({
        max_acceptable_score: policy.max_acceptable_score,
        max_red_risks_count: policy.max_red_risks_count,
        valid_from: policy.valid_from ?? today,
        valid_until: policy.valid_until ?? defaultUntil,
        approved_by: typeof policy.approved_by === "number" ? policy.approved_by : null,
        approved_at: policy.approved_at ? policy.approved_at.slice(0, 10) : today,
        notes: policy.notes ?? "",
      });
    } else {
      setForm(emptyForm);
    }
    setEditing(true);
  }

  if (isLoading) return null;

  const lang = i18n.language || "it";

  return (
    <div className="mb-4">
      <div className={`bg-blue-50 border rounded-lg px-4 py-3 flex flex-wrap gap-x-6 gap-y-2 items-center text-sm ${isError || !policy ? "border-amber-300 bg-amber-50" : "border-blue-200"}`}>
        <div className="flex items-center gap-2">
          <span className="text-xs text-blue-500 font-medium uppercase">Risk Appetite Policy</span>
          {policy?.framework_code && <span className="text-xs text-blue-400">{policy.framework_code}</span>}
          {(isError || !policy) && (
            <span className="text-xs text-amber-600 font-medium">{t("risk.appetite_missing")}</span>
          )}
        </div>

        {policy && (
          <>
            <div className="text-gray-700">
              {t("risk.appetite_max_score")} <strong className="text-orange-600">{policy.max_acceptable_score}</strong>
            </div>
            <div className="text-gray-700">
              {t("risk.appetite_max_red")} <strong className="text-red-600">{policy.max_red_risks_count}</strong>
            </div>
            <div className="flex items-center gap-2 text-gray-700">
              <span>{t("risk.appetite_valid_until")}</span>
              {expiryBadge(policy.valid_until, today, t, lang) ?? <span className="text-gray-400">—</span>}
            </div>
            {policy.approved_by_name && (
              <div className="text-gray-500 text-xs">
                {t("risk.appetite_approved_by")} <strong>{policy.approved_by_name}</strong>
                {policy.approved_at && (
                  <span className="ml-1 text-gray-400">
                    ({new Date(policy.approved_at).toLocaleDateString(lang)})
                  </span>
                )}
              </div>
            )}
          </>
        )}

        <button
          onClick={openEdit}
          className="ml-auto text-xs px-3 py-1.5 border border-blue-300 text-blue-700 rounded hover:bg-blue-100"
        >
          {policy ? t("actions.edit") : t("risk.appetite_create_btn")}
        </button>
      </div>

      {editing && (
        <div className="mt-2 border border-blue-200 rounded-lg bg-white p-4 shadow-sm">
          <h4 className="text-sm font-semibold text-gray-800 mb-3">Risk Appetite Policy</h4>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-gray-500 mb-1">{t("risk.appetite_max_score")}</label>
              <input type="number" min={1} max={25} value={form.max_acceptable_score}
                onChange={e => setForm(f => ({ ...f, max_acceptable_score: +e.target.value }))}
                className="w-full border rounded px-3 py-1.5 text-sm" />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">{t("risk.appetite_max_red")}</label>
              <input type="number" min={0} max={50} value={form.max_red_risks_count}
                onChange={e => setForm(f => ({ ...f, max_red_risks_count: +e.target.value }))}
                className="w-full border rounded px-3 py-1.5 text-sm" />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">{t("risk.appetite_valid_from")}</label>
              <input type="date" value={form.valid_from}
                onChange={e => setForm(f => ({ ...f, valid_from: e.target.value }))}
                className="w-full border rounded px-3 py-1.5 text-sm" />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">{t("risk.appetite_valid_until")}</label>
              <input type="date" value={form.valid_until ?? ""}
                onChange={e => setForm(f => ({ ...f, valid_until: e.target.value || null }))}
                className="w-full border rounded px-3 py-1.5 text-sm" />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">{t("risk.appetite_approved_by")}</label>
              <select value={form.approved_by ?? ""}
                onChange={e => setForm(f => ({ ...f, approved_by: e.target.value ? +e.target.value : null }))}
                className="w-full border rounded px-3 py-1.5 text-sm">
                <option value="">—</option>
                {users?.map(u => (
                  <option key={u.id} value={u.id}>
                    {u.first_name || u.last_name ? `${u.first_name} ${u.last_name}`.trim() : u.email}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">{t("risk.appetite_approved_at")}</label>
              <input type="date" value={form.approved_at ?? ""}
                onChange={e => setForm(f => ({ ...f, approved_at: e.target.value || null }))}
                className="w-full border rounded px-3 py-1.5 text-sm" />
            </div>
            <div className="col-span-2">
              <label className="block text-xs text-gray-500 mb-1">{t("risk.appetite_notes")}</label>
              <textarea value={form.notes} rows={2}
                onChange={e => setForm(f => ({ ...f, notes: e.target.value }))}
                placeholder={t("risk.appetite_notes_placeholder")}
                className="w-full border rounded px-3 py-1.5 text-sm" />
            </div>
          </div>
          {saveError && <p className="text-red-600 text-xs mt-2">{saveError}</p>}
          <div className="flex justify-end gap-2 mt-3">
            <button onClick={() => setEditing(false)}
              className="px-3 py-1.5 text-sm border rounded text-gray-600 hover:bg-gray-50">
              {t("actions.cancel")}
            </button>
            <button onClick={() => saveMutation.mutate(form)}
              disabled={saveMutation.isPending}
              className="px-4 py-1.5 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50">
              {saveMutation.isPending ? t("common.loading") : t("actions.save")}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
