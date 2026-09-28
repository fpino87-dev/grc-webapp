import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { bcpApi, type BcpPlan } from "../../api/endpoints/bcp";
import { biaApi } from "../../api/endpoints/bia";
import { documentsApi } from "../../api/endpoints/documents";
import { FREQUENCIES } from "./shared";

type PlantOption = { id: string; code: string; name: string };

interface Props {
  plants: PlantOption[];
  /** Piano da modificare; assente = nuovo piano. */
  plan?: BcpPlan;
  /** Nuovo piano: sito e processo già scelti (es. dalla vista Copertura). */
  initialPlantId?: string;
  initialProcessId?: string;
  onClose: () => void;
}

function apiError(err: unknown): string | null {
  const data = (err as { response?: { data?: Record<string, unknown> } })?.response?.data;
  if (!data) return null;
  if (typeof data.detail === "string") return data.detail;
  const first = Object.values(data)[0];
  return Array.isArray(first) ? String(first[0]) : null;
}

export function BcpPlanForm({ plants, plan, initialPlantId, initialProcessId, onClose }: Props) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [title, setTitle] = useState(plan?.title ?? "");
  const [plantId, setPlantId] = useState(plan?.plant ?? initialPlantId ?? "");
  const [version, setVersion] = useState(plan?.version ?? "1.0");
  const [documentId, setDocumentId] = useState(plan?.document ?? "");
  const [processIds, setProcessIds] = useState<string[]>(
    plan?.critical_processes ?? (initialProcessId ? [initialProcessId] : []),
  );
  const [rto, setRto] = useState(plan?.rto_hours != null ? String(plan.rto_hours) : "");
  const [rpo, setRpo] = useState(plan?.rpo_hours != null ? String(plan.rpo_hours) : "");
  const [frequency, setFrequency] = useState(
    `${plan?.test_frequency_value ?? 1}:${plan?.test_frequency_unit ?? "years"}`,
  );

  const { data: processesData } = useQuery({
    queryKey: ["bia-processes", plantId],
    queryFn: () => biaApi.list({ plant: plantId }),
    enabled: !!plantId,
    retry: false,
  });
  const processes = [...(processesData?.results ?? [])].sort(
    (a, b) => (b.criticality ?? 0) - (a.criticality ?? 0) || a.name.localeCompare(b.name),
  );

  const { data: documentsData } = useQuery({
    queryKey: ["documents", "bcp-link", plantId],
    queryFn: () => documentsApi.list({ plant: plantId }),
    enabled: !!plantId,
    retry: false,
  });
  const documents = (documentsData?.results ?? []).filter(d => d.status !== "archiviato");

  // Target BIA più stringenti fra i processi scelti: il piano deve rispettarli.
  const selected = processes.filter(p => processIds.includes(p.id));
  const minTarget = (values: (number | null | undefined)[]) => {
    const v = values.filter((x): x is number => x != null);
    return v.length ? Math.min(...v) : null;
  };
  const rtoTarget = minTarget(selected.map(p => p.rto_target_hours));
  const rpoTarget = minTarget(selected.map(p => p.rpo_target_hours));

  const mutation = useMutation({
    mutationFn: () => {
      const [value, unit] = frequency.split(":");
      const payload: Partial<BcpPlan> = {
        title,
        version,
        document: documentId || null,
        critical_processes: processIds,
        rto_hours: rto ? Number(rto) : null,
        rpo_hours: rpo ? Number(rpo) : null,
        test_frequency_value: Number(value),
        test_frequency_unit: unit as BcpPlan["test_frequency_unit"],
      };
      return plan ? bcpApi.update(plan.id, payload) : bcpApi.create({ ...payload, plant: plantId });
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["bcp"] });
      onClose();
    },
  });

  const toggleProcess = (id: string) =>
    setProcessIds(prev => (prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]));

  const plantInfo = plants.find(p => p.id === plantId);
  const overTarget = (value: string, target: number | null) =>
    value !== "" && target != null && Number(value) > target;

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-xl p-6 max-h-screen overflow-y-auto">
        <h3 className="text-lg font-semibold mb-4">{plan ? t("bcp.form.edit_title") : t("bcp.form.new_title")}</h3>
        <div className="space-y-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("bcp.form.title")} *</label>
            <input value={title} onChange={e => setTitle(e.target.value)} className="w-full border rounded px-3 py-2 text-sm" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("bcp.form.plant")} *</label>
              {plan ? (
                <div className="w-full border rounded px-3 py-2 text-sm text-gray-700 bg-gray-50">
                  {plantInfo ? `${plantInfo.code} — ${plantInfo.name}` : "—"}
                </div>
              ) : (
                <select
                  value={plantId}
                  onChange={e => { setPlantId(e.target.value); setProcessIds([]); setDocumentId(""); }}
                  className="w-full border rounded px-3 py-2 text-sm"
                >
                  <option value="">{t("bcp.form.select")}</option>
                  {plants.map(p => <option key={p.id} value={p.id}>{p.code} — {p.name}</option>)}
                </select>
              )}
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("bcp.form.version")}</label>
              <input value={version} onChange={e => setVersion(e.target.value)} className="w-full border rounded px-3 py-2 text-sm" />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("bcp.form.document")}</label>
            <select
              value={documentId}
              onChange={e => setDocumentId(e.target.value)}
              disabled={!plantId}
              className="w-full border rounded px-3 py-2 text-sm disabled:bg-gray-50"
            >
              <option value="">{t("bcp.form.no_document")}</option>
              {documents.map(d => (
                <option key={d.id} value={d.id}>
                  {d.document_code ? `${d.document_code} — ` : ""}{d.title} · {t(`bcp.document_status.${d.status}`, { defaultValue: d.status })}
                </option>
              ))}
            </select>
            <p className="text-xs text-gray-500 mt-1">{t("bcp.form.document_hint")}</p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("bcp.form.processes")} *</label>
            {!plantId ? (
              <p className="text-xs text-gray-400">{t("bcp.form.processes_pick_plant")}</p>
            ) : processes.length === 0 ? (
              <p className="text-xs text-gray-400">{t("bcp.form.processes_empty")}</p>
            ) : (
              <div className="border rounded max-h-40 overflow-y-auto divide-y divide-gray-100">
                {processes.map(p => (
                  <label key={p.id} className="flex items-center gap-2 px-3 py-1.5 text-sm hover:bg-gray-50 cursor-pointer">
                    <input type="checkbox" checked={processIds.includes(p.id)} onChange={() => toggleProcess(p.id)} />
                    <span className="flex-1 text-gray-800">{p.name}</span>
                    <span className="text-xs text-gray-400">
                      {t("bcp.form.criticality", { value: p.criticality })}
                      {p.rto_target_hours != null && ` · RTO ${p.rto_target_hours}h`}
                    </span>
                  </label>
                ))}
              </div>
            )}
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("bcp.form.rto")}</label>
              <input type="number" min="0" value={rto} onChange={e => setRto(e.target.value)} className="w-full border rounded px-3 py-2 text-sm" />
              {rtoTarget != null && (
                <p className={`text-xs mt-1 ${overTarget(rto, rtoTarget) ? "text-orange-700" : "text-gray-500"}`}>
                  {t("bcp.form.bia_target", { value: rtoTarget })}
                </p>
              )}
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("bcp.form.rpo")}</label>
              <input type="number" min="0" value={rpo} onChange={e => setRpo(e.target.value)} className="w-full border rounded px-3 py-2 text-sm" />
              {rpoTarget != null && (
                <p className={`text-xs mt-1 ${overTarget(rpo, rpoTarget) ? "text-orange-700" : "text-gray-500"}`}>
                  {t("bcp.form.bia_target", { value: rpoTarget })}
                </p>
              )}
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("bcp.form.frequency")}</label>
            <select value={frequency} onChange={e => setFrequency(e.target.value)} className="w-full border rounded px-3 py-2 text-sm">
              {!(FREQUENCIES as readonly string[]).includes(frequency) && (
                <option value={frequency}>{frequency}</option>
              )}
              {FREQUENCIES.map(f => (
                <option key={f} value={f}>{t(`bcp.frequency.${f.replace(":", "_")}`)}</option>
              ))}
            </select>
          </div>
        </div>

        {mutation.isError && (
          <p className="text-sm text-red-600 mt-3">{apiError(mutation.error) ?? t("bcp.form.save_error")}</p>
        )}
        <div className="flex justify-end gap-2 mt-4">
          <button onClick={onClose} className="px-4 py-2 border rounded text-sm text-gray-600 hover:bg-gray-50">{t("bcp.actions.cancel")}</button>
          <button
            onClick={() => mutation.mutate()}
            disabled={mutation.isPending || !title || !plantId || processIds.length === 0}
            className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700 disabled:opacity-50"
          >
            {mutation.isPending ? t("bcp.actions.saving") : plan ? t("bcp.actions.save") : t("bcp.actions.create")}
          </button>
        </div>
      </div>
    </div>
  );
}
