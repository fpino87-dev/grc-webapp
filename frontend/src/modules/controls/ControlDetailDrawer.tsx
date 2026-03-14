import { useState, useEffect, useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { controlsApi, type EvidenceRef, type LinkedDocument, type RequirementsCheck } from "../../api/endpoints/controls";
import { documentsApi, EVIDENCE_TYPE_LABELS } from "../../api/endpoints/documents";
import { useAuthStore } from "../../store/auth";

// ─── Helpers ──────────────────────────────────────────────────────────────────

function evidenceIcon(type: string): string {
  const map: Record<string, string> = {
    screenshot: "📸", log: "📋", report: "📄",
    verbale: "📝", certificato: "🏆", test_result: "🧪", altro: "📎",
  };
  return map[type] ?? "📎";
}

function docStatusColor(status: string): string {
  const map: Record<string, string> = {
    approvato:   "bg-green-100 text-green-800",
    revisione:   "bg-blue-100 text-blue-700",
    approvazione:"bg-blue-100 text-blue-700",
    bozza:       "bg-gray-100 text-gray-600",
    archiviato:  "bg-gray-200 text-gray-500",
  };
  return map[status] ?? "bg-gray-100 text-gray-500";
}

function ExpiryBadge({ validUntil }: { validUntil: string | null }) {
  if (!validUntil) return <span className="text-gray-400 text-xs">Nessuna scadenza</span>;
  const date = new Date(validUntil);
  const today = new Date();
  const days = Math.ceil((date.getTime() - today.getTime()) / 86400000);
  if (days < 0) return <span className="text-xs px-1.5 py-0.5 rounded bg-red-100 text-red-700 font-medium">Scaduta {Math.abs(days)}g fa</span>;
  if (days <= 30) return <span className="text-xs px-1.5 py-0.5 rounded bg-orange-100 text-orange-700 font-medium">Scade in {days}g</span>;
  return <span className="text-xs px-1.5 py-0.5 rounded bg-green-100 text-green-700 font-medium">Valida fino al {date.toLocaleDateString("it-IT")}</span>;
}

const STATUS_GUIDE = [
  { status: "compliant",    icon: "🟢", label: "Compliant",     req: "Evidenza valida non scaduta + data ultima verifica", badge: "bg-green-100 text-green-800" },
  { status: "parziale",     icon: "🟡", label: "Parziale",      req: "Evidenza anche parziale + piano di remediation (task M08)", badge: "bg-yellow-100 text-yellow-800" },
  { status: "gap",          icon: "🔴", label: "Gap",           req: "Nessuno per salvare — task remediation generato automaticamente", badge: "bg-red-100 text-red-800" },
  { status: "na",           icon: "⚪", label: "N/A",           req: "Giustificazione scritta min 20 caratteri. TISAX L3: doppia approvazione", badge: "bg-gray-100 text-gray-600" },
  { status: "non_valutato", icon: "⬜", label: "Non valutato",  req: "Abbassa il compliance score del plant", badge: "bg-gray-50 text-gray-500" },
];

type Tab = "cosa" | "valutare" | "docevidence" | "storico";

// ─── Tab 1: Cos'è ─────────────────────────────────────────────────────────────

function TabCosa({ info }: { info: NonNullable<ReturnType<typeof useDetailInfo>["data"]> }) {
  const [guidanceOpen, setGuidanceOpen] = useState(false);
  return (
    <div className="space-y-4">
      <div>
        <div className="flex flex-wrap gap-2 mb-2">
          <span className="px-2 py-0.5 text-xs font-semibold bg-blue-100 text-blue-800 rounded">{info.framework}</span>
          {info.level && <span className="px-2 py-0.5 text-xs bg-purple-100 text-purple-700 rounded">{info.level}</span>}
          {info.control_category && <span className="px-2 py-0.5 text-xs bg-teal-100 text-teal-700 rounded capitalize">{info.control_category}</span>}
          {info.domain && <span className="px-2 py-0.5 text-xs bg-gray-100 text-gray-600 rounded">{info.domain}</span>}
        </div>
        <h3 className="text-base font-semibold text-gray-900 leading-snug">{info.title}</h3>
        <p className="text-xs font-mono text-gray-400 mt-0.5">{info.control_id}</p>
      </div>

      {info.description ? (
        <div className="bg-blue-50 rounded-lg p-3 text-sm text-gray-700 leading-relaxed">
          {info.description}
        </div>
      ) : (
        <p className="text-sm text-gray-400 italic">Nessuna descrizione disponibile per questa lingua.</p>
      )}

      {info.implementation_guidance && (
        <div className="border border-gray-200 rounded-lg">
          <button
            onClick={() => setGuidanceOpen(o => !o)}
            className="w-full flex items-center justify-between px-3 py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            <span>Linee guida implementazione</span>
            <span className="text-gray-400">{guidanceOpen ? "▲" : "▼"}</span>
          </button>
          {guidanceOpen && (
            <div className="px-3 pb-3 text-sm text-gray-600 leading-relaxed border-t border-gray-100 pt-2">
              {info.implementation_guidance}
            </div>
          )}
        </div>
      )}

      {info.evidence_examples.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Esempi di evidenza accettabile</p>
          <div className="space-y-1.5">
            {info.evidence_examples.map((ex, i) => {
              const icon = ex.toLowerCase().includes("screenshot") ? "📸"
                : ex.toLowerCase().includes("log") ? "📋"
                : ex.toLowerCase().includes("certificat") ? "🏆"
                : "📄";
              return (
                <div key={i} className="flex items-center gap-2 text-sm text-gray-700">
                  <span>{icon}</span><span>{ex}</span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {info.mappings.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Mappature cross-framework</p>
          <div className="flex flex-wrap gap-1.5">
            {info.mappings.map((m, i) => (
              <span key={i} className="text-xs bg-indigo-50 border border-indigo-100 text-indigo-700 px-2 py-0.5 rounded">
                {m.relationship} → {m["target_control__framework__code"]} {m["target_control__external_id"]}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Tab 2: Come valutare ─────────────────────────────────────────────────────

function TabValutare({ instanceId, requirements }: { instanceId: string; requirements: RequirementsCheck }) {
  const qc = useQueryClient();
  const [selectedStatus, setSelectedStatus] = useState("");
  const [note, setNote] = useState("");
  const [blockError, setBlockError] = useState("");

  const mutation = useMutation({
    mutationFn: () => controlsApi.evaluate(instanceId, selectedStatus, note),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["controls"] });
      qc.invalidateQueries({ queryKey: ["control-detail", instanceId] });
      setBlockError("");
    },
    onError: (e: unknown) => {
      const msg = (e as { response?: { data?: { error?: string } } })?.response?.data?.error ?? "Errore sconosciuto";
      setBlockError(msg);
    },
  });

  const reqNotSatisfied = selectedStatus === "compliant" && !requirements.satisfied;

  return (
    <div className="space-y-4">
      <div className="rounded-lg border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="text-left px-3 py-2 text-xs font-medium text-gray-500 w-8"></th>
              <th className="text-left px-3 py-2 text-xs font-medium text-gray-500">Stato</th>
              <th className="text-left px-3 py-2 text-xs font-medium text-gray-500">Requisiti</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {STATUS_GUIDE.map(s => (
              <tr key={s.status} className="hover:bg-gray-50">
                <td className="px-3 py-2 text-base">{s.icon}</td>
                <td className="px-3 py-2">
                  <span className={`inline-flex px-2 py-0.5 rounded text-xs font-medium ${s.badge}`}>{s.label}</span>
                </td>
                <td className="px-3 py-2 text-xs text-gray-500 leading-snug">{s.req}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="border border-gray-200 rounded-lg p-3 space-y-3">
        <p className="text-sm font-medium text-gray-700">Cambia stato valutazione</p>

        <select
          value={selectedStatus}
          onChange={e => { setSelectedStatus(e.target.value); setBlockError(""); }}
          className="w-full border rounded px-3 py-2 text-sm"
        >
          <option value="">— seleziona nuovo stato —</option>
          {STATUS_GUIDE.map(s => <option key={s.status} value={s.status}>{s.icon} {s.label}</option>)}
        </select>

        {reqNotSatisfied && (
          <div className="bg-red-50 border border-red-200 rounded-lg px-3 py-2 text-xs text-red-700">
            <p className="font-semibold mb-1">⛔ Requisiti non soddisfatti — risolvi nel tab "Documenti & Evidenze"</p>
            {requirements.missing_documents.map((m, i) => <p key={i}>• Documento mancante: {m.description || m.type}</p>)}
            {requirements.missing_evidences.map((m, i) => <p key={i}>• Evidenza mancante: {m.description || m.type}</p>)}
            {requirements.expired_evidences.map((e, i) => <p key={i}>• Scaduta: {e.title} ({e.expired_on})</p>)}
          </div>
        )}

        <textarea
          value={note}
          onChange={e => setNote(e.target.value)}
          placeholder="Nota / giustificazione (obbligatoria per N/A, min 20 caratteri)"
          className="w-full border rounded px-3 py-2 text-sm resize-none"
          rows={3}
        />

        {blockError && (
          <div className="bg-red-50 border border-red-200 rounded-lg px-3 py-2 text-sm text-red-700">
            <span className="mr-1">⛔</span>{blockError}
          </div>
        )}

        <button
          onClick={() => mutation.mutate()}
          disabled={mutation.isPending || !selectedStatus || reqNotSatisfied}
          title={reqNotSatisfied ? "Risolvi i requisiti nel tab Documenti & Evidenze" : undefined}
          className="w-full py-2 bg-blue-600 text-white rounded text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
        >
          {mutation.isPending ? "Salvataggio..." : "Salva valutazione"}
        </button>
      </div>
    </div>
  );
}

// ─── Tab 3: Documenti & Evidenze ─────────────────────────────────────────────

function useDebounce(value: string, delay = 300) {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(t);
  }, [value, delay]);
  return debounced;
}

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
  const qc = useQueryClient();
  const [searchQ, setSearchQ] = useState("");
  const debounced = useDebounce(searchQ);

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
        <span className="text-xs font-semibold text-gray-700 uppercase tracking-wide">Documenti di policy</span>
        <span className="ml-auto text-xs bg-gray-100 text-gray-600 px-1.5 rounded">{documents.length}</span>
      </div>

      {/* Requisiti mancanti */}
      {requirements.missing_documents.length > 0 && (
        <div className="space-y-1">
          {requirements.missing_documents.map((m, i) => (
            <div key={i} className="flex items-center gap-1.5 text-xs bg-red-50 border border-red-200 rounded px-2 py-1">
              <span className="text-red-500 font-bold shrink-0">!</span>
              <span className="text-red-700">{m.description || m.type}</span>
              <span className="ml-auto text-xs text-red-500 font-medium shrink-0">Mancante</span>
            </div>
          ))}
        </div>
      )}

      {/* Lista documenti collegati */}
      {documents.length === 0 ? (
        <p className="text-xs text-gray-400 italic">Nessun documento collegato</p>
      ) : (
        <div className="space-y-1.5">
          {documents.map(d => (
            <div key={d.id} className="bg-white border border-gray-200 rounded px-2.5 py-2">
              <div className="flex items-start justify-between gap-1">
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-medium text-gray-800 truncate">{d.title}</p>
                  <div className="flex items-center gap-1 mt-0.5 flex-wrap">
                    <span className="text-xs bg-indigo-50 text-indigo-700 px-1 rounded">{d.document_type}</span>
                    <span className={`text-xs px-1 rounded ${docStatusColor(d.status)}`}>{d.status}</span>
                    {d.review_due_date && (
                      <span className="text-xs text-gray-400">rev. {new Date(d.review_due_date).toLocaleDateString("it-IT")}</span>
                    )}
                  </div>
                </div>
                <button
                  onClick={() => unlinkMut.mutate(d.id)}
                  disabled={unlinkMut.isPending}
                  className="text-red-400 hover:text-red-600 text-xs shrink-0 ml-1"
                  title="Scollega"
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
        <p className="text-xs font-medium text-gray-500">Collega documento</p>
        <input
          type="text"
          value={searchQ}
          onChange={e => setSearchQ(e.target.value)}
          placeholder="Cerca per titolo..."
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
                <span className="truncate flex-1">{d.title}</span>
                <span className={`shrink-0 px-1 rounded text-xs ${docStatusColor(d.status)}`}>{d.status}</span>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function EvidencesColumn({
  instanceId,
  evidences,
  requirements,
}: {
  instanceId: string;
  evidences: EvidenceRef[];
  requirements: RequirementsCheck;
}) {
  const qc = useQueryClient();
  const [searchQ, setSearchQ] = useState("");
  const [newEv, setNewEv] = useState({ title: "", evidence_type: "altro", valid_until: "" });
  const debounced = useDebounce(searchQ);
  const today = new Date().toISOString().split("T")[0];

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
  const createAndLinkMut = useMutation({
    mutationFn: async () => {
      const ev = await documentsApi.createEvidence(newEv);
      return controlsApi.linkEvidence(instanceId, ev.id);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["control-detail", instanceId] });
      setNewEv({ title: "", evidence_type: "altro", valid_until: "" });
    },
  });

  const linkedEvIds = new Set(evidences.map(e => e.id));

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 mb-1">
        <span className="text-base">🔬</span>
        <span className="text-xs font-semibold text-gray-700 uppercase tracking-wide">Evidenze operative</span>
        <span className="ml-auto text-xs bg-gray-100 text-gray-600 px-1.5 rounded">{evidences.length}</span>
      </div>

      {/* Requisiti mancanti */}
      {requirements.missing_evidences.length > 0 && (
        <div className="space-y-1">
          {requirements.missing_evidences.map((m, i) => (
            <div key={i} className="flex items-center gap-1.5 text-xs bg-red-50 border border-red-200 rounded px-2 py-1">
              <span className="text-red-500 font-bold shrink-0">!</span>
              <span className="text-red-700">{m.description || m.type}</span>
              <span className="ml-auto text-xs text-red-500 font-medium shrink-0">Mancante</span>
            </div>
          ))}
        </div>
      )}

      {/* Lista evidenze collegate */}
      {evidences.length === 0 ? (
        <p className="text-xs text-gray-400 italic">Nessuna evidenza collegata</p>
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
                  title="Scollega"
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
        <p className="text-xs font-medium text-gray-500">Collega evidenza esistente</p>
        <input
          type="text"
          value={searchQ}
          onChange={e => setSearchQ(e.target.value)}
          placeholder="Cerca per titolo..."
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

      {/* Carica nuova evidenza */}
      <div className="border border-dashed border-green-300 rounded p-2 space-y-1.5">
        <p className="text-xs font-medium text-green-700">Carica nuova evidenza</p>
        <input
          type="text"
          placeholder="Titolo *"
          value={newEv.title}
          onChange={e => setNewEv(p => ({ ...p, title: e.target.value }))}
          className="w-full border rounded px-2 py-1 text-xs"
        />
        <select
          value={newEv.evidence_type}
          onChange={e => setNewEv(p => ({ ...p, evidence_type: e.target.value }))}
          className="w-full border rounded px-2 py-1 text-xs"
        >
          {Object.entries(EVIDENCE_TYPE_LABELS).map(([v, l]) => (
            <option key={v} value={v}>{evidenceIcon(v)} {l}</option>
          ))}
        </select>
        <div>
          <label className="text-xs text-gray-500 block mb-0.5">Data validità * (non passata)</label>
          <input
            type="date"
            min={today}
            value={newEv.valid_until}
            onChange={e => setNewEv(p => ({ ...p, valid_until: e.target.value }))}
            className="w-full border rounded px-2 py-1 text-xs"
          />
        </div>
        <button
          onClick={() => createAndLinkMut.mutate()}
          disabled={createAndLinkMut.isPending || !newEv.title || !newEv.valid_until}
          className="w-full py-1 bg-green-600 text-white text-xs rounded hover:bg-green-700 disabled:opacity-50"
        >
          {createAndLinkMut.isPending ? "Caricamento..." : "Carica e collega"}
        </button>
      </div>
    </div>
  );
}

function TabDocEvidence({
  instanceId,
  evidences,
  documents,
  requirements,
}: {
  instanceId: string;
  evidences: EvidenceRef[];
  documents: LinkedDocument[];
  requirements: RequirementsCheck;
}) {
  const plant = useAuthStore(s => s.selectedPlant?.id ?? null);

  return (
    <div className="space-y-3">
      {/* Banner requisiti */}
      {!requirements.satisfied ? (
        <div className="bg-red-50 border border-red-200 rounded-lg px-3 py-2 text-xs text-red-800">
          <p className="font-semibold mb-1">⛔ Requisiti non soddisfatti per Compliant</p>
          {requirements.missing_documents.map((m, i) => <p key={i}>• Documento mancante: {m.description || m.type}</p>)}
          {requirements.missing_evidences.map((m, i) => <p key={i}>• Evidenza mancante: {m.description || m.type}</p>)}
          {requirements.expired_evidences.map((e, i) => <p key={i}>• Evidenza scaduta: {e.title} ({e.expired_on})</p>)}
        </div>
      ) : requirements.warnings.length > 0 ? (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg px-3 py-2 text-xs text-yellow-800">
          <p className="font-semibold mb-1">⚠️ Attenzione</p>
          {requirements.warnings.map((w, i) => <p key={i}>• {w}</p>)}
        </div>
      ) : (
        <div className="bg-green-50 border border-green-200 rounded-lg px-3 py-2 text-xs text-green-800">
          ✅ Tutti i requisiti soddisfatti
        </div>
      )}

      {/* Due colonne */}
      <div className="grid grid-cols-2 gap-3">
        <DocsColumn instanceId={instanceId} documents={documents} requirements={requirements} plant={plant} />
        <EvidencesColumn instanceId={instanceId} evidences={evidences} requirements={requirements} />
      </div>
    </div>
  );
}

// ─── Tab 4: Storico ───────────────────────────────────────────────────────────

function TabStorico({ history }: { history: NonNullable<ReturnType<typeof useDetailInfo>["data"]>["evaluation_history"] }) {
  if (history.length === 0) {
    return <p className="text-sm text-gray-400 italic">Nessuna valutazione registrata.</p>;
  }
  const statusIcon: Record<string, string> = {
    compliant: "🟢", parziale: "🟡", gap: "🔴", na: "⚪", non_valutato: "⬜",
  };
  return (
    <div className="relative">
      <div className="absolute left-3.5 top-0 bottom-0 w-px bg-gray-200" />
      <div className="space-y-4">
        {history.map((h, i) => {
          const status = (h.payload as Record<string, string>)["new_status"] ?? "";
          const note = (h.payload as Record<string, string>)["note"] ?? "";
          return (
            <div key={i} className="relative pl-8">
              <div className="absolute left-1.5 top-1 w-4 h-4 rounded-full bg-white border-2 border-gray-300 flex items-center justify-center text-xs">
                {statusIcon[status] ?? "•"}
              </div>
              <div className="bg-gray-50 border border-gray-200 rounded-lg px-3 py-2">
                <div className="flex items-center justify-between mb-0.5">
                  <span className="text-xs font-medium text-gray-700">{h.user_email_at_time}</span>
                  <span className="text-xs text-gray-400">{new Date(h.timestamp_utc).toLocaleString("it-IT")}</span>
                </div>
                <p className="text-xs text-gray-600">
                  ha impostato <strong>{status}</strong>
                  {note && <> — <em>"{note}"</em></>}
                </p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ─── Custom hook ──────────────────────────────────────────────────────────────

function useDetailInfo(instanceId: string | null) {
  return useQuery({
    queryKey: ["control-detail", instanceId],
    queryFn: () => controlsApi.detailInfo(instanceId!),
    enabled: !!instanceId,
    retry: false,
  });
}

// ─── Main drawer ─────────────────────────────────────────────────────────────

interface Props {
  instanceId: string | null;
  onClose: () => void;
}

export function ControlDetailDrawer({ instanceId, onClose }: Props) {
  const [tab, setTab] = useState<Tab>("cosa");
  const { data: info, isLoading } = useDetailInfo(instanceId);
  const qc = useQueryClient();
  const open = !!instanceId;

  const tabs: [Tab, string][] = [
    ["cosa",        "Cos'è"],
    ["valutare",    "Come valutare"],
    ["docevidence", "Documenti & Evidenze"],
    ["storico",     "Storico"],
  ];

  return (
    <>
      {open && <div className="fixed inset-0 bg-black/30 z-40" onClick={onClose} />}
      <div
        className={`fixed top-0 right-0 h-full z-50 bg-white shadow-2xl flex flex-col transition-transform duration-300 ease-in-out ${open ? "translate-x-0" : "translate-x-full"}`}
        style={{ width: 560 }}
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100 shrink-0 bg-gradient-to-r from-slate-700 to-slate-800">
          <div>
            <h2 className="text-white font-semibold text-base">Dettaglio controllo</h2>
            <p className="text-slate-300 text-xs mt-0.5">
              {isLoading ? "Caricamento..." : info ? `${info.control_id} — ${info.framework}` : "—"}
            </p>
          </div>
          <button onClick={onClose} className="text-white/80 hover:text-white w-8 h-8 flex items-center justify-center rounded hover:bg-white/10 text-xl">×</button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-gray-200 shrink-0">
          {tabs.map(([t, label]) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`flex-1 py-2.5 text-xs font-medium transition-colors ${
                tab === t
                  ? "border-b-2 border-slate-700 text-slate-800 bg-slate-50"
                  : "text-gray-500 hover:text-gray-700 hover:bg-gray-50"
              }`}
            >
              {label}
              {t === "docevidence" && info && !info.requirements.satisfied && (
                <span className="ml-1 inline-flex w-2 h-2 bg-red-500 rounded-full" />
              )}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-5 py-4">
          {isLoading && <div className="text-center text-gray-400 py-8">Caricamento...</div>}
          {!isLoading && info && (
            <>
              {tab === "cosa"        && <TabCosa info={info} />}
              {tab === "valutare"    && <TabValutare instanceId={instanceId!} requirements={info.requirements} />}
              {tab === "docevidence" && (
                <TabDocEvidence
                  instanceId={instanceId!}
                  evidences={info.current_evidences}
                  documents={info.linked_documents}
                  requirements={info.requirements}
                />
              )}
              {tab === "storico"     && <TabStorico history={info.evaluation_history} />}
            </>
          )}
        </div>
      </div>
    </>
  );
}
