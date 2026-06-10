import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { documentsApi, type Document } from "../../api/endpoints/documents";
import { StatusBadge } from "../../components/ui/StatusBadge";
import { useAuthStore } from "../../store/auth";
import { EditDocumentModal, UploadVersionModal } from "./DocumentFormModals";
import { useTranslation } from "react-i18next";
import i18n from "../../i18n";
import { addDaysISO, usePlantToday } from "../../utils/dates";

export function TabNda() {
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

  const today = usePlantToday();

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
    d.expiry_date <= addDaysISO(today, 30)).length;

  async function handleDownload(doc: Document) {
    try {
      const blob = await documentsApi.downloadDocument(doc.id);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = doc.latest_version?.file_name || `${doc.title}.pdf`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch {
      alert(t("documents.errors.download_failed"));
    }
  }

  function expiryCell(expiry_date: string | null) {
    if (!expiry_date) return <span className="text-gray-300">—</span>;
    const d = new Date(expiry_date + "T12:00:00").toLocaleDateString(i18n.language || "it");
    if (expiry_date < today)
      return <span className="text-xs font-semibold text-red-700 bg-red-50 px-2 py-0.5 rounded">⚠ {d}</span>;
    if (expiry_date <= addDaysISO(today, 30))
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
                    <div className="flex items-center gap-1">
                      <button onClick={() => setEditDoc(doc)} title={t("documents.actions.edit")} className="text-sm w-7 h-7 flex items-center justify-center rounded hover:bg-gray-100 text-gray-500 hover:text-gray-800">✎</button>
                      {(doc.status === "revisione" || doc.status === "approvazione") && (
                        <button onClick={() => approveMutation.mutate(doc.id)} title={t("actions.approve")} className="text-sm w-7 h-7 flex items-center justify-center rounded hover:bg-green-50 text-gray-500 hover:text-green-700">✓</button>
                      )}
                      <button onClick={() => setUploadDoc(doc)} title={t("documents.actions.new_version")} className="text-sm w-7 h-7 flex items-center justify-center rounded hover:bg-indigo-50 text-gray-500 hover:text-indigo-700">⬆</button>
                      <button onClick={() => { if (!window.confirm(t("documents.actions.delete_confirm", { title: doc.title }))) return; deleteMutation.mutate(doc.id); }} title={t("documents.actions.delete_title")} className="text-sm w-7 h-7 flex items-center justify-center rounded hover:bg-red-50 text-red-500 hover:text-red-700">🗑</button>
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
      if (file) {
        try {
          await documentsApi.uploadVersion(doc.id, file);
        } catch {
          // il documento esiste già: avvisiamo che il file non è stato caricato
          window.alert(t("documents.errors.version_upload_after_create"));
        }
      }
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
