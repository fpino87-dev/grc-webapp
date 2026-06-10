import { useTranslation } from "react-i18next";

export function CriticalityGuide() {
  const { t } = useTranslation();
  return (
    <details className="mt-2 text-xs">
      <summary className="text-blue-600 cursor-pointer hover:underline">
        {t("assets.criticality_guide_title")}
      </summary>
      <table className="mt-2 w-full border-collapse text-xs">
        <thead>
          <tr className="bg-gray-50 text-left">
            <th className="border px-2 py-1">{t("assets.criticality_table_value")}</th>
            <th className="border px-2 py-1">{t("assets.criticality_table_label")}</th>
            <th className="border px-2 py-1">{t("assets.criticality_table_downtime")}</th>
            <th className="border px-2 py-1">{t("assets.criticality_table_bcp")}</th>
          </tr>
        </thead>
        <tbody>
          {([
            [1, t("assets.criticality_1_label"), t("assets.downtime_7d_plus"), t("assets.bcp_not_required")],
            [2, t("assets.criticality_2_label"), t("assets.downtime_3_7d"), t("assets.bcp_not_required")],
            [3, t("assets.criticality_3_label"), t("assets.downtime_24_72h"), t("assets.bcp_recommended")],
            [4, t("assets.criticality_4_label"), t("assets.downtime_4_24h"), t("assets.bcp_mandatory")],
            [5, t("assets.criticality_5_label"), t("assets.downtime_sub_4h"), t("assets.bcp_mandatory")],
          ] as [number, string, string, string][]).map(([v,l,d,b]) => (
            <tr key={v}>
              <td className="border px-2 py-1 text-center font-bold">{v}</td>
              <td className="border px-2 py-1">{l}</td>
              <td className="border px-2 py-1">{d}</td>
              <td className="border px-2 py-1 text-center">{b}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </details>
  );
}
