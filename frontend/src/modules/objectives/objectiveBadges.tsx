import { useTranslation } from "react-i18next";
import type { ObjectiveStatus, ObjectiveTrack } from "../../api/endpoints/securityObjectives";

const TRACK_STYLE: Record<ObjectiveTrack, string> = {
  in_linea: "bg-green-100 text-green-700 border-green-300",
  a_rischio: "bg-amber-100 text-amber-800 border-amber-300",
  mancato: "bg-red-100 text-red-700 border-red-300",
  senza_misure: "bg-gray-100 text-gray-500 border-gray-300",
  non_applicabile: "bg-gray-50 text-gray-400 border-gray-200",
};

const STATUS_STYLE: Record<ObjectiveStatus, string> = {
  bozza: "bg-gray-100 text-gray-600 border-gray-300",
  attivo: "bg-indigo-100 text-indigo-700 border-indigo-300",
  raggiunto: "bg-green-100 text-green-700 border-green-300",
  non_raggiunto: "bg-red-100 text-red-700 border-red-300",
  sospeso: "bg-amber-50 text-amber-700 border-amber-200",
  annullato: "bg-gray-50 text-gray-400 border-gray-200",
};

export function TrackBadge({ track }: { track: ObjectiveTrack }) {
  const { t } = useTranslation();
  return (
    <span className={`inline-block px-2 py-0.5 rounded border text-xs font-medium ${TRACK_STYLE[track]}`}>
      {t(`objectives.track.${track}`)}
    </span>
  );
}

export function ObjectiveStatusBadge({ status }: { status: ObjectiveStatus }) {
  const { t } = useTranslation();
  return (
    <span className={`inline-block px-2 py-0.5 rounded border text-xs font-medium ${STATUS_STYLE[status]}`}>
      {t(`objectives.status.${status}`)}
    </span>
  );
}

/** Barra del progresso sul cammino partenza → target, con un segno che
 *  mostra dove *dovremmo* essere a questo punto del periodo. È il confronto
 *  fra i due che dice se siamo in ritardo, non il valore da solo. */
export function ProgressBar({ progress, elapsed }: { progress: number | null; elapsed: number | null }) {
  const { t } = useTranslation();
  if (progress === null) {
    return <span className="text-xs text-gray-400">{t("objectives.no_baseline")}</span>;
  }
  const clamped = Math.max(0, Math.min(progress, 100));
  const behind = elapsed !== null && progress + 15 < elapsed;
  return (
    <div className="w-32">
      <div className="relative h-2 bg-gray-200 rounded">
        <div
          className={`h-2 rounded ${behind ? "bg-amber-500" : "bg-green-500"}`}
          style={{ width: `${clamped}%` }}
        />
        {elapsed !== null && (
          <div
            className="absolute top-[-2px] w-0.5 h-3 bg-gray-600"
            style={{ left: `${Math.min(elapsed, 100)}%` }}
            title={t("objectives.elapsed_marker", { pct: elapsed })}
          />
        )}
      </div>
      <p className="text-[11px] text-gray-500 mt-0.5">{progress}%</p>
    </div>
  );
}
