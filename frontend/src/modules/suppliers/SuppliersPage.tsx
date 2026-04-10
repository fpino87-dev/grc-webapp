import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  suppliersApi,
  type Supplier,
  type QuestionnaireTemplate,
  type SupplierQuestionnaire,
  type NdaDocument,
} from "../../api/endpoints/suppliers";
import { reportingApi, type SupplierNdaEntry } from "../../api/endpoints/reporting";
import { StatusBadge } from "../../components/ui/StatusBadge";
import { apiClient } from "../../api/client";
import { useTranslation } from "react-i18next";
import i18n from "../../i18n";

// ─── Shared badge components ─────────────────────────────────────────────────

type SupplierAssessment = {
  id: string;
  assessment_date: string | null;
  status: string;
  score_overall: number | null;
  score_governance: number | null;
  score_security: number | null;
  score_bcp: number | null;
  computed_risk_level: string;
  reviewed_by: string | null;
  reviewed_at: string | null;
  review_notes: string;
};

function AssessmentStatusBadge({ status }: { status: string }) {
  const map: Record<string, { label: string; classes: string }> = {
    pianificato: { label: "Pianificato", classes: "bg-gray-100 text-gray-700" },
    in_corso: { label: "In corso", classes: "bg-blue-100 text-blue-700" },
    completato: { label: "Completato", classes: "bg-amber-100 text-amber-800" },
    approvato: { label: "Approvato", classes: "bg-green-100 text-green-800" },
    rifiutato: { label: "Rifiutato", classes: "bg-red-100 text-red-800" },
  };
  const cfg = map[status] || { label: status, classes: "bg-gray-100 text-gray-700" };
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${cfg.classes}`}>
      {cfg.label}
    </span>
  );
}

function RiskBadge({ level }: { level: string }) {
  const map: Record<string, { label: string; classes: string }> = {
    verde:   { label: "Basso",   classes: "bg-green-100 text-green-800" },
    giallo:  { label: "Medio",   classes: "bg-amber-100 text-amber-800" },
    rosso:   { label: "Alto",    classes: "bg-red-100 text-red-800" },
    nd:      { label: "N/D",     classes: "bg-gray-100 text-gray-600" },
    basso:   { label: "Basso",   classes: "bg-green-100 text-green-800" },
    medio:   { label: "Medio",   classes: "bg-amber-100 text-amber-800" },
    alto:    { label: "Alto",    classes: "bg-red-100 text-red-800" },
    critico: { label: "Critico", classes: "bg-red-200 text-red-900 font-bold" },
  };
  const cfg = map[level] || map.nd;
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${cfg.classes}`}>
      {cfg.label}
    </span>
  );
}

function QStatus({ status, sendCount }: { status: string; sendCount: number }) {
  if (status === "risposto") return <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">&#10003; Risposto</span>;
  if (status === "scaduto")  return <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-600">Scaduto</span>;
  if (sendCount >= 3) return <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-red-200 text-red-900">3° invio — contatto diretto</span>;
  if (sendCount === 2) return <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-orange-100 text-orange-800">2° invio</span>;
  return <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-700">In attesa</span>;
}

// ─── AssessmentsTable (existing, unchanged) ──────────────────────────────────

function AssessmentsTable({ supplierId }: { supplierId: string }) {
  const qc = useQueryClient();
  const [modal, setModal] = useState<null | { type: "complete" | "approve" | "reject"; assessment: SupplierAssessment }>(null);
  const [scores, setScores] = useState({ score_governance: "", score_security: "", score_bcp: "", score_overall: "", findings: "", notes: "" });
  const [error, setError] = useState("");
  const [newDate, setNewDate] = useState("");
  const [showNewForm, setShowNewForm] = useState(false);

  const { data } = useQuery<{ results: SupplierAssessment[] }>({
    queryKey: ["supplier-assessments", supplierId],
    queryFn: async () => {
      const res = await apiClient.get("/suppliers/assessments/", { params: { supplier: supplierId } });
      return res.data;
    },
  });
  const assessments = data?.results ?? [];

  const newAssessmentMutation = useMutation({
    mutationFn: async () => {
      await apiClient.post("/suppliers/assessments/", {
        supplier: supplierId,
        assessment_date: newDate,
        status: "pianificato",
      });
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["supplier-assessments", supplierId] });
      setShowNewForm(false);
      setNewDate("");
    },
    onError: () => setError("Errore durante la creazione dell'assessment"),
  });

  function computeOverall(g: string, s: string, b: string) {
    const nums = [g, s, b].map(v => (v ? Number(v) : NaN)).filter(v => !Number.isNaN(v));
    if (!nums.length) return "";
    return Math.round(nums.reduce((a, v) => a + v, 0) / nums.length).toString();
  }

  const completeMutation = useMutation({
    mutationFn: async () => {
      if (!modal) return;
      await apiClient.post(`/suppliers/assessments/${modal.assessment.id}/complete/`, {
        score_governance: scores.score_governance ? Number(scores.score_governance) : null,
        score_security:   scores.score_security   ? Number(scores.score_security)   : null,
        score_bcp:        scores.score_bcp        ? Number(scores.score_bcp)        : null,
        score_overall:    scores.score_overall     ? Number(scores.score_overall)    : null,
        findings: scores.findings,
      });
    },
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["supplier-assessments", supplierId] }); qc.invalidateQueries({ queryKey: ["suppliers"] }); setModal(null); },
    onError: () => setError("Errore durante il completamento"),
  });

  const approveMutation = useMutation({
    mutationFn: async () => {
      if (!modal) return;
      await apiClient.post(`/suppliers/assessments/${modal.assessment.id}/approve/`, { notes: scores.notes });
    },
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["supplier-assessments", supplierId] }); setModal(null); },
    onError: () => setError("Errore durante l'approvazione"),
  });

  const rejectMutation = useMutation({
    mutationFn: async () => {
      if (!modal) return;
      await apiClient.post(`/suppliers/assessments/${modal.assessment.id}/reject/`, { notes: scores.notes });
    },
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["supplier-assessments", supplierId] }); setModal(null); },
    onError: (e: any) => setError(e?.response?.data?.error || "Errore"),
  });

  return (
    <div className="px-4 pb-4 pt-2">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">Assessment interni</span>
        {!showNewForm && (
          <button
            onClick={() => setShowNewForm(true)}
            className="text-xs text-indigo-600 border border-indigo-200 rounded px-2 py-0.5 hover:bg-indigo-50"
          >
            + Nuovo assessment
          </button>
        )}
      </div>
      {showNewForm && (
        <div className="flex items-center gap-2 mb-3 p-2 bg-indigo-50 rounded">
          <label className="text-xs text-gray-600 shrink-0">Data assessment *</label>
          <input
            type="date"
            value={newDate}
            onChange={e => setNewDate(e.target.value)}
            className="border rounded px-2 py-1 text-xs"
          />
          <button
            onClick={() => newAssessmentMutation.mutate()}
            disabled={newAssessmentMutation.isPending || !newDate}
            className="text-xs bg-indigo-600 text-white rounded px-2 py-1 disabled:opacity-50"
          >
            {newAssessmentMutation.isPending ? "..." : "Crea"}
          </button>
          <button onClick={() => { setShowNewForm(false); setNewDate(""); }} className="text-xs text-gray-500 hover:text-gray-700">
            Annulla
          </button>
          {error && <span className="text-xs text-red-600">{error}</span>}
        </div>
      )}
      {assessments.length === 0 ? (
        <p className="text-xs text-gray-400 italic">Nessun assessment registrato.</p>
      ) : (
        <table className="w-full text-xs">
          <thead><tr className="text-gray-500 border-b">
            <th className="text-left py-1 pr-3">Data</th>
            <th className="text-left py-1 pr-3">Gov.</th>
            <th className="text-left py-1 pr-3">Sec.</th>
            <th className="text-left py-1 pr-3">BCP</th>
            <th className="text-left py-1 pr-3">Overall</th>
            <th className="text-left py-1 pr-3">Rischio</th>
            <th className="text-left py-1 pr-3">Stato</th>
            <th className="py-1"></th>
          </tr></thead>
          <tbody>{assessments.map(a => (
            <tr key={a.id} className="border-b border-gray-50">
              <td className="py-1 pr-3">{a.assessment_date || "—"}</td>
              <td className="py-1 pr-3">{a.score_governance ?? "—"}</td>
              <td className="py-1 pr-3">{a.score_security ?? "—"}</td>
              <td className="py-1 pr-3">{a.score_bcp ?? "—"}</td>
              <td className="py-1 pr-3 font-semibold">{a.score_overall ?? "—"}</td>
              <td className="py-1 pr-3"><RiskBadge level={a.computed_risk_level} /></td>
              <td className="py-1 pr-3"><AssessmentStatusBadge status={a.status} /></td>
              <td className="py-1 space-x-1">
                {a.status === "pianificato" && <button onClick={() => { setModal({ type: "complete", assessment: a }); setError(""); setScores({ score_governance: "", score_security: "", score_bcp: "", score_overall: "", findings: "", notes: "" }); }} className="text-blue-600 hover:underline">Completa</button>}
                {a.status === "completato"  && <><button onClick={() => { setModal({ type: "approve", assessment: a }); setError(""); setScores(p => ({...p, notes: ""})); }} className="text-green-600 hover:underline">Approva</button><button onClick={() => { setModal({ type: "reject", assessment: a }); setError(""); setScores(p => ({...p, notes: ""})); }} className="ml-1 text-red-600 hover:underline">Rifiuta</button></>}
              </td>
            </tr>
          ))}</tbody>
        </table>
      )}

      {modal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-5">
            {modal.type === "complete" && (
              <>
                <h3 className="text-base font-semibold mb-3">Completa assessment</h3>
                {["score_governance","score_security","score_bcp"].map(field => (
                  <div key={field} className="mb-2">
                    <label className="block text-xs font-medium text-gray-700 mb-0.5 capitalize">{field.replace("score_","").replace("_"," ")} (0-100)</label>
                    <input type="number" min={0} max={100} value={(scores as any)[field]} onChange={e => { const v = {...scores, [field]: e.target.value}; setScores({...v, score_overall: computeOverall(v.score_governance, v.score_security, v.score_bcp)}); }} className="w-full border rounded px-2 py-1 text-sm" />
                  </div>
                ))}
                <div className="mb-2">
                  <label className="block text-xs font-medium text-gray-700 mb-0.5">Overall (auto)</label>
                  <input type="number" value={scores.score_overall} readOnly className="w-full border rounded px-2 py-1 text-sm bg-gray-50" />
                </div>
                <div className="mb-3">
                  <label className="block text-xs font-medium text-gray-700 mb-0.5">Findings</label>
                  <textarea value={scores.findings} onChange={e => setScores(p => ({...p, findings: e.target.value}))} className="w-full border rounded px-2 py-1 text-sm" rows={2} />
                </div>
                {error && <p className="text-xs text-red-600 mb-2">{error}</p>}
                <div className="flex justify-end gap-2">
                  <button onClick={() => setModal(null)} className="px-3 py-1.5 border rounded text-sm text-gray-600">Annulla</button>
                  <button onClick={() => completeMutation.mutate()} disabled={completeMutation.isPending} className="px-3 py-1.5 bg-blue-600 text-white rounded text-sm disabled:opacity-50">
                    {completeMutation.isPending ? "..." : "Salva"}
                  </button>
                </div>
              </>
            )}
            {(modal.type === "approve" || modal.type === "reject") && (
              <>
                <h3 className="text-base font-semibold mb-3">{modal.type === "approve" ? "Approva" : "Rifiuta"} assessment</h3>
                <div className="mb-3">
                  <label className="block text-xs font-medium text-gray-700 mb-0.5">Note {modal.type === "reject" && "(min 10 caratteri) *"}</label>
                  <textarea value={scores.notes} onChange={e => setScores(p => ({...p, notes: e.target.value}))} className="w-full border rounded px-2 py-1 text-sm" rows={3} />
                </div>
                {error && <p className="text-xs text-red-600 mb-2">{error}</p>}
                <div className="flex justify-end gap-2">
                  <button onClick={() => setModal(null)} className="px-3 py-1.5 border rounded text-sm text-gray-600">Annulla</button>
                  <button onClick={() => modal.type === "approve" ? approveMutation.mutate() : rejectMutation.mutate()} disabled={approveMutation.isPending || rejectMutation.isPending} className={`px-3 py-1.5 text-white rounded text-sm disabled:opacity-50 ${modal.type === "approve" ? "bg-green-600" : "bg-red-600"}`}>
                    {approveMutation.isPending || rejectMutation.isPending ? "..." : modal.type === "approve" ? "Approva" : "Rifiuta"}
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ─── NDA components ──────────────────────────────────────────────────────────

function NdaDocStatusBadge({ status }: { status: string }) {
  const map: Record<string, { label: string; classes: string }> = {
    bozza:       { label: "Bozza",        classes: "bg-gray-100 text-gray-700" },
    revisione:   { label: "In revisione", classes: "bg-blue-100 text-blue-700" },
    approvazione:{ label: "In approvazione", classes: "bg-amber-100 text-amber-800" },
    approvato:   { label: "Approvato",    classes: "bg-green-100 text-green-800" },
    archiviato:  { label: "Archiviato",   classes: "bg-gray-200 text-gray-600" },
  };
  const cfg = map[status] ?? { label: status, classes: "bg-gray-100 text-gray-600" };
  return <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${cfg.classes}`}>{cfg.label}</span>;
}

function NdaSection({ supplierId }: { supplierId: string }) {
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
    onError: (e: any) => setUploadError(e?.response?.data?.error || "Errore durante il caricamento"),
  });

  return (
    <div className="px-4 pb-4 pt-2">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">NDA / Contratti</span>
        {!showUpload && (
          <button
            onClick={() => setShowUpload(true)}
            className="text-xs text-indigo-600 border border-indigo-200 rounded px-2 py-0.5 hover:bg-indigo-50"
          >
            + Carica NDA
          </button>
        )}
      </div>

      {showUpload && (
        <div className="mb-4 p-3 bg-indigo-50 rounded border border-indigo-100 space-y-2">
          <p className="text-xs font-medium text-indigo-800">Carica documento NDA / Contratto</p>
          <div>
            <label className="block text-xs text-gray-600 mb-0.5">File *</label>
            <input
              type="file"
              accept=".pdf,.doc,.docx"
              onChange={e => setFile(e.target.files?.[0] ?? null)}
              className="text-xs w-full"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-600 mb-0.5">Titolo *</label>
            <input
              type="text"
              value={uploadTitle}
              onChange={e => setUploadTitle(e.target.value)}
              placeholder="es. NDA con Fornitore XYZ 2026"
              className="w-full border rounded px-2 py-1 text-xs"
            />
          </div>
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="block text-xs text-gray-600 mb-0.5">Scadenza</label>
              <input
                type="date"
                value={uploadExpiry}
                onChange={e => setUploadExpiry(e.target.value)}
                className="w-full border rounded px-2 py-1 text-xs"
              />
            </div>
            <div>
              <label className="block text-xs text-gray-600 mb-0.5">Note</label>
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
              {uploadMutation.isPending ? "Caricamento..." : "Carica"}
            </button>
            <button
              onClick={() => { setShowUpload(false); setFile(null); setUploadTitle(""); setUploadExpiry(""); setUploadNotes(""); setUploadError(""); }}
              className="text-xs text-gray-500 hover:text-gray-700"
            >
              Annulla
            </button>
          </div>
        </div>
      )}

      {isLoading ? (
        <p className="text-xs text-gray-400">Caricamento...</p>
      ) : docs.length === 0 ? (
        <p className="text-xs text-gray-400 italic">Nessun documento NDA/contratto caricato.</p>
      ) : (
        <table className="w-full text-xs">
          <thead>
            <tr className="text-gray-500 border-b">
              <th className="text-left py-1 pr-3">Titolo</th>
              <th className="text-left py-1 pr-3">Stato</th>
              <th className="text-left py-1 pr-3">Scadenza</th>
              <th className="text-left py-1 pr-3">File</th>
              <th className="py-1 pr-3">Versione</th>
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
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

function ExpandedSupplierRow({ supplierId }: { supplierId: string }) {
  const [subTab, setSubTab] = useState<"assessments" | "nda">("assessments");
  return (
    <div>
      <div className="flex border-b border-gray-200 px-4 pt-2">
        <button
          onClick={() => setSubTab("assessments")}
          className={`px-3 py-1.5 text-xs font-medium border-b-2 -mb-px transition-colors ${subTab === "assessments" ? "border-indigo-600 text-indigo-700" : "border-transparent text-gray-500 hover:text-gray-700"}`}
        >
          Valutazioni
        </button>
        <button
          onClick={() => setSubTab("nda")}
          className={`px-3 py-1.5 text-xs font-medium border-b-2 -mb-px transition-colors ${subTab === "nda" ? "border-indigo-600 text-indigo-700" : "border-transparent text-gray-500 hover:text-gray-700"}`}
        >
          NDA / Contratti
        </button>
      </div>
      {subTab === "assessments" ? <AssessmentsTable supplierId={supplierId} /> : <NdaSection supplierId={supplierId} />}
    </div>
  );
}

// ─── NDA overview tab (page-level) ───────────────────────────────────────────

function NdaStatusBadge({ status }: { status: SupplierNdaEntry["nda_status"] }) {
  const map: Record<string, { label: string; classes: string }> = {
    ok:       { label: "OK",           classes: "bg-green-100 text-green-800" },
    expiring: { label: "In scadenza",  classes: "bg-yellow-100 text-yellow-800" },
    expired:  { label: "Scaduto",      classes: "bg-red-100 text-red-800" },
    draft:    { label: "Bozza",        classes: "bg-gray-100 text-gray-700" },
    missing:  { label: "Mancante",     classes: "bg-red-50 text-red-600 border border-red-200" },
  };
  const cfg = map[status] ?? map.missing;
  return <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${cfg.classes}`}>{cfg.label}</span>;
}

function NdaTab() {
  const { data, isLoading } = useQuery({
    queryKey: ["kpi-overview", ""],
    queryFn: () => reportingApi.kpiOverview(),
    retry: false,
  });

  const nda = data?.supplier_nda;

  return (
    <div>
      {isLoading && <div className="py-8 text-center text-gray-400 text-sm">Caricamento...</div>}
      {nda && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <div className="bg-white border border-green-300 rounded-lg p-4">
              <p className="text-xs text-gray-500 uppercase tracking-wide">Con NDA attivo</p>
              <p className="text-3xl font-bold text-green-600 mt-1">{nda.covered}</p>
            </div>
            <div className="bg-white border border-yellow-300 rounded-lg p-4">
              <p className="text-xs text-gray-500 uppercase tracking-wide">In scadenza (90gg)</p>
              <p className="text-3xl font-bold text-yellow-600 mt-1">{nda.expiring_soon}</p>
            </div>
            <div className="bg-white border border-red-300 rounded-lg p-4">
              <p className="text-xs text-gray-500 uppercase tracking-wide">NDA scaduto</p>
              <p className="text-3xl font-bold text-red-600 mt-1">{nda.expired}</p>
            </div>
            <div className="bg-white border border-gray-200 rounded-lg p-4">
              <p className="text-xs text-gray-500 uppercase tracking-wide">Senza NDA</p>
              <p className="text-3xl font-bold text-gray-600 mt-1">{nda.without_nda}</p>
            </div>
          </div>

          {nda.suppliers.length === 0 ? (
            <div className="text-center text-gray-400 py-8">Nessun fornitore attivo.</div>
          ) : (
            <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 border-b border-gray-200">
                  <tr>
                    <th className="text-left px-4 py-3 font-medium text-gray-600">Fornitore</th>
                    <th className="text-left px-4 py-3 font-medium text-gray-600">Rischio</th>
                    <th className="text-left px-4 py-3 font-medium text-gray-600">Stato NDA</th>
                    <th className="text-left px-4 py-3 font-medium text-gray-600">Scadenza NDA</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {nda.suppliers.map(s => (
                    <tr key={s.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3 font-medium text-gray-800">{s.name}</td>
                      <td className="px-4 py-3"><RiskBadge level={s.risk_level} /></td>
                      <td className="px-4 py-3"><NdaStatusBadge status={s.nda_status} /></td>
                      <td className="px-4 py-3 text-sm text-gray-500">
                        {s.expiry_date
                          ? <>{s.expiry_date}{s.days_to_expiry !== null && s.days_to_expiry <= 90 && <span className="ml-1 text-orange-500 text-xs">({s.days_to_expiry}gg)</span>}</>
                          : "—"
                        }
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </div>
  );
}

// ─── Tab: Fornitori ───────────────────────────────────────────────────────────

function NewSupplierModal({ onClose }: { onClose: () => void }) {
  const qc = useQueryClient();
  const [form, setForm] = useState<Partial<Supplier>>({ risk_level: "basso", status: "attivo" });

  const mutation = useMutation({
    mutationFn: suppliersApi.create,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["suppliers"] }); onClose(); },
  });

  function handleChange(e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) {
    setForm(prev => ({ ...prev, [e.target.name]: e.target.value }));
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-lg p-6">
        <h3 className="text-lg font-semibold mb-4">Nuovo fornitore</h3>
        <div className="space-y-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Nome *</label>
            <input name="name" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">P.IVA</label>
              <input name="vat_number" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Paese</label>
              <input name="country" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" placeholder="IT" />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Email fornitore *</label>
            <input name="email" type="email" required onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" placeholder="contatto@fornitore.it" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Livello rischio</label>
              <select name="risk_level" defaultValue="basso" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm">
                {["basso","medio","alto","critico"].map(r => <option key={r} value={r}>{r}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Data di Valutazione</label>
              <input name="evaluation_date" type="date" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" />
            </div>
          </div>
        </div>
        {mutation.isError && <p className="text-sm text-red-600 mt-2">Errore durante il salvataggio</p>}
        <div className="flex justify-end gap-2 mt-4">
          <button onClick={onClose} className="px-4 py-2 border rounded text-sm text-gray-600 hover:bg-gray-50">Annulla</button>
          <button onClick={() => mutation.mutate(form)} disabled={mutation.isPending || !form.name || !form.email} className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700 disabled:opacity-50">
            {mutation.isPending ? "Salvataggio..." : "Crea fornitore"}
          </button>
        </div>
      </div>
    </div>
  );
}

function EditSupplierModal({ supplier, onClose }: { supplier: Supplier; onClose: () => void }) {
  const qc = useQueryClient();
  const [form, setForm] = useState<Partial<Supplier>>({ ...supplier });

  const mutation = useMutation({
    mutationFn: () => suppliersApi.update(supplier.id, form),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["suppliers"] }); onClose(); },
  });

  function handleChange(e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) {
    setForm(prev => ({ ...prev, [e.target.name]: e.target.value }));
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-lg p-6">
        <h3 className="text-lg font-semibold mb-4">Modifica fornitore</h3>
        <div className="space-y-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Nome *</label>
            <input name="name" value={form.name ?? ""} onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">P.IVA</label>
              <input name="vat_number" value={form.vat_number ?? ""} onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Paese</label>
              <input name="country" value={form.country ?? ""} onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" placeholder="IT" />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Email fornitore *</label>
            <input name="email" type="email" required value={form.email ?? ""} onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" placeholder="contatto@fornitore.it" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Livello rischio</label>
              <select name="risk_level" value={form.risk_level ?? "basso"} onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm">
                {["basso","medio","alto","critico"].map(r => <option key={r} value={r}>{r}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Stato</label>
              <select name="status" value={form.status ?? "attivo"} onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm">
                {["attivo","sospeso","terminato"].map(s => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Data di Valutazione</label>
            <input name="evaluation_date" type="date" value={form.evaluation_date ?? ""} onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" />
          </div>
        </div>
        {mutation.isError && <p className="text-sm text-red-600 mt-2">Errore durante il salvataggio</p>}
        <div className="flex justify-end gap-2 mt-4">
          <button onClick={onClose} className="px-4 py-2 border rounded text-sm text-gray-600 hover:bg-gray-50">Annulla</button>
          <button onClick={() => mutation.mutate()} disabled={mutation.isPending || !form.name} className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700 disabled:opacity-50">
            {mutation.isPending ? "Salvataggio..." : "Aggiorna fornitore"}
          </button>
        </div>
      </div>
    </div>
  );
}

function EvalDateCell({ date }: { date: string | null }) {
  if (!date) return <span className="text-gray-400">—</span>;
  return (
    <span className="text-gray-600">
      {new Date(date).toLocaleDateString(i18n.language || "it")}
    </span>
  );
}

function ExpiryDateCell({ evaluationDate }: { evaluationDate: string | null }) {
  if (!evaluationDate) return <span className="text-gray-400">—</span>;
  const expiry = new Date(evaluationDate);
  expiry.setFullYear(expiry.getFullYear() + 1);
  const daysLeft = Math.ceil((expiry.getTime() - Date.now()) / (1000 * 60 * 60 * 24));
  let colorClass = "text-green-600";
  if (daysLeft <= 30) colorClass = "text-red-600 font-medium";
  else if (daysLeft <= 90) colorClass = "text-orange-500 font-medium";
  return (
    <span className={colorClass}>
      {expiry.toLocaleDateString(i18n.language || "it")}
      {daysLeft <= 90 && <span className="ml-1 text-xs">({daysLeft}gg)</span>}
    </span>
  );
}

function SendQuestionnaireModal({ supplier, onClose }: { supplier: Supplier; onClose: () => void }) {
  const qc = useQueryClient();
  const [templateId, setTemplateId] = useState("");
  const [error, setError] = useState("");

  const { data: templates } = useQuery({
    queryKey: ["questionnaire-templates"],
    queryFn: suppliersApi.listTemplates,
  });

  const mutation = useMutation({
    mutationFn: () => suppliersApi.sendQuestionnaire(supplier.id, templateId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["supplier-questionnaires"] });
      onClose();
    },
    onError: (e: any) => setError(e?.response?.data?.error || "Errore invio"),
  });

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-5">
        <h3 className="text-base font-semibold mb-1">Invia questionario</h3>
        <p className="text-sm text-gray-500 mb-3">Fornitore: <strong>{supplier.name}</strong> — {supplier.email || <span className="text-red-500">email non configurata</span>}</p>
        {!supplier.email && (
          <p className="text-sm text-red-600 bg-red-50 rounded p-2 mb-3">Configura l'email del fornitore prima di inviare.</p>
        )}
        <div className="mb-3">
          <label className="block text-sm font-medium text-gray-700 mb-1">Template *</label>
          <select value={templateId} onChange={e => setTemplateId(e.target.value)} className="w-full border rounded px-3 py-2 text-sm">
            <option value="">— seleziona template —</option>
            {(templates ?? []).map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
          </select>
        </div>
        {error && <p className="text-xs text-red-600 mb-2">{error}</p>}
        <div className="flex justify-end gap-2">
          <button onClick={onClose} className="px-3 py-1.5 border rounded text-sm text-gray-600">Annulla</button>
          <button onClick={() => mutation.mutate()} disabled={mutation.isPending || !templateId || !supplier.email} className="px-3 py-1.5 bg-indigo-600 text-white rounded text-sm disabled:opacity-50">
            {mutation.isPending ? "Invio..." : "Invia"}
          </button>
        </div>
      </div>
    </div>
  );
}

function ForniториTab() {
  const qc = useQueryClient();
  const [newModal, setNewModal] = useState(false);
  const [editModal, setEditModal] = useState<Supplier | null>(null);
  const [sendModal, setSendModal] = useState<Supplier | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [filterRisk, setFilterRisk] = useState("");
  const [filterStatus, setFilterStatus] = useState("");

  const deleteMutation = useMutation({
    mutationFn: (id: string) => suppliersApi.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["suppliers"] }),
    onError: () => window.alert("Errore durante l'eliminazione"),
  });

  const params: Record<string, string> = {};
  if (filterRisk) params.risk_level = filterRisk;
  if (filterStatus) params.status = filterStatus;

  const { data, isLoading } = useQuery({
    queryKey: ["suppliers", filterRisk, filterStatus],
    queryFn: () => suppliersApi.list(Object.keys(params).length ? params : undefined),
  });
  const suppliers = data?.results ?? [];

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <div className="flex gap-2">
          <select value={filterRisk} onChange={e => setFilterRisk(e.target.value)} className="border rounded px-3 py-1.5 text-sm">
            <option value="">Tutti i rischi</option>
            {["basso","medio","alto","critico"].map(r => <option key={r} value={r}>{r}</option>)}
          </select>
          <select value={filterStatus} onChange={e => setFilterStatus(e.target.value)} className="border rounded px-3 py-1.5 text-sm">
            <option value="">Tutti gli stati</option>
            {["attivo","sospeso","terminato"].map(s => <option key={s} value={s}>{s}</option>)}
          </select>
        </div>
        <button onClick={() => setNewModal(true)} className="px-4 py-2 bg-primary-600 text-white text-sm rounded hover:bg-primary-700">
          + Nuovo fornitore
        </button>
      </div>

      {newModal && <NewSupplierModal onClose={() => setNewModal(false)} />}
      {editModal && <EditSupplierModal supplier={editModal} onClose={() => setEditModal(null)} />}
      {sendModal && <SendQuestionnaireModal supplier={sendModal} onClose={() => setSendModal(null)} />}

      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-gray-400">Caricamento...</div>
        ) : suppliers.length === 0 ? (
          <div className="p-8 text-center text-gray-400">Nessun fornitore trovato.</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Nome</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">P.IVA</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Paese</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Email</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Rischio</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Stato</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Data Valutazione</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Scadenza</th>
                <th className="px-4 py-3 w-36"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {suppliers.map(s => (
                <>
                  <tr key={s.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-4 py-3 font-medium text-gray-800">
                      <button onClick={() => setExpandedId(expandedId === s.id ? null : s.id)} className="hover:underline text-left">
                        {s.name}
                      </button>
                    </td>
                    <td className="px-4 py-3 text-gray-500">{s.vat_number || "—"}</td>
                    <td className="px-4 py-3 text-gray-500">{s.country}</td>
                    <td className="px-4 py-3 text-gray-500 text-xs">{s.email || <span className="text-gray-300">—</span>}</td>
                    <td className="px-4 py-3"><RiskBadge level={s.risk_level} /></td>
                    <td className="px-4 py-3"><StatusBadge status={s.status} /></td>
                    <td className="px-4 py-3"><EvalDateCell date={s.evaluation_date} /></td>
                    <td className="px-4 py-3"><ExpiryDateCell evaluationDate={s.evaluation_date} /></td>
                    <td className="px-4 py-3 text-right space-x-1">
                      <button
                        onClick={() => setSendModal(s)}
                        title="Invia questionario"
                        className="text-xs text-indigo-600 border border-indigo-200 rounded px-2 py-1 hover:bg-indigo-50"
                      >
                        Questionario
                      </button>
                      <button
                        onClick={() => setEditModal(s)}
                        title="Modifica fornitore"
                        className="text-xs text-gray-600 border border-gray-200 rounded px-2 py-1 hover:bg-gray-50"
                      >
                        Modifica
                      </button>
                      <button
                        onClick={() => { if (window.confirm(`Eliminare il fornitore "${s.name}" e tutti i suoi questionari?`)) deleteMutation.mutate(s.id); }}
                        disabled={deleteMutation.isPending}
                        title="Elimina fornitore"
                        className="text-xs text-red-600 border border-red-200 rounded px-2 py-1 hover:bg-red-50 disabled:opacity-50"
                      >
                        Elimina
                      </button>
                    </td>
                  </tr>
                  {expandedId === s.id && (
                    <tr key={`${s.id}-expand`}>
                      <td colSpan={9} className="bg-gray-50">
                        <ExpandedSupplierRow supplierId={s.id} />
                      </td>
                    </tr>
                  )}
                </>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

// ─── Tab: Questionari ─────────────────────────────────────────────────────────

function EvaluateModal({ questionnaire, onClose }: { questionnaire: SupplierQuestionnaire; onClose: () => void }) {
  const qc = useQueryClient();
  const [evalDate, setEvalDate] = useState("");
  const [riskResult, setRiskResult] = useState<string>("medio");
  const [notes, setNotes] = useState("");
  const [error, setError] = useState("");

  const mutation = useMutation({
    mutationFn: () => suppliersApi.evaluateQuestionnaire(questionnaire.id, evalDate, riskResult, notes),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["supplier-questionnaires"] });
      qc.invalidateQueries({ queryKey: ["suppliers"] });
      onClose();
    },
    onError: (e: any) => setError(e?.response?.data?.error || "Errore"),
  });

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-5">
        <h3 className="text-base font-semibold mb-1">Registra valutazione</h3>
        <p className="text-sm text-gray-500 mb-3">Fornitore: <strong>{questionnaire.supplier_name}</strong></p>
        <div className="space-y-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Data di Valutazione *</label>
            <input type="date" value={evalDate} onChange={e => setEvalDate(e.target.value)} className="w-full border rounded px-3 py-2 text-sm" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Valutazione *</label>
            <select value={riskResult} onChange={e => setRiskResult(e.target.value)} className="w-full border rounded px-3 py-2 text-sm">
              {["basso","medio","alto","critico"].map(r => <option key={r} value={r} className="capitalize">{r.charAt(0).toUpperCase() + r.slice(1)}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Note</label>
            <textarea value={notes} onChange={e => setNotes(e.target.value)} className="w-full border rounded px-3 py-2 text-sm" rows={2} placeholder="Osservazioni dal questionario..." />
          </div>
        </div>
        {error && <p className="text-xs text-red-600 mt-2">{error}</p>}
        <div className="flex justify-end gap-2 mt-4">
          <button onClick={onClose} className="px-3 py-1.5 border rounded text-sm text-gray-600">Annulla</button>
          <button onClick={() => mutation.mutate()} disabled={mutation.isPending || !evalDate} className="px-3 py-1.5 bg-green-600 text-white rounded text-sm disabled:opacity-50">
            {mutation.isPending ? "Salvataggio..." : "Registra"}
          </button>
        </div>
      </div>
    </div>
  );
}

function QuestionariTab() {
  const qc = useQueryClient();
  const [evaluateTarget, setEvaluateTarget] = useState<SupplierQuestionnaire | null>(null);
  const [filterStatus, setFilterStatus] = useState("");

  const params: Record<string, string> = {};
  if (filterStatus) params.status = filterStatus;

  const { data, isLoading } = useQuery({
    queryKey: ["supplier-questionnaires", filterStatus],
    queryFn: () => suppliersApi.listQuestionnaires(Object.keys(params).length ? params : undefined),
  });
  const questionnaires = data ?? [];

  const resendMutation = useMutation({
    mutationFn: (id: string) => suppliersApi.resendQuestionnaire(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["supplier-questionnaires"] }),
    onError: (e: any) => window.alert(e?.response?.data?.error || "Errore reinvio"),
  });

  return (
    <div>
      {evaluateTarget && <EvaluateModal questionnaire={evaluateTarget} onClose={() => setEvaluateTarget(null)} />}

      <div className="flex items-center gap-3 mb-4">
        <select value={filterStatus} onChange={e => setFilterStatus(e.target.value)} className="border rounded px-3 py-1.5 text-sm">
          <option value="">Tutti gli stati</option>
          <option value="inviato">In attesa</option>
          <option value="risposto">Risposto</option>
          <option value="scaduto">Scaduto</option>
        </select>
        <span className="text-sm text-gray-500">{questionnaires.length} questionari</span>
      </div>

      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        {isLoading ? (
          <div className="p-6 text-center text-gray-400">Caricamento...</div>
        ) : questionnaires.length === 0 ? (
          <div className="p-6 text-center text-gray-400">Nessun questionario inviato.</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Fornitore</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Inviato a</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">1° invio</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Ultimo invio</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Stato</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Data Valutazione</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Valutazione</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Scade il</th>
                <th className="px-4 py-3 w-28"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {questionnaires.map(q => (
                <tr key={q.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium text-gray-800">{q.supplier_name}</td>
                  <td className="px-4 py-3 text-gray-500 text-xs">{q.sent_to}</td>
                  <td className="px-4 py-3 text-gray-500 text-xs">{new Date(q.sent_at).toLocaleDateString(i18n.language || "it")}</td>
                  <td className="px-4 py-3 text-gray-500 text-xs">{new Date(q.last_sent_at).toLocaleDateString(i18n.language || "it")}</td>
                  <td className="px-4 py-3"><QStatus status={q.status} sendCount={q.send_count} /></td>
                  <td className="px-4 py-3 text-gray-600">{q.evaluation_date ? new Date(q.evaluation_date).toLocaleDateString(i18n.language || "it") : "—"}</td>
                  <td className="px-4 py-3">{q.risk_result ? <RiskBadge level={q.risk_result} /> : <span className="text-gray-400">—</span>}</td>
                  <td className="px-4 py-3 text-gray-500 text-xs">{q.expires_at ? new Date(q.expires_at).toLocaleDateString(i18n.language || "it") : "—"}</td>
                  <td className="px-4 py-3 text-right space-x-1">
                    {q.status === "inviato" && (
                      <>
                        <button
                          onClick={() => resendMutation.mutate(q.id)}
                          disabled={resendMutation.isPending}
                          className="text-xs text-indigo-600 border border-indigo-200 rounded px-1.5 py-0.5 hover:bg-indigo-50 disabled:opacity-50"
                          title={q.send_count >= 3 ? "3° invio (ultimo)" : `Reinvia (${q.send_count + 1}° invio)`}
                        >
                          Reinvia {q.send_count >= 3 ? "(3°)" : ""}
                        </button>
                        <button
                          onClick={() => setEvaluateTarget(q)}
                          className="text-xs text-green-600 border border-green-200 rounded px-1.5 py-0.5 hover:bg-green-50"
                        >
                          Valuta
                        </button>
                      </>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

// ─── Tab: Template ───────────────────────────────────────────────────────────

const TEMPLATE_DEFAULT_SUBJECT = "Questionario di valutazione fornitore — {supplier_name}";
const TEMPLATE_DEFAULT_BODY =
  "Gentile {supplier_name},\n\n" +
  "nell'ambito del nostro processo di qualifica e monitoraggio fornitori, Le chiediamo di compilare il questionario di valutazione al seguente link:\n\n" +
  "{questionnaire_link}\n\n" +
  "Il questionario richiede circa 10-15 minuti. Le chiediamo di completarlo entro 7 giorni dal ricevimento di questa email.\n\n" +
  "Per qualsiasi chiarimento può rispondere a questa email.\n\n" +
  "Cordiali saluti,\n" +
  "Team Compliance";

function TemplateModal({ template, onClose }: { template?: QuestionnaireTemplate; onClose: () => void }) {
  const qc = useQueryClient();
  const isEdit = !!template;
  const [form, setForm] = useState<Partial<QuestionnaireTemplate>>(
    template
      ? { ...template }
      : { name: "", subject: TEMPLATE_DEFAULT_SUBJECT, body: TEMPLATE_DEFAULT_BODY, form_url: "" }
  );
  const [error, setError] = useState("");

  function handleChange(e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) {
    setForm(prev => ({ ...prev, [e.target.name]: e.target.value }));
  }

  const mutation = useMutation({
    mutationFn: () => isEdit ? suppliersApi.updateTemplate(template!.id, form) : suppliersApi.createTemplate(form),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["questionnaire-templates"] }); onClose(); },
    onError: (e: any) => setError(e?.response?.data?.detail || "Errore salvataggio"),
  });

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-3xl p-6">
        <h3 className="text-lg font-semibold mb-4">{isEdit ? "Modifica template" : "Nuovo template questionario"}</h3>
        <div className="space-y-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Nome template *</label>
            <input name="name" value={form.name ?? ""} onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">URL form questionario *</label>
            <input name="form_url" type="url" value={form.form_url ?? ""} onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" placeholder="https://forms.example.com/..." />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Oggetto email *</label>
            <input name="subject" value={form.subject ?? ""} onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Testo email *</label>
            <p className="text-xs text-gray-400 mb-1">Variabili disponibili: <code className="bg-gray-100 px-1 rounded">{"{supplier_name}"}</code> e <code className="bg-gray-100 px-1 rounded">{"{questionnaire_link}"}</code></p>
            <textarea name="body" value={form.body ?? ""} onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm font-mono" rows={10} />
          </div>
        </div>
        {error && <p className="text-sm text-red-600 mt-2">{error}</p>}
        <div className="flex justify-end gap-2 mt-4">
          <button onClick={onClose} className="px-4 py-2 border rounded text-sm text-gray-600 hover:bg-gray-50">Annulla</button>
          <button onClick={() => mutation.mutate()} disabled={mutation.isPending || !form.name || !form.form_url || !form.subject || !form.body} className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700 disabled:opacity-50">
            {mutation.isPending ? "Salvataggio..." : isEdit ? "Aggiorna" : "Crea template"}
          </button>
        </div>
      </div>
    </div>
  );
}

function TemplateTab() {
  const qc = useQueryClient();
  const [modal, setModal] = useState<null | "new" | QuestionnaireTemplate>(null);

  const { data: templates, isLoading } = useQuery({
    queryKey: ["questionnaire-templates"],
    queryFn: suppliersApi.listTemplates,
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => suppliersApi.deleteTemplate(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["questionnaire-templates"] }),
  });

  return (
    <div>
      {modal === "new" && <TemplateModal onClose={() => setModal(null)} />}
      {modal && modal !== "new" && <TemplateModal template={modal as QuestionnaireTemplate} onClose={() => setModal(null)} />}

      <div className="flex justify-between items-center mb-4">
        <p className="text-sm text-gray-500">Template per l'invio del questionario ai fornitori. Il link al form viene incluso automaticamente nel corpo dell'email.</p>
        <button onClick={() => setModal("new")} className="px-4 py-2 bg-primary-600 text-white text-sm rounded hover:bg-primary-700">
          + Nuovo template
        </button>
      </div>

      {isLoading ? (
        <div className="text-center text-gray-400 py-8">Caricamento...</div>
      ) : !templates?.length ? (
        <div className="text-center text-gray-400 py-8 border border-dashed rounded-lg">
          Nessun template creato. Crea il primo template per iniziare ad inviare questionari.
        </div>
      ) : (
        <div className="grid gap-4">
          {templates.map(t => (
            <div key={t.id} className="bg-white border border-gray-200 rounded-lg p-4">
              <div className="flex items-start justify-between">
                <div className="flex-1 min-w-0">
                  <h4 className="font-semibold text-gray-800">{t.name}</h4>
                  <p className="text-xs text-gray-500 mt-0.5">Oggetto: {t.subject}</p>
                  <p className="text-xs text-indigo-600 mt-0.5 truncate">Form: {t.form_url}</p>
                  <pre className="mt-2 text-xs text-gray-600 bg-gray-50 rounded p-2 whitespace-pre-wrap max-h-32 overflow-hidden font-sans">{t.body}</pre>
                </div>
                <div className="flex gap-2 ml-3 shrink-0">
                  <button onClick={() => setModal(t)} className="text-xs text-indigo-600 border border-indigo-200 rounded px-2 py-1 hover:bg-indigo-50">
                    Modifica
                  </button>
                  <button
                    onClick={() => { if (window.confirm(`Eliminare il template "${t.name}"?`)) deleteMutation.mutate(t.id); }}
                    disabled={deleteMutation.isPending}
                    className="text-xs text-red-600 border border-red-200 rounded px-2 py-1 hover:bg-red-50 disabled:opacity-50"
                  >
                    Elimina
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

type Tab = "fornitori" | "questionari" | "template" | "nda";

export function SuppliersPage() {
  const [tab, setTab] = useState<Tab>("fornitori");

  const tabs: { id: Tab; label: string }[] = [
    { id: "fornitori",   label: "Fornitori" },
    { id: "questionari", label: "Questionari" },
    { id: "template",    label: "Template questionario" },
    { id: "nda",         label: "Stato NDA" },
  ];

  return (
    <div>
      <h2 className="text-xl font-semibold text-gray-900 mb-4">Gestione Fornitori</h2>

      {/* Tab bar */}
      <div className="flex border-b border-gray-200 mb-5">
        {tabs.map(t => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
              tab === t.id
                ? "border-indigo-600 text-indigo-700"
                : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === "fornitori"   && <ForniториTab />}
      {tab === "questionari" && <QuestionariTab />}
      {tab === "template"    && <TemplateTab />}
      {tab === "nda"         && <NdaTab />}
    </div>
  );
}
