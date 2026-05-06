import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";

import {
  aiApi,
  type AssistantGap,
  type AssistantStartResponse,
} from "../../api/endpoints/ai";
import { plantsApi, type Plant } from "../../api/endpoints/plants";
import { useAuthStore } from "../../store/auth";

interface Props {
  open: boolean;
  onClose: () => void;
}

const URGENCY_STYLES: Record<string, string> = {
  red: "bg-red-50 border-red-300 text-red-800",
  yellow: "bg-yellow-50 border-yellow-300 text-yellow-800",
  green: "bg-green-50 border-green-300 text-green-800",
};

const CATEGORY_LABELS: Record<string, string> = {
  documents: "Documento",
  controls: "Controllo",
  risk: "Rischio",
  suppliers: "Fornitore",
};

function urgencyEmoji(u: string): string {
  if (u === "red") return "🔴";
  if (u === "yellow") return "🟡";
  return "🟢";
}

/**
 * Mappa categoria gap -> (path, chiave router-state) per atterrare sull'item
 * specifico. Le pagine target leggono `location.state.<key>` ed effettuano
 * scroll + highlight (vedi `lib/scrollAndHighlight.ts`).
 */
function gapTarget(category: string, refId: string): { path: string; state: Record<string, string> } | null {
  switch (category) {
    case "controls":
      return { path: "/controls", state: { openControlInstance: refId } };
    case "documents":
      return { path: "/documents", state: { openDocumentId: refId } };
    case "risk":
      return { path: "/risk", state: { openRiskId: refId } };
    case "suppliers":
      return { path: "/suppliers", state: { openSupplierId: refId } };
    default:
      return null;
  }
}

export function GrcAssistantDrawer({ open, onClose }: Props) {
  const selectedPlant = useAuthStore((s) => s.selectedPlant);
  const setPlant = useAuthStore((s) => s.setPlant);
  const navigate = useNavigate();

  const [showPlantPicker, setShowPlantPicker] = useState(false);
  const [explanations, setExplanations] = useState<
    Record<string, { text: string; interaction_id: string | null }>
  >({});

  const hasSelected = !!selectedPlant && !!selectedPlant.id;

  const { data: plants = [] } = useQuery({
    queryKey: ["plants-list-for-assistant"],
    queryFn: () => plantsApi.list(),
    enabled: open,
  });

  useEffect(() => {
    if (open && !hasSelected) {
      setShowPlantPicker(true);
    }
  }, [open, hasSelected]);

  const startQuery = useQuery<AssistantStartResponse>({
    queryKey: ["assistant-start", selectedPlant?.id],
    queryFn: () => aiApi.assistant.start(selectedPlant!.id),
    enabled: open && hasSelected && !showPlantPicker,
    staleTime: 60_000,
  });

  const explainMutation = useMutation({
    mutationFn: async (gap: AssistantGap) => {
      const res = await aiApi.assistant.explain(selectedPlant!.id, gap);
      return { gap, res };
    },
    onSuccess: ({ gap, res }) => {
      setExplanations((prev) => ({
        ...prev,
        [gap.ref_id]: { text: res.explanation, interaction_id: res.interaction_id },
      }));
    },
  });

  if (!open) return null;

  return (
    <>
      <div
        className="fixed inset-0 bg-black/30 z-40"
        onClick={onClose}
        aria-label="Chiudi assistente"
      />
      <div className="fixed top-0 right-0 h-full w-[420px] max-w-full bg-white shadow-xl z-50 flex flex-col">
        <div className="px-4 py-3 border-b flex items-center justify-between bg-blue-50">
          <div>
            <h2 className="font-semibold text-gray-800">🤖 GRC Assistant</h2>
            {hasSelected && !showPlantPicker && (
              <p className="text-xs text-gray-600 mt-0.5">
                Sito: <strong>{selectedPlant!.name}</strong>{" "}
                <button
                  onClick={() => setShowPlantPicker(true)}
                  className="ml-1 text-blue-600 hover:underline"
                >
                  cambia
                </button>
              </p>
            )}
          </div>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700 text-xl px-2"
            aria-label="Chiudi"
          >
            ×
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-4">
          {showPlantPicker ? (
            <PlantPicker
              plants={plants}
              currentId={selectedPlant?.id}
              onSelect={(p) => {
                setPlant({ id: p.id, code: p.code, name: p.name });
                setShowPlantPicker(false);
                setExplanations({});
              }}
            />
          ) : startQuery.isLoading ? (
            <p className="text-sm text-gray-500">Sto analizzando lo stato del sito…</p>
          ) : startQuery.isError ? (
            <p className="text-sm text-red-600">Errore nel caricamento. Riprova.</p>
          ) : startQuery.data ? (
            <AssistantBody
              data={startQuery.data}
              explanations={explanations}
              onExplain={(gap) => explainMutation.mutate(gap)}
              onGoTo={(gap) => {
                const target = gapTarget(gap.category, gap.ref_id);
                if (target) {
                  navigate(target.path, { state: target.state });
                } else {
                  navigate(gap.frontend_url);
                }
                onClose();
              }}
              isExplaining={explainMutation.isPending}
              explainingId={explainMutation.variables?.ref_id}
              onFeedback={async (gap, useful) => {
                const exp = explanations[gap.ref_id];
                if (exp?.interaction_id) {
                  if (useful) {
                    await aiApi.confirm(exp.interaction_id, exp.text);
                  } else {
                    await aiApi.ignore(exp.interaction_id);
                  }
                }
                setExplanations((prev) => {
                  const next = { ...prev };
                  delete next[gap.ref_id];
                  return next;
                });
              }}
            />
          ) : null}
        </div>
      </div>
    </>
  );
}

function PlantPicker({
  plants,
  onSelect,
  currentId,
}: {
  plants: Plant[];
  onSelect: (p: Plant) => void;
  currentId?: string;
}) {
  return (
    <div>
      <p className="text-sm text-gray-700 mb-3">Su quale stabilimento vuoi lavorare?</p>
      <div className="space-y-1">
        {plants.map((p) => (
          <button
            key={p.id}
            onClick={() => onSelect(p)}
            className={`w-full text-left px-3 py-2 rounded border ${
              currentId === p.id
                ? "bg-blue-50 border-blue-300"
                : "hover:bg-gray-50 border-gray-200"
            }`}
          >
            <div className="font-medium text-sm text-gray-800">{p.name}</div>
            <div className="text-xs text-gray-500">{p.code}</div>
          </button>
        ))}
        {plants.length === 0 && (
          <p className="text-sm text-gray-500">Nessuno stabilimento accessibile.</p>
        )}
      </div>
    </div>
  );
}

function AssistantBody({
  data,
  explanations,
  onExplain,
  onGoTo,
  isExplaining,
  explainingId,
  onFeedback,
}: {
  data: AssistantStartResponse;
  explanations: Record<string, { text: string; interaction_id: string | null }>;
  onExplain: (gap: AssistantGap) => void;
  onGoTo: (gap: AssistantGap) => void;
  isExplaining: boolean;
  explainingId?: string;
  onFeedback: (gap: AssistantGap, useful: boolean) => Promise<void>;
}) {
  const { summary, gaps, gaps_total, gaps_truncated } = data;
  const redCount = gaps.filter((g) => g.urgency === "red").length;

  return (
    <div className="space-y-4">
      <div className="bg-gray-50 rounded p-3 text-sm">
        {gaps_total === 0 ? (
          <p className="text-green-700">
            ✅ Nessun gap aperto sui criteri monitorati. Continua così.
          </p>
        ) : (
          <p className="text-gray-700">
            Ho trovato <strong>{gaps_total}</strong> cosa/e da sistemare
            {redCount > 0 && (
              <>
                {" "}
                — <span className="text-red-600 font-medium">{redCount} urgente/i</span>
              </>
            )}
            .
          </p>
        )}
        {summary.frameworks.length > 0 && (
          <div className="mt-2 space-y-0.5">
            {summary.frameworks.map((f) => (
              <p key={f.code} className="text-xs text-gray-600">
                <span className="font-mono">{f.code}</span>: {f.pct_compliant}% compliance ({f.compliant}/{f.total} controlli
                {f.covered_by_extender > 0 && (
                  <>, di cui <span className="text-blue-700">{f.covered_by_extender} coperti da framework esteso</span></>
                )}
                {f.na_excluded > 0 && (
                  <>; <span className="text-gray-400">{f.na_excluded} N/A esclusi</span></>
                )}
                )
              </p>
            ))}
          </div>
        )}
      </div>

      {gaps.map((gap) => (
        <div
          key={`${gap.kind}-${gap.ref_id}`}
          className={`rounded border p-3 ${URGENCY_STYLES[gap.urgency]}`}
        >
          <div className="flex items-start justify-between gap-2 mb-1">
            <span className="text-xs uppercase tracking-wide font-semibold opacity-75">
              {CATEGORY_LABELS[gap.category] ?? gap.category}
            </span>
            <span className="text-xs">{urgencyEmoji(gap.urgency)}</span>
          </div>
          <h3 className="text-sm font-semibold leading-tight">{gap.title}</h3>
          <p className="text-xs mt-1 opacity-80">{gap.subtitle}</p>

          {explanations[gap.ref_id] ? (
            <div className="mt-2 border border-amber-300 bg-amber-50 rounded p-3">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-xs bg-amber-400 text-white px-1.5 py-0.5 rounded font-bold">
                  AI
                </span>
                <span className="text-xs font-medium text-amber-800">
                  Spiegazione
                </span>
              </div>
              <p className="text-xs text-gray-800 whitespace-pre-wrap mb-3">
                {explanations[gap.ref_id].text}
              </p>
              <div className="flex gap-2">
                <button
                  onClick={() => onFeedback(gap, true)}
                  className="px-2 py-1 bg-green-600 text-white text-xs rounded hover:bg-green-700"
                  title="Segnala che la spiegazione è stata utile (migliora la qualità AI nel tempo)"
                >
                  👍 Mi è stato utile
                </button>
                <button
                  onClick={() => onFeedback(gap, false)}
                  className="px-2 py-1 bg-white border border-gray-300 text-gray-700 text-xs rounded hover:bg-gray-50"
                  title="Segnala che la spiegazione non è stata utile"
                >
                  👎 Non è stato utile
                </button>
              </div>
            </div>
          ) : (
            <div className="flex gap-2 mt-2">
              <button
                onClick={() => onGoTo(gap)}
                className="px-2 py-1 bg-blue-600 text-white text-xs rounded hover:bg-blue-700"
              >
                Vai a risolvere
              </button>
              <button
                onClick={() => onExplain(gap)}
                disabled={isExplaining && explainingId === gap.ref_id}
                className="px-2 py-1 bg-white border border-gray-300 text-xs rounded hover:bg-gray-50 disabled:opacity-50"
              >
                {isExplaining && explainingId === gap.ref_id ? "Sto pensando…" : "Spiegami"}
              </button>
            </div>
          )}
        </div>
      ))}

      {gaps_truncated && (
        <p className="text-xs text-gray-500 italic">
          Mostro le 20 più urgenti. Risolvi queste e tornerò con le successive.
        </p>
      )}
    </div>
  );
}
