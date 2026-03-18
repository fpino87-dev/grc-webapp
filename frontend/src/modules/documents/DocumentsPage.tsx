import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { documentsApi, type Document, type Evidence } from "../../api/endpoints/documents";
import { controlsApi, type ControlInstance } from "../../api/endpoints/controls";
import { plantsApi, type Plant } from "../../api/endpoints/plants";
import { StatusBadge } from "../../components/ui/StatusBadge";
import { useAuthStore } from "../../store/auth";
import { useTranslation } from "react-i18next";
import i18n from "../../i18n";

type MainTab = "documenti" | "evidenze";

// ─── Helpers evidenze ────────────────────────────────────────────────────────

function evidenceIcon(type: string): string {
  const map: Record<string, string> = {
    screenshot: "📸", log: "📋", report: "📄",
    verbale: "📝", certificato: "🏆", test_result: "🧪", altro: "📎",
  };
  return map[type] ?? "📎";
}

function ExpiryBadge({ validUntil }: { validUntil: string | null }) {
  const { t } = useTranslation();
  if (!validUntil) return <span className="text-xs text-gray-400">—</span>;
  const date = new Date(validUntil);
  const today = new Date();
  const days = Math.ceil((date.getTime() - today.getTime()) / 86400000);
  if (days < 0) return (
    <div className="text-center">
      <span className="block text-xs px-2 py-0.5 rounded bg-red-100 text-red-700 font-medium">{t("documents.evidence.expiry.expired")}</span>
      <span className="text-xs text-red-500">{t("documents.evidence.expiry.days_ago", { days: Math.abs(days) })}</span>
    </div>
  );
  if (days <= 30) return (
    <div className="text-center">
      <span className="block text-xs px-2 py-0.5 rounded bg-orange-100 text-orange-700 font-medium">{t("documents.evidence.expiry.expiring")}</span>
      <span className="text-xs text-orange-600">{t("documents.evidence.expiry.in_days", { days })}</span>
    </div>
  );
  return (
    <div className="text-center">
      <span className="block text-xs px-2 py-0.5 rounded bg-green-100 text-green-700 font-medium">{t("documents.evidence.expiry.valid")}</span>
      <span className="text-xs text-green-600">{date.toLocaleDateString(i18n.language || "it")}</span>
    </div>
  );
}

const EVIDENCE_TYPES = ["screenshot", "log", "report", "verbale", "certificato", "test_result", "altro"] as const;

function expirySort(a: Evidence, b: Evidence): number {
  if (!a.valid_until && !b.valid_until) return 0;
  if (!a.valid_until) return 1;
  if (!b.valid_until) return -1;
  const today = new Date();
  const da = new Date(a.valid_until);
  const db = new Date(b.valid_until);
  const daysA = Math.ceil((da.getTime() - today.getTime()) / 86400000);
  const daysB = Math.ceil((db.getTime() - today.getTime()) / 86400000);
  // in scadenza prima, poi valide, poi scadute
  if (daysA >= 0 && daysA <= 30 && !(daysB >= 0 && daysB <= 30)) return -1;
  if (daysB >= 0 && daysB <= 30 && !(daysA >= 0 && daysA <= 30)) return 1;
  return daysA - daysB;
}

// ─── Modal nuovo documento ──────────────────────────────────────────────────

function NewDocumentModal({ onClose }: { onClose: () => void }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const selectedPlant = useAuthStore(s => s.selectedPlant);
  const [form, setForm] = useState<Partial<Document>>({ is_mandatory: false });
  const [error, setError] = useState("");
  const [file, setFile] = useState<File | null>(null);

  const mutation = useMutation({
    mutationFn: (payload: Partial<Document>) => {
      const data: Partial<Document> = {
        ...payload,
        // collega automaticamente al sito selezionato se presente
        plant: selectedPlant ? selectedPlant.id : payload.plant ?? null,
      };
      return documentsApi.create(data);
    },
    onSuccess: async (doc) => {
      if (file) {
        try {
          await documentsApi.uploadVersion(doc.id, file);
        } catch {
          // l'errore di upload versione non deve bloccare la creazione del documento
        }
      }
      qc.invalidateQueries({ queryKey: ["documents"] });
      onClose();
    },
    onError: (e: unknown) => setError((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || t("common.save_error")),
  });

  function handleChange(e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) {
    const value = e.target.type === "checkbox" ? (e.target as HTMLInputElement).checked : e.target.value;
    setForm(prev => ({ ...prev, [e.target.name]: value }));
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-6">
        <h3 className="text-lg font-semibold mb-4">{t("documents.new.title")}</h3>
        <div className="space-y-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("documents.fields.title")} *</label>
            <input name="title" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("documents.fields.category")}</label>
              <select name="category" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm">
                <option value="">{t("common.select")}</option>
                <option value="politica">{t("documents.category.politica")}</option>
                <option value="procedura">{t("documents.category.procedura")}</option>
                <option value="istruzione">{t("documents.category.istruzione")}</option>
                <option value="registro">{t("documents.category.registro")}</option>
                <option value="verbale">{t("documents.category.verbale")}</option>
                <option value="contratto">{t("documents.category.contratto")}</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("documents.fields.document_type")}</label>
              <select name="document_type" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm">
                <option value="policy">{t("documents.type.policy")}</option>
                <option value="procedura">{t("documents.type.procedura")}</option>
                <option value="manuale">{t("documents.type.manuale")}</option>
                <option value="contratto">{t("documents.type.contratto")}</option>
                <option value="registro">{t("documents.type.registro")}</option>
                <option value="altro">{t("documents.type.altro")}</option>
              </select>
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("documents.fields.review_due_date")}</label>
            <input type="date" name="review_due_date" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" />
          </div>
          <div className="flex items-center gap-2">
            <input type="checkbox" id="is_mandatory" name="is_mandatory" onChange={handleChange} className="rounded" />
            <label htmlFor="is_mandatory" className="text-sm text-gray-700">{t("documents.fields.mandatory")}</label>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("documents.fields.file")} *</label>
            <input
              type="file"
              onChange={e => setFile(e.target.files?.[0] ?? null)}
              className="w-full text-sm"
            />
            <p className="mt-1 text-xs text-gray-500">
              {t("documents.file_help")}
            </p>
          </div>
        </div>
        {error && <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded mt-3">{error}</p>}
        <div className="flex justify-end gap-2 mt-4">
          <button onClick={onClose} className="px-4 py-2 border rounded text-sm text-gray-600 hover:bg-gray-50">{t("actions.cancel")}</button>
          <button
            onClick={() => mutation.mutate(form)}
            disabled={mutation.isPending || !form.title || !file}
            className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700 disabled:opacity-50"
          >
            {mutation.isPending ? t("common.saving") : t("documents.new.submit")}
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Modal upload nuova versione documento ─────────────────────────────────────

function UploadVersionModal({ doc, onClose }: { doc: Document; onClose: () => void }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [file, setFile] = useState<File | null>(null);
  const [changeSummary, setChangeSummary] = useState("");
  const [error, setError] = useState("");

  const mutation = useMutation({
    mutationFn: () => {
      if (!file) throw new Error(t("documents.errors.no_file_selected"));
      return documentsApi.uploadVersion(doc.id, file, changeSummary || undefined);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["documents"] });
      onClose();
    },
    onError: (e: unknown) => {
      // @ts-expect-error generic axios-like error shape
      const msg = e?.response?.data?.error || e?.response?.data?.detail || (e as Error).message;
      setError(msg || t("documents.errors.upload_failed"));
    },
  });

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-6">
        <h3 className="text-lg font-semibold mb-1">{t("documents.upload.title")}</h3>
        <p className="text-xs text-gray-500 mb-4 truncate">{doc.title}</p>
        <div className="space-y-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("documents.fields.file")} *</label>
            <input
              type="file"
              onChange={e => setFile(e.target.files?.[0] ?? null)}
              className="w-full text-sm"
            />
            <p className="mt-1 text-xs text-gray-500">
              {t("documents.file_help")}
            </p>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("documents.upload.change_notes")}</label>
            <textarea
              rows={2}
              value={changeSummary}
              onChange={e => setChangeSummary(e.target.value)}
              className="w-full border rounded px-3 py-2 text-sm resize-none"
            />
          </div>
        </div>
        {error && <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded mt-3 break-words">{error}</p>}
        <div className="flex justify-end gap-2 mt-4">
          <button onClick={onClose} className="px-4 py-2 border rounded text-sm text-gray-600 hover:bg-gray-50">{t("actions.cancel")}</button>
          <button
            onClick={() => mutation.mutate()}
            disabled={mutation.isPending || !file}
            className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700 disabled:opacity-50"
          >
            {mutation.isPending ? t("common.loading") : t("documents.upload.submit")}
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Modal cambio sito documento ───────────────────────────────────────────────

function ChangePlantModal({ doc, onClose }: { doc: Document; onClose: () => void }) {
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

// ─── Modal nuova evidenza ─────────────────────────────────────────────────────

function NewEvidenceModal({ onClose }: { onClose: () => void }) {
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

// ─── Modal collegamento controlli ─────────────────────────────────────────────

function LinkControlsModal({ doc, onClose }: { doc: Document; onClose: () => void }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [frameworkFilter, setFrameworkFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [result, setResult] = useState<string | null>(null);

  const { data: frameworks } = useQuery({
    queryKey: ["frameworks"],
    queryFn: controlsApi.frameworks,
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

  const STATUS_COLORS: Record<string, string> = {
    compliant: "text-green-700", parziale: "text-yellow-700", gap: "text-red-700",
    na: "text-gray-500", non_valutato: "text-gray-400",
  };

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

// ─── Tab Documenti ────────────────────────────────────────────────────────────

type DocStatusFilter = "tutti" | "bozza" | "revisione" | "approvazione" | "approvato";

function TabDocumenti() {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const selectedPlant = useAuthStore(s => s.selectedPlant);
  const [statusFilter, setStatusFilter] = useState<DocStatusFilter>("tutti");
  const [showNew, setShowNew] = useState(false);
  const [linkControlsDoc, setLinkControlsDoc] = useState<Document | null>(null);
  const [uploadDoc, setUploadDoc] = useState<Document | null>(null);
  const [changePlantDoc, setChangePlantDoc] = useState<Document | null>(null);
  const [filterByPlant, setFilterByPlant] = useState(true);

  const params: Record<string, string> = {};
  if (statusFilter !== "tutti") params.status = statusFilter;
  if (filterByPlant && selectedPlant) params.plant = selectedPlant.id;

  const { data, isLoading } = useQuery({
    queryKey: ["documents", statusFilter, filterByPlant, selectedPlant?.id],
    queryFn: () => documentsApi.list(params),
    retry: false,
  });

  const submitMutation = useMutation({ mutationFn: documentsApi.submit, onSuccess: () => qc.invalidateQueries({ queryKey: ["documents"] }) });
  const approveMutation = useMutation({ mutationFn: (id: string) => documentsApi.approve(id), onSuccess: () => qc.invalidateQueries({ queryKey: ["documents"] }) });
  const rejectMutation = useMutation({ mutationFn: (id: string) => documentsApi.reject(id), onSuccess: () => qc.invalidateQueries({ queryKey: ["documents"] }) });

  const documents: Document[] = data?.results ?? [];

  async function handleDownloadDocument(doc: Document) {
    try {
      const blob = await documentsApi.downloadDocument(doc.id);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      const filename = doc.latest_version?.file_name || `${doc.title || "documento"}.pdf`;
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch {
      // eslint-disable-next-line no-alert
      alert(t("documents.errors.download_failed"));
    }
  }

  const STATUS_FILTERS: { label: string; value: DocStatusFilter }[] = [
    { label: t("documents.filters.all"), value: "tutti" },
    { label: t("documents.filters.draft"), value: "bozza" },
    { label: t("documents.filters.in_review"), value: "revisione" },
    { label: t("documents.filters.in_approval"), value: "approvazione" },
    { label: t("documents.filters.approved"), value: "approvato" },
  ];

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-1 flex-wrap">
          {STATUS_FILTERS.map(f => (
            <button key={f.value} onClick={() => setStatusFilter(f.value)}
              className={`px-3 py-1.5 rounded text-sm font-medium transition-colors ${statusFilter === f.value ? "bg-primary-600 text-white" : "bg-gray-100 text-gray-600 hover:bg-gray-200"}`}>
              {f.label}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-3">
          {selectedPlant && (
            <label className="flex items-center gap-1 text-xs text-gray-600">
              <input
                type="checkbox"
                checked={filterByPlant}
                onChange={e => setFilterByPlant(e.target.checked)}
                className="rounded"
              />
              <span>{t("documents.filter.only_selected_plant")}</span>
            </label>
          )}
          <button onClick={() => setShowNew(true)} className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700 shrink-0">
            + {t("documents.new.submit")}
          </button>
        </div>
      </div>

      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-gray-400">{t("common.loading")}</div>
        ) : documents.length === 0 ? (
          <div className="p-8 text-center text-gray-400">{t("documents.empty")}</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("documents.table.title")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("documents.table.file")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("documents.table.plant")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("documents.table.type")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("documents.table.status")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("documents.table.mandatory")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("documents.table.review_due_date")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("documents.table.approved_at")}</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {documents.map(doc => (
                <tr key={doc.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3 font-medium text-gray-800">{doc.title}</td>
                  <td className="px-4 py-3 text-xs">
                    {doc.latest_version ? (
                      <button
                        type="button"
                        onClick={() => handleDownloadDocument(doc)}
                        className="text-indigo-600 hover:underline"
                      >
                        {t("documents.actions.download")}
                      </button>
                    ) : (
                      <span className="text-gray-400">—</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-gray-600 text-xs">
                    {doc.plant_code || doc.plant_name || "—"}
                  </td>
                  <td className="px-4 py-3 text-gray-600 capitalize text-xs">
                    {doc.document_type
                      ? t(`documents.type.${doc.document_type}`, { defaultValue: doc.document_type })
                      : doc.category
                      ? t(`documents.category.${doc.category}`, { defaultValue: doc.category })
                      : "—"}
                  </td>
                  <td className="px-4 py-3"><StatusBadge status={doc.status} /></td>
                  <td className="px-4 py-3">
                    {doc.is_mandatory
                      ? <span className="inline-flex px-2 py-0.5 rounded text-xs font-medium bg-red-100 text-red-800">{t("documents.mandatory.yes")}</span>
                      : <span className="inline-flex px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-500">{t("documents.mandatory.no")}</span>}
                  </td>
                  <td className="px-4 py-3 text-gray-500 text-xs">{doc.review_due_date ? new Date(doc.review_due_date).toLocaleDateString(i18n.language || "it") : "—"}</td>
                  <td className="px-4 py-3 text-gray-500 text-xs">{doc.approved_at ? new Date(doc.approved_at).toLocaleDateString(i18n.language || "it") : "—"}</td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2 flex-wrap">
                      {doc.status === "bozza" && <button onClick={() => submitMutation.mutate(doc.id)} className="text-xs text-gray-500 hover:text-blue-700 border border-gray-300 rounded px-2 py-0.5 hover:border-blue-400">{t("documents.actions.submit_for_review")}</button>}
                      {(doc.status === "revisione" || doc.status === "approvazione") && (
                        <>
                          <button onClick={() => approveMutation.mutate(doc.id)} className="text-xs text-gray-500 hover:text-green-700 border border-gray-300 rounded px-2 py-0.5 hover:border-green-400">{t("actions.approve")}</button>
                          <button onClick={() => rejectMutation.mutate(doc.id)} className="text-xs text-gray-500 hover:text-red-700 border border-gray-300 rounded px-2 py-0.5 hover:border-red-400">{t("actions.reject")}</button>
                        </>
                      )}
                      <button
                        onClick={() => setUploadDoc(doc)}
                        className="text-xs text-gray-500 hover:text-indigo-700 border border-gray-300 rounded px-2 py-0.5 hover:border-indigo-400"
                      >
                        {t("documents.actions.new_version")}
                      </button>
                      <button
                        onClick={() => setLinkControlsDoc(doc)}
                        className="text-xs text-indigo-600 hover:text-indigo-800 border border-indigo-200 rounded px-2 py-0.5 hover:border-indigo-400"
                      >
                        {t("documents.actions.link_controls")}
                      </button>
                      <button
                        onClick={() => setChangePlantDoc(doc)}
                        className="text-xs text-gray-500 hover:text-amber-700 border border-gray-300 rounded px-2 py-0.5 hover:border-amber-400"
                      >
                        {t("documents.actions.change_plant")}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {showNew && <NewDocumentModal onClose={() => setShowNew(false)} />}
      {linkControlsDoc && <LinkControlsModal doc={linkControlsDoc} onClose={() => setLinkControlsDoc(null)} />}
      {uploadDoc && <UploadVersionModal doc={uploadDoc} onClose={() => setUploadDoc(null)} />}
      {changePlantDoc && <ChangePlantModal doc={changePlantDoc} onClose={() => setChangePlantDoc(null)} />}
    </div>
  );
}

// ─── Tab Evidenze ─────────────────────────────────────────────────────────────

type ExpiryFilter = "tutti" | "valide" | "in_scadenza" | "scadute";

function TabEvidenze() {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const selectedPlant = useAuthStore(s => s.selectedPlant);
  const [typeFilter, setTypeFilter] = useState("");
  const [expiryFilter, setExpiryFilter] = useState<ExpiryFilter>("tutti");
  const [showNew, setShowNew] = useState(false);
  const [filterByPlant, setFilterByPlant] = useState(true);

  async function handleDownloadEvidence(ev: Evidence) {
    try {
      const blob = await documentsApi.downloadEvidence(ev.id);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      const filename = ev.file_path ? ev.file_path.split("/").pop() || ev.title || "evidenza" : ev.title || "evidenza";
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch {
      // eslint-disable-next-line no-alert
      alert(t("documents.errors.evidence_download_failed"));
    }
  }

  const params: Record<string, string> = {};
  if (typeFilter) params.evidence_type = typeFilter;
  if (expiryFilter !== "tutti") params.expiry = expiryFilter;
  if (filterByPlant && selectedPlant) params.plant = selectedPlant.id;

  const { data, isLoading } = useQuery({
    queryKey: ["evidences", typeFilter, expiryFilter, filterByPlant, selectedPlant?.id],
    queryFn: () => documentsApi.evidences(params),
    retry: false,
  });

  const evidences: Evidence[] = [...(data?.results ?? [])].sort(expirySort);

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2 flex-wrap">
          {/* Filtro scadenza */}
          {(["tutti", "in_scadenza", "valide", "scadute"] as ExpiryFilter[]).map(f => {
            const labels = {
              tutti: t("documents.evidence.filters.all"),
              valide: t("documents.evidence.filters.valid"),
              in_scadenza: t("documents.evidence.filters.expiring"),
              scadute: t("documents.evidence.filters.expired"),
            };
            const colors = { tutti: "", valide: "text-green-700", in_scadenza: "text-orange-700", scadute: "text-red-700" };
            return (
              <button key={f} onClick={() => setExpiryFilter(f)}
                className={`px-3 py-1.5 rounded text-sm font-medium transition-colors ${expiryFilter === f ? "bg-primary-600 text-white" : `bg-gray-100 hover:bg-gray-200 ${colors[f]}`}`}>
                {labels[f]}
              </button>
            );
          })}

          {/* Filtro tipo */}
          <select value={typeFilter} onChange={e => setTypeFilter(e.target.value)} className="border rounded px-2 py-1.5 text-sm">
            <option value="">{t("documents.evidence.filters.all_types")}</option>
              {EVIDENCE_TYPES.map((v) => <option key={v} value={v}>{t(`documents.evidence.types.${v}`)}</option>)}
          </select>
        </div>
        <div className="flex items-center gap-3">
          {selectedPlant && (
            <label className="flex items-center gap-1 text-xs text-gray-600">
              <input
                type="checkbox"
                checked={filterByPlant}
                onChange={e => setFilterByPlant(e.target.checked)}
                className="rounded"
              />
              <span>{t("documents.filter.only_selected_plant")}</span>
            </label>
          )}
          <button onClick={() => setShowNew(true)} className="px-4 py-2 bg-green-600 text-white rounded text-sm hover:bg-green-700 shrink-0">
            + {t("documents.evidence.new.submit")}
          </button>
        </div>
      </div>

      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-gray-400">{t("common.loading")}</div>
        ) : evidences.length === 0 ? (
          <div className="p-8 text-center text-gray-400">{t("documents.evidence.empty")}</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("documents.evidence.table.type")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("documents.evidence.table.title")}</th>
                <th className="text-center px-4 py-3 font-medium text-gray-600">{t("documents.evidence.table.expiry")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("documents.evidence.table.plant")}</th>
                <th className="text-center px-4 py-3 font-medium text-gray-600">{t("documents.evidence.table.linked_controls")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("documents.evidence.table.uploaded_by")}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {evidences.map(ev => (
                <tr key={ev.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1.5">
                      <span className="text-base">{evidenceIcon(ev.evidence_type)}</span>
                      <span className="text-xs text-gray-500">{t(`documents.evidence.types.${ev.evidence_type}`, { defaultValue: ev.evidence_type })}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3 font-medium text-gray-800 max-w-xs">
                    <div className="truncate">{ev.title}</div>
                    {ev.description && <div className="text-xs text-gray-400 truncate">{ev.description}</div>}
                    {(ev.file_url || ev.file_path) && (
                      <button
                        type="button"
                        onClick={() => handleDownloadEvidence(ev)}
                        className="mt-1 inline-flex text-xs text-indigo-600 hover:underline"
                      >
                        {t("documents.evidence.actions.download_file")}
                      </button>
                    )}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <ExpiryBadge validUntil={ev.valid_until} />
                  </td>
                  <td className="px-4 py-3 text-gray-600 text-xs">{ev.plant_name || "—"}</td>
                  <td className="px-4 py-3 text-center">
                    <span className={`inline-flex items-center justify-center w-6 h-6 rounded-full text-xs font-medium ${ev.control_instances_count > 0 ? "bg-blue-100 text-blue-700" : "bg-gray-100 text-gray-400"}`}>
                      {ev.control_instances_count}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-500 text-xs">{ev.uploaded_by_username || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {showNew && <NewEvidenceModal onClose={() => setShowNew(false)} />}
    </div>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────

export function DocumentsPage() {
  const { t } = useTranslation();
  const [mainTab, setMainTab] = useState<MainTab>("documenti");

  return (
    <div>
      <h2 className="text-xl font-semibold text-gray-900 mb-4">{t("documents.title")}</h2>

      {/* Tab principali */}
      <div className="flex gap-1 mb-5 border-b border-gray-200">
        <button
          onClick={() => setMainTab("documenti")}
          className={`px-5 py-2.5 text-sm font-medium transition-colors -mb-px ${
            mainTab === "documenti"
              ? "border-b-2 border-primary-600 text-primary-700 bg-primary-50 rounded-t"
              : "text-gray-500 hover:text-gray-700"
          }`}
        >
          📄 {t("documents.tabs.documents")}
        </button>
        <button
          onClick={() => setMainTab("evidenze")}
          className={`px-5 py-2.5 text-sm font-medium transition-colors -mb-px ${
            mainTab === "evidenze"
              ? "border-b-2 border-green-600 text-green-700 bg-green-50 rounded-t"
              : "text-gray-500 hover:text-gray-700"
          }`}
        >
          🏆 {t("documents.tabs.evidences")}
        </button>
      </div>

      {mainTab === "documenti" && <TabDocumenti />}
      {mainTab === "evidenze" && <TabEvidenze />}
    </div>
  );
}
