import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { apiClient } from "../../api/client";

interface CompetencyGap {
  competency: string; role: string; required_level: number;
  current_level: number; gap: number; evidence_type: string;
}
interface CompetencyWarning { competency: string; expired_on: string; message: string; }
interface GapAnalysisResult {
  user_id: string; user_name: string; roles: string[];
  gaps: CompetencyGap[]; ok: string[]; warnings: CompetencyWarning[];
  gap_count: number;
}

export function CompetencyPanel({ userId }: { userId: number }) {
  const { t } = useTranslation();
  const { data, isLoading } = useQuery({
    queryKey: ["competency-gap", userId],
    queryFn: () =>
      apiClient.get<GapAnalysisResult>(`/auth/user-competencies/gap-analysis/?user=${userId}`)
        .then(r => r.data),
    retry: false,
  });

  if (isLoading) return <p className="text-xs text-gray-400 p-4">{t("users.competency_gap.loading")}</p>;
  if (!data) return null;

  return (
    <div className="text-sm">
      <div className="flex items-center gap-3 mb-3">
        <h4 className="font-semibold text-gray-700">
          {t("users.competency_gap.title", { name: data.user_name })}
        </h4>
        {data.gap_count > 0 && (
          <span className="px-2 py-0.5 bg-red-100 text-red-700 text-xs rounded">
            {t("users.competency_gap.gap_count", { count: data.gap_count })}
          </span>
        )}
        {data.ok.length > 0 && !data.gap_count && (
          <span className="px-2 py-0.5 bg-green-100 text-green-700 text-xs rounded">
            {t("users.competency_gap.complete")}
          </span>
        )}
      </div>

      {data.gaps.length > 0 && (
        <div className="mb-3">
          <p className="text-xs font-medium text-red-600 mb-1">{t("users.competency_gap.to_fill")}</p>
          <div className="space-y-1">
            {data.gaps.map((g, i) => (
              <div key={i} className="flex items-center gap-2 bg-red-50 rounded px-3 py-1.5 text-xs">
                <span className="font-medium text-red-700">{g.competency}</span>
                <span className="text-gray-500">({g.role})</span>
                <span className="ml-auto text-red-600">
                  {t("users.competency_gap.level_from_to", { current: g.current_level, required: g.required_level })}
                </span>
                <span className="text-gray-400 capitalize">{g.evidence_type}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {data.warnings.length > 0 && (
        <div className="mb-3">
          <p className="text-xs font-medium text-orange-600 mb-1">{t("users.competency_gap.expired")}</p>
          <div className="space-y-1">
            {data.warnings.map((w, i) => (
              <div key={i} className="flex items-center gap-2 bg-orange-50 rounded px-3 py-1.5 text-xs">
                <span className="text-orange-700">{w.message}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {data.ok.length > 0 && (
        <div>
          <p className="text-xs font-medium text-green-600 mb-1">{t("users.competency_gap.ok")}</p>
          <div className="flex flex-wrap gap-1">
            {data.ok.map((c, i) => (
              <span key={i} className="bg-green-50 text-green-700 text-xs px-2 py-0.5 rounded">{c}</span>
            ))}
          </div>
        </div>
      )}

      {data.gaps.length === 0 && data.warnings.length === 0 && data.ok.length === 0 && (
        <p className="text-xs text-gray-400">{t("users.competency_gap.none")}</p>
      )}
    </div>
  );
}

