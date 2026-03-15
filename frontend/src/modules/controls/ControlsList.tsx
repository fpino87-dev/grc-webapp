import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { controlsApi, type ControlInstance } from "../../api/endpoints/controls";
import { useAuthStore } from "../../store/auth";
import { StatusBadge } from "../../components/ui/StatusBadge";
import { ControlDetailDrawer } from "./ControlDetailDrawer";

const STATUS_OPTIONS = ["compliant", "parziale", "gap", "na", "non_valutato"];

const RELATIONSHIP_LABEL: Record<string, string> = {
  covers:      "copre",
  extends:     "estende",
  equivalente: "≡",
  parziale:    "⊂",
  correlato:   "~",
};

function MappingBadges({ mappings }: { mappings: ControlInstance["mapped_controls"] }) {
  if (!mappings?.length) return null;
  return (
    <div className="flex flex-wrap gap-1 mt-1">
      {mappings.map((m, i) => (
        <span
          key={i}
          title={`${RELATIONSHIP_LABEL[m.relationship] ?? m.relationship} ${m.external_id}`}
          className="inline-flex items-center gap-0.5 text-xs bg-indigo-50 text-indigo-600 border border-indigo-100 rounded px-1.5 py-0.5"
        >
          <span className="opacity-60">{RELATIONSHIP_LABEL[m.relationship] ?? m.relationship}</span>
          <span className="font-mono">{m.framework_code}</span>
        </span>
      ))}
    </div>
  );
}

function InlineStatusSelect({ instance }: { instance: ControlInstance }) {
  const qc = useQueryClient();
  const [editing, setEditing] = useState(false);
  const [propagated, setPropagated] = useState<number | null>(null);

  const updateMutation = useMutation({
    mutationFn: (status: string) => controlsApi.updateInstance(instance.id, { status: status as ControlInstance["status"] }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["controls"] });
      setEditing(false);
    },
  });

  const propagateMutation = useMutation({
    mutationFn: () => controlsApi.propagate(instance.id),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ["controls"] });
      setPropagated(data.propagated_to);
      setTimeout(() => setPropagated(null), 3000);
    },
  });

  const hasMappings = instance.mapped_controls?.length > 0;

  if (editing) {
    return (
      <select
        autoFocus
        defaultValue={instance.status}
        onChange={e => updateMutation.mutate(e.target.value)}
        onBlur={() => setEditing(false)}
        className="border rounded px-1 py-0.5 text-xs"
      >
        {STATUS_OPTIONS.map(s => <option key={s} value={s}>{s}</option>)}
      </select>
    );
  }

  return (
    <div className="flex items-center gap-2 flex-wrap">
      <button onClick={() => setEditing(true)} title="Clicca per modificare" className="group flex items-center gap-1">
        <StatusBadge status={instance.status} />
        <span className="text-gray-300 group-hover:text-gray-500 text-xs">✎</span>
      </button>
      {instance.suggestion_differs && instance.suggested_status && (
        <span
          title={`Suggerimento sistema: ${instance.suggested_status}`}
          className="text-xs px-1.5 py-0.5 rounded border border-dashed border-indigo-300 text-indigo-500"
        >
          → {instance.suggested_status}
        </span>
      )}
      {hasMappings && instance.status !== "non_valutato" && (
        <button
          onClick={() => propagateMutation.mutate()}
          disabled={propagateMutation.isPending}
          title="Propaga questo stato ai controlli correlati"
          className="text-xs text-indigo-500 hover:text-indigo-700 border border-indigo-200 rounded px-1.5 py-0.5 hover:bg-indigo-50 disabled:opacity-50"
        >
          {propagateMutation.isPending ? "..." : propagated !== null ? `✓ ${propagated}` : "⇒ propaga"}
        </button>
      )}
    </div>
  );
}

function ExportToolbar({ frameworks, plantId }: { frameworks: Framework[]; plantId?: string }) {
  const token = useAuthStore(s => s.token);
  const [exporting, setExporting] = useState<string | null>(null);
  const [exportError, setExportError] = useState("");

  async function handleExport(frameworkCode: string, format: string) {
    const params = new URLSearchParams({ framework: frameworkCode, fmt: format });
    if (plantId) params.set("plant", plantId);
    try {
      setExporting(format);
      setExportError("");
      const response = await fetch(
        `/api/v1/controls/export/?${params.toString()}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      if (!response.ok) {
        let msg = "Errore download";
        try { const err = await response.json(); msg = err.error || msg; } catch {}
        setExportError(msg);
        return;
      }
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      const date = new Date().toISOString().slice(0, 10);
      a.download = `${format}_${frameworkCode}_${date}.html`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch {
      setExportError("Errore di rete durante il download");
    } finally {
      setExporting(null);
    }
  }

  const hasISO = frameworks.some(f => f.code === "ISO27001");
  const hasTISAX = frameworks.some(f => f.code === "TISAX_L2" || f.code === "TISAX_L3");
  const hasNIS2 = frameworks.some(f => f.code === "NIS2");
  const tisaxCode = frameworks.find(f => f.code === "TISAX_L3")?.code
    ?? frameworks.find(f => f.code === "TISAX_L2")?.code;

  if (!hasISO && !hasTISAX && !hasNIS2) return null;

  return (
    <div>
      <div className="flex gap-2 flex-wrap">
        {hasISO && (
          <button
            onClick={() => handleExport("ISO27001", "soa")}
            disabled={exporting === "soa"}
            className="px-3 py-1.5 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 disabled:opacity-60"
          >
            {exporting === "soa" ? "Download..." : "Scarica SOA"}
          </button>
        )}
        {hasTISAX && tisaxCode && (
          <button
            onClick={() => handleExport(tisaxCode, "vda_isa")}
            disabled={exporting === "vda_isa"}
            className="px-3 py-1.5 bg-purple-600 text-white text-sm rounded hover:bg-purple-700 disabled:opacity-60"
          >
            {exporting === "vda_isa" ? "Download..." : "Scarica VDA ISA"}
          </button>
        )}
        {hasNIS2 && (
          <button
            onClick={() => handleExport("NIS2", "compliance_matrix")}
            disabled={exporting === "compliance_matrix"}
            className="px-3 py-1.5 bg-green-600 text-white text-sm rounded hover:bg-green-700 disabled:opacity-60"
          >
            {exporting === "compliance_matrix" ? "Download..." : "Scarica NIS2 Matrix"}
          </button>
        )}
      </div>
      {exportError && (
        <p className="text-sm text-red-600 mt-1">
          {exportError}
          <button onClick={() => setExportError("")} className="ml-2 underline">Chiudi</button>
        </p>
      )}
    </div>
  );
}

export function ControlsList() {
  const [statusFilter, setStatusFilter] = useState("");
  const [selectedInstance, setSelectedInstance] = useState<string | null>(null);
  const selectedPlant = useAuthStore(s => s.selectedPlant);

  const params: Record<string, string> = {};
  if (statusFilter) params.status = statusFilter;
  if (selectedPlant?.id) params.plant = selectedPlant.id;

  const { data, isLoading } = useQuery({
    queryKey: ["controls", statusFilter, selectedPlant?.id],
    queryFn: () => controlsApi.instances(Object.keys(params).length ? params : undefined),
    retry: false,
  });

  const { data: frameworks } = useQuery({
    queryKey: ["frameworks"],
    queryFn: () => controlsApi.frameworks(),
    retry: false,
  });

  const instances = data?.results ?? [];

  const stats = STATUS_OPTIONS.reduce(
    (acc, s) => ({ ...acc, [s]: instances.filter((c) => c.status === s).length }),
    {} as Record<string, number>
  );

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <h2 className="text-xl font-semibold text-gray-900">Compliance — Controlli</h2>
        <ExportToolbar frameworks={frameworks ?? []} plantId={selectedPlant?.id} />
      </div>

      {frameworks && frameworks.length > 0 && (
        <div className="flex gap-2 mb-4 flex-wrap">
          {frameworks.map((f) => (
            <span key={f.id} className="text-xs bg-blue-50 border border-blue-200 text-blue-700 px-2 py-1 rounded">
              {f.code} v{f.version}
            </span>
          ))}
        </div>
      )}

      <div className="flex gap-2 mb-4 flex-wrap">
        <button
          onClick={() => setStatusFilter("")}
          className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
            statusFilter === "" ? "bg-primary-600 text-white" : "bg-white border border-gray-300 text-gray-600 hover:bg-gray-50"
          }`}
        >
          Tutti ({instances.length})
        </button>
        {STATUS_OPTIONS.map((s) => (
          <button
            key={s}
            onClick={() => setStatusFilter(s)}
            className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
              statusFilter === s ? "bg-primary-600 text-white" : "bg-white border border-gray-300 text-gray-600 hover:bg-gray-50"
            }`}
          >
            <StatusBadge status={s} /> ({stats[s] ?? 0})
          </button>
        ))}
      </div>

      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-gray-400">Caricamento...</div>
        ) : instances.length === 0 ? (
          <div className="p-8 text-center text-gray-400">Nessun controllo trovato</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-600">ID Controllo</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Framework</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Titolo</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Stato</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Ultima valutazione</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {instances.map((c) => (
                <tr key={c.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3 font-mono text-xs text-gray-500">
                    <div className="flex items-center gap-1">
                      <span>{c.control_external_id || c.control}</span>
                      <button
                        onClick={() => setSelectedInstance(c.id)}
                        className="ml-1 w-5 h-5 rounded-full bg-indigo-100 text-indigo-600 hover:bg-indigo-200 flex items-center justify-center shrink-0"
                        title="Gestione controllo"
                      >
                        <svg viewBox="0 0 12 12" className="w-3 h-3 fill-current" aria-hidden="true">
                          <path d="M3 2l7 4-7 4V2z" />
                        </svg>
                      </button>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-xs bg-blue-50 text-blue-700 px-1.5 py-0.5 rounded">
                      {c.framework_code}
                    </span>
                  </td>
                  <td className="px-4 py-3 max-w-xs">
                    <div className="text-gray-700 truncate">{c.control_title || "—"}</div>
                    <MappingBadges mappings={c.mapped_controls} />
                  </td>
                  <td className="px-4 py-3">
                    <InlineStatusSelect instance={c} />
                  </td>
                  <td className="px-4 py-3 text-gray-500 text-xs">
                    {c.last_evaluated_at
                      ? new Date(c.last_evaluated_at).toLocaleDateString("it-IT")
                      : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <ControlDetailDrawer
        instanceId={selectedInstance}
        onClose={() => setSelectedInstance(null)}
      />
    </div>
  );
}
