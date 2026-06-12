import { useState, useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { controlsApi, type EvidenceRef, type LinkedDocument, type RequirementsCheck, type EvidenceRequirement } from "../../../api/endpoints/controls";
import { documentsApi } from "../../../api/endpoints/documents";
import { useAuthStore } from "../../../store/auth";
import { addYearsISO, usePlantToday } from "../../../utils/dates";
import i18n from "../../../i18n";
import { evidenceIcon, docStatusColor, ExpiryBadge, useDebounce } from "./shared";

function DocsColumn({
  instanceId,
  documents,
  requirements,
  plant,
}: {
  instanceId: string;
  documents: LinkedDocument[];
  requirements: RequirementsCheck;
  plant: string | null;
}) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [searchQ, setSearchQ] = useState("");
  const debounced = useDebounce(searchQ);

  function requirementLabel(type: string, description?: string) {
    if (type === "any") return description || "";
    return t(`documents.type.${type}`, { defaultValue: description || type });
  }

  const { data: searchResults } = useQuery({
    queryKey: ["doc-search", debounced, plant],
    queryFn: () => documentsApi.searchDocuments(debounced, plant ?? undefined),
    enabled: debounced.length > 2,
  });

  const unlinkMut = useMutation({
    mutationFn: (docId: string) => controlsApi.unlinkDocument(instanceId, docId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["control-detail", instanceId] }),
  });
  const linkMut = useMutation({
    mutationFn: (docId: string) => controlsApi.linkDocument(instanceId, docId),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["control-detail", instanceId] }); setSearchQ(""); },
  });

  const linkedIds = new Set(documents.map(d => d.id));

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 mb-1">
        <span className="text-base">📄</span>
        <span className="text-xs font-semibold text-gray-700 uppercase tracking-wide">{t("controls.drawer.docs.policy_docs")}</span>
        <span className="ml-auto text-xs bg-gray-100 text-gray-600 px-1.5 rounded">{documents.length}</span>
      </div>

      {/* Requisiti mancanti */}
      {requirements.missing_documents.length > 0 && (
        <div className="space-y-1">
          {requirements.missing_documents.map((m, i) => (
            <div key={i} className="flex items-center gap-1.5 text-xs bg-red-50 border border-red-200 rounded px-2 py-1">
              <span className="text-red-500 font-bold shrink-0">!</span>
              <span className="text-red-700">{requirementLabel(m.type, m.description)}</span>
              <span className="ml-auto text-xs text-red-500 font-medium shrink-0">{t("controls.drawer.docs.missing")}</span>
            </div>
          ))}
        </div>
      )}

      {/* Lista documenti collegati */}
      {documents.length === 0 ? (
        <p className="text-xs text-gray-400 italic">{t("controls.drawer.docs.none_linked")}</p>
      ) : (
        <div className="space-y-1.5">
          {documents.map(d => (
            <div key={d.id} className="bg-white border border-gray-200 rounded px-2.5 py-2">
              <div className="flex items-start justify-between gap-1">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-1.5 flex-wrap">
                    {d.document_code && (
                      <span className="font-mono text-xs font-semibold text-indigo-700 bg-indigo-50 px-1.5 py-0.5 rounded shrink-0">{d.document_code}</span>
                    )}
                    <p className="text-xs font-medium text-gray-800 truncate">{d.title}</p>
                  </div>
                  <div className="flex items-center gap-1 mt-0.5 flex-wrap">
                    <span className="text-xs bg-indigo-50 text-indigo-700 px-1 rounded">
                      {t(`documents.type.${d.document_type}`, { defaultValue: d.document_type })}
                    </span>
                    <span className={`text-xs px-1 rounded ${docStatusColor(d.status)}`}>
                      {t(`status.${d.status}`, { defaultValue: d.status })}
                    </span>
                    {d.review_due_date && (
                      <span className="text-xs text-gray-400">
                        {t("controls.drawer.docs.review_abbrev")} {new Date(d.review_due_date).toLocaleDateString(i18n.language || "it")}
                      </span>
                    )}
                  </div>
                </div>
                <button
                  onClick={() => unlinkMut.mutate(d.id)}
                  disabled={unlinkMut.isPending}
                  className="text-red-400 hover:text-red-600 text-xs shrink-0 ml-1"
                  title={t("controls.drawer.docs.unlink")}
                >
                  ✕
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Collega documento */}
      <div className="border border-dashed border-gray-300 rounded p-2 space-y-1.5">
        <p className="text-xs font-medium text-gray-500">{t("controls.drawer.docs.link_doc")}</p>
        <input
          type="text"
          value={searchQ}
          onChange={e => setSearchQ(e.target.value)}
          placeholder={t("controls.drawer.docs.search_placeholder")}
          className="w-full border rounded px-2 py-1 text-xs"
        />
        {searchResults && searchResults.results.length > 0 && (
          <div className="border rounded divide-y divide-gray-100 max-h-32 overflow-y-auto bg-white">
            {searchResults.results.filter(d => !linkedIds.has(d.id)).slice(0, 8).map(d => (
              <button
                key={d.id}
                onClick={() => linkMut.mutate(d.id)}
                disabled={linkMut.isPending}
                className="w-full text-left px-2 py-1.5 text-xs hover:bg-blue-50 text-gray-700 flex items-center gap-1.5"
              >
                <span className="text-gray-400">📄</span>
                {d.document_code && (
                  <span className="font-mono text-xs font-semibold text-indigo-700 shrink-0">{d.document_code}</span>
                )}
                <span className="truncate flex-1">{d.title}</span>
                <span className={`shrink-0 px-1 rounded text-xs ${docStatusColor(d.status)}`}>
                  {t(`status.${d.status}`, { defaultValue: d.status })}
                </span>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Dropzone multi-file upload ───────────────────────────────────────────────

type UploadItem = {
  id: string;
  file: File;
  title: string;
  evidence_type: string;
  valid_until: string;
};

function DropzoneUpload({ instanceId, plant }: { instanceId: string; plant: string | null }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [queue, setQueue] = useState<UploadItem[]>([]);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState({ current: 0, total: 0 });

  const oneYearOut = addYearsISO(usePlantToday(), 1);

  function addFiles(files: FileList | File[]) {
    const items: UploadItem[] = Array.from(files).map(file => ({
      id: `${Date.now()}-${Math.random()}`,
      file,
      title: file.name.replace(/\.[^/.]+$/, ""),
      evidence_type: "altro",
      valid_until: oneYearOut,
    }));
    setQueue(prev => [...prev, ...items]);
  }

  function removeItem(id: string) {
    setQueue(prev => prev.filter(i => i.id !== id));
  }

  function updateItem(id: string, field: keyof UploadItem, value: string) {
    setQueue(prev => prev.map(i => i.id === id ? { ...i, [field]: value } : i));
  }

  async function uploadAll() {
    if (!queue.length) return;
    setUploading(true);
    setProgress({ current: 0, total: queue.length });
    for (let i = 0; i < queue.length; i++) {
      const item = queue[i];
      try {
        const ev = await documentsApi.createEvidence({
          file: item.file,
          title: item.title,
          evidence_type: item.evidence_type,
          valid_until: item.valid_until,
          plant: plant ?? undefined,
        });
        await controlsApi.linkEvidence(instanceId, ev.id);
      } catch {
        // continue with next file on error
      }
      setProgress({ current: i + 1, total: queue.length });
    }
    setQueue([]);
    setUploading(false);
    qc.invalidateQueries({ queryKey: ["control-detail", instanceId] });
    qc.invalidateQueries({ queryKey: ["evidences"] });
  }

  const canUpload = queue.length > 0 && queue.every(i => i.title && i.valid_until) && !uploading;

  const EVIDENCE_TYPES_LIST = ["screenshot", "log", "report", "verbale", "certificato", "test_result", "altro"] as const;

  return (
    <div className="space-y-2">
      <div
        className={`border-2 border-dashed rounded-lg p-3 text-center cursor-pointer transition-colors ${isDragging ? "border-green-400 bg-green-50" : "border-gray-300 hover:border-gray-400 hover:bg-gray-50"}`}
        onDragOver={e => { e.preventDefault(); setIsDragging(true); }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={e => { e.preventDefault(); setIsDragging(false); addFiles(e.dataTransfer.files); }}
        onClick={() => fileInputRef.current?.click()}
      >
        <div className="text-xl mb-0.5">📎</div>
        <p className="text-xs text-gray-600 font-medium">{t("controls.drawer.docs.dropzone_hint")}</p>
        <p className="text-xs text-gray-400">{t("controls.drawer.docs.dropzone_or_browse")}</p>
        <p className="text-xs text-gray-300 mt-0.5">PDF · XLS · DOCX · PNG · JPG — max 50 MB</p>
        <input ref={fileInputRef} type="file" multiple className="hidden" onChange={e => e.target.files && addFiles(e.target.files)} />
      </div>

      {queue.length > 0 && (
        <div className="space-y-1.5">
          <p className="text-xs font-medium text-gray-600">{t("controls.drawer.docs.upload_queue_title", { count: queue.length })}</p>
          {queue.map(item => (
            <div key={item.id} className="border rounded p-1.5 bg-gray-50 space-y-1">
              <div className="flex items-center gap-1">
                <span className="text-xs text-gray-400 shrink-0">📎</span>
                <input
                  value={item.title}
                  onChange={e => updateItem(item.id, "title", e.target.value)}
                  className="flex-1 border rounded px-1.5 py-0.5 text-xs min-w-0"
                />
                <button onClick={() => removeItem(item.id)} className="text-red-400 hover:text-red-600 text-xs shrink-0 ml-1">✕</button>
              </div>
              <div className="flex gap-1">
                <select
                  value={item.evidence_type}
                  onChange={e => updateItem(item.id, "evidence_type", e.target.value)}
                  className="border rounded px-1 py-0.5 text-xs flex-1"
                >
                  {EVIDENCE_TYPES_LIST.map(v => (
                    <option key={v} value={v}>{evidenceIcon(v)} {t(`documents.evidence.types.${v}`)}</option>
                  ))}
                </select>
                <input
                  type="date"
                  value={item.valid_until}
                  onChange={e => updateItem(item.id, "valid_until", e.target.value)}
                  className="border rounded px-1 py-0.5 text-xs"
                />
              </div>
            </div>
          ))}
          <button
            onClick={uploadAll}
            disabled={!canUpload}
            className="w-full py-1.5 bg-green-600 text-white text-xs rounded hover:bg-green-700 disabled:opacity-50 font-medium"
          >
            {uploading
              ? t("controls.drawer.docs.uploading_progress", { current: progress.current, total: progress.total })
              : t("controls.drawer.docs.upload_all_link", { count: queue.length })}
          </button>
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────

function EvidencesColumn({
  instanceId,
  evidences,
  requirements,
  plant,
}: {
  instanceId: string;
  evidences: EvidenceRef[];
  requirements: RequirementsCheck;
  plant: string | null;
}) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [searchQ, setSearchQ] = useState("");
  const debounced = useDebounce(searchQ);

  function requirementLabel(type: string, description?: string) {
    if (type === "any") return description || "";
    return t(`documents.evidence.types.${type}`, { defaultValue: description || type });
  }

  const { data: searchResults } = useQuery({
    queryKey: ["ev-search", debounced],
    queryFn: () => documentsApi.searchEvidences(debounced),
    enabled: debounced.length > 2,
  });

  const unlinkMut = useMutation({
    mutationFn: (evId: string) => controlsApi.unlinkEvidence(instanceId, evId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["control-detail", instanceId] }),
  });
  const linkMut = useMutation({
    mutationFn: (evId: string) => controlsApi.linkEvidence(instanceId, evId),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["control-detail", instanceId] }); setSearchQ(""); },
  });

  const linkedEvIds = new Set(evidences.map(e => e.id));

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 mb-1">
        <span className="text-base">🔬</span>
        <span className="text-xs font-semibold text-gray-700 uppercase tracking-wide">{t("controls.drawer.docs.operational_evidence")}</span>
        <span className="ml-auto text-xs bg-gray-100 text-gray-600 px-1.5 rounded">{evidences.length}</span>
      </div>

      {/* Requisiti mancanti */}
      {requirements.missing_evidences.length > 0 && (
        <div className="space-y-1">
          {requirements.missing_evidences.map((m, i) => (
            <div key={i} className="flex items-center gap-1.5 text-xs bg-red-50 border border-red-200 rounded px-2 py-1">
              <span className="text-red-500 font-bold shrink-0">!</span>
              <span className="text-red-700">{requirementLabel(m.type, m.description)}</span>
              <span className="ml-auto text-xs text-red-500 font-medium shrink-0">{t("controls.drawer.docs.missing")}</span>
            </div>
          ))}
        </div>
      )}

      {/* Lista evidenze collegate */}
      {evidences.length === 0 ? (
        <p className="text-xs text-gray-400 italic">{t("controls.drawer.docs.no_evidence_linked")}</p>
      ) : (
        <div className="space-y-1.5">
          {evidences.map(e => (
            <div key={e.id} className="bg-white border border-gray-200 rounded px-2.5 py-2">
              <div className="flex items-start justify-between gap-1">
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-medium text-gray-800 truncate">
                    {evidenceIcon(e.evidence_type)} {e.title}
                  </p>
                  <div className="mt-0.5">
                    <ExpiryBadge validUntil={e.valid_until} />
                  </div>
                </div>
                <button
                  onClick={() => unlinkMut.mutate(e.id)}
                  disabled={unlinkMut.isPending}
                  className="text-red-400 hover:text-red-600 text-xs shrink-0 ml-1"
                  title={t("controls.drawer.docs.unlink")}
                >
                  ✕
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Collega evidenza esistente */}
      <div className="border border-dashed border-gray-300 rounded p-2 space-y-1.5">
        <p className="text-xs font-medium text-gray-500">{t("controls.drawer.docs.link_existing_evidence")}</p>
        <input
          type="text"
          value={searchQ}
          onChange={e => setSearchQ(e.target.value)}
          placeholder={t("controls.drawer.docs.search_placeholder")}
          className="w-full border rounded px-2 py-1 text-xs"
        />
        {searchResults && searchResults.results.length > 0 && (
          <div className="border rounded divide-y divide-gray-100 max-h-32 overflow-y-auto bg-white">
            {searchResults.results.filter(ev => !linkedEvIds.has(ev.id)).slice(0, 8).map(ev => (
              <button
                key={ev.id}
                onClick={() => linkMut.mutate(ev.id)}
                disabled={linkMut.isPending}
                className="w-full text-left px-2 py-1.5 text-xs hover:bg-blue-50 text-gray-700 flex items-center gap-1.5"
              >
                <span>{evidenceIcon(ev.evidence_type)}</span>
                <span className="truncate flex-1">{ev.title}</span>
                {ev.valid_until && <ExpiryBadge validUntil={ev.valid_until} />}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Dropzone caricamento evidenze */}
      <div className="border border-dashed border-green-300 rounded p-2">
        <p className="text-xs font-medium text-green-700 mb-1.5">{t("controls.drawer.docs.upload_new_evidence")}</p>
        <DropzoneUpload instanceId={instanceId} plant={plant} />
      </div>
    </div>
  );
}

export function TabDocEvidence({
  instanceId,
  evidences,
  documents,
  requirements,
  evidenceRequirement,
}: {
  instanceId: string;
  evidences: EvidenceRef[];
  documents: LinkedDocument[];
  requirements: RequirementsCheck;
  evidenceRequirement: EvidenceRequirement;
}) {
  const { t } = useTranslation();
  const plant = useAuthStore(s => s.selectedPlant?.id ?? null);
  const noRequirements = !evidenceRequirement ||
    (!evidenceRequirement.documents?.length && !evidenceRequirement.evidences?.length &&
     !evidenceRequirement.min_documents && !evidenceRequirement.min_evidences);

  function requirementLabel(kind: "document" | "evidence", type: string, description?: string) {
    if (type === "any") return description || "";
    if (kind === "document") return t(`documents.type.${type}`, { defaultValue: description || type });
    return t(`documents.evidence.types.${type}`, { defaultValue: description || type });
  }

  return (
    <div className="space-y-3">
      {/* Banner requisiti */}
      {requirements.not_applicable ? (
        <div className="bg-gray-50 border border-gray-200 rounded-lg px-3 py-2 text-xs text-gray-500">
          ℹ️ {t("controls.drawer.evaluation.requirements.not_applicable")}
        </div>
      ) : noRequirements ? (
        <div className="bg-gray-50 border border-gray-200 rounded-lg px-3 py-2 text-xs text-gray-500">
          ℹ️ {t("controls.drawer.evaluation.requirements.none")}
        </div>
      ) : !requirements.satisfied ? (
        <div className="bg-red-50 border border-red-200 rounded-lg px-3 py-2 text-xs text-red-800">
          <p className="font-semibold mb-1">⛔ {t("controls.drawer.docs.requirements.not_satisfied_for_compliant")}</p>
          {requirements.missing_documents.map((m, i) => <p key={i}>• {t("controls.drawer.evaluation.requirements.missing_document")}: {requirementLabel("document", m.type, m.description)}</p>)}
          {requirements.missing_evidences.map((m, i) => <p key={i}>• {t("controls.drawer.evaluation.requirements.missing_evidence")}: {requirementLabel("evidence", m.type, m.description)}</p>)}
          {requirements.expired_evidences.map((e, i) => <p key={i}>• {t("controls.drawer.evaluation.requirements.expired_evidence")}: {e.title} ({e.expired_on})</p>)}
        </div>
      ) : requirements.warnings.length > 0 ? (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg px-3 py-2 text-xs text-yellow-800">
          <p className="font-semibold mb-1">⚠️ {t("controls.drawer.evaluation.requirements.warning")}</p>
          {requirements.warnings.map((w, i) => <p key={i}>• {w}</p>)}
        </div>
      ) : (
        <div className="bg-green-50 border border-green-200 rounded-lg px-3 py-2 text-xs text-green-800">
          ✅ {t("controls.drawer.evaluation.requirements.satisfied")}
        </div>
      )}

      {/* Due colonne */}
      <div className="grid grid-cols-2 gap-3">
        <DocsColumn instanceId={instanceId} documents={documents} requirements={requirements} plant={plant} />
        <EvidencesColumn instanceId={instanceId} evidences={evidences} requirements={requirements} plant={plant} />
      </div>
    </div>
  );
}
