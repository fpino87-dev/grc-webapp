import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "../../api/client";
import { auditTrailApi, type AuditLogEntry } from "../../api/endpoints/auditTrail";
import i18n from "../../i18n";

const LEVEL_COLORS: Record<string, string> = {
  L1: "bg-red-100 text-red-800",
  L2: "bg-yellow-100 text-yellow-800",
  L3: "bg-gray-100 text-gray-600",
};

// ─── Guida ai livelli drawer ────────────────────────────────────────────────

function LevelCard({
  level, title, badge, description, examples, border, bg,
}: {
  level: string; title: string; badge: string; description: string;
  examples: { icon: string; text: string }[]; border: string; bg: string;
}) {
  return (
    <div className={`rounded-lg border-2 ${border} ${bg} p-4`}>
      <div className="flex items-center justify-between mb-2">
        <h4 className="font-bold text-gray-900">{title}</h4>
        <span className="text-xs font-medium px-2 py-0.5 rounded bg-white/70 text-gray-700 border border-gray-200">
          {badge}
        </span>
      </div>
      <p className="text-xs text-gray-700 mb-3 leading-relaxed">{description}</p>
      <ul className="space-y-1">
        {examples.map((ex, i) => (
          <li key={i} className="text-xs text-gray-600 flex items-start gap-1.5">
            <span>{ex.icon}</span>
            <span>{ex.text}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

type IntegrityResult = { status: "ok" | "error"; checked?: number; message: string; corrupted_id?: string; action_code?: string } | null;

function LevelsDrawer({ onClose }: { onClose: () => void }) {
  const [integrityResult, setIntegrityResult] = useState<IntegrityResult>(null);
  const [checking, setChecking] = useState(false);

  async function handleVerify() {
    setChecking(true);
    setIntegrityResult(null);
    try {
      const resp = await apiClient.get<IntegrityResult>("/audit-trail/verify-integrity/");
      setIntegrityResult(resp.data);
    } catch {
      setIntegrityResult({ status: "error", message: "Errore di connessione durante la verifica" });
    } finally {
      setChecking(false);
    }
  }

  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/30 z-40" onClick={onClose} />

      {/* Drawer */}
      <div className="fixed top-0 right-0 h-full w-[480px] bg-white z-50 shadow-2xl flex flex-col overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 shrink-0">
          <h3 className="text-lg font-bold text-gray-900">Guida ai livelli L</h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 w-8 h-8 flex items-center justify-center rounded hover:bg-gray-100 text-2xl"
          >
            ×
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-6 py-5 space-y-6">

          {/* Sezione 1 */}
          <section>
            <h4 className="text-sm font-bold text-gray-800 mb-2">Cosa sono i livelli L</h4>
            <p className="text-sm text-gray-600 leading-relaxed">
              Il sistema GRC classifica ogni evento registrato in uno dei tre
              livelli di retention e rilevanza normativa. Il livello determina
              per quanto tempo il record viene conservato e chi può accedervi.
            </p>
          </section>

          {/* Sezione 2 — Card livelli */}
          <section className="space-y-4">
            <LevelCard
              level="L1"
              title="L1 — Critico"
              badge="Conservazione 5 anni"
              bg="bg-red-50"
              border="border-red-300"
              description="Eventi ad alto impatto normativo che richiedono conservazione massima. Includono: approvazioni formali, chiusura incidenti NIS2, approvazione riesame di direzione, download di report ufficiali, accettazione rischi, token auditor esterni emessi o revocati."
              examples={[
                { icon: "🔴", text: "Incidente NIS2 chiuso" },
                { icon: "🔴", text: "Riesame di direzione approvato" },
                { icon: "🔴", text: "Rischio critico accettato formalmente" },
                { icon: "🔴", text: "Token auditor esterno creato/revocato" },
              ]}
            />

            <LevelCard
              level="L2"
              title="L2 — Operativo"
              badge="Conservazione 3 anni"
              bg="bg-orange-50"
              border="border-orange-300"
              description="Eventi operativi ordinari del ciclo GRC. Includono: valutazione controlli, creazione e aggiornamento assessment, snapshot generati, avanzamento fasi PDCA, task completati, caricamento evidenze, modifiche a plant e asset."
              examples={[
                { icon: "🟡", text: "Controllo valutato (compliant/gap/parziale)" },
                { icon: "🟡", text: "Risk assessment completato" },
                { icon: "🟡", text: "Snapshot riesame generato" },
                { icon: "🟡", text: "Ciclo PDCA avanzato di fase" },
                { icon: "🟡", text: "Evidenza caricata e collegata" },
              ]}
            />

            <LevelCard
              level="L3"
              title="L3 — Informativo"
              badge="Conservazione 1 anno"
              bg="bg-yellow-50"
              border="border-yellow-300"
              description="Eventi di consultazione e attività a basso impatto. Includono: accessi in lettura a dati sensibili, export di report non formali, ricerche nell'audit trail stesso, modifiche a preferenze utente, operazioni di sistema automatiche (Celery task, check notturni)."
              examples={[
                { icon: "⚪", text: "Accesso a dati riservati" },
                { icon: "⚪", text: "Export report non formale" },
                { icon: "⚪", text: "Task Celery notturno completato" },
                { icon: "⚪", text: "Preferenze utente modificate" },
              ]}
            />
          </section>

          {/* Sezione 3 — Perché è importante */}
          <section>
            <h4 className="text-sm font-bold text-gray-800 mb-2">Perché è importante</h4>
            <p className="text-sm text-gray-600 leading-relaxed">
              ISO 27001 (clausola A.12.4) e TISAX richiedono che i log
              di sicurezza siano protetti da manomissioni e conservati
              per un periodo adeguato. Ogni record nell'audit trail è
              protetto da una catena di hash SHA-256: qualsiasi tentativo
              di modifica o cancellazione è rilevabile automaticamente
              con il comando "Verifica integrità".
            </p>
          </section>

          {/* Verifica integrità */}
          <section className="border-t border-gray-200 pt-4">
            <button
              onClick={handleVerify}
              disabled={checking}
              className="w-full px-4 py-2.5 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 transition-colors"
            >
              {checking ? "Verifica in corso..." : "Verifica integrità audit trail"}
            </button>

            {integrityResult && (
              <div className={`mt-3 rounded-lg px-4 py-3 text-sm ${
                integrityResult.status === "ok"
                  ? "bg-green-50 border border-green-300 text-green-800"
                  : "bg-red-50 border border-red-300 text-red-800"
              }`}>
                <p className="font-semibold mb-0.5">
                  {integrityResult.status === "ok" ? "Integrità verificata" : "Anomalia rilevata"}
                </p>
                <p className="text-xs">{integrityResult.message}</p>
                {integrityResult.status === "ok" && integrityResult.checked !== undefined && (
                  <p className="text-xs mt-1 text-green-600">{integrityResult.checked} record controllati</p>
                )}
                {integrityResult.corrupted_id && (
                  <p className="text-xs mt-1 font-mono">ID: {integrityResult.corrupted_id}</p>
                )}
              </div>
            )}
          </section>
        </div>
      </div>
    </>
  );
}

// ─── Pagina principale ───────────────────────────────────────────────────────

export function AuditTrailPage() {
  const [levelFilter, setLevelFilter] = useState("");
  const [entityFilter, setEntityFilter] = useState("");
  const [showDrawer, setShowDrawer] = useState(false);

  const params: Record<string, string> = {};
  if (levelFilter) params.level = levelFilter;
  if (entityFilter) params.entity_type = entityFilter;

  const { data, isLoading } = useQuery({
    queryKey: ["audit-trail", levelFilter, entityFilter],
    queryFn: () => auditTrailApi.list(params),
    retry: false,
  });

  const entries: AuditLogEntry[] = data?.results ?? [];

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold text-gray-900">Audit Trail</h2>
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-400 bg-gray-100 px-2 py-1 rounded">Sola lettura — append-only</span>
          <button
            onClick={() => setShowDrawer(true)}
            className="px-3 py-1.5 bg-white border border-gray-300 rounded text-sm text-gray-700 hover:bg-gray-50 flex items-center gap-1.5"
          >
            <span>ℹ️</span>
            <span>Guida ai livelli</span>
          </button>
        </div>
      </div>

      <div className="mb-4 flex items-center gap-4">
        <div>
          <label className="text-xs text-gray-500 mr-1">Livello:</label>
          <select value={levelFilter} onChange={e => setLevelFilter(e.target.value)} className="border rounded px-2 py-1.5 text-sm">
            <option value="">Tutti</option>
            <option value="L1">L1 (critico)</option>
            <option value="L2">L2 (importante)</option>
            <option value="L3">L3 (info)</option>
          </select>
        </div>
        <div>
          <label className="text-xs text-gray-500 mr-1">Entità:</label>
          <input
            value={entityFilter}
            onChange={e => setEntityFilter(e.target.value)}
            placeholder="es. plant"
            className="border rounded px-2 py-1.5 text-sm w-32"
          />
        </div>
      </div>

      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-gray-400">Caricamento...</div>
        ) : entries.length === 0 ? (
          <div className="p-8 text-center text-gray-400">Nessun evento registrato</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Data/Ora</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Utente</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Azione</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Entità</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Livello</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {entries.map(e => (
                <tr key={e.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3 text-gray-500 text-xs font-mono whitespace-nowrap">
                    {new Date(e.timestamp_utc).toLocaleString(i18n.language || "it")}
                  </td>
                  <td className="px-4 py-3 text-gray-700 text-xs">{e.user_email_at_time}</td>
                  <td className="px-4 py-3 font-mono text-xs text-gray-600">{e.action_code}</td>
                  <td className="px-4 py-3 text-xs">
                    <span className="bg-blue-50 text-blue-700 px-1.5 py-0.5 rounded">{e.entity_type}</span>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${LEVEL_COLORS[e.level] ?? "bg-gray-100 text-gray-600"}`}>
                      {e.level}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {showDrawer && <LevelsDrawer onClose={() => setShowDrawer(false)} />}
    </div>
  );
}
