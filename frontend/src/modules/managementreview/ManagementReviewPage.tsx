import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { managementReviewApi, type ManagementReview } from "../../api/endpoints/managementReview";
import { plantsApi } from "../../api/endpoints/plants";
import { StatusBadge } from "../../components/ui/StatusBadge";
import { ModuleHelp } from "../../components/ui/ModuleHelp";
import i18n from "../../i18n";

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

type SnapFramework = { framework_name: string; total: number; pct_compliant: number; by_status: Record<string, number>; expired_evidence_count: number };
type SnapOwner = { owner__first_name: string; owner__last_name: string; owner__email: string; totale: number; rossi: number };

function KpiBox({ label, value, color }: { label: string; value: number | string; color?: string }) {
  return (
    <div className="bg-gray-50 rounded p-3 text-center">
      <div className={`text-xl font-bold ${color ?? "text-gray-800"}`}>{value}</div>
      <div className="text-xs text-gray-500 mt-0.5">{label}</div>
    </div>
  );
}

function SnapSection({ title, children, defaultOpen = true }: { title: string; children: React.ReactNode; defaultOpen?: boolean }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="border border-gray-200 rounded overflow-hidden">
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full text-left px-4 py-2 bg-gray-50 text-xs font-semibold text-gray-700 flex justify-between items-center hover:bg-gray-100"
      >
        {title}
        <span className="text-gray-400">{open ? "▲" : "▼"}</span>
      </button>
      {open && <div className="px-4 py-3">{children}</div>}
    </div>
  );
}

function ReviewDetail({ review, onClose }: { review: ManagementReview; onClose: () => void }) {
  const qc = useQueryClient();
  const [note, setNote] = useState("");
  const [snapshotError, setSnapshotError] = useState("");
  const [approveError, setApproveError] = useState("");
  const [downloading, setDownloading] = useState(false);

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

  async function handleDownload() {
    setDownloading(true);
    try {
      const date = review.review_date?.replace(/-/g, "") ?? "";
      await managementReviewApi.downloadReport(review.id, `riesame_${review.id}_${date}.html`);
    } finally {
      setDownloading(false);
    }
  }

  const snap = review.snapshot_data as Record<string, any>;
  const frameworks = snap?.frameworks as Record<string, SnapFramework> | undefined;
  const documenti = snap?.documenti as Record<string, number> | undefined;
  const rischi = snap?.rischi as Record<string, number> | undefined;
  const ownerList = snap?.risks_by_owner as SnapOwner[] | undefined;
  const incidenti = snap?.incidenti as Record<string, number> | undefined;
  const pdca = snap?.pdca as Record<string, number> | undefined;
  const bcp = snap?.bcp as { processi_critici_senza_bcp: number; nomi: string[] } | undefined;
  const task = snap?.task as Record<string, number> | undefined;

  const isApproved = review.approval_status === "approvato";
  const hasSnapshot = !!review.snapshot_generated_at;

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl flex flex-col max-h-[90vh]">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100 shrink-0">
          <div>
            <h3 className="text-lg font-semibold text-gray-900">{review.title}</h3>
            <p className="text-xs text-gray-400 mt-0.5">Data riunione: {review.review_date}</p>
          </div>
          <div className="flex items-center gap-2">
            {hasSnapshot && (
              <button
                onClick={handleDownload}
                disabled={downloading}
                className="px-3 py-1.5 bg-indigo-600 text-white rounded text-xs hover:bg-indigo-700 disabled:opacity-50 flex items-center gap-1"
              >
                {downloading ? "Download..." : "Scarica relazione CISO"}
              </button>
            )}
            <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-2xl w-8 h-8 flex items-center justify-center rounded hover:bg-gray-100">×</button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">

          {/* Snapshot generation */}
          <section>
            <h4 className="text-sm font-semibold text-gray-700 mb-3">Dati riesame</h4>
            {!hasSnapshot ? (
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
                  Snapshot generato il {new Date(review.snapshot_generated_at!).toLocaleString(i18n.language || "it")} — questi dati sono congelati
                </p>

                {frameworks && Object.keys(frameworks).length > 0 && (
                  <SnapSection title="Compliance per framework">
                    <div className="space-y-2">
                      {Object.entries(frameworks).map(([code, fw]) => {
                        const color = fw.pct_compliant >= 80 ? "bg-green-500" : fw.pct_compliant >= 60 ? "bg-yellow-400" : "bg-red-500";
                        return (
                          <div key={code}>
                            <div className="flex justify-between text-xs mb-0.5">
                              <span className="font-medium text-gray-700">{code} — {fw.framework_name}</span>
                              <span className="font-semibold">{fw.pct_compliant}% ({fw.by_status?.compliant ?? 0}/{fw.total})</span>
                            </div>
                            <div className="h-2 bg-gray-200 rounded overflow-hidden">
                              <div className={`h-full ${color}`} style={{ width: `${fw.pct_compliant}%` }} />
                            </div>
                            {fw.expired_evidence_count > 0 && (
                              <p className="text-xs text-amber-600 mt-0.5">{fw.expired_evidence_count} evidenze scadute</p>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </SnapSection>
                )}

                {rischi && (
                  <SnapSection title="Profilo di rischio">
                    <div className="grid grid-cols-4 gap-2">
                      <KpiBox label="Critici" value={rischi.rosso ?? 0} color="text-red-600" />
                      <KpiBox label="Medi" value={rischi.giallo ?? 0} color="text-yellow-600" />
                      <KpiBox label="Bassi" value={rischi.verde ?? 0} color="text-green-600" />
                      <KpiBox label="Critici senza piano" value={rischi.senza_piano ?? 0} color="text-red-600" />
                    </div>
                    {(rischi.senza_owner ?? 0) > 0 && (
                      <p className="text-xs text-amber-600 mt-2">{rischi.senza_owner} rischi senza owner assegnato</p>
                    )}
                  </SnapSection>
                )}

                {ownerList && ownerList.length > 0 && (
                  <SnapSection title="Rischi per owner" defaultOpen={false}>
                    <table className="w-full text-xs">
                      <thead><tr className="border-b border-gray-200"><th className="text-left py-1 font-medium text-gray-600">Owner</th><th className="text-right py-1 font-medium text-gray-600">Tot</th><th className="text-right py-1 font-medium text-gray-600">Critici</th></tr></thead>
                      <tbody>
                        {ownerList.map((o, i) => {
                          const name = `${o.owner__first_name} ${o.owner__last_name}`.trim() || o.owner__email || "—";
                          return (
                            <tr key={i} className="border-b border-gray-100">
                              <td className="py-1 text-gray-700">{name}</td>
                              <td className="py-1 text-right">{o.totale}</td>
                              <td className="py-1 text-right text-red-600 font-medium">{o.rossi}</td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </SnapSection>
                )}

                {documenti && (
                  <SnapSection title="Documenti e evidenze" defaultOpen={false}>
                    <div className="grid grid-cols-4 gap-2">
                      <KpiBox label="Approvati" value={documenti.approvati ?? 0} />
                      <KpiBox label="In scadenza (90gg)" value={documenti.in_scadenza ?? 0} color="text-yellow-600" />
                      <KpiBox label="Scaduti" value={documenti.scaduti ?? 0} color="text-red-600" />
                      <KpiBox label="Evidenze scadute" value={documenti.evidenze_scadute ?? 0} color="text-red-600" />
                    </div>
                  </SnapSection>
                )}

                {incidenti && (
                  <SnapSection title="Incidenti (ultimi 12 mesi)" defaultOpen={false}>
                    <div className="grid grid-cols-4 gap-2">
                      <KpiBox label="Totale" value={incidenti.totale_12m ?? 0} />
                      <KpiBox label="NIS2" value={incidenti.nis2_notificati ?? 0} color="text-red-600" />
                      <KpiBox label="Aperti" value={incidenti.aperti ?? 0} color="text-orange-600" />
                      <KpiBox label="Chiusi senza RCA" value={incidenti.senza_rca ?? 0} color="text-amber-600" />
                    </div>
                  </SnapSection>
                )}

                {pdca && (
                  <SnapSection title="PDCA e task" defaultOpen={false}>
                    <div className="grid grid-cols-4 gap-2">
                      <KpiBox label="PDCA aperti" value={pdca.aperti ?? 0} />
                      <KpiBox label="Bloccati >90gg" value={pdca.bloccati_plan_90gg ?? 0} color="text-red-600" />
                      <KpiBox label="Chiusi 12m" value={pdca.chiusi_12m ?? 0} color="text-green-600" />
                      <KpiBox label="Task scaduti" value={task?.scaduti ?? 0} color="text-red-600" />
                    </div>
                  </SnapSection>
                )}

                {bcp && bcp.processi_critici_senza_bcp > 0 && (
                  <SnapSection title="BCP" defaultOpen={false}>
                    <p className="text-xs text-red-600 font-medium">{bcp.processi_critici_senza_bcp} processi critici senza piano BCP</p>
                    {bcp.nomi.length > 0 && <p className="text-xs text-gray-600 mt-1">{bcp.nomi.join(", ")}</p>}
                  </SnapSection>
                )}
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
                  Approvato il {new Date(review.approved_at).toLocaleString(i18n.language || "it")}
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
                  disabled={approveMutation.isPending || !hasSnapshot}
                  title={!hasSnapshot ? "Genera prima lo snapshot dei dati" : undefined}
                  className="px-4 py-2 bg-green-600 text-white rounded text-sm hover:bg-green-700 disabled:opacity-50"
                >
                  {approveMutation.isPending ? "Approvazione..." : "Approva riesame"}
                </button>
                {!hasSnapshot && (
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
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);
  const qc = useQueryClient();

  const deleteMutation = useMutation({
    mutationFn: (id: string) => managementReviewApi.delete(id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["management-review"] }); setConfirmDelete(null); },
  });

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
        <h2 className="text-xl font-semibold text-gray-900 flex items-center">
          Governance — Revisione Direzione
          <ModuleHelp
            title="Revisione di Direzione — M13"
            description="Gestisce il riesame periodico del management ISMS.
    Genera uno snapshot congelato dei dati GRC al momento della riunione
    e produce la relazione formale del CISO scaricabile."
            steps={[
              "Crea la revisione con titolo, plant e data riunione",
              "Premi 'Genera snapshot dati': i KPI vengono congelati in quel momento",
              "Presenta i dati in riunione — lo snapshot non cambierà più",
              "Le delibere vengono registrate come ReviewAction con owner e scadenza",
              "Approva il riesame con nota formale",
              "Scarica la relazione CISO in HTML (stampabile/archiviabile)",
            ]}
            connections={[
              { module: "M06 Risk", relation: "Rischi per livello e per owner nello snapshot" },
              { module: "M09 Incidenti", relation: "Incidenti ultimi 12 mesi nello snapshot" },
              { module: "M11 PDCA", relation: "PDCA aperti e bloccati nello snapshot" },
            ]}
            configNeeded={["Nominare il CISO come chair in M00 Governance"]}
          />
        </h2>
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
                      ? <span className="text-green-600">✓ {new Date(r.snapshot_generated_at).toLocaleDateString(i18n.language || "it")}</span>
                      : <span className="text-gray-400">—</span>}
                  </td>
                  <td className="px-4 py-3 text-gray-500 text-xs">{r.review_date}</td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-3">
                      <button onClick={() => setSelected(r)} className="text-xs text-primary-600 hover:underline">Dettaglio</button>
                      {confirmDelete === r.id ? (
                        <span className="flex items-center gap-1">
                          <button
                            onClick={() => deleteMutation.mutate(r.id)}
                            disabled={deleteMutation.isPending}
                            className="text-xs text-white bg-red-600 hover:bg-red-700 px-2 py-0.5 rounded disabled:opacity-50"
                          >
                            Conferma
                          </button>
                          <button onClick={() => setConfirmDelete(null)} className="text-xs text-gray-500 hover:underline">Annulla</button>
                        </span>
                      ) : (
                        <button
                          onClick={() => setConfirmDelete(r.id)}
                          className="text-xs text-red-500 hover:text-red-700 hover:underline"
                        >
                          Elimina
                        </button>
                      )}
                    </div>
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
