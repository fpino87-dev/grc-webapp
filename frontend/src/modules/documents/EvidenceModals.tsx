import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { documentsApi, type Evidence } from "../../api/endpoints/documents";
import { controlsApi, type ControlInstance } from "../../api/endpoints/controls";
import { StatusBadge } from "../../components/ui/StatusBadge";
import { useAuthStore } from "../../store/auth";
import { EVIDENCE_TYPES } from "./documentUtils";
import { useTranslation } from "react-i18next";

// ─── Modal nuova evidenza ───────────────────────────────────────────────────

export function NewEvidenceModal({ onClose }: { onClose: () => void }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const selectedPlant = useAuthStore(s => s.selectedPlant);
  const [form, setForm] = useState<Partial<Evidence>>({ evidence_type: "altro" });
  const [error, setError] = useState("");
  const [file, setFile] = useState<File | null>(null);

  const mutation = useMutation({
    mutationFn: (payload: Partial<Evidence> & { file?: File }) => {
      const data: Partial<Evidence> & { file?: File } = {
        ...payload,
        // collega automaticamente al sito selezionato se presente
        plant: selectedPlant ? selectedPlant.id : payload.plant ?? null,
      };
      return documentsApi.createEvidence(data);
    },
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["evidences"] }); onClose(); },
    onError: (e: unknown) => setError((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || t("common.error")),
  });

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-6">
        <h3 className="text-lg font-semibold mb-4">{t("documents.evidence.new.title")}</h3>
        <div className="space-y-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("documents.fields.title")} *</label>
            <input onChange={e => setForm(p => ({ ...p, title: e.target.value }))} className="w-full border rounded px-3 py-2 text-sm" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("documents.evidence.fields.type")}</label>
            <select value={form.evidence_type} onChange={e => setForm(p => ({ ...p, evidence_type: e.target.value }))} className="w-full border rounded px-3 py-2 text-sm">
              {EVIDENCE_TYPES.map((v) => <option key={v} value={v}>{t(`documents.evidence.types.${v}`)}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("documents.evidence.fields.valid_until")} *</label>
            <input type="date" onChange={e => setForm(p => ({ ...p, valid_until: e.target.value }))} className="w-full border rounded px-3 py-2 text-sm" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("documents.fields.description")}</label>
            <textarea onChange={e => setForm(p => ({ ...p, description: e.target.value }))} rows={2} className="w-full border rounded px-3 py-2 text-sm resize-none" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("documents.fields.file")} *</label>
            <input
              type="file"
              onChange={e => setFile(e.target.files?.[0] ?? null)}
              className="w-full text-sm"
            />
          </div>
        </div>
        {error && <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded mt-3">{error}</p>}
        <div className="flex justify-end gap-2 mt-4">
          <button onClick={onClose} className="px-4 py-2 border rounded text-sm text-gray-600 hover:bg-gray-50">{t("actions.cancel")}</button>
          <button
            onClick={() => mutation.mutate({ ...form, file: file ?? undefined })}
            disabled={mutation.isPending || !form.title || !form.valid_until || !file}
            className="px-4 py-2 bg-green-600 text-white rounded text-sm hover:bg-green-700 disabled:opacity-50"
          >
            {mutation.isPending ? t("common.saving") : t("documents.evidence.new.submit")}
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Modal collega evidenza a controlli ─────────────────────────────────────

export function LinkEvidenceToControlModal({ ev, onClose }: { ev: Evidence; onClose: () => void }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [frameworkFilter, setFrameworkFilter] = useState("");
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [result, setResult] = useState<string | null>(null);

  const { data: frameworks } = useQuery({
    queryKey: ["frameworks"],
    queryFn: () => controlsApi.frameworks(),
    retry: false,
  });

  const params: Record<string, string> = { page_size: "200" };
  if (frameworkFilter) params.framework = frameworkFilter;

  const { data: instances } = useQuery({
    queryKey: ["controls-for-ev-link", frameworkFilter],
    queryFn: () => controlsApi.instances(params),
    retry: false,
  });

  const linkMut = useMutation({
    mutationFn: async () => {
      for (const instanceId of Array.from(selected)) {
        await controlsApi.linkEvidence(instanceId, ev.id);
      }
      return { count: selected.size };
    },
    onSuccess: (data: { count: number }) => {
      qc.invalidateQueries({ queryKey: ["evidences"] });
      setResult(t("documents.evidence.link_controls.result_linked", { count: data.count }));
      setSelected(new Set());
    },
  });

  const controls: ControlInstance[] = instances?.results ?? [];

  function toggle(id: string) {
    setSelected(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl flex flex-col max-h-[85vh]">
        <div className="flex items-center justify-between px-6 py-4 border-b shrink-0">
          <div>
            <h3 className="text-lg font-semibold text-gray-900">{t("documents.evidence.link_controls.title")}</h3>
            <p className="text-xs text-gray-400 mt-0.5 truncate max-w-md">{ev.title}</p>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-700 text-2xl w-8 h-8 flex items-center justify-center rounded hover:bg-gray-100">×</button>
        </div>

        <div className="px-6 py-3 border-b shrink-0">
          <select value={frameworkFilter} onChange={e => setFrameworkFilter(e.target.value)} className="border rounded px-2 py-1.5 text-sm w-full">
            <option value="">{t("controls.framework_filter.all")}</option>
            {(frameworks ?? []).map(fw => <option key={fw.id} value={fw.code}>{fw.code} — {fw.name}</option>)}
          </select>
        </div>

        <div className="flex-1 overflow-y-auto px-4 py-2">
          {controls.length === 0 ? (
            <p className="text-sm text-gray-400 text-center py-8">{t("controls.empty")}</p>
          ) : (
            <div className="divide-y divide-gray-100">
              {controls.map(ci => (
                <label key={ci.id} className="flex items-center gap-3 py-2 px-2 hover:bg-gray-50 cursor-pointer rounded">
                  <input type="checkbox" checked={selected.has(ci.id)} onChange={() => toggle(ci.id)} className="rounded" />
                  <span className="text-xs font-mono text-gray-500 w-20 shrink-0">{ci.control_external_id}</span>
                  <span className="text-xs text-gray-800 flex-1 truncate">{ci.control_title}</span>
                  <span className="text-xs bg-gray-100 text-gray-600 px-1.5 rounded shrink-0">{ci.framework_code}</span>
                  <span className="shrink-0"><StatusBadge status={ci.status} /></span>
                </label>
              ))}
            </div>
          )}
        </div>

        <div className="px-6 py-4 border-t shrink-0 flex items-center justify-between gap-3">
          <div className="text-xs text-gray-500">
            {selected.size > 0
              ? t("documents.controls_link.selected_count", { count: selected.size })
              : t("documents.controls_link.none_selected")}
          </div>
          {result && <p className="text-xs text-green-700 font-medium">{result}</p>}
          <div className="flex gap-2">
            <button onClick={onClose} className="px-4 py-2 border rounded text-sm text-gray-600 hover:bg-gray-50">{t("common.close")}</button>
            <button
              onClick={() => linkMut.mutate()}
              disabled={selected.size === 0 || linkMut.isPending}
              className="px-4 py-2 bg-green-600 text-white rounded text-sm hover:bg-green-700 disabled:opacity-50"
            >
              {linkMut.isPending ? t("documents.controls_link.linking") : t("documents.controls_link.submit")}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
