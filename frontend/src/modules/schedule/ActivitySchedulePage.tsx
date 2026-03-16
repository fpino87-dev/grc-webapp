import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { scheduleApi, ActivityItem } from "../../api/endpoints/schedule";
import { plantsApi } from "../../api/endpoints/plants";
import { ModuleHelp } from "../../components/ui/ModuleHelp";

const URGENCY_COLOR: Record<string, string> = {
  green:  "bg-green-100 text-green-800 border-green-200",
  yellow: "bg-yellow-100 text-yellow-800 border-yellow-200",
  red:    "bg-red-100 text-red-800 border-red-200",
};

const URGENCY_DOT: Record<string, string> = {
  green:  "bg-green-500",
  yellow: "bg-yellow-500",
  red:    "bg-red-500",
};

const MONTH_OPTIONS = [
  { label: "3 mesi",   value: 3 },
  { label: "6 mesi",   value: 6 },
  { label: "12 mesi",  value: 12 },
];

function ActivityRow({ item }: { item: ActivityItem }) {
  return (
    <tr className="hover:bg-gray-50">
      <td className="px-4 py-3">
        <div className="flex items-center gap-2">
          <span className={`inline-block w-2 h-2 rounded-full ${URGENCY_DOT[item.urgency]}`} />
          <span className="text-sm font-medium text-gray-900">{item.label}</span>
        </div>
      </td>
      <td className="px-4 py-3 text-sm text-gray-600">{item.category_label}</td>
      <td className="px-4 py-3 text-sm text-gray-700">{item.due_date}</td>
      <td className="px-4 py-3">
        <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${URGENCY_COLOR[item.urgency]}`}>
          {item.days_left === 0 ? "Oggi" : item.days_left < 0 ? "Scaduto" : `${item.days_left}gg`}
        </span>
      </td>
      <td className="px-4 py-3 text-sm text-gray-500">{item.status}</td>
    </tr>
  );
}

export function ActivitySchedulePage() {
  const [plantId, setPlantId] = useState<string>("");
  const [months, setMonths] = useState(6);
  const [urgencyFilter, setUrgencyFilter] = useState<string>("all");

  const { data: plants } = useQuery({
    queryKey: ["plants"],
    queryFn: () => plantsApi.list(),
    retry: false,
  });

  const { data, isLoading, refetch } = useQuery({
    queryKey: ["activity-schedule", plantId, months],
    queryFn: () => scheduleApi.getActivitySchedule({
      plant: plantId || undefined,
      months,
    }),
    retry: false,
  });

  const activities = data?.results ?? [];
  const filtered = urgencyFilter === "all" ? activities : activities.filter(a => a.urgency === urgencyFilter);

  const red = activities.filter(a => a.urgency === "red").length;
  const yellow = activities.filter(a => a.urgency === "yellow").length;
  const green = activities.filter(a => a.urgency === "green").length;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-semibold text-gray-900 flex items-center">
          Activity Schedule
          <ModuleHelp
            title="Activity Schedule"
            description="Vista calendario aggregata di tutte le scadenze GRC:
    documenti, evidenze, assessment, test BCP, finding, formazione.
    Le scadenze sono calcolate dalla Policy configurata."
            steps={[
              "Seleziona il plant e il periodo (1-12 mesi)",
              "Filtra per tipo (documenti, rischi, finding, ecc.) o stato",
              "Clicca su ogni attività per andare direttamente al modulo",
              "Configura le scadenze in 'Policy Scadenze' (solo CISO/Admin)",
            ]}
            connections={[
              { module: "Policy Scadenze", relation: "Le regole configurate determinano tutte le scadenze" },
              { module: "Documenti Obbligatori", relation: "Mostra stato documenti per framework" },
            ]}
            configNeeded={[
              "Configurare Policy Scadenze con 'Crea policy default'",
              "Caricare i documenti obbligatori con load_required_documents",
            ]}
          />
        </h2>
        <button
          onClick={() => refetch()}
          className="text-sm text-blue-600 hover:underline"
        >
          Aggiorna
        </button>
      </div>

      {/* Filters */}
      <div className="bg-white border border-gray-200 rounded-lg p-4 mb-6">
        <div className="flex flex-wrap gap-4 items-end">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Sito</label>
            <select
              value={plantId}
              onChange={e => setPlantId(e.target.value)}
              className="border border-gray-300 rounded px-2 py-1.5 text-sm"
            >
              <option value="">Tutti i siti</option>
              {plants?.map(p => (
                <option key={p.id} value={p.id}>[{p.code}] {p.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Orizzonte</label>
            <div className="flex gap-1">
              {MONTH_OPTIONS.map(opt => (
                <button
                  key={opt.value}
                  onClick={() => setMonths(opt.value)}
                  className={`px-2 py-1 text-xs rounded border ${
                    months === opt.value
                      ? "bg-blue-600 text-white border-blue-600"
                      : "text-gray-600 border-gray-300 hover:bg-gray-50"
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Urgenza</label>
            <div className="flex gap-1">
              {[
                { value: "all",    label: "Tutte" },
                { value: "red",    label: "Critiche" },
                { value: "yellow", label: "Attenzione" },
                { value: "green",  label: "Ok" },
              ].map(opt => (
                <button
                  key={opt.value}
                  onClick={() => setUrgencyFilter(opt.value)}
                  className={`px-2 py-1 text-xs rounded border ${
                    urgencyFilter === opt.value
                      ? "bg-gray-700 text-white border-gray-700"
                      : "text-gray-600 border-gray-300 hover:bg-gray-50"
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Summary KPIs */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-xs font-medium text-red-700 uppercase tracking-wide">Critiche (&lt;7gg)</p>
          <p className="text-3xl font-bold text-red-700 mt-1">{red}</p>
        </div>
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <p className="text-xs font-medium text-yellow-700 uppercase tracking-wide">Attenzione</p>
          <p className="text-3xl font-bold text-yellow-700 mt-1">{yellow}</p>
        </div>
        <div className="bg-green-50 border border-green-200 rounded-lg p-4">
          <p className="text-xs font-medium text-green-700 uppercase tracking-wide">Nei tempi</p>
          <p className="text-3xl font-bold text-green-700 mt-1">{green}</p>
        </div>
      </div>

      {/* Table */}
      <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-gray-400 text-sm">Caricamento...</div>
        ) : filtered.length === 0 ? (
          <div className="p-8 text-center text-gray-400 text-sm italic">
            {activities.length === 0
              ? "Nessuna scadenza nei prossimi " + months + " mesi"
              : "Nessuna scadenza per il filtro selezionato"}
          </div>
        ) : (
          <table className="w-full text-left">
            <thead>
              <tr className="bg-gray-50 border-b border-gray-200">
                <th className="px-4 py-3 text-xs font-semibold text-gray-600 uppercase tracking-wide">Attività</th>
                <th className="px-4 py-3 text-xs font-semibold text-gray-600 uppercase tracking-wide">Categoria</th>
                <th className="px-4 py-3 text-xs font-semibold text-gray-600 uppercase tracking-wide">Scadenza</th>
                <th className="px-4 py-3 text-xs font-semibold text-gray-600 uppercase tracking-wide">Giorni</th>
                <th className="px-4 py-3 text-xs font-semibold text-gray-600 uppercase tracking-wide">Stato</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {filtered.map((item, idx) => (
                <ActivityRow key={`${item.category}-${item.ref_id}-${idx}`} item={item} />
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
