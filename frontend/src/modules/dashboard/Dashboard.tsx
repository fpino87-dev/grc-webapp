import { useQuery } from "@tanstack/react-query";
import { controlsApi } from "../../api/endpoints/controls";
import { incidentsApi } from "../../api/endpoints/incidents";
import { plantsApi } from "../../api/endpoints/plants";
import { StatusBadge } from "../../components/ui/StatusBadge";

function KpiCard({
  label,
  value,
  sub,
  color = "blue",
}: {
  label: string;
  value: string | number;
  sub?: string;
  color?: string;
}) {
  const colors: Record<string, string> = {
    blue: "bg-blue-50 border-blue-200 text-blue-700",
    green: "bg-green-50 border-green-200 text-green-700",
    red: "bg-red-50 border-red-200 text-red-700",
    yellow: "bg-yellow-50 border-yellow-200 text-yellow-700",
  };
  return (
    <div className={`border rounded-lg p-4 ${colors[color]}`}>
      <p className="text-xs font-medium uppercase tracking-wide opacity-70">{label}</p>
      <p className="text-3xl font-bold mt-1">{value}</p>
      {sub && <p className="text-xs mt-1 opacity-60">{sub}</p>}
    </div>
  );
}

export function Dashboard() {
  const { data: controlsData } = useQuery({
    queryKey: ["controls-summary"],
    queryFn: () => controlsApi.instances(),
    retry: false,
  });
  const { data: incidentsData } = useQuery({
    queryKey: ["incidents-summary"],
    queryFn: () => incidentsApi.list({ status: "aperto" }),
    retry: false,
  });
  const { data: plants } = useQuery({
    queryKey: ["plants"],
    queryFn: () => plantsApi.list(),
    retry: false,
  });

  const controls = controlsData?.results ?? [];
  const compliant = controls.filter((c) => c.status === "compliant").length;
  const gap = controls.filter((c) => c.status === "gap").length;
  const openIncidents = incidentsData?.count ?? 0;

  return (
    <div>
      <h2 className="text-xl font-semibold text-gray-900 mb-6">Dashboard</h2>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <KpiCard label="Siti attivi" value={plants?.length ?? "—"} color="blue" />
        <KpiCard
          label="Controlli compliant"
          value={controls.length ? `${Math.round((compliant / controls.length) * 100)}%` : "—"}
          sub={`${compliant} / ${controls.length}`}
          color="green"
        />
        <KpiCard
          label="Controlli in gap"
          value={gap}
          sub="richiedono azione"
          color={gap > 0 ? "red" : "green"}
        />
        <KpiCard
          label="Incidenti aperti"
          value={openIncidents}
          color={openIncidents > 0 ? "yellow" : "green"}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">Ultimi controlli in gap</h3>
          {gap === 0 ? (
            <p className="text-sm text-gray-400 italic">Nessun gap rilevato</p>
          ) : (
            <div className="space-y-2">
              {controls
                .filter((c) => c.status === "gap")
                .slice(0, 5)
                .map((c) => (
                  <div key={c.id} className="flex items-center justify-between text-sm">
                    <span className="text-gray-700 truncate flex-1">
                      {c.control_external_id} — {c.control_title || c.control}
                    </span>
                    <StatusBadge status={c.status} />
                  </div>
                ))}
            </div>
          )}
        </div>

        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">Siti</h3>
          {!plants?.length ? (
            <p className="text-sm text-gray-400 italic">Nessun sito configurato</p>
          ) : (
            <div className="space-y-2">
              {plants.slice(0, 6).map((p) => (
                <div key={p.id} className="flex items-center justify-between text-sm">
                  <span className="font-medium text-gray-700">
                    [{p.code}] {p.name}
                  </span>
                  <div className="flex gap-1">
                    <StatusBadge status={p.status} />
                    {p.nis2_scope !== "non_soggetto" && <StatusBadge status={p.nis2_scope} />}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
