import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine, ReferenceArea,
} from "recharts";
import {
  osintApi, classifyScore, scoreBadgeColor, deltaArrow, deltaColor,
  type OsintEntityDetail, type HistoryPoint, type OsintScanDetail,
} from "../../api/endpoints/osint";

function ScorePill({ label, score }: { label: string; score: number }) {
  const cls = classifyScore(score);
  const colors = {
    critical: "bg-red-100 text-red-700 border-red-200",
    warning: "bg-orange-100 text-orange-700 border-orange-200",
    attention: "bg-yellow-100 text-yellow-700 border-yellow-200",
    ok: "bg-green-100 text-green-700 border-green-200",
  };
  return (
    <div className={`flex flex-col items-center px-3 py-2 rounded-lg border ${colors[cls]}`}>
      <span className="text-xs font-medium">{label}</span>
      <span className="text-xl font-bold mt-0.5">{score}</span>
    </div>
  );
}

function FindingRow({ icon, text }: { icon: string; text: string }) {
  return (
    <div className="flex items-start gap-2 text-sm py-1">
      <span className="mt-0.5">{icon}</span>
      <span className="text-gray-700">{text}</span>
    </div>
  );
}

function ScanFindings({ entity }: { entity: OsintEntityDetail }) {
  const { t } = useTranslation();
  const scan = entity.last_scan;
  if (!scan) return <p className="text-sm text-gray-400">{t("osint.detail.no_scan")}</p>;

  const findings: { icon: string; text: string }[] = [];

  // SSL
  if (scan.ssl_valid === false || (scan.ssl_days_remaining !== null && scan.ssl_days_remaining <= 0)) {
    findings.push({ icon: "❌", text: t("osint.findings.ssl_expired", { date: scan.ssl_expiry_date ?? "N/D" }) });
  } else if (scan.ssl_days_remaining !== null && scan.ssl_days_remaining <= 30) {
    findings.push({ icon: "⚠️", text: t("osint.findings.ssl_expiry_soon", { days: scan.ssl_days_remaining }) });
  } else if (scan.ssl_valid === true) {
    findings.push({ icon: "✅", text: t("osint.findings.ssl_ok", { days: scan.ssl_days_remaining ?? "?" }) });
  }

  // DMARC
  if (scan.dmarc_present === false) {
    findings.push({ icon: "❌", text: t("osint.findings.dmarc_missing") });
  } else if (scan.dmarc_present === true && scan.dmarc_policy === "none") {
    findings.push({ icon: "⚠️", text: t("osint.findings.dmarc_none") });
  } else if (scan.dmarc_present === true) {
    findings.push({ icon: "✅", text: t("osint.findings.dmarc_ok", { policy: scan.dmarc_policy }) });
  }

  // SPF
  if (scan.spf_present === false) {
    findings.push({ icon: "❌", text: t("osint.findings.spf_missing") });
  } else if (scan.spf_present === true && scan.spf_policy === "+all") {
    findings.push({ icon: "⚠️", text: t("osint.findings.spf_plus_all") });
  } else if (scan.spf_present === true) {
    findings.push({ icon: "✅", text: t("osint.findings.spf_ok") });
  }

  // DNSSEC
  if (scan.dnssec_enabled === true) {
    findings.push({ icon: "✅", text: t("osint.findings.dnssec_ok") });
  } else if (scan.dnssec_enabled === false) {
    findings.push({ icon: "⚠️", text: t("osint.findings.dnssec_missing") });
  }

  // Domain expiry
  if (scan.domain_expiry_date) {
    const expiry = new Date(scan.domain_expiry_date);
    const daysLeft = Math.ceil((expiry.getTime() - Date.now()) / 86400000);
    if (daysLeft <= 30) {
      findings.push({ icon: "⚠️", text: t("osint.findings.domain_expiry_soon", { days: daysLeft, date: scan.domain_expiry_date }) });
    } else {
      findings.push({ icon: "✅", text: t("osint.findings.domain_expiry_ok", { date: scan.domain_expiry_date }) });
    }
  }

  // Blacklist
  if (scan.in_blacklist) {
    findings.push({ icon: "❌", text: t("osint.findings.blacklist", { sources: (scan.blacklist_sources || []).join(", ") || "N/D" }) });
  } else {
    findings.push({ icon: "✅", text: t("osint.findings.no_blacklist") });
  }

  // VirusTotal
  if (scan.vt_malicious && scan.vt_malicious > 0) {
    findings.push({ icon: "⚠️", text: t("osint.findings.vt_malicious", { count: scan.vt_malicious }) });
  }

  // AbuseIPDB
  if (scan.abuseipdb_score !== null && scan.abuseipdb_score !== undefined) {
    if (scan.abuseipdb_score > 0) {
      findings.push({ icon: "⚠️", text: t("osint.findings.abuseipdb_flagged", { score: scan.abuseipdb_score, reports: scan.abuseipdb_reports ?? 0 }) });
    } else {
      findings.push({ icon: "✅", text: t("osint.findings.abuseipdb_clean") });
    }
  }

  // OTX
  if (scan.otx_pulses && scan.otx_pulses > 0) {
    findings.push({ icon: "⚠️", text: t("osint.findings.otx_pulses", { count: scan.otx_pulses }) });
  }

  // GSB
  if (scan.gsb_status && scan.gsb_status !== "" && scan.gsb_status !== "safe") {
    findings.push({ icon: "❌", text: t("osint.findings.gsb_unsafe", { status: scan.gsb_status }) });
  }

  // HIBP
  if (scan.hibp_breaches && scan.hibp_breaches > 0) {
    findings.push({ icon: "🔓", text: t("osint.findings.breach", { count: scan.hibp_breaches }) });
  }

  // Enricher errors
  const errorNames = Object.keys(scan.enricher_errors || {});
  if (errorNames.length > 0) {
    findings.push({ icon: "⚪", text: t("osint.findings.enricher_error", { names: errorNames.join(", ") }) });
  }

  if (findings.length === 0) {
    return <p className="text-sm text-gray-400">{t("osint.detail.no_scan")}</p>;
  }

  return (
    <div className="space-y-0.5">
      {findings.map((f, i) => <FindingRow key={i} icon={f.icon} text={f.text} />)}
    </div>
  );
}

function TechDataRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex justify-between items-center py-1 border-b border-gray-50 text-sm">
      <span className="text-gray-500 shrink-0 mr-3">{label}</span>
      <span className="text-gray-800 text-right font-mono text-xs truncate max-w-[55%]">{value}</span>
    </div>
  );
}

function bool(v: boolean | null | undefined): string {
  if (v === null || v === undefined) return "—";
  return v ? "✅" : "❌";
}

function ScanTechData({ scan }: { scan: OsintScanDetail }) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);

  return (
    <div className="border rounded-lg overflow-hidden">
      <button
        className="w-full flex items-center justify-between px-4 py-2.5 bg-gray-50 hover:bg-gray-100 text-sm font-medium text-gray-700"
        onClick={() => setOpen(o => !o)}
      >
        <span>🔬 {t("osint.detail.tech_data")}</span>
        <span className="text-gray-400">{open ? "▲" : "▼"}</span>
      </button>
      {open && (
        <div className="px-4 py-2 bg-white">
          <p className="text-xs font-semibold text-gray-500 uppercase mb-1 mt-1">SSL</p>
          <TechDataRow label={t("osint.detail.ssl_issuer")} value={scan.ssl_issuer || "—"} />
          <TechDataRow label={t("osint.detail.ssl_wildcard")} value={bool(scan.ssl_wildcard)} />

          <p className="text-xs font-semibold text-gray-500 uppercase mb-1 mt-3">WHOIS</p>
          <TechDataRow label={t("osint.detail.domain_expiry")} value={scan.domain_expiry_date ?? "—"} />
          <TechDataRow label={t("osint.detail.domain_registrar")} value={scan.domain_registrar || "—"} />
          <TechDataRow label={t("osint.detail.registrar_country")} value={scan.registrar_country || "—"} />
          <TechDataRow label={t("osint.detail.whois_privacy")} value={bool(scan.whois_privacy)} />

          <p className="text-xs font-semibold text-gray-500 uppercase mb-1 mt-3">DNS</p>
          <TechDataRow label={t("osint.detail.dnssec")} value={bool(scan.dnssec_enabled)} />
          <TechDataRow label={t("osint.detail.mx")} value={bool(scan.mx_present)} />

          <p className="text-xs font-semibold text-gray-500 uppercase mb-1 mt-3">Reputation</p>
          <TechDataRow label="VirusTotal suspicious" value={scan.vt_suspicious ?? "—"} />
          <TechDataRow label={t("osint.detail.abuseipdb")} value={scan.abuseipdb_score !== null ? `${scan.abuseipdb_score} (${scan.abuseipdb_reports ?? 0} rep.)` : "—"} />
          <TechDataRow label={t("osint.detail.otx_pulses")} value={scan.otx_pulses ?? "—"} />
          <TechDataRow label={t("osint.detail.gsb")} value={scan.gsb_status || "—"} />

          {(scan.hibp_breaches ?? 0) > 0 && (
            <>
              <p className="text-xs font-semibold text-gray-500 uppercase mb-1 mt-3">HIBP</p>
              <TechDataRow label={t("osint.detail.hibp_last")} value={scan.hibp_latest_breach ?? "—"} />
              <TechDataRow label={t("osint.detail.hibp_types")} value={(scan.hibp_data_types || []).join(", ") || "—"} />
            </>
          )}

          {Object.keys(scan.enricher_errors || {}).length > 0 && (
            <>
              <p className="text-xs font-semibold text-red-500 uppercase mb-1 mt-3">{t("osint.detail.enricher_errors")}</p>
              {Object.entries(scan.enricher_errors).map(([name, err]) => (
                <div key={name} className="text-xs text-red-600 py-0.5">
                  <span className="font-medium">{name}:</span> {err}
                </div>
              ))}
            </>
          )}
        </div>
      )}
    </div>
  );
}

function HistoryChart({ data }: { data: HistoryPoint[] }) {
  const reversed = [...data].reverse();
  return (
    <ResponsiveContainer width="100%" height={180}>
      <LineChart data={reversed} margin={{ top: 5, right: 5, bottom: 5, left: -20 }}>
        <ReferenceArea y1={70} y2={100} fill="#fee2e2" fillOpacity={0.5} />
        <ReferenceArea y1={50} y2={70} fill="#fed7aa" fillOpacity={0.5} />
        <ReferenceArea y1={30} y2={50} fill="#fef9c3" fillOpacity={0.5} />
        <ReferenceArea y1={0} y2={30} fill="#dcfce7" fillOpacity={0.5} />
        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
        <XAxis
          dataKey="scan_date"
          tick={{ fontSize: 10 }}
          tickFormatter={v => new Date(v).toLocaleDateString("it-IT", { month: "short", day: "numeric" })}
        />
        <YAxis domain={[0, 100]} tick={{ fontSize: 10 }} reversed />
        <Tooltip
          formatter={(v: number) => [v, "Score"]}
          labelFormatter={l => new Date(l).toLocaleDateString("it-IT")}
        />
        <Line
          type="monotone"
          dataKey="score_total"
          stroke="#6366f1"
          strokeWidth={2}
          dot={(props) => {
            const point = reversed[props.index];
            return point?.has_alerts
              ? <circle key={props.index} cx={props.cx} cy={props.cy} r={4} fill="#ef4444" stroke="#ef4444" />
              : <circle key={props.index} cx={props.cx} cy={props.cy} r={2} fill="#6366f1" />;
          }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}

export function OsintEntityDrawer({ entityId, onClose }: { entityId: string; onClose: () => void }) {
  const { t } = useTranslation();
  const qc = useQueryClient();

  const { data: entity, isLoading } = useQuery({
    queryKey: ["osint-entity", entityId],
    queryFn: () => osintApi.entity(entityId),
  });

  const { data: history = [] } = useQuery({
    queryKey: ["osint-entity-history", entityId],
    queryFn: () => osintApi.entityHistory(entityId),
  });

  const scanMutation = useMutation({
    mutationFn: () => osintApi.forceScan(entityId),
    onSuccess: () => {
      setTimeout(() => qc.invalidateQueries({ queryKey: ["osint-entity", entityId] }), 2000);
    },
  });

  if (isLoading || !entity) {
    return (
      <div className="fixed inset-0 z-50 flex" onClick={onClose}>
        <div className="ml-auto w-full max-w-2xl bg-white h-full shadow-xl flex items-center justify-center">
          <span className="text-gray-400">{t("common.loading")}</span>
        </div>
      </div>
    );
  }

  const scan = entity.last_scan;
  const delta = scan ? (history.length > 1 ? scan.score_total - history[1]?.score_total : 0) : null;

  return (
    <div className="fixed inset-0 z-50 flex" onClick={onClose}>
      <div
        className="ml-auto w-full max-w-2xl bg-white h-full shadow-xl overflow-y-auto"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="sticky top-0 bg-white border-b px-6 py-4 flex items-center justify-between z-10">
          <div>
            <h2 className="font-bold text-gray-900 text-lg">{entity.display_name}</h2>
            <p className="text-xs text-gray-500">{entity.domain}</p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => scanMutation.mutate()}
              disabled={scanMutation.isPending}
              className="px-3 py-1.5 text-sm border rounded hover:bg-gray-50 disabled:opacity-50"
            >
              {scanMutation.isPending ? "⏳" : "🔄"} {t("osint.detail.force_scan")}
            </button>
            <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded">✕</button>
          </div>
        </div>

        <div className="p-6 space-y-6">
          {/* Score totale */}
          {scan && (
            <div className="flex items-center gap-4 p-4 border rounded-lg bg-gray-50">
              <div>
                <div className="text-xs text-gray-500 mb-1">{t("osint.detail.total_score")}</div>
                <span className={`text-3xl font-bold ${scoreBadgeColor(classifyScore(scan.score_total))}`}>
                  {scan.score_total}
                </span>
              </div>
              {delta !== null && (
                <div className={`text-sm font-medium ${deltaColor(delta)}`}>
                  {deltaArrow(delta)} {t("osint.detail.vs_last_week")}
                </div>
              )}
              <div className="ml-auto text-xs text-gray-400">
                {t("osint.detail.last_scan")}: {new Date(scan.scan_date).toLocaleDateString("it-IT")}
              </div>
            </div>
          )}

          {/* 4 score */}
          {scan && (
            <div className="grid grid-cols-4 gap-3">
              <ScorePill label="SSL" score={scan.score_ssl} />
              <ScorePill label="DNS" score={scan.score_dns} />
              <ScorePill label={t("osint.detail.reputation")} score={scan.score_reputation} />
              <ScorePill label="GRC" score={scan.score_grc_context} />
            </div>
          )}

          {/* Finding */}
          <div>
            <h3 className="text-sm font-semibold text-gray-700 mb-2">{t("osint.detail.findings")}</h3>
            <ScanFindings entity={entity} />
          </div>

          {/* Dati tecnici (collassabile) */}
          {scan && <ScanTechData scan={scan} />}

          {/* Grafico storico */}
          {history.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-gray-700 mb-2">{t("osint.detail.history")}</h3>
              <HistoryChart data={history} />
            </div>
          )}

          {/* Alert attivi */}
          {entity.active_alerts.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-gray-700 mb-2">{t("osint.detail.active_alerts")}</h3>
              <div className="space-y-2">
                {entity.active_alerts.map(a => (
                  <div key={a.id} className={`flex items-start gap-3 p-3 rounded-lg border ${
                    a.severity === "critical" ? "border-red-200 bg-red-50" :
                    a.severity === "warning" ? "border-orange-200 bg-orange-50" : "border-gray-200 bg-gray-50"
                  }`}>
                    <span>{a.severity === "critical" ? "🔴" : a.severity === "warning" ? "🟠" : "ℹ️"}</span>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900">{a.description}</p>
                      {a.linked_incident_id && (
                        <p className="text-xs text-blue-600 mt-0.5">
                          → {t("osint.detail.linked_incident")} #{a.linked_incident_id.slice(0, 8)}
                        </p>
                      )}
                      {a.linked_task_id && (
                        <p className="text-xs text-blue-600 mt-0.5">
                          → {t("osint.detail.linked_task")} #{a.linked_task_id.slice(0, 8)}
                        </p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
