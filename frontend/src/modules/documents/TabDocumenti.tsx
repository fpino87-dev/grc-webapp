import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { documentsApi, type Document } from "../../api/endpoints/documents";
import { StatusBadge } from "../../components/ui/StatusBadge";
import { useAuthStore } from "../../store/auth";
import { InlineTypeEdit } from "./documentUtils";
import { NewDocumentModal, EditDocumentModal, UploadVersionModal } from "./DocumentFormModals";
import { ChangePlantModal, ShareDocumentModal, LinkControlsModal } from "./DocumentShareModals";
import { useTranslation } from "react-i18next";
import i18n from "../../i18n";

type DocStatusFilter = "tutti" | "bozza" | "revisione" | "approvazione" | "approvato";

export function TabDocumenti() {
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

  // I contratti/NDA vivono nel tab dedicato: li escludiamo sia dalla lista
  // sia dai contatori del banner, che devono essere coerenti tra loro.
  const allDocuments: Document[] = [...(data?.results ?? [])]
    .filter(d => d.document_type !== "contratto")
    .sort((a, b) => {
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
                    <div className="flex items-center gap-1">
                      <button onClick={() => setEditDoc(doc)} title={t("documents.actions.edit")} className="text-sm w-7 h-7 flex items-center justify-center rounded hover:bg-gray-100 text-gray-500 hover:text-gray-800">✎</button>
                      {doc.status === "bozza" && <button onClick={() => submitMutation.mutate(doc.id)} title={t("documents.actions.submit_for_review")} className="text-sm w-7 h-7 flex items-center justify-center rounded hover:bg-blue-50 text-gray-500 hover:text-blue-700">▷</button>}
                      {(doc.status === "revisione" || doc.status === "approvazione") && (
                        <>
                          <button onClick={() => approveMutation.mutate(doc.id)} title={t("actions.approve")} className="text-sm w-7 h-7 flex items-center justify-center rounded hover:bg-green-50 text-gray-500 hover:text-green-700">✓</button>
                          <button onClick={() => rejectMutation.mutate(doc.id)} title={t("actions.reject")} className="text-sm w-7 h-7 flex items-center justify-center rounded hover:bg-red-50 text-gray-500 hover:text-red-600">✗</button>
                        </>
                      )}
                      <button onClick={() => setUploadDoc(doc)} title={t("documents.actions.new_version")} className="text-sm w-7 h-7 flex items-center justify-center rounded hover:bg-indigo-50 text-gray-500 hover:text-indigo-700">⬆</button>
                      <button onClick={() => setLinkControlsDoc(doc)} title={t("documents.actions.link_controls")} className="text-sm w-7 h-7 flex items-center justify-center rounded hover:bg-indigo-50 text-indigo-500 hover:text-indigo-800">⛓</button>
                      <button onClick={() => setChangePlantDoc(doc)} title={t("documents.actions.change_plant")} className="text-sm w-7 h-7 flex items-center justify-center rounded hover:bg-amber-50 text-gray-500 hover:text-amber-700">🏭</button>
                      {!doc.is_shared_with_current && (
                        <button onClick={() => setShareDoc(doc)} title={t("documents.actions.share_hint", { defaultValue: "Condividi con altri plant" })} className="text-sm w-7 h-7 flex items-center justify-center rounded hover:bg-indigo-50 text-indigo-400 hover:text-indigo-700">🔗</button>
                      )}
                      <button type="button" title={t("documents.actions.delete_title")} onClick={() => { if (!window.confirm(t("documents.actions.delete_confirm", { title: doc.title }))) return; deleteMutation.mutate(doc.id); }} disabled={deleteMutation.isPending} className="text-sm w-7 h-7 flex items-center justify-center rounded hover:bg-red-50 text-red-500 hover:text-red-700 disabled:opacity-50">🗑</button>
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
