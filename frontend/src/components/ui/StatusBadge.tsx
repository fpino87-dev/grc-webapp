interface Props {
  status: string;
}

import { useTranslation } from "react-i18next";

const styles: Record<string, string> = {
  compliant: "bg-green-100 text-green-800",
  parziale: "bg-yellow-100 text-yellow-800",
  gap: "bg-red-100 text-red-800",
  na: "bg-gray-100 text-gray-600",
  non_valutato: "bg-gray-100 text-gray-500",
  aperto: "bg-red-100 text-red-700",
  in_analisi: "bg-orange-100 text-orange-700",
  chiuso: "bg-green-100 text-green-700",
  in_corso: "bg-blue-100 text-blue-700",
  scaduto: "bg-red-200 text-red-800",
  bozza: "bg-gray-100 text-gray-700",
  revisione: "bg-blue-100 text-blue-700",
  approvazione: "bg-amber-100 text-amber-800",
  approvato: "bg-green-100 text-green-700",
  respinto: "bg-red-100 text-red-700",
  completato: "bg-green-100 text-green-700",
  annullato: "bg-gray-100 text-gray-600",
  bassa: "bg-green-100 text-green-700",
  media: "bg-yellow-100 text-yellow-700",
  alta: "bg-orange-100 text-orange-700",
  critica: "bg-red-100 text-red-800",
  attivo: "bg-green-100 text-green-700",
  in_dismissione: "bg-yellow-100 text-yellow-700",
  si: "bg-red-100 text-red-700",
  no: "bg-green-100 text-green-700",
  da_valutare: "bg-yellow-100 text-yellow-700",
};

const labels: Record<string, string> = {
  compliant: "Compliant",
  parziale: "Parziale",
  gap: "Gap",
  na: "N/A",
  non_valutato: "Non valutato",
  aperto: "Aperto",
  in_analisi: "In analisi",
  chiuso: "Chiuso",
  in_corso: "In corso",
  scaduto: "Scaduto",
  bozza: "Bozza",
  revisione: "In revisione",
  approvazione: "In approvazione",
  approvato: "Approvato",
  respinto: "Respinto",
  completato: "Completato",
  annullato: "Annullato",
  bassa: "Bassa",
  media: "Media",
  alta: "Alta",
  critica: "Critica",
  attivo: "Attivo",
  in_dismissione: "In dismissione",
  essenziale: "NIS2 Essenziale",
  importante: "NIS2 Importante",
  non_soggetto: "Non soggetto",
  si: "Sì",
  no: "No",
  da_valutare: "Da valutare",
};

export function StatusBadge({ status }: Props) {
  const { t } = useTranslation();
  const fallbackLabel = labels[status] ?? status;
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
        styles[status] ?? "bg-gray-100 text-gray-600"
      }`}
    >
      {t(`status.${status}`, { defaultValue: fallbackLabel })}
    </span>
  );
}
