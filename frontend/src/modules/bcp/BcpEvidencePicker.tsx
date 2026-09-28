import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { documentsApi } from "../../api/endpoints/documents";
import { fmtDate } from "./shared";

interface Props {
  plantId: string;
  file: File | null;
  onFileChange: (file: File | null) => void;
  selectedIds: string[];
  onSelectedChange: (ids: string[]) => void;
  /** Evidenze già collegate: non si propongono di nuovo. */
  excludeIds?: string[];
}

/**
 * Evidenze di un test BCP: un file nuovo (diventa un'evidenza "Risultato test"
 * del sito) e/o evidenze già presenti in Documenti › Evidenze, del sito del
 * piano o di organizzazione.
 */
export function BcpEvidencePicker({ plantId, file, onFileChange, selectedIds, onSelectedChange, excludeIds = [] }: Props) {
  const { t } = useTranslation();
  const [search, setSearch] = useState("");

  const { data, isLoading } = useQuery({
    queryKey: ["documents", "evidences", "bcp-picker", plantId],
    queryFn: () => documentsApi.evidences({ plant: plantId }),
    enabled: !!plantId,
    retry: false,
  });
  const query = search.trim().toLowerCase();
  const candidates = (data?.results ?? [])
    .filter(e => !excludeIds.includes(e.id))
    .filter(e => !query || e.title.toLowerCase().includes(query));

  const toggle = (id: string) =>
    onSelectedChange(selectedIds.includes(id) ? selectedIds.filter(x => x !== id) : [...selectedIds, id]);

  return (
    <div className="space-y-2">
      <div>
        <label className="block text-xs font-medium text-gray-600 mb-1">{t("bcp.evidence.upload")}</label>
        <input type="file" onChange={e => onFileChange(e.target.files?.[0] ?? null)} className="w-full border rounded px-3 py-1.5 text-sm" />
        {file && <p className="text-xs text-gray-500 mt-1">{t("bcp.evidence.upload_hint")}</p>}
      </div>
      <div>
        <label className="block text-xs font-medium text-gray-600 mb-1">
          {t("bcp.evidence.existing")}
          {selectedIds.length > 0 && <span className="ml-1 text-primary-700">({selectedIds.length})</span>}
        </label>
        <input
          value={search}
          onChange={e => setSearch(e.target.value)}
          placeholder={t("bcp.evidence.search")}
          className="w-full border rounded px-3 py-1.5 text-sm mb-1"
        />
        <div className="border rounded max-h-36 overflow-y-auto divide-y divide-gray-100">
          {isLoading ? (
            <p className="px-3 py-2 text-xs text-gray-400">{t("bcp.loading")}</p>
          ) : candidates.length === 0 ? (
            <p className="px-3 py-2 text-xs text-gray-400">{t("bcp.evidence.none")}</p>
          ) : (
            candidates.map(e => (
              <label key={e.id} className="flex items-center gap-2 px-3 py-1.5 text-sm hover:bg-gray-50 cursor-pointer">
                <input type="checkbox" checked={selectedIds.includes(e.id)} onChange={() => toggle(e.id)} />
                <span className="flex-1 truncate text-gray-800" title={e.title}>{e.title}</span>
                <span className="text-[11px] text-gray-400 whitespace-nowrap">
                  {e.plant ? "" : `${t("bcp.evidence.org")} · `}
                  {e.valid_until ? t("bcp.evidence.valid_until", { date: fmtDate(e.valid_until) }) : ""}
                </span>
              </label>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
