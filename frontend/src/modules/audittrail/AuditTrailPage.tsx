import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { auditTrailApi, type AuditLogEntry } from "../../api/endpoints/auditTrail";

const LEVEL_COLORS: Record<string, string> = {
  L1: "bg-red-100 text-red-800",
  L2: "bg-yellow-100 text-yellow-800",
  L3: "bg-gray-100 text-gray-600",
};

export function AuditTrailPage() {
  const [levelFilter, setLevelFilter] = useState("");
  const [entityFilter, setEntityFilter] = useState("");

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
        <span className="text-xs text-gray-400 bg-gray-100 px-2 py-1 rounded">Sola lettura — append-only</span>
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
                    {new Date(e.timestamp_utc).toLocaleString("it-IT")}
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
    </div>
  );
}
