import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "../../api/client";
import { useAuthStore } from "../../store/auth";
import { useTranslation } from "react-i18next";

// ─── Dati statici BIA/Risk (testi via i18n) ──────────────────────────────────

const CRITICALITY_COLORS: Record<number, string> = {
  1: "text-green-700",
  2: "text-yellow-700",
  3: "text-orange-700",
  4: "text-red-600",
  5: "text-red-800 font-bold",
};

// ─── Helper: cella heatmap ───────────────────────────────────────────────────

function cellColor(score: number): string {
  if (score >= 15) return "bg-red-500 text-white";
  if (score >= 8)  return "bg-yellow-400 text-gray-800";
  return "bg-green-400 text-white";
}

// ─── TAB 1: BIA ──────────────────────────────────────────────────────────────

function TabBia() {
  const { t } = useTranslation();
  const [sliders, setSliders] = useState<Record<string, number>>({ economico: 3, clienti: 3, normativo: 3 });

  const biaLevels = useMemo(() => ([
    { value: 1, label: t("eval_assistant.bia.levels.1.label"), downtime: t("eval_assistant.bia.levels.1.downtime"), color: "bg-green-100 text-green-800 border-green-200", example: t("eval_assistant.bia.levels.1.example") },
    { value: 2, label: t("eval_assistant.bia.levels.2.label"), downtime: t("eval_assistant.bia.levels.2.downtime"), color: "bg-yellow-100 text-yellow-800 border-yellow-200", example: t("eval_assistant.bia.levels.2.example") },
    { value: 3, label: t("eval_assistant.bia.levels.3.label"), downtime: t("eval_assistant.bia.levels.3.downtime"), color: "bg-orange-100 text-orange-800 border-orange-200", example: t("eval_assistant.bia.levels.3.example") },
    { value: 4, label: t("eval_assistant.bia.levels.4.label"), downtime: t("eval_assistant.bia.levels.4.downtime"), color: "bg-red-100 text-red-800 border-red-200", example: t("eval_assistant.bia.levels.4.example") },
    { value: 5, label: t("eval_assistant.bia.levels.5.label"), downtime: t("eval_assistant.bia.levels.5.downtime"), color: "bg-red-200 text-red-900 border-red-300", example: t("eval_assistant.bia.levels.5.example") },
  ]), [t]);

  const sliderQuestions = useMemo(() => ([
    { id: "economico", label: t("eval_assistant.bia.questions.economic.label"), low: t("eval_assistant.bia.questions.economic.low"), high: t("eval_assistant.bia.questions.economic.high") },
    { id: "clienti", label: t("eval_assistant.bia.questions.customers.label"), low: t("eval_assistant.bia.questions.customers.low"), high: t("eval_assistant.bia.questions.customers.high") },
    { id: "normativo", label: t("eval_assistant.bia.questions.regulatory.label"), low: t("eval_assistant.bia.questions.regulatory.low"), high: t("eval_assistant.bia.questions.regulatory.high") },
  ]), [t]);

  const avg = Math.round(Object.values(sliders).reduce((a, b) => a + b, 0) / sliderQuestions.length);
  const suggested = biaLevels.find(l => l.value === avg) ?? biaLevels[2];

  return (
    <div className="space-y-5">
      {/* Tabella criticità */}
      <div>
        <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">{t("eval_assistant.bia.scale_title")}</p>
        <div className="rounded-lg border border-gray-200 overflow-hidden text-sm">
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="text-left px-3 py-2 text-xs font-medium text-gray-500">{t("eval_assistant.bia.columns.level")}</th>
                <th className="text-left px-3 py-2 text-xs font-medium text-gray-500">{t("eval_assistant.bia.columns.max_downtime")}</th>
                <th className="text-left px-3 py-2 text-xs font-medium text-gray-500">{t("eval_assistant.bia.columns.example")}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {biaLevels.map(l => (
                <tr key={l.value} className="hover:bg-gray-50">
                  <td className="px-3 py-2">
                    <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded border text-xs font-medium ${l.color}`}>
                      {l.value} — {l.label}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-xs text-gray-600 font-mono">{l.downtime}</td>
                  <td className="px-3 py-2 text-xs text-gray-500">{l.example}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Slider guida */}
      <div>
        <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">{t("eval_assistant.bia.guided_estimate_title")}</p>
        <div className="space-y-4">
          {sliderQuestions.map(q => (
            <div key={q.id}>
              <div className="flex justify-between mb-1">
                <span className="text-sm font-medium text-gray-700">{q.label}</span>
                <span className={`text-sm font-bold ${CRITICALITY_COLORS[sliders[q.id]]}`}>{sliders[q.id]}</span>
              </div>
              <input
                type="range" min={1} max={5} step={1}
                value={sliders[q.id]}
                onChange={e => setSliders(s => ({ ...s, [q.id]: Number(e.target.value) }))}
                className="w-full h-2 rounded-lg appearance-none cursor-pointer bg-gray-200 accent-blue-600"
              />
              <div className="flex justify-between text-xs text-gray-400 mt-0.5">
                <span>{q.low}</span>
                <span>{q.high}</span>
              </div>
            </div>
          ))}
        </div>

        <div className={`mt-4 rounded-lg px-4 py-3 border ${suggested.color}`}>
          <p className="text-xs font-semibold uppercase tracking-wide mb-0.5">{t("eval_assistant.bia.suggested_title")}</p>
          <p className="text-lg font-bold">{suggested.value} — {suggested.label}</p>
          <p className="text-xs mt-0.5">{t("eval_assistant.bia.suggested_downtime", { downtime: suggested.downtime })}</p>
        </div>
      </div>
    </div>
  );
}

// ─── TAB 2: Risk ─────────────────────────────────────────────────────────────

function TabRisk() {
  const { t } = useTranslation();
  const riskZones = useMemo(() => ([
    { key: "green", label: t("eval_assistant.risk.zones.green.label"), range: t("eval_assistant.risk.zones.green.range"), desc: t("eval_assistant.risk.zones.green.desc"), bg: "bg-green-100", text: "text-green-800" },
    { key: "yellow", label: t("eval_assistant.risk.zones.yellow.label"), range: t("eval_assistant.risk.zones.yellow.range"), desc: t("eval_assistant.risk.zones.yellow.desc"), bg: "bg-yellow-100", text: "text-yellow-800" },
    { key: "red", label: t("eval_assistant.risk.zones.red.label"), range: t("eval_assistant.risk.zones.red.range"), desc: t("eval_assistant.risk.zones.red.desc"), bg: "bg-red-100", text: "text-red-800" },
  ]), [t]);

  const itDimensions = useMemo(() => ([
    { code: "esposizione", label: t("eval_assistant.risk.it_dimensions.exposure.label"), weight: "30%", desc: t("eval_assistant.risk.it_dimensions.exposure.desc") },
    { code: "cve", label: t("eval_assistant.risk.it_dimensions.cve.label"), weight: "25%", desc: t("eval_assistant.risk.it_dimensions.cve.desc") },
    { code: "minaccia", label: t("eval_assistant.risk.it_dimensions.threat.label"), weight: "25%", desc: t("eval_assistant.risk.it_dimensions.threat.desc") },
    { code: "gap_ctrl", label: t("eval_assistant.risk.it_dimensions.controls_gap.label"), weight: "20%", desc: t("eval_assistant.risk.it_dimensions.controls_gap.desc") },
  ]), [t]);

  const otDimensions = useMemo(() => ([
    { code: "purdue", label: t("eval_assistant.risk.ot_dimensions.purdue.label"), weight: "25%", desc: t("eval_assistant.risk.ot_dimensions.purdue.desc") },
    { code: "patchability", label: t("eval_assistant.risk.ot_dimensions.patchability.label"), weight: "20%", desc: t("eval_assistant.risk.ot_dimensions.patchability.desc") },
    { code: "impatto_fis", label: t("eval_assistant.risk.ot_dimensions.physical_impact.label"), weight: "25%", desc: t("eval_assistant.risk.ot_dimensions.physical_impact.desc") },
    { code: "segmentaz", label: t("eval_assistant.risk.ot_dimensions.segmentation.label"), weight: "15%", desc: t("eval_assistant.risk.ot_dimensions.segmentation.desc") },
    { code: "rilevabilita", label: t("eval_assistant.risk.ot_dimensions.detection.label"), weight: "15%", desc: t("eval_assistant.risk.ot_dimensions.detection.desc") },
  ]), [t]);

  return (
    <div className="space-y-5">
      {/* Heatmap 5×5 */}
      <div>
        <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">{t("eval_assistant.risk.matrix_title")}</p>
        <div className="overflow-auto">
          <table className="text-xs border-collapse">
            <thead>
              <tr>
                <th className="w-12 text-right pr-2 text-gray-400 font-normal">P\I</th>
                {[1,2,3,4,5].map(i => (
                  <th key={i} className="w-10 h-8 text-center text-gray-500 font-medium">{i}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {[5,4,3,2,1].map(p => (
                <tr key={p}>
                  <td className="text-right pr-2 text-gray-500 font-medium">{p}</td>
                  {[1,2,3,4,5].map(i => {
                    const score = p * i;
                    return (
                      <td key={i} className={`w-10 h-8 text-center rounded text-xs font-bold border border-white/50 ${cellColor(score)}`}>
                        {score}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="mt-2 flex gap-2">
          {riskZones.map(z => (
            <div key={z.key} className={`flex-1 rounded px-2 py-1.5 text-xs ${z.bg} ${z.text}`}>
              <span className="font-semibold">{z.label}</span> <span className="opacity-75">{z.range}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Zone e significato */}
      <div className="space-y-2">
        {riskZones.map(z => (
          <div key={z.key} className={`rounded-lg px-3 py-2 border ${z.bg} border-opacity-50`}>
            <span className={`font-semibold text-sm ${z.text}`}>{z.label} — {z.range}</span>
            <p className="text-xs text-gray-600 mt-0.5">{z.desc}</p>
          </div>
        ))}
      </div>

      {/* Dimensioni IT */}
      <div>
        <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">{t("eval_assistant.risk.it_dimensions_title")}</p>
        <div className="space-y-1.5">
          {itDimensions.map(d => (
            <div key={d.code} className="flex gap-2 items-start bg-blue-50 rounded px-3 py-2">
              <span className="text-xs font-mono font-bold text-blue-700 shrink-0 w-24">{d.label} <span className="text-blue-400">({d.weight})</span></span>
              <span className="text-xs text-gray-600">{d.desc}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Dimensioni OT */}
      <div>
        <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">{t("eval_assistant.risk.ot_dimensions_title")}</p>
        <div className="space-y-1.5">
          {otDimensions.map(d => (
            <div key={d.code} className="flex gap-2 items-start bg-orange-50 rounded px-3 py-2">
              <span className="text-xs font-mono font-bold text-orange-700 shrink-0 w-24">{d.label} <span className="text-orange-400">({d.weight})</span></span>
              <span className="text-xs text-gray-600">{d.desc}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ─── TAB 3: Connessioni ───────────────────────────────────────────────────────

function TabConnessioni() {
  const { t } = useTranslation();
  const selectedPlant = useAuthStore(s => s.selectedPlant);
  const plantId = selectedPlant?.id;

  const { data: missingBcp } = useQuery({
    queryKey: ["bcp-missing-plans", plantId],
    queryFn: () => apiClient.get(`/bcp/plans/missing-plans/${plantId ? `?plant=${plantId}` : ""}`).then(r => r.data as unknown[]),
    enabled: true,
    retry: false,
  });

  const { data: redRisks } = useQuery({
    queryKey: ["risk-red-no-pdca", plantId],
    queryFn: () => apiClient.get(`/risk/assessments/?risk_level=rosso&has_pdca=false${plantId ? `&plant=${plantId}` : ""}`).then(r => (r.data as { results?: unknown[] }).results ?? r.data as unknown[]),
    retry: false,
  });

  const missingCount = Array.isArray(missingBcp) ? missingBcp.length : 0;
  const redCount = Array.isArray(redRisks) ? redRisks.length : 0;

  return (
    <div className="space-y-5">
      {/* Diagramma SVG */}
      <div>
        <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">{t("eval_assistant.connections.chain_title")}</p>
        <div className="bg-gray-50 rounded-lg p-3 overflow-auto">
          <svg viewBox="0 0 420 280" className="w-full text-xs" style={{ minWidth: 360 }}>
            {/* Nodi */}
            <g>
              {/* BIA */}
              <rect x="10" y="10" width="120" height="40" rx="6" fill="#dbeafe" stroke="#3b82f6" strokeWidth="1.5"/>
              <text x="70" y="26" textAnchor="middle" fill="#1e40af" fontWeight="bold" fontSize="11">
                {t("eval_assistant.connections.nodes.bia_title")}
              </text>
              <text x="70" y="42" textAnchor="middle" fill="#3b82f6" fontSize="9">
                {t("eval_assistant.connections.nodes.bia_subtitle")}
              </text>

              {/* Risk */}
              <rect x="200" y="10" width="130" height="40" rx="6" fill="#fef3c7" stroke="#d97706" strokeWidth="1.5"/>
              <text x="265" y="26" textAnchor="middle" fill="#92400e" fontWeight="bold" fontSize="11">
                {t("eval_assistant.connections.nodes.risk_title")}
              </text>
              <text x="265" y="42" textAnchor="middle" fill="#d97706" fontSize="9">
                {t("eval_assistant.connections.nodes.risk_subtitle")}
              </text>

              {/* BCP */}
              <rect x="10" y="120" width="120" height="40" rx="6" fill="#d1fae5" stroke="#10b981" strokeWidth="1.5"/>
              <text x="70" y="136" textAnchor="middle" fill="#065f46" fontWeight="bold" fontSize="11">
                {t("eval_assistant.connections.nodes.bcp_title")}
              </text>
              <text x="70" y="152" textAnchor="middle" fill="#10b981" fontSize="9">
                {t("eval_assistant.connections.nodes.bcp_subtitle")}
              </text>

              {/* Score > 14 */}
              <rect x="200" y="120" width="130" height="40" rx="6" fill="#fee2e2" stroke="#ef4444" strokeWidth="1.5"/>
              <text x="265" y="136" textAnchor="middle" fill="#991b1b" fontWeight="bold" fontSize="11">
                {t("eval_assistant.connections.nodes.score_title")}
              </text>
              <text x="265" y="152" textAnchor="middle" fill="#ef4444" fontSize="9">
                {t("eval_assistant.connections.nodes.score_subtitle")}
              </text>

              {/* PDCA */}
              <rect x="200" y="220" width="130" height="40" rx="6" fill="#f3e8ff" stroke="#8b5cf6" strokeWidth="1.5"/>
              <text x="265" y="236" textAnchor="middle" fill="#5b21b6" fontWeight="bold" fontSize="11">
                {t("eval_assistant.connections.nodes.pdca_title")}
              </text>
              <text x="265" y="252" textAnchor="middle" fill="#8b5cf6" fontSize="9">
                {t("eval_assistant.connections.nodes.pdca_subtitle")}
              </text>

              {/* Lesson Learned */}
              <rect x="10" y="220" width="120" height="40" rx="6" fill="#fce7f3" stroke="#ec4899" strokeWidth="1.5"/>
              <text x="70" y="236" textAnchor="middle" fill="#9d174d" fontWeight="bold" fontSize="11">
                {t("eval_assistant.connections.nodes.lesson_title")}
              </text>
              <text x="70" y="252" textAnchor="middle" fill="#ec4899" fontSize="9">
                {t("eval_assistant.connections.nodes.lesson_subtitle")}
              </text>
            </g>

            {/* Frecce */}
            <defs>
              <marker id="arr" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
                <polygon points="0 0, 8 3, 0 6" fill="#6b7280"/>
              </marker>
            </defs>
            {/* BIA → Risk */}
            <line x1="130" y1="30" x2="198" y2="30" stroke="#6b7280" strokeWidth="1.5" markerEnd="url(#arr)"/>
            <text x="164" y="24" textAnchor="middle" fill="#6b7280" fontSize="8">
              {t("eval_assistant.connections.edges.criticality")}
            </text>

            {/* BIA ↓ BCP */}
            <line x1="70" y1="50" x2="70" y2="118" stroke="#6b7280" strokeWidth="1.5" markerEnd="url(#arr)"/>

            {/* Risk ↓ Score */}
            <line x1="265" y1="50" x2="265" y2="118" stroke="#6b7280" strokeWidth="1.5" markerEnd="url(#arr)"/>

            {/* Score ↓ PDCA */}
            <line x1="265" y1="160" x2="265" y2="218" stroke="#ef4444" strokeWidth="1.5" markerEnd="url(#arr)"/>

            {/* Score → BCP */}
            <line x1="200" y1="140" x2="132" y2="140" stroke="#6b7280" strokeWidth="1.5" markerEnd="url(#arr)"/>
            <text x="166" y="134" textAnchor="middle" fill="#6b7280" fontSize="8">
              {t("eval_assistant.connections.edges.rto_rpo")}
            </text>

            {/* PDCA → Lesson */}
            <line x1="200" y1="240" x2="132" y2="240" stroke="#6b7280" strokeWidth="1.5" markerEnd="url(#arr)"/>

            {/* BCP → Lesson */}
            <line x1="70" y1="160" x2="70" y2="218" stroke="#6b7280" strokeWidth="1.5" markerEnd="url(#arr)"/>
          </svg>
        </div>
      </div>

      {/* Alert dinamici */}
      <div className="space-y-2">
        <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">{t("eval_assistant.connections.realtime_alerts_title")}</p>

        {missingCount > 0 ? (
          <div className="flex items-start gap-2 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2.5">
            <span className="text-lg shrink-0">⚠️</span>
            <div>
              <p className="text-sm font-semibold text-amber-800">
                {t("eval_assistant.connections.missing_bcp.title", { count: missingCount })}
              </p>
              <p className="text-xs text-amber-600 mt-0.5">
                {t("eval_assistant.connections.missing_bcp.body")}
              </p>
            </div>
          </div>
        ) : (
          <div className="flex items-center gap-2 bg-green-50 border border-green-200 rounded-lg px-3 py-2.5">
            <span className="text-lg">✅</span>
            <p className="text-sm text-green-700">{t("eval_assistant.connections.missing_bcp.ok")}</p>
          </div>
        )}

        {redCount > 0 ? (
          <div className="flex items-start gap-2 bg-red-50 border border-red-200 rounded-lg px-3 py-2.5">
            <span className="text-lg shrink-0">🔴</span>
            <div>
              <p className="text-sm font-semibold text-red-800">
                {t("eval_assistant.connections.missing_pdca.title", { count: redCount })}
              </p>
              <p className="text-xs text-red-600 mt-0.5">
                {t("eval_assistant.connections.missing_pdca.body")}
              </p>
            </div>
          </div>
        ) : (
          <div className="flex items-center gap-2 bg-green-50 border border-green-200 rounded-lg px-3 py-2.5">
            <span className="text-lg">✅</span>
            <p className="text-sm text-green-700">{t("eval_assistant.connections.missing_pdca.ok")}</p>
          </div>
        )}

        {!plantId && (
          <p className="text-xs text-gray-400 text-center mt-1">
            {t("eval_assistant.connections.select_plant_hint")}
          </p>
        )}
      </div>
    </div>
  );
}

// ─── Componente principale ────────────────────────────────────────────────────

type Tab = "bia" | "risk" | "connessioni";

interface Props {
  open: boolean;
  onClose: () => void;
}

export function AssistenteValutazione({ open, onClose }: Props) {
  const { t: tt } = useTranslation();
  const [tab, setTab] = useState<Tab>("bia");

  return (
    <>
      {/* Overlay */}
      {open && (
        <div
          className="fixed inset-0 bg-black/30 z-40"
          onClick={onClose}
        />
      )}

      {/* Drawer */}
      <div
        className={`fixed top-0 right-0 h-full z-50 bg-white shadow-2xl flex flex-col transition-transform duration-300 ease-in-out ${open ? "translate-x-0" : "translate-x-full"}`}
        style={{ width: 420 }}
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100 shrink-0 bg-gradient-to-r from-blue-600 to-blue-700">
          <div>
            <h2 className="text-white font-semibold text-base">{tt("eval_assistant.title")}</h2>
            <p className="text-blue-200 text-xs mt-0.5">{tt("eval_assistant.subtitle")}</p>
          </div>
          <button
            onClick={onClose}
            className="text-white/80 hover:text-white w-8 h-8 flex items-center justify-center rounded-lg hover:bg-white/10 text-xl"
          >
            ×
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-gray-200 shrink-0">
          {(["bia", "risk", "connessioni"] as Tab[]).map(tabKey => (
            <button
              key={tabKey}
              onClick={() => setTab(tabKey)}
              className={`flex-1 py-2.5 text-sm font-medium transition-colors capitalize ${
                tab === tabKey
                  ? "border-b-2 border-blue-600 text-blue-700 bg-blue-50"
                  : "text-gray-500 hover:text-gray-700 hover:bg-gray-50"
              }`}
            >
              {tabKey === "connessioni" ? tt("eval_assistant.tabs.connections") : tabKey.toUpperCase()}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-5 py-4">
          {tab === "bia" && <TabBia />}
          {tab === "risk" && <TabRisk />}
          {tab === "connessioni" && <TabConnessioni />}
        </div>
      </div>
    </>
  );
}
