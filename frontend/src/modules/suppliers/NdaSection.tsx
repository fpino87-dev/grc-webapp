import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { suppliersApi, type NdaDocument } from "../../api/endpoints/suppliers";
import { apiClient } from "../../api/client";
import { NdaDocStatusBadge } from "./supplierBadges";
import { useTranslation } from "react-i18next";

export function NdaSection({ supplierId }: { supplierId: string }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [showUpload, setShowUpload] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [uploadTitle, setUploadTitle] = useState("");
  const [uploadExpiry, setUploadExpiry] = useState("");
  const [uploadNotes, setUploadNotes] = useState("");
  const [uploadError, setUploadError] = useState("");

  const { data, isLoading } = useQuery({
    queryKey: ["supplier-nda", supplierId],
    queryFn: () => suppliersApi.ndaList(supplierId),
  });
  const docs: NdaDocument[] = data?.results ?? [];

  const deleteMutation = useMutation({
    mutationFn: (id: string) => apiClient.delete(`/documents/documents/${id}/`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["supplier-nda", supplierId] }),
  });

  const approveMutation = useMutation({
    mutationFn: (id: string) => apiClient.patch(`/documents/documents/${id}/`, { status: "approvato" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["supplier-nda", supplierId] }),
  });

  async function downloadNda(docId: string, fileName: string) {
    const res = await apiClient.get(`/documents/documents/${docId}/download-latest/`, { responseType: "blob" });
    const url = URL.createObjectURL(res.data);
    const a = document.createElement("a");
    a.href = url;
    a.download = fileName;
    a.click();
    URL.revokeObjectURL(url);
  }

  const uploadMutation = useMutation({
    mutationFn: () => {
      const fd = new FormData();
      fd.append("file", file as File);
      fd.append("title", uploadTitle);
      if (uploadExpiry) fd.append("expiry_date", uploadExpiry);
      if (uploadNotes) fd.append("notes", uploadNotes);
      return suppliersApi.ndaUpload(supplierId, fd);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["supplier-nda", supplierId] });
      qc.invalidateQueries({ queryKey: ["kpi-overview"] });
      setShowUpload(false);
      setFile(null);
      setUploadTitle("");
      setUploadExpiry("");
      setUploadNotes("");
      setUploadError("");
    },
    onError: (e: any) => setUploadError(e?.response?.data?.error || t("suppliers.ndasec.error_upload")),
  });

  return (
    <div className="px-4 pb-4 pt-2">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">{t("suppliers.ndasec.section_title")}</span>
        {!showUpload && (
          <button
            onClick={() => setShowUpload(true)}
            className="text-xs text-indigo-600 border border-indigo-200 rounded px-2 py-0.5 hover:bg-indigo-50"
          >
            {t("suppliers.ndasec.upload_btn")}
          </button>
        )}
      </div>

      {showUpload && (
        <div className="mb-4 p-3 bg-indigo-50 rounded border border-indigo-100 space-y-2">
          <p className="text-xs font-medium text-indigo-800">{t("suppliers.ndasec.modal_title")}</p>
          <div>
            <label className="block text-xs text-gray-600 mb-0.5">{t("suppliers.ndasec.file_label")}</label>
            <input
              type="file"
              accept=".pdf,.doc,.docx"
              onChange={e => setFile(e.target.files?.[0] ?? null)}
              className="text-xs w-full"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-600 mb-0.5">{t("suppliers.ndasec.title_label")}</label>
            <input
              type="text"
              value={uploadTitle}
              onChange={e => setUploadTitle(e.target.value)}
              placeholder={t("suppliers.ndasec.title_placeholder")}
              className="w-full border rounded px-2 py-1 text-xs"
            />
          </div>
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="block text-xs text-gray-600 mb-0.5">{t("suppliers.ndasec.expiry_label")}</label>
              <input
                type="date"
                value={uploadExpiry}
                onChange={e => setUploadExpiry(e.target.value)}
                className="w-full border rounded px-2 py-1 text-xs"
              />
            </div>
            <div>
              <label className="block text-xs text-gray-600 mb-0.5">{t("suppliers.ndasec.notes_label")}</label>
              <input
                type="text"
                value={uploadNotes}
                onChange={e => setUploadNotes(e.target.value)}
                className="w-full border rounded px-2 py-1 text-xs"
              />
            </div>
          </div>
          {uploadError && <p className="text-xs text-red-600">{uploadError}</p>}
          <div className="flex gap-2">
            <button
              onClick={() => uploadMutation.mutate()}
              disabled={uploadMutation.isPending || !file || !uploadTitle.trim()}
              className="text-xs bg-indigo-600 text-white rounded px-3 py-1.5 disabled:opacity-50"
            >
              {uploadMutation.isPending ? t("suppliers.ndasec.uploading") : t("suppliers.ndasec.submit")}
            </button>
            <button
              onClick={() => { setShowUpload(false); setFile(null); setUploadTitle(""); setUploadExpiry(""); setUploadNotes(""); setUploadError(""); }}
              className="text-xs text-gray-500 hover:text-gray-700"
            >
              {t("actions.cancel")}
            </button>
          </div>
        </div>
      )}

      {isLoading ? (
        <p className="text-xs text-gray-400">{t("common.loading")}</p>
      ) : docs.length === 0 ? (
        <p className="text-xs text-gray-400 italic">{t("suppliers.ndasec.none")}</p>
      ) : (
        <table className="w-full text-xs">
          <thead>
            <tr className="text-gray-500 border-b">
              <th className="text-left py-1 pr-3">{t("suppliers.ndasec.col_title")}</th>
              <th className="text-left py-1 pr-3">{t("suppliers.ndasec.col_status")}</th>
              <th className="text-left py-1 pr-3">{t("suppliers.ndasec.col_expiry")}</th>
              <th className="text-left py-1 pr-3">{t("suppliers.ndasec.col_file")}</th>
              <th className="py-1 pr-3 text-center">{t("suppliers.ndasec.col_version")}</th>
              <th className="py-1"></th>
            </tr>
          </thead>
          <tbody>
            {docs.map(doc => (
              <tr key={doc.id} className="border-b border-gray-50">
                <td className="py-1.5 pr-3 font-medium text-gray-800">{doc.title}</td>
                <td className="py-1.5 pr-3"><NdaDocStatusBadge status={doc.status} /></td>
                <td className="py-1.5 pr-3 text-gray-500">
                  {doc.expiry_date
                    ? (() => {
                        const d = new Date(doc.expiry_date);
                        const daysLeft = Math.ceil((d.getTime() - Date.now()) / 86400000);
                        const cls = daysLeft < 0 ? "text-red-600 font-medium" : daysLeft <= 30 ? "text-red-500" : daysLeft <= 90 ? "text-orange-500" : "text-gray-600";
                        return <span className={cls}>{doc.expiry_date}{daysLeft <= 90 && <span className="ml-1">({daysLeft}gg)</span>}</span>;
                      })()
                    : "—"
                  }
                </td>
                <td className="py-1.5 pr-3 text-gray-500">
                  {doc.latest_version ? doc.latest_version.file_name : <span className="text-gray-300">—</span>}
                </td>
                <td className="py-1.5 pr-3 text-center text-gray-500">
                  {doc.latest_version ? `v${doc.latest_version.version_number}` : "—"}
                </td>
                <td className="py-1.5 whitespace-nowrap space-x-2">
                  {doc.status !== "approvato" && (
                    <button
                      onClick={() => approveMutation.mutate(doc.id)}
                      disabled={approveMutation.isPending}
                      className="text-green-600 hover:underline disabled:opacity-40"
                      title={t("suppliers.ndasec.approve_title")}
                    >
                      {t("actions.approve")}
                    </button>
                  )}
                  {doc.latest_version && (
                    <button
                      onClick={() => downloadNda(doc.id, doc.latest_version!.file_name)}
                      className="text-indigo-600 hover:underline"
                      title={t("documents.actions.download")}
                    >
                      {t("suppliers.ndasec.download")}
                    </button>
                  )}
                  <button
                    onClick={() => { if (window.confirm(t("suppliers.ndasec.delete_confirm", { title: doc.title }))) deleteMutation.mutate(doc.id); }}
                    disabled={deleteMutation.isPending}
                    className="text-red-400 hover:text-red-600 disabled:opacity-40"
                    title={t("actions.delete")}
                  >
                    ✕
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
