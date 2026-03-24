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

  const suggestMutation = useMutation({
    mutationFn: () => aiApi.suggest(taskType, entityId),
    onSuccess: (data) => {
      setInteractionId(data.interaction_id);
      setResult(data.result);
      setProvider(data.provider);
      setModel(data.model);
      setUsedFallback(data.used_fallback);
      setEdited(JSON.stringify(data.result, null, 2));
    },
  });

  const confirmMutation = useMutation({
    mutationFn: async () => {
      if (interactionId) {
        await aiApi.confirm(interactionId, edited);
      }
    },
    onSuccess: () => onAccept(result),
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
    if (autoTrigger && entityId && !result && !suggestMutation.isPending) {
      suggestMutation.mutate();
    }
  }, [autoTrigger, entityId, result, suggestMutation]);

  const providerBadge = useMemo(() => {
    const isLocal = provider === "ollama";
    return isLocal ? `locale${usedFallback ? " (fallback)" : ""}` : "cloud";
  }, [provider, usedFallback]);

  if (suggestMutation.isPending && !result) {
    return <div className="border rounded p-3 text-sm text-gray-600">Generazione suggerimento AI...</div>;
  }

  return (
    <div className="border rounded-lg p-3 bg-white">
      {suggestMutation.isError && (
        <div className="mb-2 rounded border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
          Errore AI. Riprovare.
        </div>
      )}
      {usedFallback && (
        <div className="mb-2 rounded border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
          Modalita locale attiva: budget cloud esaurito. Verificare il suggerimento.
        </div>
      )}
      <div className="flex items-center justify-between">
        <div className="text-sm font-medium">Suggerimento AI</div>
        <div className={`text-xs px-2 py-0.5 rounded ${provider === "ollama" ? "bg-yellow-100 text-yellow-800" : "bg-green-100 text-green-700"}`}>
          {providerBadge} - {model || provider}
        </div>
      </div>
      <textarea
        className="mt-2 w-full border rounded p-2 text-xs min-h-28 font-mono"
        value={edited}
        onChange={(e) => setEdited(e.target.value)}
        placeholder="Nessun suggerimento disponibile."
      />
      <div className="mt-2 flex gap-2">
        {!autoTrigger && (
          <button onClick={() => suggestMutation.mutate()} className="px-3 py-1.5 text-xs border rounded">
            Genera
          </button>
        )}
        <button
          onClick={() => confirmMutation.mutate()}
          disabled={!result || confirmMutation.isPending}
          className="px-3 py-1.5 text-xs bg-green-600 text-white rounded disabled:opacity-50"
        >
          Applica
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
