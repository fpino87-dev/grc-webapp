import { useState, useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceArea,
} from "recharts";
import {
  osintApi, classifyScore,
  EXPECTED_POSTURES,
  type ExpectedPosture, type OsintEntityDetail, type HistoryPoint,
  type OsintScanDetail, type OsintFinding, type OsintAlert,
} from "../../api/endpoints/osint";
import { Link } from "react-router-dom";
import { GradeBadge, ReportToSupplierDialog, findingTitle } from "./shared";

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
      {/* sicurezza della dimensione (100 − rischio): più alto = meglio */}
      <span className="text-xl font-bold mt-0.5">{100 - score}</span>
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

/** Controlli superati (✅): i problemi veri arrivano dal backend (tab Problemi). */
function ScanFindings({ entity }: { entity: OsintEntityDetail }) {
  const { t } = useTranslation();
  const scan = entity.last_scan;
  if (!scan) return <p className="text-sm text-gray-400">{t("osint.detail.no_scan")}</p>;

  const findings: { icon: string; text: string }[] = [];

  // SSL
  const issuerSuffix = scan.ssl_issuer ? ` (CA: ${scan.ssl_issuer})` : "";
  if (scan.ssl_valid === null && !scan.enricher_errors?.ssl) {
    // Check eseguito ma nessun HTTPS trovato — non è un errore
    findings.push({ icon: "ℹ️", text: t("osint.findings.ssl_no_https", { domain: entity.domain }) });
  } else if (scan.ssl_valid === false && scan.ssl_expiry_date === null && scan.ssl_days_remaining === null) {
    // Dati legacy: TLS non raggiungibile
    findings.push({ icon: "❌", text: t("osint.findings.ssl_unreachable", { domain: entity.domain }) });
  } else if (scan.ssl_valid === false || (scan.ssl_days_remaining !== null && scan.ssl_days_remaining <= 0)) {
    findings.push({ icon: "❌", text: t("osint.findings.ssl_expired", { date: scan.ssl_expiry_date ?? "N/D" }) + issuerSuffix });
  } else if (scan.ssl_days_remaining !== null && scan.ssl_days_remaining <= 30) {
    findings.push({ icon: "⚠️", text: t("osint.findings.ssl_expiry_soon", { days: scan.ssl_days_remaining }) + issuerSuffix });
  } else if (scan.ssl_valid === true) {
    findings.push({ icon: "✅", text: t("osint.findings.ssl_ok", { days: scan.ssl_days_remaining ?? "?" }) + issuerSuffix });
  }

  // DMARC e SPF — rilevanti solo se il dominio ha un mail server
  const hasMx = scan.mx_present !== false;
  if (hasMx) {
    if (scan.dmarc_present === false) {
      findings.push({ icon: "❌", text: t("osint.findings.dmarc_missing") });
    } else if (scan.dmarc_present === true && scan.dmarc_policy === "none") {
      findings.push({ icon: "⚠️", text: t("osint.findings.dmarc_none") });
    } else if (scan.dmarc_present === true) {
      findings.push({ icon: "✅", text: t("osint.findings.dmarc_ok", { policy: scan.dmarc_policy }) });
    }

    if (scan.spf_present === false) {
      findings.push({ icon: "❌", text: t("osint.findings.spf_missing") });
    } else if (scan.spf_present === true && scan.spf_policy === "+all") {
      findings.push({ icon: "⚠️", text: t("osint.findings.spf_plus_all") });
    } else if (scan.spf_present === true) {
      findings.push({ icon: "✅", text: t("osint.findings.spf_ok") });
    }

    // DKIM — sondaggio dei selettori comuni (assenza = WARNING, non prova assoluta)
    if (scan.dkim_present === false) {
      findings.push({ icon: "⚠️", text: t("osint.findings.dkim_missing") });
    } else if (scan.dkim_present === true) {
      findings.push({ icon: "✅", text: t("osint.findings.dkim_ok", { selectors: (scan.dkim_selectors_found || []).join(", ") || "?" }) });
    }

    // MTA-STS — irrobustimento del trasporto TLS (assenza = INFO)
    if (scan.mta_sts_present === false) {
      findings.push({ icon: "ℹ️", text: t("osint.findings.mta_sts_missing") });
    } else if (scan.mta_sts_present === true) {
      findings.push({ icon: "✅", text: t("osint.findings.mta_sts_ok") });
    }
  }

  // DNSSEC — solo se il dominio ha una presenza rilevabile (web o mail).
  // Per domini NXDOMAIN/senza DNS, dnssec_enabled===false è un artefatto, non un gap.
  const domainHasPresence = scan.ssl_valid !== null || scan.mx_present === true || scan.spf_present === true || scan.dmarc_present === true;
  if (scan.dnssec_enabled === true) {
    findings.push({ icon: "✅", text: t("osint.findings.dnssec_ok") });
  } else if (scan.dnssec_enabled === false && domainHasPresence) {
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

  // abuse.ch ThreatFox / URLhaus
  if (scan.threatfox_iocs && scan.threatfox_iocs > 0) {
    findings.push({ icon: "🛑", text: t("osint.findings.threatfox_listed", { count: scan.threatfox_iocs, malware: (scan.threatfox_malware || []).join(", ") || "N/D" }) });
  }
  if (scan.urlhaus_urls && scan.urlhaus_urls > 0) {
    findings.push({ icon: "🛑", text: t("osint.findings.urlhaus_listed", { count: scan.urlhaus_urls }) });
  }

  // HIBP
  if (scan.hibp_breaches && scan.hibp_breaches > 0) {
    findings.push({ icon: "🔓", text: t("osint.findings.breach", { count: scan.hibp_breaches }) });
  }

  // Certificate Transparency monitoring
  if ((scan.ct_unexpected_issuers || []).length > 0) {
    findings.push({ icon: "🛑", text: t("osint.findings.ct_unexpected_issuer", { issuers: (scan.ct_unexpected_issuers || []).join(", ") }) });
  } else if ((scan.ct_recent_certs || []).length > 0) {
    findings.push({ icon: "📜", text: t("osint.findings.ct_recent_certs", { count: (scan.ct_recent_certs || []).length }) });
  }

  // Enricher errors
  const errorNames = Object.keys(scan.enricher_errors || {});
  if (errorNames.length > 0) {
    findings.push({ icon: "⚪", text: t("osint.findings.enricher_error", { names: errorNames.join(", ") }) });
  }

  const passed = findings.filter(f => f.icon === "✅");
  if (passed.length === 0) {
    return <p className="text-sm text-gray-400">{t("osint.drawer.no_passed")}</p>;
  }

  return (
    <div className="space-y-0.5">
      {passed.map((f, i) => <FindingRow key={i} icon={f.icon} text={f.text} />)}
    </div>
  );
}

function TechDataRow({ label, value, tooltip }: { label: string; value: React.ReactNode; tooltip?: string }) {
  return (
    <div className="flex justify-between items-center py-1 border-b border-gray-50 text-sm">
      <span className="text-gray-500 shrink-0 mr-3 inline-flex items-center gap-1">
        {label}
        {tooltip && (
          <span
            title={tooltip}
            className="cursor-help text-gray-400 hover:text-gray-600 text-[11px] border border-gray-300 rounded-full w-4 h-4 inline-flex items-center justify-center leading-none"
            aria-label={tooltip}
          >
            ?
          </span>
        )}
      </span>
      <span className="text-gray-800 text-right font-mono text-xs truncate max-w-[55%]">{value}</span>
    </div>
  );
}

function secBool(v: boolean | null | undefined): string {
  if (v === null || v === undefined) return "—";
  return v ? "✅" : "❌";
}

function yesNo(v: boolean | null | undefined): string {
  if (v === null || v === undefined) return "—";
  return v ? "Sì" : "No";
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
          <TechDataRow
            label={t("osint.detail.ssl_issuer")}
            value={scan.ssl_issuer || (scan.ssl_valid ? "(non rilevato)" : "—")}
          />
          <TechDataRow label={t("osint.detail.ssl_wildcard")} value={yesNo(scan.ssl_wildcard)} />

          <p className="text-xs font-semibold text-gray-500 uppercase mb-1 mt-3">WHOIS</p>
          <TechDataRow label={t("osint.detail.domain_expiry")} value={scan.domain_expiry_date ?? "—"} />
          <TechDataRow label={t("osint.detail.domain_registrar")} value={scan.domain_registrar || "—"} />
          <TechDataRow label={t("osint.detail.registrar_country")} value={scan.registrar_country || "—"} />
          <TechDataRow label={t("osint.detail.whois_privacy")} value={yesNo(scan.whois_privacy)} />

          <p className="text-xs font-semibold text-gray-500 uppercase mb-1 mt-3">DNS</p>
          <TechDataRow
            label={t("osint.detail.dnssec")}
            value={secBool(scan.dnssec_enabled)}
            tooltip={t("osint.detail.tooltip.dnssec")}
          />
          <TechDataRow label={t("osint.detail.mx")} value={yesNo(scan.mx_present)} />
          <TechDataRow
            label="SPF"
            value={scan.spf_present === null || scan.spf_present === undefined ? "—" : (scan.spf_present ? (scan.spf_policy || "✅") : "❌")}
            tooltip={t("osint.detail.tooltip.spf")}
          />
          <TechDataRow
            label="DMARC"
            value={scan.dmarc_present === null || scan.dmarc_present === undefined ? "—" : (scan.dmarc_present ? (scan.dmarc_policy || "✅") : "❌")}
            tooltip={t("osint.detail.tooltip.dmarc")}
          />

          <p className="text-xs font-semibold text-gray-500 uppercase mb-1 mt-3">Reputation</p>
          <TechDataRow label="VirusTotal suspicious" value={scan.vt_suspicious ?? "—"} />
          <TechDataRow label={t("osint.detail.abuseipdb")} value={scan.abuseipdb_score !== null ? `${scan.abuseipdb_score} (${scan.abuseipdb_reports ?? 0} rep.)` : "—"} />
          <TechDataRow label={t("osint.detail.otx_pulses")} value={scan.otx_pulses ?? "—"} />
          <TechDataRow label={t("osint.detail.gsb")} value={scan.gsb_status || "—"} />
          <TechDataRow label={t("osint.detail.threatfox")} value={scan.threatfox_iocs === null || scan.threatfox_iocs === undefined ? "—" : (scan.threatfox_iocs > 0 ? `${scan.threatfox_iocs} (${(scan.threatfox_malware || []).join(", ") || "?"})` : "0")} />
          <TechDataRow label={t("osint.detail.urlhaus")} value={scan.urlhaus_urls ?? "—"} />

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
  // In sicurezza (100 − rischio): più alto = meglio, come il voto.
  const reversed = [...data].reverse().map(p => ({ ...p, security: 100 - p.score_total }));
  return (
    <ResponsiveContainer width="100%" height={180}>
      <LineChart data={reversed} margin={{ top: 5, right: 5, bottom: 5, left: -20 }}>
        <ReferenceArea y1={0} y2={30} fill="#fee2e2" fillOpacity={0.5} />
        <ReferenceArea y1={30} y2={50} fill="#fed7aa" fillOpacity={0.5} />
        <ReferenceArea y1={50} y2={70} fill="#fef9c3" fillOpacity={0.5} />
        <ReferenceArea y1={70} y2={100} fill="#dcfce7" fillOpacity={0.5} />
        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
        <XAxis
          dataKey="scan_date"
          tick={{ fontSize: 10 }}
          tickFormatter={v => new Date(v).toLocaleDateString(undefined, { month: "short", day: "numeric" })}
        />
        <YAxis domain={[0, 100]} tick={{ fontSize: 10 }} />
        <Tooltip
          formatter={(v: number) => [v, "/100"]}
          labelFormatter={l => new Date(l).toLocaleDateString()}
        />
        <Line
          type="monotone"
          dataKey="security"
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
  const [isScanning, setIsScanning] = useState(false);
  const pollingRef = useRef<{ initialScanDate: string | null; attempts: number } | null>(null);

  const { data: entity, isLoading } = useQuery({
    queryKey: ["osint-entity", entityId],
    queryFn: () => osintApi.entity(entityId),
    refetchInterval: isScanning ? 4000 : false,
  });

  // Quando arriva un nuovo scan_date diverso da quello iniziale → fine polling.
  if (isScanning && pollingRef.current && entity?.last_scan?.scan_date) {
    const currentDate = entity.last_scan.scan_date;
    const initial = pollingRef.current.initialScanDate;
    pollingRef.current.attempts += 1;
    const elapsedAttempts = pollingRef.current.attempts;
    if (currentDate !== initial || elapsedAttempts > 30 /* ~2min */) {
      pollingRef.current = null;
      setIsScanning(false);
    }
  }

  const { data: history = [] } = useQuery({
    queryKey: ["osint-entity-history", entityId],
    queryFn: () => osintApi.entityHistory(entityId),
  });

  const qc = useQueryClient();

  // Postura attesa: senza dichiararla, ogni assenza (DMARC, HTTPS) resta
  // ambigua e il modulo la segnala per prudenza.
  const postureMutation = useMutation({
    mutationFn: (data: { expected_mail?: ExpectedPosture; expected_web?: ExpectedPosture }) =>
      osintApi.setPosture(entityId, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["osint-entity", entityId] });
      qc.invalidateQueries({ queryKey: ["osint-entities"] });
    },
  });

  const scanMutation = useMutation({
    mutationFn: () => osintApi.forceScan(entityId),
    onSuccess: () => {
      pollingRef.current = {
        initialScanDate: entity?.last_scan?.scan_date ?? null,
        attempts: 0,
      };
      setIsScanning(true);
    },
  });

  const [tab, setTab] = useState<DrawerTab>("overview");
  const [reporting, setReporting] = useState<OsintFinding | null>(null);

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
  const isSupplier = entity.entity_type === "supplier";
  const findings = entity.findings ?? [];
  const openFindings = findings.filter(f => OPEN.includes(f.status));
  const tabs: DrawerTab[] = ["overview", "problems", "passed", "tech", "events", "settings"];

  return (
    <div className="fixed inset-0 z-50 flex" onClick={onClose}>
      <div className="ml-auto w-full max-w-2xl bg-white h-full shadow-2xl flex flex-col" onClick={e => e.stopPropagation()}
        role="dialog" aria-modal="true" aria-label={entity.display_name}>
        <header className="px-6 pt-5 pb-3 border-b border-gray-100">
          <div className="flex items-start gap-4">
            <GradeBadge grade={entity.grade} security={entity.security} size="lg" />
            <div className="flex-1 min-w-0">
              <h2 className="font-semibold text-gray-900 text-lg truncate">{entity.display_name}</h2>
              <p className="text-sm text-gray-500 truncate">{entity.domain} · {t(`osint.entity_type.${entity.entity_type}`)}</p>
              {isSupplier && <p className="text-xs text-gray-500 mt-1">{t("osint.drawer.supplier_mode")}</p>}
            </div>
            <button onClick={() => scanMutation.mutate()} disabled={scanMutation.isPending || isScanning}
              className="px-3 py-1.5 text-sm border rounded-lg hover:bg-gray-50 disabled:opacity-50">
              {(scanMutation.isPending || isScanning) ? "⏳" : "🔄"} {t("osint.detail.force_scan")}
            </button>
            <button onClick={onClose} aria-label={t("osint.drawer.close")} className="text-gray-400 hover:text-gray-700 text-2xl leading-none">×</button>
          </div>
          <nav className="flex gap-1 mt-4 -mb-3 overflow-x-auto">
            {tabs.map(k => (
              <button key={k} onClick={() => setTab(k)}
                className={`px-3 py-2 text-sm whitespace-nowrap border-b-2 ${tab === k ? "border-primary-600 text-primary-700 font-medium" : "border-transparent text-gray-500 hover:text-gray-700"}`}>
                {t(`osint.drawer.tabs.${k}`)}
                {k === "problems" && openFindings.length > 0 && <span className="ml-1 text-xs text-gray-400">{openFindings.length}</span>}
              </button>
            ))}
          </nav>
        </header>

        <div className="flex-1 overflow-y-auto px-6 py-5 space-y-5">
          {tab === "overview" && (
            <>
              {scan ? (
                <>
                  <div className="grid grid-cols-4 gap-3">
                    <ScorePill label="SSL" score={scan.score_ssl} />
                    <ScorePill label="DNS" score={scan.score_dns} />
                    <ScorePill label={t("osint.detail.reputation")} score={scan.score_reputation} />
                    <ScorePill label="GRC" score={scan.score_grc_context} />
                  </div>
                  <p className="text-xs text-gray-400">
                    {t("osint.detail.last_scan")}: {new Date(scan.scan_date).toLocaleDateString()} · {t("osint.drawer.dim_hint")}
                  </p>
                </>
              ) : <p className="text-sm text-gray-400">{t("osint.detail.no_scan")}</p>}
              {history.length > 0 && (
                <div>
                  <h3 className="text-sm font-semibold text-gray-700 mb-2">{t("osint.detail.history")}</h3>
                  <HistoryChart data={history} />
                </div>
              )}
              {openFindings.length > 0 && (
                <button onClick={() => setTab("problems")} className="w-full text-left rounded-xl border border-gray-200 px-4 py-3 hover:bg-gray-50">
                  <p className="text-sm font-medium text-gray-900">
                    {isSupplier ? t("osint.drawer.open_supplier", { count: openFindings.filter(f => f.severity === "critical").length })
                      : t("osint.drawer.open_own", { count: openFindings.length })} →
                  </p>
                </button>
              )}
            </>
          )}

          {tab === "problems" && (isSupplier
            ? <SupplierProblems findings={findings} onReport={setReporting} />
            : <OwnProblems findings={findings} />)}

          {tab === "passed" && <ScanFindings entity={entity} />}

          {tab === "tech" && (scan ? <ScanTechData scan={scan} /> : <p className="text-sm text-gray-400">{t("osint.detail.no_scan")}</p>)}

          {tab === "events" && <EventsList events={entity.events ?? entity.active_alerts} />}

          {tab === "settings" && (
            <div className="border border-gray-200 rounded-xl p-4">
              <h3 className="text-sm font-semibold text-gray-700 mb-1">{t("osint.posture.title")}</h3>
              <p className="text-xs text-gray-500 mb-3">{t("osint.posture.hint")}</p>
              <div className="grid grid-cols-2 gap-3">
                {(["expected_mail", "expected_web"] as const).map((field) => (
                  <label key={field} className="text-xs text-gray-600">
                    {t(`osint.posture.${field}`)}
                    <select value={entity[field] ?? "unknown"} disabled={postureMutation.isPending}
                      onChange={(e) => postureMutation.mutate({ [field]: e.target.value as ExpectedPosture })}
                      className="block w-full border rounded-lg px-2 py-1.5 text-sm mt-0.5">
                      {EXPECTED_POSTURES.map((v) => <option key={v} value={v}>{t(`osint.posture.values.${v}`)}</option>)}
                    </select>
                  </label>
                ))}
              </div>
              {entity.duplicate_candidate_of && (
                <p className="text-xs text-amber-700 mt-3">
                  {entity.duplicate_verified === true ? t("osint.posture.duplicate_confirmed")
                    : entity.duplicate_verified === false ? t("osint.posture.duplicate_distinct") : t("osint.posture.duplicate_candidate")}
                </p>
              )}
            </div>
          )}
        </div>
      </div>
      {reporting && <ReportToSupplierDialog finding={reporting} onClose={() => setReporting(null)} />}
    </div>
  );
}

type DrawerTab = "overview" | "problems" | "passed" | "tech" | "events" | "settings";
const OPEN: string[] = ["open", "acknowledged", "in_progress", "reported"];
const SEV_ICON: Record<string, string> = { critical: "🔴", warning: "🟠", info: "ℹ️" };

/** Problemi propri: da correggere (playbook completo e task in Risoluzione). */
function OwnProblems({ findings }: { findings: OsintFinding[] }) {
  const { t } = useTranslation();
  const open = findings.filter(f => OPEN.includes(f.status));
  const closed = findings.filter(f => !OPEN.includes(f.status));
  if (findings.length === 0) return <p className="text-sm text-gray-400">✓ {t("osint.drawer.no_problems")}</p>;
  return (
    <div className="space-y-3">
      {open.map(f => (
        <div key={f.id} className="rounded-xl border border-gray-200 p-3">
          <p className="text-sm font-medium text-gray-900">{SEV_ICON[f.severity]} {findingTitle(t, f)}</p>
          {f.playbook?.what && <p className="text-xs text-gray-600 mt-1">{f.playbook.what}</p>}
          <p className="text-xs text-gray-400 mt-1">
            {t(`osint.remediation.status.${f.status}`, { defaultValue: f.status })} · {t("osint.remediation.first_seen")}: {new Date(f.first_seen).toLocaleDateString()}
            {f.linked_task_id && <> · <Link to="/tasks" className="text-primary-700 hover:underline">{t("osint.drawer.open_task")}</Link></>}
          </p>
        </div>
      ))}
      {open.length > 0 && (
        <Link to="/osint/remediation" className="inline-block text-sm text-primary-700 hover:underline">{t("osint.drawer.go_fix")} →</Link>
      )}
      {closed.length > 0 && (
        <details className="text-sm">
          <summary className="cursor-pointer text-gray-500">{t("osint.drawer.closed_recent", { count: closed.length })}</summary>
          <ul className="mt-2 space-y-1">
            {closed.map(f => (
              <li key={f.id} className="text-xs text-gray-500">✓ {findingTitle(t, f)} · {t(`osint.remediation.status.${f.status}`, { defaultValue: f.status })}</li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}

/** Problemi del fornitore: non da correggere. I critici si segnalano,
 *  il resto è solo informativo. */
function SupplierProblems({ findings, onReport }: { findings: OsintFinding[]; onReport: (f: OsintFinding) => void }) {
  const { t } = useTranslation();
  const critical = findings.filter(f => f.severity === "critical" && OPEN.includes(f.status));
  const minor = findings.filter(f => f.severity !== "critical" && OPEN.includes(f.status));
  const history = findings.filter(f => f.reported_at && !OPEN.includes(f.status));
  return (
    <div className="space-y-4">
      <p className="text-xs text-gray-500">{t("osint.drawer.supplier_intro")}</p>
      {critical.length === 0 && <p className="text-sm text-gray-400">✓ {t("osint.drawer.no_critical")}</p>}
      {critical.map(f => (
        <div key={f.id} className="rounded-xl border border-red-100 bg-red-50/40 p-3">
          <div className="flex items-start gap-3">
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-gray-900">🔴 {findingTitle(t, f)}</p>
              <p className="text-xs text-gray-500 mt-0.5">
                {f.status === "reported" && f.reported_at
                  ? t("osint.drawer.reported_on", { date: new Date(f.reported_at).toLocaleDateString(), who: f.reported_by_name ?? "—" })
                  : t("osint.drawer.not_reported", { date: new Date(f.first_seen).toLocaleDateString() })}
                {f.report_overdue && <span className="ml-1 text-amber-700 font-medium">· {t("osint.drawer.still_open")}</span>}
              </p>
              {f.report_note && <p className="text-xs text-gray-600 mt-1 italic" title={f.report_note}>“{f.report_note}”</p>}
            </div>
            <button onClick={() => onReport(f)}
              className={`shrink-0 px-3 py-1.5 text-xs rounded-lg ${f.status === "reported" && !f.report_overdue ? "border border-gray-300 text-gray-700" : "bg-gray-900 text-white"}`}>
              {f.status === "reported" ? t("osint.dash.remind") : t("osint.dash.report_btn")}
            </button>
          </div>
        </div>
      ))}
      {minor.length > 0 && (
        <details className="text-sm">
          <summary className="cursor-pointer text-gray-500">{t("osint.drawer.minor_info", { count: minor.length })}</summary>
          <ul className="mt-2 space-y-1">
            {minor.map(f => <li key={f.id} className="text-xs text-gray-600">{SEV_ICON[f.severity]} {findingTitle(t, f)}</li>)}
          </ul>
        </details>
      )}
      {history.length > 0 && (
        <div>
          <p className="text-xs font-medium text-gray-600 mb-1">{t("osint.drawer.report_history")}</p>
          <ul className="space-y-1">
            {history.map(f => (
              <li key={f.id} className="text-xs text-gray-600">
                ✓ {findingTitle(t, f)} · {t("osint.drawer.reported_resolved", {
                  reported: new Date(f.reported_at!).toLocaleDateString(),
                  resolved: f.resolved_at ? new Date(f.resolved_at).toLocaleDateString() : "—",
                })}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

/** Cronologia degli alert: quando è emerso cosa e cosa ha generato. */
function EventsList({ events }: { events: OsintAlert[] }) {
  const { t } = useTranslation();
  if (events.length === 0) return <p className="text-sm text-gray-400">{t("osint.drawer.no_events")}</p>;
  return (
    <ol className="relative border-l border-gray-200 ml-2 space-y-3">
      {events.map(a => (
        <li key={a.id} className="ml-4">
          <span className="absolute -left-1.5 mt-1.5 w-3 h-3 rounded-full border-2 border-white bg-gray-300" />
          <p className="text-xs text-gray-400">{new Date(a.created_at).toLocaleString()}</p>
          <p className="text-sm text-gray-800">{SEV_ICON[a.severity]} {a.description}</p>
          <p className="text-xs space-x-2">
            {a.linked_incident_id && <Link to={`/incidents?incident=${a.linked_incident_id}`} className="text-primary-700 hover:underline">{t("osint.detail.linked_incident")} →</Link>}
            {a.linked_task_id && <Link to="/tasks" className="text-primary-700 hover:underline">{t("osint.detail.linked_task")} →</Link>}
            {a.status === "pending_escalation" && <span className="text-amber-700">{t("osint.drawer.pending_escalation")}</span>}
          </p>
        </li>
      ))}
    </ol>
  );
}
