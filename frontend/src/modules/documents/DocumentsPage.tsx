import { useEffect, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useLocation } from "react-router-dom";
import { documentsApi, type Document, type Evidence } from "../../api/endpoints/documents";
import { controlsApi, type ControlInstance } from "../../api/endpoints/controls";
import { plantsApi, type Plant } from "../../api/endpoints/plants";
import { suppliersApi, type Supplier } from "../../api/endpoints/suppliers";
import { StatusBadge } from "../../components/ui/StatusBadge";
import { useAuthStore } from "../../store/auth";
import { useTranslation } from "react-i18next";
import i18n from "../../i18n";
import { scrollAndHighlight } from "../../lib/scrollAndHighlight";

type MainTab = "documenti" | "nda" | "evidenze";

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

// ─── Inline edit tipo documento ───────────────────────────────────────────────

const DOC_TYPES = ["policy", "procedura", "manuale", "contratto", "registro", "altro"] as const;

function InlineTypeEdit({ doc }: { doc: Document }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [editing, setEditing] = useState(false);

  const mutation = useMutation({
    mutationFn: (document_type: string) => documentsApi.update(doc.id, { document_type }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["documents"] }); setEditing(false); },
  });

  if (editing) {
    return (
      <select
        autoFocus
        defaultValue={doc.document_type ?? ""}
        onChange={e => mutation.mutate(e.target.value)}
        onBlur={() => setEditing(false)}
        className="border rounded px-1 py-0.5 text-xs"
        disabled={mutation.isPending}
      >
        {DOC_TYPES.map(v => (
          <option key={v} value={v}>{t(`documents.type.${v}`)}</option>
        ))}
      </select>
    );
  }

  return (
    <button
      onClick={() => setEditing(true)}
      className="group flex items-center gap-1 text-left"
      title={t("documents.actions.change_type")}
    >
      <span className="capitalize text-xs">
        {doc.document_type
          ? t(`documents.type.${doc.document_type}`, { defaultValue: doc.document_type })
          : doc.category
          ? t(`documents.category.${doc.category}`, { defaultValue: doc.category })
          : "—"}
      </span>
      <span className="text-gray-300 group-hover:text-gray-500 text-xs">✎</span>
    </button>
  );
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
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("documents.fields.document_code")}</label>
              <input name="document_code" onChange={handleChange} placeholder="D-ITA-INF-001" className="w-full border rounded px-3 py-2 text-sm font-mono" />
            </div>
            <div className="col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("documents.fields.title")} *</label>
              <input name="title" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" />
            </div>
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

// ─── Modal condivisione documento multi-plant ─────────────────────────────────

function ShareDocumentModal({ doc, onClose }: { doc: Document; onClose: () => void }) {
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

// ─── Modal modifica documento ─────────────────────────────────────────────────

function EditDocumentModal({ doc, onClose }: { doc: Document; onClose: () => void }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [form, setForm] = useState<Partial<Document>>({
    document_code: doc.document_code || "",
    title: doc.title || "",
    document_type: doc.document_type || "",
    category: doc.category || "",
    review_due_date: doc.review_due_date || "",
    expiry_date: doc.expiry_date || "",
    is_mandatory: doc.is_mandatory,
    supplier: doc.supplier || null,
  });
  const [error, setError] = useState("");

  const isContract = form.document_type === "contratto";

  const { data: suppliersData } = useQuery({
    queryKey: ["suppliers-for-doc-edit"],
    queryFn: () => suppliersApi.list({ page_size: "200" }),
    enabled: isContract,
    retry: false,
  });
  const suppliers: Supplier[] = suppliersData?.results ?? [];

  const mutation = useMutation({
    mutationFn: (payload: Partial<Document>) => documentsApi.update(doc.id, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["documents"] });
      qc.invalidateQueries({ queryKey: ["documents-nda"] });
      onClose();
    },
    onError: (e: unknown) => {
      // @ts-expect-error axios-like error
      const msg = e?.response?.data?.detail || (e as Error).message;
      setError(msg || t("common.save_error"));
    },
  });

  function handleChange(e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) {
    const value = e.target.type === "checkbox" ? (e.target as HTMLInputElement).checked : e.target.value || null;
    setForm(prev => ({ ...prev, [e.target.name]: value }));
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-lg p-6 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">{t("documents.edit.title")}</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl w-7 h-7 flex items-center justify-center">×</button>
        </div>
        <div className="space-y-3">
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("documents.fields.document_code")}</label>
              <input
                name="document_code"
                value={form.document_code ?? ""}
                onChange={e => setForm(prev => ({ ...prev, document_code: e.target.value }))}
                placeholder="D-ITA-INF-001"
                className="w-full border rounded px-3 py-2 text-sm font-mono"
              />
            </div>
            <div className="col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("documents.fields.title")} *</label>
              <input
                name="title"
                value={form.title ?? ""}
                onChange={e => setForm(prev => ({ ...prev, title: e.target.value }))}
                className="w-full border rounded px-3 py-2 text-sm"
              />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("documents.fields.document_type")}</label>
              <select name="document_type" value={form.document_type ?? ""} onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm">
                <option value="policy">{t("documents.type.policy")}</option>
                <option value="procedura">{t("documents.type.procedura")}</option>
                <option value="manuale">{t("documents.type.manuale")}</option>
                <option value="contratto">{t("documents.type.contratto")}</option>
                <option value="registro">{t("documents.type.registro")}</option>
                <option value="altro">{t("documents.type.altro")}</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("documents.fields.category")}</label>
              <select name="category" value={form.category ?? ""} onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm">
                <option value="">{t("common.select")}</option>
                <option value="politica">{t("documents.category.politica")}</option>
                <option value="procedura">{t("documents.category.procedura")}</option>
                <option value="istruzione">{t("documents.category.istruzione")}</option>
                <option value="registro">{t("documents.category.registro")}</option>
                <option value="verbale">{t("documents.category.verbale")}</option>
                <option value="contratto">{t("documents.category.contratto")}</option>
              </select>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("documents.fields.review_due_date")}</label>
              <input type="date" name="review_due_date" value={form.review_due_date ?? ""} onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("documents.fields.expiry_date")}</label>
              <input type="date" name="expiry_date" value={form.expiry_date ?? ""} onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" />
            </div>
          </div>
          {isContract && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("documents.fields.supplier")}</label>
              <select name="supplier" value={form.supplier ?? ""} onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm">
                <option value="">{t("common.select")}</option>
                {suppliers.map(s => (
                  <option key={s.id} value={s.id}>{s.name}</option>
                ))}
              </select>
            </div>
          )}
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="edit_is_mandatory"
              name="is_mandatory"
              checked={!!form.is_mandatory}
              onChange={e => setForm(prev => ({ ...prev, is_mandatory: e.target.checked }))}
              className="rounded"
            />
            <label htmlFor="edit_is_mandatory" className="text-sm text-gray-700">{t("documents.fields.mandatory")}</label>
          </div>
        </div>
        {error && <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded mt-3">{error}</p>}
        <div className="flex justify-end gap-2 mt-4">
          <button onClick={onClose} className="px-4 py-2 border rounded text-sm text-gray-600 hover:bg-gray-50">{t("actions.cancel")}</button>
          <button
            onClick={() => {
              const payload: Partial<Document> = {
                ...form,
                review_due_date: form.review_due_date || null,
                expiry_date: form.expiry_date || null,
                supplier: form.supplier || null,
              };
              mutation.mutate(payload);
            }}
            disabled={mutation.isPending || !form.title}
            className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700 disabled:opacity-50"
          >
            {mutation.isPending ? t("common.saving") : t("documents.edit.submit")}
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

// ─── Modal collega evidenza a controlli ──────────────────────────────────────

function LinkEvidenceToControlModal({ ev, onClose }: { ev: Evidence; onClose: () => void }) {
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

// ─── Tab Documenti ────────────────────────────────────────────────────────────

type DocStatusFilter = "tutti" | "bozza" | "revisione" | "approvazione" | "approvato";

function TabDocumenti() {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const selectedPlant = useAuthStore(s => s.selectedPlant);
  const [statusFilter, setStatusFilter] = useState<DocStatusFilter>("tutti");
  const [quickFilter, setQuickFilter] = useState<"" | "mandatory_gap" | "review_overdue" | "expired">("");
  const [search, setSearch] = useState("");
  const [showNew, setShowNew] = useState(false);
  const [editDoc, setEditDoc] = useState<Document | null>(null);
  const [linkControlsDoc, setLinkControlsDoc] = useState<Document | null>(null);
  const [uploadDoc, setUploadDoc] = useState<Document | null>(null);
  const [changePlantDoc, setChangePlantDoc] = useState<Document | null>(null);
  const [shareDoc, setShareDoc] = useState<Document | null>(null);
  const [filterByPlant, setFilterByPlant] = useState(true);

  const params: Record<string, string> = { page_size: "500" };
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
  const deleteMutation = useMutation({
    mutationFn: (id: string) => documentsApi.remove(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["documents"] }),
    onError: (e: any) => window.alert(e?.response?.data?.detail || t("common.error")),
  });

  const today = new Date().toISOString().slice(0, 10);

  const allDocuments: Document[] = [...(data?.results ?? [])].sort((a, b) => {
    const ca = a.document_code || "￿";
    const cb = b.document_code || "￿";
    return ca.localeCompare(cb, undefined, { sensitivity: "base" }) ||
      (a.title ?? "").localeCompare(b.title ?? "", undefined, { sensitivity: "base" });
  });

  // Contatori per il dashboard banner
  const mandatoryGap  = allDocuments.filter(d => d.is_mandatory && d.status !== "approvato").length;
  const reviewOverdue = allDocuments.filter(d => d.review_due_date && d.review_due_date < today).length;
  const expired       = allDocuments.filter(d => d.expiry_date && d.expiry_date < today).length;

  const documents = allDocuments.filter(d => {
    if (d.document_type === "contratto") return false; // NDA/contratti nel tab dedicato
    if (search) {
      const q = search.toLowerCase();
      if (!d.title.toLowerCase().includes(q) && !d.document_code.toLowerCase().includes(q)) return false;
    }
    if (quickFilter === "mandatory_gap")  return d.is_mandatory && d.status !== "approvato";
    if (quickFilter === "review_overdue") return !!d.review_due_date && d.review_due_date < today;
    if (quickFilter === "expired")        return !!d.expiry_date && d.expiry_date < today;
    return true;
  });

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
      {/* Dashboard banner — mandatory/scaduti */}
      {!isLoading && (mandatoryGap > 0 || reviewOverdue > 0 || expired > 0) && (
        <div className="mb-4 grid grid-cols-3 gap-3">
          {mandatoryGap > 0 && (
            <button
              onClick={() => { setQuickFilter(quickFilter === "mandatory_gap" ? "" : "mandatory_gap"); setStatusFilter("tutti"); }}
              className={`flex items-center gap-3 px-4 py-3 rounded-lg border text-left transition-colors ${quickFilter === "mandatory_gap" ? "bg-red-100 border-red-400" : "bg-red-50 border-red-200 hover:bg-red-100"}`}
            >
              <span className="text-2xl">📋</span>
              <div>
                <div className="text-sm font-semibold text-red-800">{mandatoryGap} {t("documents.dashboard.mandatory_gap")}</div>
                <div className="text-xs text-red-600">{t("documents.dashboard.mandatory_gap_sub")}</div>
              </div>
            </button>
          )}
          {reviewOverdue > 0 && (
            <button
              onClick={() => { setQuickFilter(quickFilter === "review_overdue" ? "" : "review_overdue"); setStatusFilter("tutti"); }}
              className={`flex items-center gap-3 px-4 py-3 rounded-lg border text-left transition-colors ${quickFilter === "review_overdue" ? "bg-amber-100 border-amber-400" : "bg-amber-50 border-amber-200 hover:bg-amber-100"}`}
            >
              <span className="text-2xl">🔄</span>
              <div>
                <div className="text-sm font-semibold text-amber-800">{reviewOverdue} {t("documents.dashboard.review_overdue")}</div>
                <div className="text-xs text-amber-600">{t("documents.dashboard.review_overdue_sub")}</div>
              </div>
            </button>
          )}
          {expired > 0 && (
            <button
              onClick={() => { setQuickFilter(quickFilter === "expired" ? "" : "expired"); setStatusFilter("tutti"); }}
              className={`flex items-center gap-3 px-4 py-3 rounded-lg border text-left transition-colors ${quickFilter === "expired" ? "bg-orange-100 border-orange-400" : "bg-orange-50 border-orange-200 hover:bg-orange-100"}`}
            >
              <span className="text-2xl">⏰</span>
              <div>
                <div className="text-sm font-semibold text-orange-800">{expired} {t("documents.dashboard.expired")}</div>
                <div className="text-xs text-orange-600">{t("documents.dashboard.expired_sub")}</div>
              </div>
            </button>
          )}
        </div>
      )}

      <div className="flex items-center justify-between mb-3 gap-3 flex-wrap">
        <div className="flex items-center gap-1 flex-wrap">
          {STATUS_FILTERS.map(f => (
            <button key={f.value} onClick={() => { setStatusFilter(f.value); setQuickFilter(""); }}
              className={`px-3 py-1.5 rounded text-sm font-medium transition-colors ${statusFilter === f.value && !quickFilter ? "bg-primary-600 text-white" : "bg-gray-100 text-gray-600 hover:bg-gray-200"}`}>
              {f.label}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-3">
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder={t("documents.search_placeholder")}
            className="border rounded px-3 py-1.5 text-sm w-52"
          />
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
                <th className="text-left px-4 py-3 font-medium text-gray-600 w-32">{t("documents.table.code")}</th>
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
                <tr key={doc.id} data-row-id={doc.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3">
                    {doc.document_code
                      ? <span className="font-mono text-xs font-semibold text-indigo-700 bg-indigo-50 px-2 py-0.5 rounded">{doc.document_code}</span>
                      : <span className="text-gray-300">—</span>}
                  </td>
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
                    <div className="flex flex-col gap-0.5">
                      <span>{doc.plant_code || doc.plant_name || t("documents.org_wide", { defaultValue: "Org-wide" })}</span>
                      {doc.is_shared_with_current && (
                        <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded bg-indigo-50 text-indigo-600 text-xs font-medium w-fit">
                          🔗 {t("documents.shared_badge", { defaultValue: "condiviso" })}
                        </span>
                      )}
                      {!doc.is_shared_with_current && (doc.shared_plant_names?.length ?? 0) > 0 && (
                        <span className="text-gray-400 text-xs">
                          🔗 {doc.shared_plant_names!.length} {t("documents.shared_with_n_plants", { defaultValue: "plant" })}
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-gray-600">
                    <InlineTypeEdit doc={doc} />
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
                      <button
                        onClick={() => setEditDoc(doc)}
                        className="text-xs text-gray-500 hover:text-primary-700 border border-gray-300 rounded px-2 py-0.5 hover:border-primary-400"
                        title={t("documents.actions.edit")}
                      >
                        ✎ {t("documents.actions.edit")}
                      </button>
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
                      {!doc.is_shared_with_current && (
                        <button
                          onClick={() => setShareDoc(doc)}
                          title={t("documents.actions.share_hint", { defaultValue: "Condividi con altri plant" })}
                          className="text-xs text-indigo-500 hover:text-indigo-700 border border-indigo-200 rounded px-2 py-0.5 hover:border-indigo-400"
                        >
                          🔗 {t("documents.actions.share", { defaultValue: "Condividi" })}
                        </button>
                      )}
                      <button
                        type="button"
                        title={t("documents.actions.delete_title")}
                        onClick={() => {
                          if (!window.confirm(t("documents.actions.delete_confirm", { title: doc.title }))) return;
                          deleteMutation.mutate(doc.id);
                        }}
                        disabled={deleteMutation.isPending}
                        className="text-xs text-red-600 hover:text-red-800 border border-red-200 rounded px-2 py-0.5 disabled:opacity-50"
                      >
                        🗑
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
      {editDoc && <EditDocumentModal doc={editDoc} onClose={() => setEditDoc(null)} />}
      {linkControlsDoc && <LinkControlsModal doc={linkControlsDoc} onClose={() => setLinkControlsDoc(null)} />}
      {uploadDoc && <UploadVersionModal doc={uploadDoc} onClose={() => setUploadDoc(null)} />}
      {changePlantDoc && <ChangePlantModal doc={changePlantDoc} onClose={() => setChangePlantDoc(null)} />}
      {shareDoc && <ShareDocumentModal doc={shareDoc} onClose={() => setShareDoc(null)} />}
    </div>
  );
}

// ─── Tab NDA / Contratti ──────────────────────────────────────────────────────

function TabNda() {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const selectedPlant = useAuthStore(s => s.selectedPlant);
  const [filterByPlant, setFilterByPlant] = useState(true);
  const [search, setSearch] = useState("");
  const [showNew, setShowNew] = useState(false);
  const [editDoc, setEditDoc] = useState<Document | null>(null);
  const [uploadDoc, setUploadDoc] = useState<Document | null>(null);

  const params: Record<string, string> = { page_size: "500", document_type: "contratto" };
  if (filterByPlant && selectedPlant) params.plant = selectedPlant.id;

  const { data, isLoading } = useQuery({
    queryKey: ["documents-nda", filterByPlant, selectedPlant?.id],
    queryFn: () => documentsApi.list(params),
    retry: false,
  });

  const approveMutation = useMutation({
    mutationFn: (id: string) => documentsApi.approve(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["documents-nda"] }),
  });
  const deleteMutation = useMutation({
    mutationFn: (id: string) => documentsApi.remove(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["documents-nda"] }),
    onError: (e: any) => window.alert(e?.response?.data?.detail || t("common.error")),
  });

  const today = new Date().toISOString().slice(0, 10);

  const ndas: Document[] = [...(data?.results ?? [])]
    .sort((a, b) => {
      const ca = a.document_code || "￿";
      const cb = b.document_code || "￿";
      return ca.localeCompare(cb, undefined, { sensitivity: "base" }) ||
        (a.title ?? "").localeCompare(b.title ?? "", undefined, { sensitivity: "base" });
    })
    .filter(d => {
      if (!search) return true;
      const q = search.toLowerCase();
      return d.title.toLowerCase().includes(q) ||
        d.document_code.toLowerCase().includes(q) ||
        (d.supplier_name ?? "").toLowerCase().includes(q);
    });

  const expired  = ndas.filter(d => d.expiry_date && d.expiry_date < today).length;
  const expiring = ndas.filter(d => d.expiry_date && d.expiry_date >= today &&
    d.expiry_date <= new Date(Date.now() + 30 * 86400000).toISOString().slice(0, 10)).length;

  async function handleDownload(doc: Document) {
    try {
      const blob = await documentsApi.downloadDocument(doc.id);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = doc.latest_version?.file_name || `${doc.title}.pdf`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch { /* ignore */ }
  }

  function expiryCell(expiry_date: string | null) {
    if (!expiry_date) return <span className="text-gray-300">—</span>;
    const d = new Date(expiry_date + "T12:00:00").toLocaleDateString(i18n.language || "it");
    if (expiry_date < today)
      return <span className="text-xs font-semibold text-red-700 bg-red-50 px-2 py-0.5 rounded">⚠ {d}</span>;
    const diffDays = Math.floor((new Date(expiry_date).getTime() - Date.now()) / 86400000);
    if (diffDays <= 30)
      return <span className="text-xs font-semibold text-amber-700 bg-amber-50 px-2 py-0.5 rounded">⏰ {d}</span>;
    return <span className="text-xs text-gray-600">{d}</span>;
  }

  return (
    <div>
      {/* Banner scadenze */}
      {!isLoading && (expired > 0 || expiring > 0) && (
        <div className="mb-4 flex gap-3">
          {expired > 0 && (
            <div className="flex items-center gap-2 px-4 py-2 rounded-lg border bg-red-50 border-red-200 text-sm">
              <span>⚠</span>
              <span className="font-semibold text-red-800">{expired} {t("documents.nda.expired")}</span>
            </div>
          )}
          {expiring > 0 && (
            <div className="flex items-center gap-2 px-4 py-2 rounded-lg border bg-amber-50 border-amber-200 text-sm">
              <span>⏰</span>
              <span className="font-semibold text-amber-800">{expiring} {t("documents.nda.expiring")}</span>
            </div>
          )}
        </div>
      )}

      <div className="flex items-center justify-between mb-3 gap-3 flex-wrap">
        <input
          value={search}
          onChange={e => setSearch(e.target.value)}
          placeholder={t("documents.nda.search_placeholder")}
          className="border rounded px-3 py-1.5 text-sm w-64"
        />
        <div className="flex items-center gap-3">
          {selectedPlant && (
            <label className="flex items-center gap-1 text-xs text-gray-600">
              <input type="checkbox" checked={filterByPlant}
                onChange={e => setFilterByPlant(e.target.checked)} className="rounded" />
              <span>{t("documents.filter.only_selected_plant")}</span>
            </label>
          )}
          <button onClick={() => setShowNew(true)}
            className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700 shrink-0">
            + {t("documents.nda.new_btn")}
          </button>
        </div>
      </div>

      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-gray-400">{t("common.loading")}</div>
        ) : ndas.length === 0 ? (
          <div className="p-8 text-center text-gray-400">{t("documents.nda.empty")}</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-600 w-32">{t("documents.table.code")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("documents.table.title")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("documents.nda.supplier_col")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("documents.table.status")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("documents.nda.expiry_col")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("documents.table.file")}</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {ndas.map(doc => (
                <tr key={doc.id} data-row-id={doc.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3">
                    {doc.document_code
                      ? <span className="font-mono text-xs font-semibold text-indigo-700 bg-indigo-50 px-2 py-0.5 rounded">{doc.document_code}</span>
                      : <span className="text-gray-300">—</span>}
                  </td>
                  <td className="px-4 py-3 font-medium text-gray-800">{doc.title}</td>
                  <td className="px-4 py-3 text-gray-600 text-xs">
                    {doc.supplier_name
                      ? <span className="font-medium text-gray-700">{doc.supplier_name}</span>
                      : <span className="text-gray-300">—</span>}
                  </td>
                  <td className="px-4 py-3"><StatusBadge status={doc.status} /></td>
                  <td className="px-4 py-3">{expiryCell(doc.expiry_date)}</td>
                  <td className="px-4 py-3 text-xs">
                    {doc.latest_version
                      ? <button onClick={() => handleDownload(doc)} className="text-indigo-600 hover:underline">{t("documents.actions.download")}</button>
                      : <span className="text-gray-400">—</span>}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => setEditDoc(doc)}
                        className="text-xs text-gray-500 hover:text-primary-700 border border-gray-300 rounded px-2 py-0.5 hover:border-primary-400"
                        title={t("documents.actions.edit")}
                      >
                        ✎ {t("documents.actions.edit")}
                      </button>
                      {(doc.status === "revisione" || doc.status === "approvazione") && (
                        <button onClick={() => approveMutation.mutate(doc.id)}
                          className="text-xs text-gray-500 hover:text-green-700 border border-gray-300 rounded px-2 py-0.5 hover:border-green-400">
                          {t("actions.approve")}
                        </button>
                      )}
                      <button onClick={() => setUploadDoc(doc)}
                        className="text-xs text-gray-500 hover:text-indigo-700 border border-gray-300 rounded px-2 py-0.5 hover:border-indigo-400">
                        {t("documents.actions.new_version")}
                      </button>
                      <button
                        onClick={() => {
                          if (!window.confirm(t("documents.actions.delete_confirm", { title: doc.title }))) return;
                          deleteMutation.mutate(doc.id);
                        }}
                        className="text-xs text-red-600 hover:text-red-800 border border-red-200 rounded px-2 py-0.5">
                        🗑
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {showNew && <NewNdaModal onClose={() => { setShowNew(false); qc.invalidateQueries({ queryKey: ["documents-nda"] }); }} />}
      {editDoc && <EditDocumentModal doc={editDoc} onClose={() => setEditDoc(null)} />}
      {uploadDoc && <UploadVersionModal doc={uploadDoc} onClose={() => setUploadDoc(null)} />}
    </div>
  );
}

function NewNdaModal({ onClose }: { onClose: () => void }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const selectedPlant = useAuthStore(s => s.selectedPlant);
  const [form, setForm] = useState<Partial<Document>>({ document_type: "contratto", category: "contratto" });
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState("");

  const mutation = useMutation({
    mutationFn: (payload: Partial<Document>) =>
      documentsApi.create({ ...payload, plant: selectedPlant?.id ?? payload.plant ?? null }),
    onSuccess: async (doc) => {
      if (file) { try { await documentsApi.uploadVersion(doc.id, file); } catch { /* ignore */ } }
      qc.invalidateQueries({ queryKey: ["documents-nda"] });
      onClose();
    },
    onError: (e: any) => setError(e?.response?.data?.detail || t("common.save_error")),
  });

  function handleChange(e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) {
    const value = e.target.type === "checkbox" ? (e.target as HTMLInputElement).checked : e.target.value;
    setForm(prev => ({ ...prev, [e.target.name]: value }));
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-6 max-h-[90vh] overflow-y-auto">
        <h3 className="text-lg font-semibold mb-4">{t("documents.nda.new_title")}</h3>
        <div className="space-y-3">
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("documents.fields.document_code")}</label>
              <input name="document_code" onChange={handleChange} placeholder="D-ITA-NDA-001" className="w-full border rounded px-3 py-2 text-sm font-mono" />
            </div>
            <div className="col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("documents.fields.title")} *</label>
              <input name="title" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("documents.nda.expiry_col")}</label>
            <input type="date" name="expiry_date" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t("documents.table.file")}</label>
            <input type="file" onChange={e => setFile(e.target.files?.[0] ?? null)}
              accept=".pdf,.doc,.docx" className="w-full border rounded px-3 py-2 text-sm" />
          </div>
        </div>
        {error && <p className="text-red-600 text-xs mt-2">{error}</p>}
        <div className="flex justify-end gap-2 mt-4">
          <button onClick={onClose} className="px-3 py-1.5 text-sm border rounded text-gray-600 hover:bg-gray-50">{t("actions.cancel")}</button>
          <button onClick={() => mutation.mutate(form)} disabled={mutation.isPending || !form.title}
            className="px-4 py-1.5 text-sm bg-primary-600 text-white rounded hover:bg-primary-700 disabled:opacity-50">
            {mutation.isPending ? t("common.loading") : t("actions.save")}
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Tab Evidenze ─────────────────────────────────────────────────────────────

type ExpiryFilter = "tutti" | "valide" | "in_scadenza" | "scadute";

// ─── Grouped view helpers ─────────────────────────────────────────────────────

type ControlGroup = {
  groupKey: string;
  control_external_id: string;
  control_title: string;
  framework_code: string;
  evidences: Evidence[];
};

function buildEvidenceGroups(evidences: Evidence[], unassignedLabel: string): ControlGroup[] {
  const groups = new Map<string, ControlGroup>();
  const unassigned: Evidence[] = [];

  for (const ev of evidences) {
    if (!ev.linked_controls || ev.linked_controls.length === 0) {
      unassigned.push(ev);
    } else {
      for (const ctrl of ev.linked_controls) {
        if (!groups.has(ctrl.id)) {
          groups.set(ctrl.id, {
            groupKey: ctrl.id,
            control_external_id: ctrl.control_external_id,
            control_title: ctrl.control_title,
            framework_code: ctrl.framework_code,
            evidences: [],
          });
        }
        groups.get(ctrl.id)!.evidences.push(ev);
      }
    }
  }

  const sorted = Array.from(groups.values()).sort((a, b) => {
    const fw = a.framework_code.localeCompare(b.framework_code);
    if (fw !== 0) return fw;
    return a.control_external_id.localeCompare(b.control_external_id, undefined, { numeric: true, sensitivity: "base" });
  });

  if (unassigned.length > 0) {
    sorted.push({
      groupKey: "__unassigned__",
      control_external_id: "",
      control_title: unassignedLabel,
      framework_code: "",
      evidences: unassigned,
    });
  }

  return sorted;
}

function TabEvidenze() {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const selectedPlant = useAuthStore(s => s.selectedPlant);
  const [typeFilter, setTypeFilter] = useState("");
  const [expiryFilter, setExpiryFilter] = useState<ExpiryFilter>("tutti");
  const [showNew, setShowNew] = useState(false);
  const [filterByPlant, setFilterByPlant] = useState(true);
  const [linkControlsEv, setLinkControlsEv] = useState<Evidence | null>(null);
  const [groupedView, setGroupedView] = useState(false);
  const [collapsedGroups, setCollapsedGroups] = useState<Set<string>>(new Set());

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

  const params: Record<string, string> = { page_size: "500" };
  if (typeFilter) params.evidence_type = typeFilter;
  if (expiryFilter !== "tutti") params.expiry = expiryFilter;
  if (filterByPlant && selectedPlant) params.plant = selectedPlant.id;

  const { data, isLoading } = useQuery({
    queryKey: ["evidences", typeFilter, expiryFilter, filterByPlant, selectedPlant?.id],
    queryFn: () => documentsApi.evidences(params),
    retry: false,
  });

  const deleteEvidenceMutation = useMutation({
    mutationFn: (id: string) => documentsApi.removeEvidence(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["evidences"] }),
    onError: (e: any) => window.alert(e?.response?.data?.detail || t("common.error")),
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
          <button
            onClick={() => setGroupedView(v => !v)}
            className={`px-3 py-1.5 rounded text-sm font-medium border transition-colors ${groupedView ? "bg-blue-600 text-white border-blue-600" : "bg-white text-gray-600 border-gray-300 hover:bg-gray-50"}`}
          >
            📁 {groupedView ? t("documents.evidence.toggle_flat") : t("documents.evidence.toggle_grouped")}
          </button>
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

      {/* Evidence table — flat or grouped */}
      {isLoading ? (
        <div className="bg-white rounded-lg border border-gray-200 p-8 text-center text-gray-400">{t("common.loading")}</div>
      ) : evidences.length === 0 ? (
        <div className="bg-white rounded-lg border border-gray-200 p-8 text-center text-gray-400">{t("documents.evidence.empty")}</div>
      ) : groupedView ? (
        /* ── Grouped view ── */
        <div className="space-y-3">
          {buildEvidenceGroups(evidences, t("documents.evidence.group_unassigned")).map(group => {
            const isCollapsed = collapsedGroups.has(group.groupKey);
            return (
              <div key={group.groupKey} className="bg-white rounded-lg border border-gray-200 overflow-hidden">
                <button
                  onClick={() => setCollapsedGroups(prev => {
                    const next = new Set(prev);
                    if (next.has(group.groupKey)) next.delete(group.groupKey);
                    else next.add(group.groupKey);
                    return next;
                  })}
                  className="w-full flex items-center gap-3 px-4 py-3 bg-gray-50 hover:bg-gray-100 transition-colors text-left"
                >
                  <span className="text-gray-400">{isCollapsed ? "▶" : "▼"}</span>
                  {group.framework_code && (
                    <span className="text-xs px-1.5 py-0.5 rounded bg-blue-100 text-blue-700 font-medium shrink-0">{group.framework_code}</span>
                  )}
                  {group.control_external_id && (
                    <span className="text-xs font-mono text-gray-500 shrink-0">{group.control_external_id}</span>
                  )}
                  <span className="text-sm font-medium text-gray-800 flex-1 truncate">{group.control_title}</span>
                  <span className="text-xs bg-green-100 text-green-700 px-1.5 rounded shrink-0">
                    {t("documents.evidence.group_count", { count: group.evidences.length })}
                  </span>
                </button>
                {!isCollapsed && (
                  <table className="w-full text-sm">
                    <tbody className="divide-y divide-gray-100">
                      {group.evidences.map(ev => (
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
                              <button type="button" onClick={() => handleDownloadEvidence(ev)} className="mt-1 inline-flex text-xs text-indigo-600 hover:underline">
                                {t("documents.evidence.actions.download_file")}
                              </button>
                            )}
                          </td>
                          <td className="px-4 py-3 text-center"><ExpiryBadge validUntil={ev.valid_until} /></td>
                          <td className="px-4 py-3 text-gray-600 text-xs">{ev.plant_name || "—"}</td>
                          <td className="px-4 py-3 text-gray-500 text-xs">{ev.uploaded_by_username || "—"}</td>
                          <td className="px-4 py-3 text-right">
                            <div className="flex items-center justify-end gap-1.5">
                              <button onClick={() => setLinkControlsEv(ev)} className="text-xs text-indigo-600 hover:text-indigo-800 border border-indigo-200 rounded px-1.5 py-0.5 hover:border-indigo-400">
                                {t("documents.evidence.actions.link_controls")}
                              </button>
                              <button
                                type="button"
                                title={t("documents.evidence.actions.delete_title")}
                                onClick={() => { if (!window.confirm(t("documents.evidence.actions.delete_confirm", { title: ev.title }))) return; deleteEvidenceMutation.mutate(ev.id); }}
                                disabled={deleteEvidenceMutation.isPending}
                                className="text-xs text-red-600 border border-red-200 rounded px-1.5 py-0.5 hover:bg-red-50 disabled:opacity-50"
                              >🗑</button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            );
          })}
        </div>
      ) : (
        /* ── Flat view ── */
        <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("documents.evidence.table.type")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("documents.evidence.table.title")}</th>
                <th className="text-center px-4 py-3 font-medium text-gray-600">{t("documents.evidence.table.expiry")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("documents.evidence.table.plant")}</th>
                <th className="text-center px-4 py-3 font-medium text-gray-600">{t("documents.evidence.table.linked_controls")}</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">{t("documents.evidence.table.uploaded_by")}</th>
                <th className="px-4 py-3 w-10"></th>
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
                      <button type="button" onClick={() => handleDownloadEvidence(ev)} className="mt-1 inline-flex text-xs text-indigo-600 hover:underline">
                        {t("documents.evidence.actions.download_file")}
                      </button>
                    )}
                  </td>
                  <td className="px-4 py-3 text-center"><ExpiryBadge validUntil={ev.valid_until} /></td>
                  <td className="px-4 py-3 text-gray-600 text-xs">{ev.plant_name || "—"}</td>
                  <td className="px-4 py-3 text-center">
                    <span className={`inline-flex items-center justify-center w-6 h-6 rounded-full text-xs font-medium ${ev.control_instances_count > 0 ? "bg-blue-100 text-blue-700" : "bg-gray-100 text-gray-400"}`}>
                      {ev.control_instances_count}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-500 text-xs">{ev.uploaded_by_username || "—"}</td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex items-center justify-end gap-1.5">
                      <button onClick={() => setLinkControlsEv(ev)} className="text-xs text-indigo-600 hover:text-indigo-800 border border-indigo-200 rounded px-1.5 py-0.5 hover:border-indigo-400">
                        {t("documents.evidence.actions.link_controls")}
                      </button>
                      <button
                        type="button"
                        title={t("documents.evidence.actions.delete_title")}
                        onClick={() => { if (!window.confirm(t("documents.evidence.actions.delete_confirm", { title: ev.title }))) return; deleteEvidenceMutation.mutate(ev.id); }}
                        disabled={deleteEvidenceMutation.isPending}
                        className="text-xs text-red-600 border border-red-200 rounded px-1.5 py-0.5 hover:bg-red-50 disabled:opacity-50"
                      >🗑</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showNew && <NewEvidenceModal onClose={() => setShowNew(false)} />}
      {linkControlsEv && <LinkEvidenceToControlModal ev={linkControlsEv} onClose={() => setLinkControlsEv(null)} />}
    </div>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────

export function DocumentsPage() {
  const { t } = useTranslation();
  const location = useLocation();
  const [mainTab, setMainTab] = useState<MainTab>("documenti");

  // Deep-link dal GRC Assistant: forziamo tab "documenti" e scrolliamo alla riga.
  useEffect(() => {
    const state = location.state as { openDocumentId?: string } | null;
    if (state?.openDocumentId) {
      setMainTab("documenti");
      scrollAndHighlight(state.openDocumentId);
    }
  }, [location.state]);

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
          onClick={() => setMainTab("nda")}
          className={`px-5 py-2.5 text-sm font-medium transition-colors -mb-px ${
            mainTab === "nda"
              ? "border-b-2 border-amber-600 text-amber-700 bg-amber-50 rounded-t"
              : "text-gray-500 hover:text-gray-700"
          }`}
        >
          📝 {t("documents.tabs.nda")}
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
      {mainTab === "nda" && <TabNda />}
      {mainTab === "evidenze" && <TabEvidenze />}
    </div>
  );
}
