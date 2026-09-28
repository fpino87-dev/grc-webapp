import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { bcpApi, type BcpTest, type BcpTestEvidence } from "../../api/endpoints/bcp";
import {
  EvidencePreviewModal, canPreviewEvidence, downloadEvidenceFile,
} from "../../components/ui/EvidencePreviewModal";
import { BcpEvidencePicker } from "./BcpEvidencePicker";
import { fmtDate } from "./shared";

/** Evidenze di un test registrato: consultazione e aggiunta (non rimozione:
 *  esito e prove del test restano quelli registrati). */
export function BcpTestEvidences({ test, onClose }: { test: BcpTest; onClose: () => void }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [items, setItems] = useState<BcpTestEvidence[]>(test.evidence_items ?? []);
  const [adding, setAdding] = useState(items.length === 0);
  const [file, setFile] = useState<File | null>(null);
  const [ids, setIds] = useState<string[]>([]);
  const [preview, setPreview] = useState<BcpTestEvidence | null>(null);
  const [downloadError, setDownloadError] = useState(false);

  const mutation = useMutation({
    mutationFn: () => bcpApi.addTestEvidences(test.id, { evidenceIds: ids, file }),
    onSuccess: (updated) => {
      setItems(updated.evidence_items);
      setFile(null);
      setIds([]);
      setAdding(false);
      qc.invalidateQueries({ queryKey: ["bcp"] });
    },
  });
  const errorDetail = (mutation.error as { response?: { data?: { detail?: string } } } | null)?.response?.data?.detail;

  async function download(ev: BcpTestEvidence) {
    setDownloadError(false);
    try {
      await downloadEvidenceFile(ev);
    } catch {
      setDownloadError(true);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-lg p-6 max-h-screen overflow-y-auto">
        <h3 className="text-lg font-semibold mb-1">{t("bcp.evidence.title")}</h3>
        <p className="text-sm text-gray-500 mb-4">{test.plan_title} · {fmtDate(test.test_date)}</p>

        {items.length === 0 ? (
          <p className="text-sm text-amber-700 mb-3">{t("bcp.evidence.missing")}</p>
        ) : (
          <ul className="divide-y divide-gray-100 border rounded mb-3">
            {items.map(ev => (
              <li key={ev.id} className="flex items-center gap-2 px-3 py-2 text-sm">
                <span className="flex-1 truncate text-gray-800" title={ev.title}>{ev.title}</span>
                {ev.valid_until && (
                  <span className="text-[11px] text-gray-400 whitespace-nowrap">
                    {t("bcp.evidence.valid_until", { date: fmtDate(ev.valid_until) })}
                  </span>
                )}
                {ev.file_name && canPreviewEvidence(ev) && (
                  <button onClick={() => setPreview(ev)} className="text-xs text-primary-700 hover:underline">{t("bcp.evidence.preview")}</button>
                )}
                {ev.file_name && (
                  <button onClick={() => download(ev)} className="text-xs text-primary-700 hover:underline">{t("bcp.evidence.download")}</button>
                )}
              </li>
            ))}
          </ul>
        )}
        {downloadError && <p className="text-xs text-red-600 mb-2">{t("bcp.evidence.download_error")}</p>}

        {adding ? (
          <div className="border-t pt-3">
            <BcpEvidencePicker
              plantId={test.plant}
              file={file}
              onFileChange={setFile}
              selectedIds={ids}
              onSelectedChange={setIds}
              excludeIds={items.map(e => e.id)}
            />
            {mutation.isError && <p className="text-sm text-red-600 mt-2">{errorDetail ?? t("bcp.form.save_error")}</p>}
          </div>
        ) : (
          <button onClick={() => setAdding(true)} className="text-sm text-primary-700 hover:underline">
            {t("bcp.evidence.add")}
          </button>
        )}

        <div className="flex justify-end gap-2 mt-4">
          <button onClick={onClose} className="px-4 py-2 border rounded text-sm text-gray-600 hover:bg-gray-50">{t("bcp.actions.close")}</button>
          {adding && (
            <button
              onClick={() => mutation.mutate()}
              disabled={mutation.isPending || (!file && ids.length === 0)}
              className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700 disabled:opacity-50"
            >
              {mutation.isPending ? t("bcp.actions.saving") : t("bcp.evidence.attach")}
            </button>
          )}
        </div>
      </div>
      {preview && <EvidencePreviewModal evidence={preview} onClose={() => setPreview(null)} />}
    </div>
  );
}
