import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { managementReviewApi, type ManagementReview } from "../../api/endpoints/managementReview";
import { plantsApi } from "../../api/endpoints/plants";
import { StatusBadge } from "../../components/ui/StatusBadge";

function NewReviewModal({ plants, onClose }: { plants: { id: string; code: string; name: string }[]; onClose: () => void }) {
  const qc = useQueryClient();
  const [form, setForm] = useState<Partial<ManagementReview>>({});
  const [error, setError] = useState("");

  const mutation = useMutation({
    mutationFn: managementReviewApi.create,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["management-review"] }); onClose(); },
    onError: (e: any) => setError(e?.response?.data?.detail || "Errore durante il salvataggio"),
  });

  function handleChange(e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) {
    setForm(prev => ({ ...prev, [e.target.name]: e.target.value || null }));
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-6">
        <h3 className="text-lg font-semibold mb-4">Nuova revisione direzione</h3>
        <div className="space-y-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Titolo *</label>
            <input name="title" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" placeholder="es. Revisione direzione Q1 2026" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Sito (opzionale)</label>
            <select name="plant" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm">
              <option value="">— org-wide —</option>
              {plants.map(p => <option key={p.id} value={p.id}>{p.code} — {p.name}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Data riunione</label>
            <input type="date" name="review_date" onChange={handleChange} className="w-full border rounded px-3 py-2 text-sm" />
          </div>
        </div>
        {error && <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded mt-3">{error}</p>}
        <div className="flex justify-end gap-2 mt-4">
          <button onClick={onClose} className="px-4 py-2 border rounded text-sm text-gray-600 hover:bg-gray-50">Annulla</button>
          <button
            onClick={() => mutation.mutate(form)}
            disabled={mutation.isPending || !form.title}
            className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700 disabled:opacity-50"
          >
            {mutation.isPending ? "Salvataggio..." : "Crea revisione"}
          </button>
        </div>
      </div>
    </div>
  );
}

const APPROVAL_COLORS: Record<string, string> = {
  bozza:     "bg-gray-100 text-gray-600",
  in_review: "bg-blue-100 text-blue-700",
  approvato: "bg-green-100 text-green-700",
  rifiutato: "bg-red-100 text-red-700",
};

function ReviewDetail({ review, onClose }: { review: ManagementReview; onClose: () => void }) {
  const qc = useQueryClient();
  const [note, setNote] = useState("");
  const [snapshotError, setSnapshotError] = useState("");
  const [approveError, setApproveError] = useState("");

  const snapshotMutation = useMutation({
    mutationFn: () => managementReviewApi.generateSnapshot(review.id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["management-review"] }); setSnapshotError(""); },
    onError: (e: any) => setSnapshotError(e?.response?.data?.error || "Errore"),
  });

  const approveMutation = useMutation({
    mutationFn: () => managementReviewApi.approve(review.id, note),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["management-review"] }); setApproveError(""); },
    onError: (e: any) => setApproveError(e?.response?.data?.error || "Errore"),
  });

  const snap = review.snapshot_data as Record<string, any>;
  const riskSum = snap?.risk_summary as Record<string, number> | undefined;
  const incidents = snap?.incidents as Record<string, number> | undefined;
  const pdca = snap?.pdca as Record<string, number> | undefined;
  const frameworks = snap?.frameworks as Record<string, { pct_compliant: number; total: number }> | undefined;

  const isApproved = review.approval_status === "approvato";

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl flex flex-col max-h-[90vh]">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100 shrink-0">
          <div>
            <h3 className="text-lg font-semibold text-gray-900">{review.title}</h3>
            <p className="text-xs text-gray-400 mt-0.5">Data riunione: {review.review_date}</p>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-2xl w-8 h-8 flex items-center justify-center rounded hover:bg-gray-100">×</button>
        </div>

        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-6">

          {/* Snapshot */}
          <section>
            <h4 className="text-sm font-semibold text-gray-700 mb-3">Dati riesame</h4>
            {!review.snapshot_generated_at ? (
              <div className="border border-dashed border-gray-300 rounded p-4 text-center">
                <p className="text-sm text-gray-500 mb-3">Nessuno snapshot disponibile. Genera i dati da congelare per questa revisione.</p>
                {snapshotError && <p className="text-xs text-red-600 mb-2">{snapshotError}</p>}
                <button
                  onClick={() => snapshotMutation.mutate()}
                  disabled={snapshotMutation.isPending}
                  className="px-4 py-2 bg-blue-600 text-white rounded text-sm hover:bg-blue-700 disabled:opacity-50"
                >
                  {snapshotMutation.isPending ? "Generazione in corso..." : "Genera snapshot dati"}
                </button>
              </div>
            ) : (
              <div className="space-y-3">
                <p className="text-xs text-blue-600 bg-blue-50 rounded px-3 py-2">
                  Snapshot generato il {new Date(review.snapshot_generated_at).toLocaleString("it-IT")} — questi dati non cambieranno
                </p>
                {frameworks && (
                  <div>
                    <p className="text-xs font-medium text-gray-600 mb-1">Compliance per framework</p>
                    <div className="grid grid-cols-2 gap-2">
                      {Object.entries(frameworks).map(([code, data]) => (
                        <div key={code} className="bg-gray-50 rounded px-3 py-2 flex justify-between text-sm">
                          <span className="font-mono text-xs text-gray-600">{code}</span>
                          <span className="font-semibold text-gray-800">{data.pct_compliant}%</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                <div className="grid grid-cols-3 gap-2">
                  {riskSum && (
                    <div className="bg-gray-50 rounded px-3 py-2">
                      <p className="text-xs text-gray-500 mb-1">Rischi</p>
                      <p className="text-xs"><span className="text-green-600 font-semibold">{riskSum.verde}</span> verdi · <span className="text-yellow-600 font-semibold">{riskSum.giallo}</span> gialli · <span className="text-red-600 font-semibold">{riskSum.rosso}</span> rossi</p>
                    </div>
                  )}
                  {incidents && (
                    <div className="bg-gray-50 rounded px-3 py-2">
                      <p className="text-xs text-gray-500 mb-1">Incidenti (12m)</p>
                      <p className="text-xs"><span className="font-semibold">{incidents.totale}</span> tot · <span className="text-orange-600 font-semibold">{incidents.aperti}</span> aperti · <span className="text-red-600 font-semibold">{incidents.nis2}</span> NIS2</p>
                    </div>
                  )}
                  {pdca && (
                    <div className="bg-gray-50 rounded px-3 py-2">
                      <p className="text-xs text-gray-500 mb-1">PDCA</p>
                      <p className="text-xs"><span className="font-semibold">{pdca.aperti}</span> aperti · <span className="text-red-600 font-semibold">{pdca.scaduti}</span> scaduti</p>
                    </div>
                  )}
                </div>
              </div>
            )}
          </section>

          {/* Approvazione */}
          <section>
            <h4 className="text-sm font-semibold text-gray-700 mb-3">Approvazione</h4>
            <div className="flex items-center gap-3 mb-3">
              <span className={`text-xs px-2 py-1 rounded font-medium ${APPROVAL_COLORS[review.approval_status] ?? "bg-gray-100 text-gray-600"}`}>
                {review.approval_status}
              </span>
              {isApproved && review.approved_at && (
                <span className="text-xs text-gray-500">
                  Approvato il {new Date(review.approved_at).toLocaleString("it-IT")}
                  {review.approval_note && ` — ${review.approval_note}`}
                </span>
              )}
            </div>
            {!isApproved && (
              <div className="space-y-2">
                <textarea
                  value={note}
                  onChange={e => setNote(e.target.value)}
                  placeholder="Nota di approvazione (opzionale)..."
                  rows={2}
                  className="w-full border rounded px-3 py-2 text-sm"
                />
                {approveError && <p className="text-xs text-red-600">{approveError}</p>}
                <button
                  onClick={() => approveMutation.mutate()}
                  disabled={approveMutation.isPending || !review.snapshot_generated_at}
                  title={!review.snapshot_generated_at ? "Genera prima lo snapshot dei dati" : undefined}
                  className="px-4 py-2 bg-green-600 text-white rounded text-sm hover:bg-green-700 disabled:opacity-50"
                >
                  {approveMutation.isPending ? "Approvazione..." : "Approva riesame"}
                </button>
                {!review.snapshot_generated_at && (
                  <p className="text-xs text-amber-600">Genera prima lo snapshot dei dati per poter approvare</p>
                )}
              </div>
            )}
          </section>
        </div>
      </div>
    </div>
  );
}

export function ManagementReviewPage() {
  const [showNew, setShowNew] = useState(false);
  const [selected, setSelected] = useState<ManagementReview | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["management-review"],
    queryFn: () => managementReviewApi.list(),
    retry: false,
  });

  const { data: plants } = useQuery({
    queryKey: ["plants"],
    queryFn: () => plantsApi.list(),
    retry: false,
  });

  const reviews = data?.results ?? [];

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold text-gray-900">Governance — Revisione Direzione</h2>
        <button onClick={() => setShowNew(true)} className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700">
          + Nuova revisione
        </button>
      </div>

      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-gray-400">Caricamento...</div>
        ) : reviews.length === 0 ? (
          <div className="p-8 text-center">
            <p className="text-gray-400 mb-2">Nessuna revisione registrata</p>
            <button onClick={() => setShowNew(true)} className="text-sm text-primary-600 hover:underline">Crea la prima revisione →</button>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Titolo</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Stato</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Approvazione</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Snapshot</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Data riunione</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {reviews.map(r => (
                <tr key={r.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3 font-medium text-gray-800">{r.title}</td>
                  <td className="px-4 py-3"><StatusBadge status={r.status} /></td>
                  <td className="px-4 py-3">
                    <span className={`text-xs px-2 py-0.5 rounded ${APPROVAL_COLORS[r.approval_status] ?? "bg-gray-100 text-gray-600"}`}>
                      {r.approval_status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-500">
                    {r.snapshot_generated_at
                      ? <span className="text-green-600">✓ {new Date(r.snapshot_generated_at).toLocaleDateString("it-IT")}</span>
                      : <span className="text-gray-400">—</span>}
                  </td>
                  <td className="px-4 py-3 text-gray-500 text-xs">{r.review_date}</td>
                  <td className="px-4 py-3">
                    <button onClick={() => setSelected(r)} className="text-xs text-primary-600 hover:underline">Dettaglio</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {showNew && plants && <NewReviewModal plants={plants} onClose={() => setShowNew(false)} />}
      {selected && <ReviewDetail review={selected} onClose={() => setSelected(null)} />}
    </div>
  );
}
