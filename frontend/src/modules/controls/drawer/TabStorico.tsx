import { useTranslation } from "react-i18next";
import { type ControlDetailInfo } from "../../../api/endpoints/controls";
import i18n from "../../../i18n";

export function TabStorico({ history }: { history: ControlDetailInfo["evaluation_history"] }) {
  const { t } = useTranslation();
  if (history.length === 0) {
    return <p className="text-sm text-gray-400 italic">{t("controls.drawer.history.empty")}</p>;
  }
  const statusIcon: Record<string, string> = {
    compliant: "🟢", parziale: "🟡", gap: "🔴", na: "⚪", non_valutato: "⬜",
  };
  return (
    <div className="relative">
      <div className="absolute left-3.5 top-0 bottom-0 w-px bg-gray-200" />
      <div className="space-y-4">
        {history.map((h, i) => {
          const status = (h.payload as Record<string, string>)["new_status"] ?? "";
          const note = (h.payload as Record<string, string>)["note"] ?? "";
          return (
            <div key={i} className="relative pl-8">
              <div className="absolute left-1.5 top-1 w-4 h-4 rounded-full bg-white border-2 border-gray-300 flex items-center justify-center text-xs">
                {statusIcon[status] ?? "•"}
              </div>
              <div className="bg-gray-50 border border-gray-200 rounded-lg px-3 py-2">
                <div className="flex items-center justify-between mb-0.5">
                  <span className="text-xs font-medium text-gray-700">{h.user_email_at_time}</span>
                  <span className="text-xs text-gray-400">{new Date(h.timestamp_utc).toLocaleString(i18n.language || "it")}</span>
                </div>
                <p className="text-xs text-gray-600">
                  {t("controls.drawer.history.set_status")} <strong>{t(`status.${status}`, { defaultValue: status })}</strong>
                  {note && <> — <em>"{note}"</em></>}
                </p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
