import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { documentsApi, type Document } from "../../api/endpoints/documents";
import { suppliersApi, type Supplier } from "../../api/endpoints/suppliers";
import { useAuthStore } from "../../store/auth";
import { useTranslation } from "react-i18next";

// ─── Modal nuovo documento ──────────────────────────────────────────────────

export function NewDocumentModal({ onClose }: { onClose: () => void }) {
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
          // il documento esiste già: avvisiamo che il file non è stato caricato
          window.alert(t("documents.errors.version_upload_after_create"));
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

// ─── Modal upload nuova versione documento ──────────────────────────────────

export function UploadVersionModal({ doc, onClose }: { doc: Document; onClose: () => void }) {
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

// ─── Modal modifica documento ───────────────────────────────────────────────

export function EditDocumentModal({ doc, onClose }: { doc: Document; onClose: () => void }) {
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
