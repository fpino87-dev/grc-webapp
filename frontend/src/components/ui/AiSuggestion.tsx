import { useState } from "react";
import { useTranslation } from "react-i18next";

interface Props {
  suggestionId: string;
  output: string;
  onAccept: (final: string) => void;
  onIgnore: () => void;
}

export function AiSuggestion({ suggestionId, output, onAccept, onIgnore }: Props) {
  const { t } = useTranslation();
  const [editing, setEditing] = useState(false);
  const [edited, setEdited] = useState(output);

  return (
    <div className="border border-amber-300 bg-amber-50 rounded-lg p-4 my-3">
      <div className="flex items-center gap-2 mb-2">
        <span className="text-xs bg-amber-400 text-white px-2 py-0.5 rounded font-bold">
          {t("ai.ai_badge")}
        </span>
        <span className="text-sm font-medium text-amber-800">
          {t("ai.suggestion_label")}
        </span>
      </div>
      {editing ? (
        <textarea
          className="w-full border rounded p-2 text-sm min-h-24"
          value={edited}
          onChange={(e) => setEdited(e.target.value)}
        />
      ) : (
        <p className="text-sm text-gray-700 mb-3 whitespace-pre-wrap">{output}</p>
      )}
      <div className="flex gap-2 mt-2">
        <button
          onClick={() => onAccept(output)}
          className="px-3 py-1 bg-green-600 text-white text-sm rounded hover:bg-green-700"
        >
          {t("ai.accept")}
        </button>
        {!editing ? (
          <button
            onClick={() => setEditing(true)}
            className="px-3 py-1 bg-blue-600 text-white text-sm rounded hover:bg-blue-700"
          >
            {t("ai.edit_and_use")}
          </button>
        ) : (
          <button
            onClick={() => onAccept(edited)}
            className="px-3 py-1 bg-blue-600 text-white text-sm rounded hover:bg-blue-700"
          >
            Salva modifiche
          </button>
        )}
        <button
          onClick={onIgnore}
          className="px-3 py-1 bg-gray-200 text-gray-700 text-sm rounded hover:bg-gray-300"
        >
          {t("ai.ignore")}
        </button>
      </div>
    </div>
  );
}

