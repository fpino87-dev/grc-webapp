import { useEffect, useMemo, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { aiApi } from "../../api/endpoints/ai";

interface AiSuggestionBannerProps {
  taskType: string;
  entityId: string;
  onAccept: (result: unknown) => void;
  onIgnore: () => void;
  autoTrigger?: boolean;
}

export function AiSuggestionBanner({
  taskType,
  entityId,
  onAccept,
  onIgnore,
  autoTrigger = false,
}: AiSuggestionBannerProps) {
  const [interactionId, setInteractionId] = useState<string | null>(null);
  const [result, setResult] = useState<unknown>(null);
  const [provider, setProvider] = useState("");
  const [model, setModel] = useState("");
  const [usedFallback, setUsedFallback] = useState(false);
  const [edited, setEdited] = useState("");
  const [isEditing, setIsEditing] = useState(false);

  const suggestMutation = useMutation({
    mutationFn: () => aiApi.suggest(taskType, entityId),
    onSuccess: (data) => {
      setInteractionId(data.interaction_id);
      setResult(data.result);
      setProvider(data.provider);
      setModel(data.model);
      setUsedFallback(data.used_fallback);
      setEdited(JSON.stringify(data.result, null, 2));
      setIsEditing(false);
    },
  });

  const confirmMutation = useMutation({
    mutationFn: async () => {
      if (interactionId) {
        await aiApi.confirm(interactionId, edited);
      }
    },
    onSuccess: () => {
      try {
        onAccept(JSON.parse(edited));
      } catch {
        onAccept(result);
      }
    },
  });

  const ignoreMutation = useMutation({
    mutationFn: async () => {
      if (interactionId) {
        await aiApi.ignore(interactionId);
      }
    },
    onSuccess: () => onIgnore(),
  });

  useEffect(() => {
    if (autoTrigger && entityId && !result && !suggestMutation.isPending && !suggestMutation.isError) {
      suggestMutation.mutate();
    }
  }, [autoTrigger, entityId, result, suggestMutation.isPending, suggestMutation.isError]);

  const providerBadge = useMemo(() => {
    const isLocal = provider === "ollama";
    return isLocal ? `locale${usedFallback ? " (fallback)" : ""}` : "cloud";
  }, [provider, usedFallback]);

  const prettyText = useMemo(() => {
    const data = result as Record<string, unknown> | null;
    if (!data || typeof data !== "object") return "";

    if (taskType === "incident_classify") {
      return [
        `Categoria ENISA: ${String(data.category ?? "—")}`,
        `Sottocategoria: ${String(data.subcategory ?? "—")}`,
        `Severita suggerita: ${String(data.severity ?? "—")}`,
        `Probabile NIS2: ${Boolean(data.nis2_likely) ? "Si" : "No"}`,
        `Motivazione: ${String(data.nis2_reason ?? "—")}`,
        `Confidenza: ${String(data.confidence ?? "—")}`,
      ].join("\n");
    }

    if (taskType === "rca_draft") {
      const list = (value: unknown) =>
        Array.isArray(value) && value.length > 0 ? value.map((v) => `- ${String(v)}`).join("\n") : "- —";

      return [
        "1) Sommario esecutivo",
        String(data.summary ?? "—"),
        "",
        "2) Causa radice",
        String(data.root_cause ?? "—"),
        "",
        "3) Fattori contributivi",
        list(data.contributing_factors),
        "",
        "4) Timeline",
        list(data.timeline),
        "",
        "5) Azioni immediate",
        list(data.immediate_actions),
        "",
        "6) Azioni preventive",
        list(data.preventive_actions),
        "",
        "7) Lesson learned",
        String(data.lessons_learned ?? "—"),
      ].join("\n");
    }

    if (taskType === "gap_actions") {
      const actions = Array.isArray(data.actions) ? data.actions : [];
      if (actions.length === 0) return "Nessuna azione suggerita.";
      return actions
        .map((action, idx) => {
          const item = action as Record<string, unknown>;
          return `${idx + 1}. ${String(item.title ?? "Azione")}\n   Priorita: ${String(item.priority ?? "—")}\n   Descrizione: ${String(item.description ?? "—")}`;
        })
        .join("\n\n");
    }

    return JSON.stringify(data, null, 2);
  }, [result, taskType]);

  if (suggestMutation.isPending && !result) {
    return <div className="border rounded p-3 text-sm text-gray-600">Analisi AI in corso...</div>;
  }

  return (
    <div className="border rounded-lg p-3 bg-white">
      {suggestMutation.isError && (
        <div className="mb-2 rounded border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700 flex items-center justify-between">
          <span>Servizio AI non disponibile. Riprovare oppure verificare la configurazione provider.</span>
          <button onClick={() => suggestMutation.mutate()} className="ml-3 px-2 py-0.5 text-xs border border-red-300 rounded hover:bg-red-100">Riprova</button>
        </div>
      )}
      {usedFallback && (
        <div className="mb-2 rounded border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
          Modalita locale attiva: budget cloud esaurito. Validare il contenuto prima dell'adozione.
        </div>
      )}
      <div className="flex items-center justify-between">
        <div className="text-sm font-medium">Raccomandazione AI</div>
        <div className={`text-xs px-2 py-0.5 rounded ${provider === "ollama" ? "bg-yellow-100 text-yellow-800" : "bg-green-100 text-green-700"}`}>
          {providerBadge} - {model || provider}
        </div>
      </div>
      {!isEditing && (
        <div className="mt-2 whitespace-pre-wrap rounded border bg-gray-50 p-3 text-xs text-gray-800 min-h-28">
          {prettyText || "Nessun suggerimento disponibile."}
        </div>
      )}
      {isEditing && (
        <textarea
          className="mt-2 w-full border rounded p-2 text-xs min-h-28 font-mono"
          value={edited}
          onChange={(e) => setEdited(e.target.value)}
          placeholder="Nessun suggerimento disponibile."
        />
      )}
      <div className="mt-2 flex gap-2">
        {!autoTrigger && (
          <button onClick={() => suggestMutation.mutate()} className="px-3 py-1.5 text-xs border rounded">
            Genera raccomandazione
          </button>
        )}
        <button
          onClick={() => setIsEditing((prev) => !prev)}
          disabled={!result}
          className="px-3 py-1.5 text-xs border rounded disabled:opacity-50"
        >
          {isEditing ? "Anteprima" : "Modifica"}
        </button>
        <button
          onClick={() => confirmMutation.mutate()}
          disabled={!result || confirmMutation.isPending}
          className="px-3 py-1.5 text-xs bg-green-600 text-white rounded disabled:opacity-50"
        >
          Conferma e applica
        </button>
        <button
          onClick={() => ignoreMutation.mutate()}
          disabled={!interactionId || ignoreMutation.isPending}
          className="px-3 py-1.5 text-xs border rounded"
        >
          Ignora
        </button>
      </div>
    </div>
  );
}
