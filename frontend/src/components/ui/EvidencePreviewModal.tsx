import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { documentsApi } from "../../api/endpoints/documents";
import i18n from "../../i18n";

/**
 * Anteprima in-app di un'evidenza (M07) senza doverla scaricare.
 *
 * Il file arriva come blob autenticato via `documentsApi.downloadEvidence`
 * (l'endpoint richiede JWT, quindi non è indirizzabile da <img src>/<iframe src>).
 *
 * SICUREZZA: il blob restituito dal server viene sempre ricostruito con un MIME
 * type derivato dall'estensione in whitelist, mai con quello dichiarato dalla
 * risposta. Così un file HTML/SVG caricato con estensione .pdf viene renderizzato
 * come PDF corrotto e non può eseguire script nell'origine dell'app.
 */

export interface PreviewableEvidence {
  id: string;
  title: string;
  valid_until?: string | null;
  file_name?: string | null;
  file_path?: string | null;
}

const PREVIEW_MIME: Record<string, string> = {
  pdf: "application/pdf",
  png: "image/png",
  jpg: "image/jpeg",
  jpeg: "image/jpeg",
  txt: "text/plain",
  csv: "text/csv",
};

const MAX_TEXT_PREVIEW_CHARS = 200_000;

export function evidenceFileName(ev: PreviewableEvidence): string {
  const raw = ev.file_name || (ev.file_path ? ev.file_path.split("/").pop() : "");
  return raw || ev.title || "evidenza";
}

function evidenceExtension(ev: PreviewableEvidence): string {
  const name = evidenceFileName(ev);
  const idx = name.lastIndexOf(".");
  return idx > -1 ? name.slice(idx + 1).toLowerCase() : "";
}

/** True se il browser sa mostrare il file senza convertitori server-side. */
export function canPreviewEvidence(ev: PreviewableEvidence): boolean {
  return evidenceExtension(ev) in PREVIEW_MIME;
}

/** Scarica il file dell'evidenza mantenendo il nome originale. */
export async function downloadEvidenceFile(ev: PreviewableEvidence): Promise<void> {
  const blob = await documentsApi.downloadEvidence(ev.id);
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = evidenceFileName(ev);
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(url);
}

type PreviewKind = "pdf" | "image" | "text";

export function EvidencePreviewModal({
  evidence,
  onClose,
}: {
  evidence: PreviewableEvidence;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const [textContent, setTextContent] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [downloading, setDownloading] = useState(false);

  const ext = evidenceExtension(evidence);
  const mime = PREVIEW_MIME[ext];
  const kind: PreviewKind | null =
    mime === "application/pdf" ? "pdf" : mime?.startsWith("image/") ? "image" : mime ? "text" : null;

  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onClose]);

  useEffect(() => {
    if (!kind) return;
    let objectUrl: string | null = null;
    let cancelled = false;

    documentsApi
      .downloadEvidence(evidence.id)
      .then(async raw => {
        if (cancelled) return;
        const safe = new Blob([raw], { type: mime });
        if (kind === "text") {
          const text = await safe.text();
          if (!cancelled) setTextContent(text.slice(0, MAX_TEXT_PREVIEW_CHARS));
        } else {
          objectUrl = URL.createObjectURL(safe);
          if (!cancelled) setBlobUrl(objectUrl);
        }
      })
      .catch(() => { if (!cancelled) setError(t("documents.errors.evidence_download_failed")); });

    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [evidence.id, kind, mime, t]);

  async function handleDownload() {
    setDownloading(true);
    try {
      await downloadEvidenceFile(evidence);
    } catch {
      setError(t("documents.errors.evidence_download_failed"));
    } finally {
      setDownloading(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-lg shadow-xl w-full max-w-4xl h-[85vh] flex flex-col overflow-hidden"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-start gap-3 px-4 py-3 border-b border-gray-200">
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold text-gray-800 truncate">{evidence.title}</p>
            <div className="flex items-center gap-2 mt-0.5 flex-wrap">
              <span className="text-xs text-gray-400 truncate">{evidenceFileName(evidence)}</span>
              {evidence.valid_until && (
                <span className="text-xs text-gray-500">
                  {t("controls.drawer.expiry.valid_until", {
                    date: new Date(evidence.valid_until).toLocaleDateString(i18n.language || "it"),
                  })}
                </span>
              )}
            </div>
          </div>
          <button
            type="button"
            onClick={handleDownload}
            disabled={downloading}
            className="text-xs border border-indigo-200 text-indigo-600 rounded px-2 py-1 hover:bg-indigo-50 disabled:opacity-50 shrink-0"
          >
            ⬇ {t("documents.evidence.actions.download_file")}
          </button>
          <button
            type="button"
            onClick={onClose}
            title={t("common.close")}
            className="text-gray-400 hover:text-gray-600 text-lg leading-none shrink-0"
          >
            ✕
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 min-h-0 bg-gray-50">
          {error ? (
            <p className="p-4 text-sm text-red-600">{error}</p>
          ) : !kind ? (
            <div className="p-6 text-center">
              <p className="text-sm text-gray-600">{t("documents.evidence.actions.preview_unsupported")}</p>
            </div>
          ) : kind === "text" ? (
            textContent === null ? (
              <p className="p-4 text-sm text-gray-400">{t("common.loading")}</p>
            ) : (
              <pre className="p-4 text-xs text-gray-800 whitespace-pre-wrap break-words h-full overflow-auto">
                {textContent}
              </pre>
            )
          ) : !blobUrl ? (
            <p className="p-4 text-sm text-gray-400">{t("common.loading")}</p>
          ) : kind === "image" ? (
            <div className="h-full overflow-auto flex items-center justify-center p-4">
              <img src={blobUrl} alt={evidence.title} className="max-w-full" />
            </div>
          ) : (
            <iframe src={blobUrl} title={evidence.title} className="w-full h-full border-0" />
          )}
        </div>
      </div>
    </div>
  );
}
