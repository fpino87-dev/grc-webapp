import { useEffect, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  checklistsApi,
  CHECKLIST_FREQUENCIES,
  MONTH_BASED_FREQUENCIES,
  type ChecklistFrequency,
  type ChecklistTemplateItem,
} from "../../api/endpoints/checklists";
import { plantsApi } from "../../api/endpoints/plants";

interface FormState {
  name: string;
  description: string;
  frequency: ChecklistFrequency;
  days_of_week: number[];
  day_of_month: number;
  start_month: number;
  plant: string;
  is_active: boolean;
  items: ChecklistTemplateItem[];
}

const EMPTY: FormState = {
  name: "",
  description: "",
  frequency: "daily",
  days_of_week: [],
  day_of_month: 1,
  start_month: 1,
  plant: "",
  is_active: true,
  items: [{ order: 0, text: "", is_mandatory: true }],
};

// 0=lunedì … 6=domenica (allineato a date.weekday() del backend).
const WEEKDAY_KEYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"] as const;

export function ChecklistTemplateForm() {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const { id } = useParams();
  const isEdit = Boolean(id);
  const [form, setForm] = useState<FormState>(EMPTY);

  const { data: plants } = useQuery({
    queryKey: ["plants"],
    queryFn: () => plantsApi.list(),
    retry: false,
  });

  const { data: existing } = useQuery({
    queryKey: ["checklist-template", id],
    queryFn: () => checklistsApi.getTemplate(id!),
    enabled: isEdit,
    retry: false,
  });

  useEffect(() => {
    if (existing) {
      setForm({
        name: existing.name,
        description: existing.description ?? "",
        frequency: existing.frequency,
        days_of_week: existing.days_of_week ?? [],
        day_of_month: existing.day_of_month ?? 1,
        start_month: existing.start_month ?? 1,
        plant: existing.plant ?? "",
        is_active: existing.is_active,
        items:
          existing.items.length > 0
            ? existing.items.map((it, i) => ({ ...it, order: i }))
            : [{ order: 0, text: "", is_mandatory: true }],
      });
    }
  }, [existing]);

  const mutation = useMutation({
    mutationFn: () => {
      const payload = {
        name: form.name,
        description: form.description,
        frequency: form.frequency,
        // I giorni valgono per giornaliera (più giorni) e settimanale (uno
        // solo); il giorno del mese solo per la mensile.
        days_of_week:
          form.frequency === "daily"
            ? form.days_of_week
            : form.frequency === "weekly"
              ? form.days_of_week.slice(0, 1)
              : [],
        day_of_month: isMonthBased ? form.day_of_month : 1,
        start_month: isMonthBased ? form.start_month : 1,
        plant: form.plant || null,
        is_active: form.is_active,
        // Si rimanda l'item completo (id compreso, quando esiste): il backend
        // aggiorna in place gli item già usati dai run e conserva tipo, unità
        // e soglie numeriche non modificabili da questo form.
        items: form.items
          .filter((it) => it.text.trim())
          .map((it, i) => ({ ...it, order: i, text: it.text.trim() })),
      };
      return isEdit
        ? checklistsApi.updateTemplate(id!, payload)
        : checklistsApi.createTemplate(payload);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["checklist-templates"] });
      navigate("/checklists/templates");
    },
  });

  function updateItem(idx: number, patch: Partial<ChecklistTemplateItem>) {
    setForm((prev) => ({
      ...prev,
      items: prev.items.map((it, i) => (i === idx ? { ...it, ...patch } : it)),
    }));
  }

  function addItem() {
    setForm((prev) => ({
      ...prev,
      items: [...prev.items, { order: prev.items.length, text: "", is_mandatory: true }],
    }));
  }

  function removeItem(idx: number) {
    setForm((prev) => ({ ...prev, items: prev.items.filter((_, i) => i !== idx) }));
  }

  function moveItem(idx: number, dir: -1 | 1) {
    setForm((prev) => {
      const next = [...prev.items];
      const target = idx + dir;
      if (target < 0 || target >= next.length) return prev;
      [next[idx], next[target]] = [next[target], next[idx]];
      return { ...prev, items: next };
    });
  }

  function toggleDay(day: number) {
    setForm((prev) => {
      // Settimanale: un solo giorno di generazione, il click sostituisce.
      if (prev.frequency === "weekly") return { ...prev, days_of_week: [day] };
      return {
        ...prev,
        days_of_week: prev.days_of_week.includes(day)
          ? prev.days_of_week.filter((d) => d !== day)
          : [...prev.days_of_week, day].sort((a, b) => a - b),
      };
    });
  }

  const isMonthBased = MONTH_BASED_FREQUENCIES.includes(form.frequency);
  // Nomi dei mesi nella lingua attiva: evita 12 stringhe tradotte a mano.
  const monthName = (m: number) =>
    new Date(2026, m - 1, 1).toLocaleDateString(i18n.language, { month: "long" });

  const canSave = form.name.trim() && form.items.some((it) => it.text.trim());

  return (
    <div className="max-w-2xl">
      <button
        onClick={() => navigate("/checklists/templates")}
        className="text-sm text-gray-500 hover:text-gray-700 mb-3"
      >
        ← {t("checklists.templates.back")}
      </button>
      <h2 className="text-xl font-semibold text-gray-900 mb-4">
        {isEdit ? t("checklists.templates.edit") : t("checklists.templates.new")}
      </h2>

      <div className="bg-white rounded-lg border border-gray-200 p-6 space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">{t("checklists.templates.name")}</label>
          <input
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            className="w-full border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-400"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">{t("checklists.templates.description")}</label>
          <textarea
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
            rows={2}
            className="w-full border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-400"
          />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("checklists.templates.frequency")}</label>
            <select
              value={form.frequency}
              onChange={(e) => setForm({ ...form, frequency: e.target.value as ChecklistFrequency })}
              className="w-full border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-400"
            >
              {CHECKLIST_FREQUENCIES.map((f) => (
                <option key={f} value={f}>{t(`checklists.frequency.${f}`)}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("checklists.templates.plant")}</label>
            <select
              value={form.plant}
              onChange={(e) => setForm({ ...form, plant: e.target.value })}
              className="w-full border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-400"
            >
              <option value="">{t("checklists.templates.all_plants")}</option>
              {(plants ?? []).map((p) => (
                <option key={p.id} value={p.id}>{p.code} — {p.name}</option>
              ))}
            </select>
          </div>
        </div>

        {(form.frequency === "daily" || form.frequency === "weekly") && (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {form.frequency === "weekly"
                ? t("checklists.templates.day_of_week")
                : t("checklists.templates.days_of_week")}
            </label>
            <div className="flex flex-wrap gap-1.5">
              {WEEKDAY_KEYS.map((key, day) => {
                const selected =
                  form.frequency === "weekly"
                    ? (form.days_of_week[0] ?? 0) === day
                    : form.days_of_week.includes(day);
                return (
                  <button
                    key={key}
                    type="button"
                    onClick={() => toggleDay(day)}
                    aria-pressed={selected}
                    className={
                      "px-2.5 py-1 text-sm rounded border " +
                      (selected
                        ? "bg-primary-600 text-white border-primary-600"
                        : "bg-white text-gray-600 border-gray-300 hover:bg-gray-50")
                    }
                  >
                    {t(`checklists.weekdays.${key}`)}
                  </button>
                );
              })}
            </div>
            <p className="text-xs text-gray-500 mt-1">
              {form.frequency === "weekly"
                ? t("checklists.templates.day_of_week_hint")
                : t("checklists.templates.days_of_week_hint")}
            </p>
          </div>
        )}

        {isMonthBased && (
          <div className="grid grid-cols-2 gap-3">
            {form.frequency !== "monthly" && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  {t("checklists.templates.start_month")}
                </label>
                <select
                  value={form.start_month}
                  onChange={(e) => setForm({ ...form, start_month: Number(e.target.value) })}
                  className="w-full border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-400"
                >
                  {Array.from({ length: 12 }, (_, i) => i + 1).map((m) => (
                    <option key={m} value={m} className="capitalize">{monthName(m)}</option>
                  ))}
                </select>
                <p className="text-xs text-gray-500 mt-1">
                  {t("checklists.templates.start_month_hint")}
                </p>
              </div>
            )}
            <div className={form.frequency === "monthly" ? "col-span-2" : ""}>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {form.frequency === "monthly"
                ? t("checklists.templates.day_of_month")
                : t("checklists.templates.day_of_period")}
            </label>
            <select
              value={form.day_of_month}
              onChange={(e) => setForm({ ...form, day_of_month: Number(e.target.value) })}
              className="w-full border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-400"
            >
              {Array.from({ length: 28 }, (_, i) => i + 1).map((d) => (
                <option key={d} value={d}>
                  {t("checklists.templates.day_of_month_option", { day: d })}
                </option>
              ))}
              <option value={0}>{t("checklists.templates.day_of_month_last")}</option>
            </select>
            <p className="text-xs text-gray-500 mt-1">
              {form.frequency === "monthly"
                ? t("checklists.templates.day_of_month_hint")
                : t("checklists.templates.day_of_period_hint")}
            </p>
            </div>
          </div>
        )}

        {form.frequency === "ad_hoc" && (
          <p className="text-xs text-gray-600 bg-gray-50 border border-gray-200 rounded px-3 py-2">
            {t("checklists.templates.ad_hoc_hint")}
          </p>
        )}

        <label className="flex items-center gap-2 text-sm text-gray-700">
          <input
            type="checkbox"
            checked={form.is_active}
            onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
            className="rounded border-gray-300 text-primary-600 focus:ring-primary-400"
          />
          {t("checklists.templates.active")}
        </label>

        {/* Items dinamici */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <label className="block text-sm font-medium text-gray-700">{t("checklists.templates.items")}</label>
            <button
              onClick={addItem}
              className="text-xs text-primary-700 hover:text-primary-900 border border-primary-300 rounded px-2 py-1 hover:bg-primary-50"
            >
              + {t("checklists.templates.add_item")}
            </button>
          </div>
          <div className="space-y-2">
            {form.items.map((item, idx) => (
              <div key={idx} className="flex items-center gap-2">
                <div className="flex flex-col">
                  <button
                    onClick={() => moveItem(idx, -1)}
                    disabled={idx === 0}
                    className="text-gray-400 hover:text-gray-700 disabled:opacity-30 leading-none text-xs"
                    title="↑"
                  >
                    ▴
                  </button>
                  <button
                    onClick={() => moveItem(idx, 1)}
                    disabled={idx === form.items.length - 1}
                    className="text-gray-400 hover:text-gray-700 disabled:opacity-30 leading-none text-xs"
                    title="↓"
                  >
                    ▾
                  </button>
                </div>
                <input
                  value={item.text}
                  onChange={(e) => updateItem(idx, { text: e.target.value })}
                  placeholder={t("checklists.templates.item_placeholder")}
                  className="flex-1 border rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary-400"
                />
                <label className="flex items-center gap-1 text-xs text-gray-600 whitespace-nowrap">
                  <input
                    type="checkbox"
                    checked={item.is_mandatory}
                    onChange={(e) => updateItem(idx, { is_mandatory: e.target.checked })}
                    className="rounded border-gray-300 text-primary-600 focus:ring-primary-400"
                  />
                  {t("checklists.templates.mandatory")}
                </label>
                <button
                  onClick={() => removeItem(idx)}
                  disabled={form.items.length === 1}
                  className="text-gray-400 hover:text-red-600 disabled:opacity-30"
                  title={t("actions.delete")}
                >
                  ✕
                </button>
              </div>
            ))}
          </div>
        </div>

        {mutation.isError && (
          <p className="text-sm text-red-600">{t("common.save_error")}</p>
        )}

        <div className="flex justify-end gap-2 pt-2">
          <button
            onClick={() => navigate("/checklists/templates")}
            className="px-4 py-2 border rounded text-sm text-gray-600 hover:bg-gray-50"
          >
            {t("actions.cancel")}
          </button>
          <button
            onClick={() => mutation.mutate()}
            disabled={!canSave || mutation.isPending}
            className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700 disabled:opacity-50"
          >
            {mutation.isPending ? t("common.saving") : t("actions.save")}
          </button>
        </div>
      </div>
    </div>
  );
}
