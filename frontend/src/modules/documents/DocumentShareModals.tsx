import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { documentsApi, type Document } from "../../api/endpoints/documents";
import { controlsApi, type ControlInstance } from "../../api/endpoints/controls";
import { plantsApi, type Plant } from "../../api/endpoints/plants";
import { StatusBadge } from "../../components/ui/StatusBadge";
import { useTranslation } from "react-i18next";

// ─── Modal cambio sito documento ────────────────────────────────────────────

export function ChangePlantModal({ doc, onClose }: { doc: Document; onClose: () => void }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const { data: plants } = useQuery({
    queryKey: ["plants"],
    queryFn: plantsApi.list,
    retry: false,
  });
  const [plantId, setPlantId] = useState<string>(doc.plant ?? "");
  const [error, setError] = useState("");

  const mutation = useMutation({
    mutationFn: () => documentsApi.update(doc.id, { plant: plantId || null }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["documents"] });
      onClose();
    },
    onError: (e: unknown) => {
      // @ts-expect-error axios-like error
      const msg = e?.response?.data?.detail || (e as Error).message;
      setError(msg || t("documents.errors.update_plant_failed"));
    },
  });

  const plantOptions: Plant[] = plants ?? [];

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-6">
        <h3 className="text-lg font-semibold mb-1">{t("documents.change_plant.title")}</h3>
        <p className="text-xs text-gray-500 mb-4 truncate">{doc.title}</p>
        <div className="space-y-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("documents.fields.plant")}</label>
            <select
              value={plantId}
              onChange={e => setPlantId(e.target.value)}
              className="w-full border rounded px-3 py-2 text-sm"
            >
              <option value="">{t("documents.change_plant.none")}</option>
              {plantOptions.map(p => (
                <option key={p.id} value={p.id}>
                  {p.code} — {p.name}
                </option>
              ))}
            </select>
          </div>
        </div>
        {error && <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded mt-3 break-words">{error}</p>}
        <div className="flex justify-end gap-2 mt-4">
          <button onClick={onClose} className="px-4 py-2 border rounded text-sm text-gray-600 hover:bg-gray-50">{t("actions.cancel")}</button>
          <button
            onClick={() => mutation.mutate()}
            disabled={mutation.isPending}
            className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700 disabled:opacity-50"
          >
            {mutation.isPending ? t("common.saving") : t("actions.save")}
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Modal condivisione documento multi-plant ───────────────────────────────

export function ShareDocumentModal({ doc, onClose }: { doc: Document; onClose: () => void }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const { data: plants } = useQuery({ queryKey: ["plants"], queryFn: plantsApi.list, retry: false });
  const [selected, setSelected] = useState<Set<string>>(
    new Set((doc.shared_plant_names ?? []).map(p => p.id))
  );
  const [error, setError] = useState("");

  const mutation = useMutation({
    mutationFn: () => documentsApi.shareDocument(doc.id, Array.from(selected)),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["documents"] }); onClose(); },
    onError: (e: unknown) => setError((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || t("common.error")),
  });

  const plantOptions = (plants ?? []).filter(p => p.id !== doc.plant);

  function toggle(id: string) {
    setSelected(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-6">
        <h3 className="text-lg font-semibold mb-1">{t("documents.share.title", { defaultValue: "Condividi con altri plant" })}</h3>
        <p className="text-xs text-gray-500 mb-1 truncate">{doc.title}</p>
        <p className="text-xs text-gray-400 mb-4">
          {t("documents.share.hint", { defaultValue: "Il documento resterà di proprietà del plant originale. I plant selezionati potranno vederlo e scaricarlo senza dover ricaricare il file." })}
        </p>
        <div className="max-h-60 overflow-y-auto border rounded divide-y">
          {plantOptions.length === 0 && (
            <p className="px-3 py-4 text-sm text-gray-400 text-center">{t("documents.share.no_plants", { defaultValue: "Nessun altro plant disponibile" })}</p>
          )}
          {plantOptions.map(p => (
            <label key={p.id} className="flex items-center gap-3 px-3 py-2.5 hover:bg-gray-50 cursor-pointer">
              <input
                type="checkbox"
                checked={selected.has(p.id)}
                onChange={() => toggle(p.id)}
                className="w-4 h-4 accent-indigo-600"
              />
              <span className="text-sm text-gray-700">
                <span className="font-mono text-xs text-gray-500 mr-1">{p.code}</span>
                {p.name}
              </span>
              {selected.has(p.id) && <span className="ml-auto text-xs text-indigo-500">✓</span>}
            </label>
          ))}
        </div>
        <p className="text-xs text-gray-400 mt-2">
          {selected.size > 0
            ? t("documents.share.selected_count", { count: selected.size, defaultValue: `${selected.size} plant selezionati` })
            : t("documents.share.none_selected", { defaultValue: "Nessun plant selezionato — il documento sarà visibile solo al plant proprietario" })}
        </p>
        {error && <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded mt-3">{error}</p>}
        <div className="flex justify-end gap-2 mt-4">
          <button onClick={onClose} className="px-4 py-2 border rounded text-sm text-gray-600 hover:bg-gray-50">{t("actions.cancel")}</button>
          <button
            onClick={() => mutation.mutate()}
            disabled={mutation.isPending}
            className="px-4 py-2 bg-indigo-600 text-white rounded text-sm hover:bg-indigo-700 disabled:opacity-50"
          >
            {mutation.isPending ? t("common.saving") : t("actions.save")}
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Modal collegamento controlli ───────────────────────────────────────────

export function LinkControlsModal({ doc, onClose }: { doc: Document; onClose: () => void }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [frameworkFilter, setFrameworkFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [result, setResult] = useState<string | null>(null);

  const { data: frameworks } = useQuery({
    queryKey: ["frameworks"],
    queryFn: () => controlsApi.frameworks(),
    retry: false,
  });

  const params: Record<string, string> = { page_size: "200" };
  if (frameworkFilter) params.framework = frameworkFilter;
  if (statusFilter) params.status = statusFilter;

  const { data: instances } = useQuery({
    queryKey: ["controls-for-link", frameworkFilter, statusFilter],
    queryFn: () => controlsApi.instances(params),
    retry: false,
  });

  const linkMut = useMutation({
    mutationFn: () => documentsApi.linkControls(doc.id, Array.from(selected)),
    onSuccess: (data: { count: number }) => {
      qc.invalidateQueries({ queryKey: ["documents"] });
      setResult(t("documents.controls_link.result_linked", { count: data.count }));
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
            <h3 className="text-lg font-semibold text-gray-900">{t("documents.controls_link.title")}</h3>
            <p className="text-xs text-gray-400 mt-0.5 truncate max-w-md">{doc.title}</p>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-700 text-2xl w-8 h-8 flex items-center justify-center rounded hover:bg-gray-100">×</button>
        </div>

        <div className="px-6 py-3 border-b shrink-0 flex gap-3">
          <select value={frameworkFilter} onChange={e => setFrameworkFilter(e.target.value)} className="border rounded px-2 py-1.5 text-sm flex-1">
            <option value="">{t("controls.framework_filter.all")}</option>
            {(frameworks ?? []).map(fw => <option key={fw.id} value={fw.code}>{fw.code} — {fw.name}</option>)}
          </select>
          <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)} className="border rounded px-2 py-1.5 text-sm">
            <option value="">{t("documents.controls_link.all_statuses")}</option>
            <option value="compliant">{t("status.compliant")}</option>
            <option value="parziale">{t("status.parziale")}</option>
            <option value="gap">{t("status.gap")}</option>
            <option value="non_valutato">{t("status.non_valutato")}</option>
          </select>
        </div>

        <div className="flex-1 overflow-y-auto px-4 py-2">
          {controls.length === 0 ? (
            <p className="text-sm text-gray-400 text-center py-8">{t("controls.empty")}</p>
          ) : (
            <div className="divide-y divide-gray-100">
              {controls.map(ci => (
                <label key={ci.id} className="flex items-center gap-3 py-2 px-2 hover:bg-gray-50 cursor-pointer rounded">
                  <input
                    type="checkbox"
                    checked={selected.has(ci.id)}
                    onChange={() => toggle(ci.id)}
                    className="rounded"
                  />
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
              className="px-4 py-2 bg-blue-600 text-white rounded text-sm hover:bg-blue-700 disabled:opacity-50"
            >
              {linkMut.isPending ? t("documents.controls_link.linking") : t("documents.controls_link.submit")}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
