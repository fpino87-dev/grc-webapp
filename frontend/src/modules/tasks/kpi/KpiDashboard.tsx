import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { ResponsiveContainer, LineChart, Line } from "recharts";
import { kpiApi, type KpiDefinitionListItem, type KpiStatus } from "../../../api/endpoints/kpi";
import { plantsApi } from "../../../api/endpoints/plants";
import { useAuthStore } from "../../../store/auth";
import { KpiTrendModal } from "./KpiTrendModal";
import i18n from "../../../i18n";

const STATUS_STYLE: Record<KpiStatus, string> = {
  ok: "bg-green-100 text-green-700",
  warning: "bg-yellow-100 text-yellow-700",
  critical: "bg-red-100 text-red-700",
  no_data: "bg-gray-100 text-gray-500",
};

function Sparkline({ kpiCode, plantId }: { kpiCode: string; plantId?: string }) {
  const { data } = useQuery({
    queryKey: ["kpi-sparkline", kpiCode, plantId],
    queryFn: () => kpiApi.getKpiTrend(kpiCode, plantId, 8),
    retry: false,
  });
  const points = (data?.results ?? [])
    .filter((s) => s.value != null)
    .map((s) => ({ v: s.value }));
  if (points.length < 2) {
    return <div className="h-10" />;
  }
  return (
    <ResponsiveContainer width="100%" height={40}>
      <LineChart data={points} margin={{ top: 4, right: 2, left: 2, bottom: 4 }}>
        <Line type="monotone" dataKey="v" stroke="#2563eb" strokeWidth={1.5} dot={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}

function KpiCard({
  kpi,
  plantId,
  onOpen,
}: {
  kpi: KpiDefinitionListItem;
  plantId?: string;
  onOpen: () => void;
}) {
  const { t } = useTranslation();
  return (
    <button
      onClick={onOpen}
      className="text-left bg-white rounded-lg border border-gray-200 p-4 hover:shadow-md hover:border-primary-300 transition-all"
    >
      <div className="flex items-start justify-between mb-1">
        <span className="text-sm font-medium text-gray-700 line-clamp-2">{kpi.name}</span>
        <span className={`shrink-0 ml-2 inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${STATUS_STYLE[kpi.last_status]}`}>
          {t(`kpi.status.${kpi.last_status}`)}
        </span>
      </div>
      <div className="flex items-baseline gap-1 mb-2">
        <span className="text-2xl font-bold text-gray-900">
          {kpi.last_value != null ? kpi.last_value : "—"}
        </span>
        {kpi.unit && <span className="text-sm text-gray-400">{kpi.unit}</span>}
      </div>
      <Sparkline kpiCode={kpi.kpi_code} plantId={plantId} />
      <p className="mt-1 text-[11px] text-gray-400">{kpi.kpi_code}</p>
    </button>
  );
}

export function KpiDashboard() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const selectedPlant = useAuthStore((s) => s.selectedPlant);
  const [plantFilter, setPlantFilter] = useState("");
  const [openKpi, setOpenKpi] = useState<KpiDefinitionListItem | null>(null);

  const { data: plants } = useQuery({
    queryKey: ["plants"],
    queryFn: () => plantsApi.list(),
    retry: false,
  });

  const effectivePlant = plantFilter || selectedPlant?.id || "";
  const params: Record<string, string> = { is_active: "true" };
  if (effectivePlant) params.plant = effectivePlant;

  const { data, isLoading } = useQuery({
    queryKey: ["kpi-definitions-dash", effectivePlant],
    queryFn: () => kpiApi.getKpiDefinitions(params),
    retry: false,
  });

  const computeMutation = useMutation({
    mutationFn: () => kpiApi.computeNow(),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["kpi-definitions-dash"] });
      qc.invalidateQueries({ queryKey: ["kpi-sparkline"] });
    },
  });

  const kpis: KpiDefinitionListItem[] = data?.results ?? [];

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold text-gray-900">{t("kpi.dashboard.title")}</h2>
        <div className="flex items-center gap-2">
          <button
            onClick={() => computeMutation.mutate()}
            disabled={computeMutation.isPending}
            className="px-4 py-2 border border-primary-300 text-primary-700 rounded text-sm hover:bg-primary-50 disabled:opacity-50"
          >
            {computeMutation.isPending ? t("kpi.dashboard.computing") : t("kpi.dashboard.compute_now")}
          </button>
          <button
            onClick={() => navigate("/kpi/definitions")}
            className="px-4 py-2 bg-primary-600 text-white rounded text-sm hover:bg-primary-700"
          >
            {t("kpi.dashboard.manage")}
          </button>
        </div>
      </div>

      <div className="mb-4 flex items-center gap-3">
        <select
          value={plantFilter}
          onChange={(e) => setPlantFilter(e.target.value)}
          className="border rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary-400"
        >
          <option value="">{t("kpi.dashboard.all_plants")}</option>
          {(plants ?? []).map((p) => (
            <option key={p.id} value={p.id}>{p.code} — {p.name}</option>
          ))}
        </select>
        {computeMutation.isSuccess && (
          <span className="text-xs text-green-600">{computeMutation.data?.detail}</span>
        )}
      </div>

      {isLoading ? (
        <div className="p-8 text-center text-gray-400">{t("common.loading")}</div>
      ) : kpis.length === 0 ? (
        <div className="bg-white rounded-lg border border-gray-200 p-8 text-center text-gray-400">
          {t("kpi.dashboard.empty")}
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {kpis.map((kpi) => (
            <KpiCard
              key={kpi.id}
              kpi={kpi}
              plantId={effectivePlant || undefined}
              onOpen={() => setOpenKpi(kpi)}
            />
          ))}
        </div>
      )}

      {openKpi && (
        <KpiTrendModal
          kpiCode={openKpi.kpi_code}
          kpiName={openKpi.name}
          plantId={effectivePlant || undefined}
          onClose={() => setOpenKpi(null)}
        />
      )}
    </div>
  );
}
