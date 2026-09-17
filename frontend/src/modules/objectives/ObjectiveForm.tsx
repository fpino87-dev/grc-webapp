import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { securityObjectivesApi, type SecurityObjective } from "../../api/endpoints/securityObjectives";
import { kpiApi } from "../../api/endpoints/kpi";
import { plantsApi } from "../../api/endpoints/plants";

const ROLES = ["compliance_officer", "risk_manager", "plant_manager", "control_owner", "internal_auditor"];
const ORIGINS = ["politica", "risk_assessment", "audit", "requisito", "incidente", "riesame", "altro"];

interface Props {
  objective?: SecurityObjective;
  onClose: () => void;
}

export function ObjectiveForm({ objective, onClose }: Props) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [error, setError] = useState<string>("");
  const [form, setForm] = useState({
    code: objective?.code ?? "",
    title: objective?.title ?? "",
    description: objective?.description ?? "",
    origin: objective?.origin ?? "politica",
    plant: objective?.plant ?? "",
    measure_source: objective?.measure_source ?? "kpi",
    kpi_definition: objective?.kpi_definition ?? "",
    unit: objective?.unit ?? "",
    start_date: objective?.start_date ?? new Date().toISOString().slice(0, 10),
    baseline_value: objective?.baseline_value?.toString() ?? "",
    target_value: objective?.target_value?.toString() ?? "",
    target_direction: objective?.target_direction ?? "above",
    target_date: objective?.target_date ?? "",
    owner_role: objective?.owner_role ?? "",
    resources: objective?.resources ?? "",
    evaluation_method: objective?.evaluation_method ?? "",
  });

  const { data: plants = [] } = useQuery({ queryKey: ["plants"], queryFn: plantsApi.list });
  const { data: kpis } = useQuery({
    queryKey: ["kpi-definitions", form.plant],
    queryFn: () => kpiApi.getKpiDefinitions(form.plant ? { plant: form.plant } : undefined),
    enabled: form.measure_source === "kpi",
  });

  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));

  const save = useMutation({
    mutationFn: () => {
      const payload: Record<string, unknown> = {
        ...form,
        plant: form.plant || null,
        kpi_definition: form.measure_source === "kpi" ? form.kpi_definition || null : null,
        baseline_value: form.baseline_value === "" ? null : Number(form.baseline_value),
        target_value: Number(form.target_value),
      };
      return objective
        ? securityObjectivesApi.update(objective.id, payload)
        : securityObjectivesApi.create(payload);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["security-objectives"] });
      onClose();
    },
    onError: (e: { response?: { data?: Record<string, string[] | string> } }) => {
      const data = e.response?.data ?? {};
      const first = Object.entries(data)[0];
      setError(first ? `${first[0]}: ${[first[1]].flat().join(" ")}` : t("common.error"));
    },
  });

  const field = "w-full border border-gray-300 rounded px-2 py-1.5 text-sm";
  const label = "block text-xs font-medium text-gray-600 mb-1";

  return (
    <div className="fixed inset-0 bg-black/40 flex items-start justify-center z-50 overflow-y-auto py-8">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-3xl p-6 mx-4">
        <h3 className="text-lg font-semibold mb-1">
          {objective ? t("objectives.form.edit_title") : t("objectives.form.new_title")}
        </h3>
        <p className="text-xs text-gray-500 mb-4">{t("objectives.form.intro")}</p>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className={label}>{t("objectives.fields.code")}</label>
            <input className={field} value={form.code} onChange={(e) => set("code", e.target.value)}
                   placeholder="OBJ-2026-01" />
          </div>
          <div>
            <label className={label}>{t("objectives.fields.plant")}</label>
            <select className={field} value={form.plant} onChange={(e) => set("plant", e.target.value)}>
              <option value="">{t("objectives.fields.plant_org")}</option>
              {plants.map((p) => <option key={p.id} value={p.id}>{p.code} — {p.name}</option>)}
            </select>
          </div>
          <div className="col-span-2">
            <label className={label}>{t("objectives.fields.title")}</label>
            <input className={field} value={form.title} onChange={(e) => set("title", e.target.value)} />
          </div>
          <div className="col-span-2">
            <label className={label}>{t("objectives.fields.description")}</label>
            <textarea className={field} rows={2} value={form.description}
                      onChange={(e) => set("description", e.target.value)} />
          </div>
          <div>
            <label className={label}>{t("objectives.fields.origin")}</label>
            <select className={field} value={form.origin} onChange={(e) => set("origin", e.target.value)}>
              {ORIGINS.map((o) => <option key={o} value={o}>{t(`objectives.origin.${o}`)}</option>)}
            </select>
          </div>
          <div>
            <label className={label}>{t("objectives.fields.owner_role")}</label>
            <select className={field} value={form.owner_role} onChange={(e) => set("owner_role", e.target.value)}>
              <option value="">—</option>
              {ROLES.map((r) => <option key={r} value={r}>{t(`governance.roles.${r}`)}</option>)}
            </select>
          </div>

          <div className="col-span-2 border-t pt-4">
            <label className={label}>{t("objectives.fields.measure_source")}</label>
            <div className="flex gap-4 text-sm">
              {(["kpi", "manual"] as const).map((src) => (
                <label key={src} className="flex items-center gap-1.5">
                  <input type="radio" checked={form.measure_source === src}
                         onChange={() => set("measure_source", src)} />
                  {t(`objectives.measure_source.${src}`)}
                </label>
              ))}
            </div>
            <p className="text-[11px] text-gray-500 mt-1">{t("objectives.form.measure_hint")}</p>
          </div>

          {form.measure_source === "kpi" ? (
            <div className="col-span-2">
              <label className={label}>{t("objectives.fields.kpi")}</label>
              <select className={field} value={form.kpi_definition}
                      onChange={(e) => set("kpi_definition", e.target.value)}>
                <option value="">—</option>
                {(kpis?.results ?? []).map((k) => (
                  <option key={k.id} value={k.id}>{k.kpi_code} — {k.name}</option>
                ))}
              </select>
            </div>
          ) : (
            <div>
              <label className={label}>{t("objectives.fields.unit")}</label>
              <input className={field} value={form.unit} onChange={(e) => set("unit", e.target.value)}
                     placeholder="%" />
            </div>
          )}

          <div>
            <label className={label}>{t("objectives.fields.start_date")}</label>
            <input type="date" className={field} value={form.start_date}
                   onChange={(e) => set("start_date", e.target.value)} />
          </div>
          <div>
            <label className={label}>{t("objectives.fields.baseline_value")}</label>
            <input type="number" step="any" className={field} value={form.baseline_value}
                   onChange={(e) => set("baseline_value", e.target.value)} />
          </div>
          <div>
            <label className={label}>{t("objectives.fields.target_value")}</label>
            <input type="number" step="any" className={field} value={form.target_value}
                   onChange={(e) => set("target_value", e.target.value)} />
          </div>
          <div>
            <label className={label}>{t("objectives.fields.target_direction")}</label>
            <select className={field} value={form.target_direction}
                    onChange={(e) => set("target_direction", e.target.value)}>
              <option value="above">{t("objectives.direction.above")}</option>
              <option value="below">{t("objectives.direction.below")}</option>
            </select>
          </div>
          <div>
            <label className={label}>{t("objectives.fields.target_date")}</label>
            <input type="date" className={field} value={form.target_date}
                   onChange={(e) => set("target_date", e.target.value)} />
          </div>
          <div className="col-span-2">
            <label className={label}>{t("objectives.fields.resources")}</label>
            <textarea className={field} rows={2} value={form.resources}
                      onChange={(e) => set("resources", e.target.value)} />
          </div>
          <div className="col-span-2">
            <label className={label}>{t("objectives.fields.evaluation_method")}</label>
            <textarea className={field} rows={2} value={form.evaluation_method}
                      onChange={(e) => set("evaluation_method", e.target.value)} />
            <p className="text-[11px] text-gray-500 mt-1">{t("objectives.form.evaluation_hint")}</p>
          </div>
        </div>

        {error && <p className="text-sm text-red-600 mt-3">{error}</p>}

        <div className="flex justify-end gap-2 mt-5">
          <button className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800" onClick={onClose}>
            {t("actions.cancel")}
          </button>
          <button
            className="px-4 py-2 text-sm bg-indigo-600 text-white rounded hover:bg-indigo-700 disabled:opacity-50"
            disabled={save.isPending}
            onClick={() => { setError(""); save.mutate(); }}
          >
            {t("actions.save")}
          </button>
        </div>
      </div>
    </div>
  );
}
