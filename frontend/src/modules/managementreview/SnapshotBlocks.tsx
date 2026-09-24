import { useTranslation } from "react-i18next";
import { StatusBadge } from "../../components/ui/StatusBadge";
import i18n from "../../i18n";
import {
  DetailTable, KpiBox, KpiGrid, SnapSection, fmtDate, isOverdue,
  type Snap, type SnapAudit, type SnapDoc, type SnapFinding, type SnapFramework, type SnapIncident,
  type SnapKpi, type SnapObjective, type SnapPdca, type SnapPendingDoc, type SnapPrevAction, type SnapRisk,
  type SnapSite, type SnapTask,
} from "./shared";

// Ogni blocco mostra i dati congelati di un'area; se lo snapshot non contiene
// ancora quell'area (snapshot generati prima dell'estensione) non rende nulla.

export function PreviousActionsBlock({ snap }: { snap: Snap }) {
  const { t } = useTranslation();
  const prev = snap.azioni_precedenti;
  if (!prev) return null;
  if (!prev.riesame_precedente) {
    return <p className="text-xs text-gray-500 italic">{t("management_review.snap.first_review")}</p>;
  }
  return (
    <div>
      <p className="text-xs text-gray-500 mb-2">
        {t("management_review.snap.previous_review", { title: prev.riesame_precedente.title, date: fmtDate(prev.riesame_precedente.review_date) })}
      </p>
      <KpiGrid>
        <KpiBox label={t("management_review.snap.prev_total")} value={prev.totale ?? 0} />
        <KpiBox label={t("management_review.snap.prev_closed")} value={prev.chiuse ?? 0} color="text-green-600" />
        <KpiBox label={t("management_review.snap.prev_open")} value={prev.aperte ?? 0} color="text-orange-600" />
        <KpiBox label={t("management_review.snap.prev_overdue")} value={prev.scadute ?? 0} color="text-red-600" />
      </KpiGrid>
      <DetailTable
        headers={[
          t("management_review.snap.col_action"), t("management_review.snap.col_owner"),
          t("management_review.snap.col_due"), t("management_review.snap.col_status"), t("management_review.snap.col_review"),
        ]}
        rows={((prev.elenco ?? []) as SnapPrevAction[]).map(a => [
          <span className="whitespace-pre-line">{a.description}</span>,
          a.owner || "—",
          <span className={a.overdue ? "text-red-600 font-medium" : ""}>{fmtDate(a.due_date)}</span>,
          a.status === "chiuso"
            ? <span className="text-green-700">{t("management_review.actions.closed")}</span>
            : <span className={a.overdue ? "text-red-600 font-medium" : "text-orange-600"}>
                {a.overdue ? t("management_review.actions.overdue") : t("management_review.actions.open")}
              </span>,
          <span className="text-gray-500">{a.review_title} · {fmtDate(a.review_date)}</span>,
        ])}
        total={prev.totale}
      />
    </div>
  );
}

export function ComplianceBlock({ snap }: { snap: Snap }) {
  const { t } = useTranslation();
  const frameworks = snap.frameworks as Record<string, SnapFramework> | undefined;
  if (!frameworks || Object.keys(frameworks).length === 0) return null;
  const lang = i18n.language || "it";
  return (
    <div className="space-y-2">
      {Object.entries(frameworks).map(([code, fw]) => {
        const color = fw.pct_compliant >= 80 ? "bg-green-500" : fw.pct_compliant >= 60 ? "bg-yellow-400" : "bg-red-500";
        return (
          <div key={code}>
            <div className="flex justify-between text-xs mb-0.5 gap-2">
              <span className="font-medium text-gray-700">{code} — {fw.framework_name}</span>
              <span className="font-semibold shrink-0">{fw.pct_compliant}% ({fw.by_status?.compliant ?? 0}/{fw.total})</span>
            </div>
            <div className="h-2 bg-gray-200 rounded overflow-hidden">
              <div className={`h-full ${color}`} style={{ width: `${fw.pct_compliant}%` }} />
            </div>
            {fw.expired_evidence_count > 0 && (
              <p className="text-xs text-amber-600 mt-0.5">{t("management_review.snap.expired_evidence", { count: fw.expired_evidence_count })}</p>
            )}
            {fw.gap_controls && fw.gap_controls.length > 0 && (
              <div className="mt-1 pl-2 border-l-2 border-red-200">
                <p className="text-xs text-gray-500">{t("management_review.snap.gap_controls")}</p>
                {fw.gap_controls.slice(0, 5).map(g => (
                  <p key={g.id} className="text-xs text-gray-700 truncate">
                    <span className="font-medium">{g.control__external_id}</span>{" "}
                    {g.titles?.[lang] || g.titles?.it || g.titles?.en || ""}
                  </p>
                ))}
                {(fw.by_status?.gap ?? 0) > 5 && (
                  <p className="text-xs text-gray-400">{t("management_review.snap.more", { count: (fw.by_status?.gap ?? 0) - 5 })}</p>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

export function KpiBlock({ snap }: { snap: Snap }) {
  const { t } = useTranslation();
  const k = snap.kpi;
  if (!k) return null;
  const counts = k.status_counts ?? {};
  return (
    <div>
      <KpiGrid>
        <KpiBox label={t("management_review.snap.kpi_total")} value={k.totale ?? 0} />
        <KpiBox label={t("management_review.snap.kpi_critical")} value={counts.critical ?? 0} color="text-red-600" />
        <KpiBox label={t("management_review.snap.kpi_warning")} value={counts.warning ?? 0} color="text-orange-600" />
        <KpiBox label={t("management_review.snap.kpi_no_data")} value={counts.no_data ?? 0} color="text-gray-500" />
      </KpiGrid>
      <DetailTable
        title={t("management_review.snap.kpi_attention_list")}
        headers={[
          t("management_review.snap.col_kpi"), t("management_review.snap.col_value"),
          t("management_review.snap.col_status"), t("management_review.snap.col_thresholds"),
        ]}
        rows={((k.elenco_attenzione ?? []) as SnapKpi[]).map(i => [
          <span>{i.name}{i.plant_code && <span className="text-gray-400"> · {i.plant_code}</span>}</span>,
          `${i.value ?? "—"} ${i.unit ?? ""}`.trim(),
          <span className={i.status === "critical" ? "text-red-600 font-medium" : "text-orange-600"}>
            {t(`management_review.snap.kpi_status_${i.status}`)}
          </span>,
          `${i.threshold_warning ?? "—"} / ${i.threshold_critical ?? "—"}`,
        ])}
        total={k.attenzione}
      />
    </div>
  );
}

export function ObjectivesBlock({ snap }: { snap: Snap }) {
  const { t } = useTranslation();
  const o = snap.obiettivi;
  if (!o) return null;
  const tone: Record<string, string> = {
    mancato: "text-red-600 font-medium",
    a_rischio: "text-orange-600 font-medium",
    in_linea: "text-green-600",
    senza_misure: "text-gray-400",
  };
  return (
    <div>
      <KpiGrid>
        <KpiBox label={t("objectives.counters.active")} value={o.attivi ?? 0} />
        <KpiBox label={t("objectives.counters.missed")} value={o.mancati ?? 0} color="text-red-600" />
        <KpiBox label={t("objectives.counters.at_risk")} value={o.a_rischio ?? 0} color="text-orange-600" />
        <KpiBox label={t("objectives.counters.achieved")} value={o.raggiunti ?? 0} color="text-green-600" />
      </KpiGrid>
      <DetailTable
        title={t("management_review.snap.objectives_list")}
        headers={[
          t("objectives.fields.objective"), t("objectives.baseline_to_target"),
          t("objectives.current_value"), t("objectives.progress"),
          t("objectives.fields.target_date"), t("objectives.fields.track"),
        ]}
        rows={((o.elenco ?? []) as SnapObjective[]).map(i => [
          <span>{i.title}<span className="text-gray-400"> · {i.code}{i.plant_code ? ` · ${i.plant_code}` : ""}</span></span>,
          `${i.baseline_value ?? "—"} → ${i.target_value} ${i.unit ?? ""}`.trim(),
          `${i.current_value ?? "—"} ${i.unit ?? ""}`.trim(),
          i.progress_pct === null ? "—" : `${i.progress_pct}%`,
          fmtDate(i.target_date),
          <span className={tone[i.track] ?? ""}>{t(`objectives.track.${i.track}`)}</span>,
        ])}
        total={o.totale}
      />
    </div>
  );
}

export function AuditBlock({ snap }: { snap: Snap }) {
  const { t } = useTranslation();
  const a = snap.audit;
  if (!a) return null;
  return (
    <div>
      <KpiGrid>
        <KpiBox label={t("management_review.snap.audit_12m")} value={a.audit_12m ?? 0} />
        <KpiBox label={t("management_review.snap.nc_major")} value={a.nc_aperte_maggiori ?? 0} color="text-red-600" />
        <KpiBox label={t("management_review.snap.nc_minor")} value={a.nc_aperte_minori ?? 0} color="text-orange-600" />
        <KpiBox label={t("management_review.snap.findings_overdue")} value={a.finding_scaduti ?? 0} color="text-red-600" />
      </KpiGrid>
      <DetailTable
        title={t("management_review.snap.audits_list")}
        headers={[
          t("management_review.snap.col_audit"), t("management_review.snap.col_date"),
          t("management_review.snap.col_framework"), t("management_review.snap.col_readiness"), t("management_review.snap.col_findings"),
        ]}
        rows={((a.elenco_audit ?? []) as SnapAudit[]).map(x => [
          <span>
            {x.title}{x.plant_code && <span className="text-gray-400"> · {x.plant_code}</span>}
            {x.audit_type && x.audit_type !== "interno" && (
              <span className="ml-1 text-xs text-indigo-700">
                ({t(`audit_prep.audit_type.${x.audit_type}`)}{x.requesting_party ? ` — ${x.requesting_party}` : ""})
              </span>
            )}
          </span>,
          fmtDate(x.audit_date), x.framework ?? "—",
          x.readiness_score != null ? `${x.readiness_score}%` : "—", x.findings,
        ])}
        total={a.audit_12m}
      />
      <DetailTable
        title={t("management_review.snap.nc_open_list")}
        headers={[
          t("management_review.snap.col_finding"), t("management_review.snap.col_type"),
          t("management_review.snap.col_audit"), t("management_review.snap.col_response_due"),
        ]}
        rows={((a.elenco_nc_aperte ?? []) as SnapFinding[]).map(f => [
          f.title,
          <span className={f.finding_type === "major_nc" ? "text-red-600 font-medium" : "text-orange-600"}>
            {t(`management_review.snap.finding_${f.finding_type}`)}
          </span>,
          f.audit,
          <span className={f.overdue ? "text-red-600 font-medium" : ""}>{fmtDate(f.response_deadline)}</span>,
        ])}
        total={(a.nc_aperte_maggiori ?? 0) + (a.nc_aperte_minori ?? 0)}
      />
    </div>
  );
}

export function IncidentsBlock({ snap }: { snap: Snap }) {
  const { t } = useTranslation();
  const inc = snap.incidenti;
  if (!inc) return null;
  return (
    <div>
      <KpiGrid>
        <KpiBox label={t("management_review.snap.total")} value={inc.totale_12m ?? 0} />
        <KpiBox label={t("management_review.snap.nis2")} value={inc.nis2_notificati ?? 0} color="text-red-600" />
        <KpiBox label={t("management_review.snap.open")} value={inc.aperti ?? 0} color="text-orange-600" />
        <KpiBox label={t("management_review.snap.closed_no_rca")} value={inc.senza_rca ?? 0} color="text-amber-600" />
      </KpiGrid>
      {(["elenco_aperti", "elenco_nis2"] as const).map(key => (
        <DetailTable
          key={key}
          title={t(key === "elenco_aperti" ? "management_review.snap.incidents_open_list" : "management_review.snap.incidents_nis2_list")}
          headers={[
            t("management_review.snap.col_incident"), t("management_review.snap.col_detected"),
            t("management_review.snap.col_severity"), t("management_review.snap.col_status"),
          ]}
          rows={((inc[key] ?? []) as SnapIncident[]).map(i => [
            <span className="font-medium">{i.title}</span>, fmtDate(i.detected_at),
            <StatusBadge status={i.severity} />, <StatusBadge status={i.status} />,
          ])}
          total={key === "elenco_aperti" ? inc.aperti : inc.nis2_notificati}
        />
      ))}
    </div>
  );
}

export function PdcaTasksBlock({ snap }: { snap: Snap }) {
  const { t } = useTranslation();
  const pdca = snap.pdca;
  const task = snap.task;
  if (!pdca) return null;
  return (
    <div>
      <KpiGrid>
        <KpiBox label={t("management_review.snap.pdca_open")} value={pdca.aperti ?? 0} />
        <KpiBox label={t("management_review.snap.blocked_90")} value={pdca.bloccati_plan_90gg ?? 0} color="text-red-600" />
        <KpiBox label={t("management_review.snap.closed_12m")} value={pdca.chiusi_12m ?? 0} color="text-green-600" />
        <KpiBox label={t("management_review.snap.tasks_overdue")} value={task?.scaduti ?? 0} color="text-red-600" />
      </KpiGrid>
      <DetailTable
        title={t("management_review.snap.pdca_blocked_list")}
        headers={[t("management_review.snap.col_cycle"), t("management_review.snap.col_opened")]}
        rows={((pdca.elenco_bloccati ?? []) as SnapPdca[]).map(c => [c.title, fmtDate(c.created_at)])}
        total={pdca.bloccati_plan_90gg}
      />
      <DetailTable
        title={t("management_review.snap.tasks_overdue_list")}
        headers={[
          t("management_review.snap.col_task"), t("management_review.snap.col_priority"),
          t("management_review.snap.col_due"), t("management_review.snap.col_role"),
        ]}
        rows={((task?.elenco_scaduti ?? []) as SnapTask[]).map(tk => [
          tk.title, <StatusBadge status={tk.priority} />,
          <span className="text-red-600">{fmtDate(tk.due_date)}</span>,
          tk.assigned_role ? t(`governance.roles.${tk.assigned_role}`, tk.assigned_role) : "—",
        ])}
        total={task?.scaduti}
      />
    </div>
  );
}

// Stati del workflow documentale: le etichette esistono già nel modulo Documenti.
const DOC_STATUS_KEY: Record<string, string> = {
  bozza: "documents.filters.draft",
  revisione: "documents.filters.in_review",
  approvazione: "documents.filters.in_approval",
};

export function DocumentsBlock({ snap, approvedHere }: { snap: Snap; approvedHere?: Set<string> }) {
  const { t } = useTranslation();
  const d = snap.documenti;
  if (!d) return null;
  const headers = [t("management_review.snap.col_document"), t("management_review.snap.col_owner"), t("management_review.snap.col_review_due")];
  return (
    <div>
      <KpiGrid>
        <KpiBox label={t("management_review.snap.approved")} value={d.approvati ?? 0} />
        <KpiBox label={t("management_review.snap.expiring_90")} value={d.in_scadenza ?? 0} color="text-yellow-600" />
        <KpiBox label={t("management_review.snap.expired")} value={d.scaduti ?? 0} color="text-red-600" />
        <KpiBox label={t("management_review.snap.expired_evidence_kpi")} value={d.evidenze_scadute ?? 0} color="text-red-600" />
      </KpiGrid>
      <DetailTable
        title={t("management_review.snap.docs_pending")}
        headers={[
          t("management_review.snap.col_document"), t("documents.fields.document_type"),
          t("documents.table.status"), t("management_review.snap.col_version"),
          t("management_review.snap.col_created"),
        ]}
        rows={((d.elenco_non_approvati ?? []) as SnapPendingDoc[]).map(x => [
          <span className="font-medium">{x.document_code ? `[${x.document_code}] ` : ""}{x.title}</span>,
          t(`documents.type.${x.document_type}`, { defaultValue: x.document_type }),
          approvedHere?.has(x.id)
            ? <span className="text-green-700 font-medium">{t("management_review.deliberated.approved_here")}</span>
            : <span className="text-yellow-700">{DOC_STATUS_KEY[x.status] ? t(DOC_STATUS_KEY[x.status]) : x.status}</span>,
          x.version || "—", fmtDate(x.created_at),
        ])}
        total={d.non_approvati_obbligatori}
        empty={t("management_review.snap.docs_pending_empty")}
      />
      <DetailTable
        title={t("management_review.snap.docs_expired")}
        headers={headers}
        rows={((d.elenco_scaduti ?? []) as SnapDoc[]).map(x => [
          <span className="font-medium">{x.title}</span>, x.owner || "—",
          <span className="text-red-600">{fmtDate(x.review_due_date)}</span>,
        ])}
        total={d.scaduti}
      />
      <DetailTable
        title={t("management_review.snap.docs_expiring")}
        headers={headers}
        rows={((d.elenco_in_scadenza ?? []) as SnapDoc[]).map(x => [x.title, x.owner || "—", fmtDate(x.review_due_date)])}
        total={d.in_scadenza}
      />
      <DetailTable
        title={t("management_review.snap.docs_approved_since", { date: fmtDate(d.approvati_dal) })}
        headers={[t("management_review.snap.col_document"), t("management_review.snap.col_owner"), t("management_review.snap.col_approved_at")]}
        rows={((d.elenco_approvati_periodo ?? []) as SnapDoc[]).map(x => [x.title, x.owner || "—", fmtDate(x.approved_at)])}
        total={d.approvati_periodo}
      />
    </div>
  );
}

export function RisksBlock({ snap }: { snap: Snap }) {
  const { t } = useTranslation();
  const r = snap.rischi;
  const bcp = snap.bcp as { processi_critici_senza_bcp: number; nomi: string[] } | undefined;
  if (!r) return null;
  const yesNo = (v: boolean) => v
    ? <span className="text-green-700">{t("management_review.snap.yes")}</span>
    : <span className="text-red-600 font-medium">{t("management_review.snap.no")}</span>;
  return (
    <div>
      <KpiGrid>
        <KpiBox label={t("management_review.snap.critical")} value={r.rosso ?? 0} color="text-red-600" />
        <KpiBox label={t("management_review.snap.medium")} value={r.giallo ?? 0} color="text-yellow-600" />
        <KpiBox label={t("management_review.snap.low")} value={r.verde ?? 0} color="text-green-600" />
        <KpiBox label={t("management_review.snap.critical_no_plan")} value={r.senza_piano ?? 0} color="text-red-600" />
      </KpiGrid>
      {(r.senza_owner ?? 0) > 0 && (
        <p className="text-xs text-amber-600 mt-2">{t("management_review.snap.risks_no_owner", { count: r.senza_owner })}</p>
      )}
      <DetailTable
        title={t("management_review.snap.top_critical")}
        headers={[
          t("management_review.snap.col_risk"), t("management_review.snap.col_asset_process"),
          t("management_review.snap.col_score"), t("management_review.snap.col_treatment"),
          t("management_review.snap.col_owner"), t("management_review.snap.col_plan"),
        ]}
        rows={((r.top_critici ?? []) as SnapRisk[]).map(x => [
          <span className="font-medium">{x.name}</span>,
          x.asset || x.process || "—",
          <span>{x.inherent_score ?? "—"} → <span className="text-red-600 font-semibold">{x.score ?? "—"}</span></span>,
          x.treatment ? t(`risk.treatment_${x.treatment}`, x.treatment) : "—",
          x.owner || <span className="text-amber-600">—</span>,
          yesNo(x.has_plan),
        ])}
        total={r.rosso}
      />
      <DetailTable
        title={t("management_review.snap.accepted_risks")}
        headers={[
          t("management_review.snap.col_risk"), t("management_review.snap.col_score"),
          t("management_review.snap.col_accepted_by"), t("management_review.snap.col_acceptance_expiry"),
        ]}
        rows={((r.elenco_accettati ?? []) as SnapRisk[]).map(x => [
          x.name, x.score ?? "—", x.accepted_by || "—",
          <span className={isOverdue(x.acceptance_expiry) ? "text-red-600 font-medium" : ""}>{fmtDate(x.acceptance_expiry)}</span>,
        ])}
        total={r.accettati_formalmente}
      />
      {bcp && bcp.processi_critici_senza_bcp > 0 && (
        <div className="mt-3">
          <p className="text-xs text-red-600 font-medium">{t("management_review.snap.critical_no_bcp", { count: bcp.processi_critici_senza_bcp })}</p>
          {bcp.nomi.length > 0 && <p className="text-xs text-gray-600 mt-1">{bcp.nomi.join(", ")}</p>}
        </div>
      )}
    </div>
  );
}

export function OpportunitiesBlock({ snap }: { snap: Snap }) {
  const { t } = useTranslation();
  const a = snap.audit;
  const items = (a?.elenco_opportunita ?? []) as SnapFinding[];
  if (items.length === 0) return null;
  return (
    <DetailTable
      title={t("management_review.snap.opportunities_list")}
      headers={[t("management_review.snap.col_finding"), t("management_review.snap.col_audit")]}
      rows={items.map(f => [f.title, f.audit])}
      total={a.opportunita_aperte}
    />
  );
}

export function SitesBlock({ snap }: { snap: Snap }) {
  const { t } = useTranslation();
  const sites = (snap.siti ?? []) as SnapSite[];
  if (sites.length === 0) return null;
  return (
    <DetailTable
      headers={[
        t("management_review.snap.col_site"), t("management_review.snap.col_compliance"),
        t("management_review.snap.critical"), t("management_review.snap.open_incidents"), t("management_review.snap.tasks_overdue"),
      ]}
      rows={sites.map(s => [
        <span><span className="font-medium">{s.code}</span> <span className="text-gray-500">{s.name}</span></span>,
        s.pct_compliant != null ? `${s.pct_compliant}%` : "—",
        <span className={s.rischi_critici ? "text-red-600 font-medium" : ""}>{s.rischi_critici}</span>,
        s.incidenti_aperti,
        <span className={s.task_scaduti ? "text-red-600" : ""}>{s.task_scaduti}</span>,
      ])}
    />
  );
}

/** Dati dello snapshot pertinenti a ciascun punto obbligatorio dell'ordine del giorno. */
export function AgendaData({ code, snap, approvedHere }: {
  code: string; snap: Snap; approvedHere?: Set<string>;
}) {
  const { t } = useTranslation();
  switch (code) {
    case "azioni_precedenti":
      return <PreviousActionsBlock snap={snap} />;
    case "prestazioni":
      return (
        <div className="space-y-2">
          <SnapSection title={t("management_review.snap.compliance_fw")} defaultOpen={false}><ComplianceBlock snap={snap} /></SnapSection>
          {snap.kpi && <SnapSection title={t("management_review.snap.kpi_section")} defaultOpen={false}><KpiBlock snap={snap} /></SnapSection>}
          {snap.obiettivi && <SnapSection title={t("management_review.snap.objectives_section")} defaultOpen={false}><ObjectivesBlock snap={snap} /></SnapSection>}
          {snap.audit && <SnapSection title={t("management_review.snap.audit_section")} defaultOpen={false}><AuditBlock snap={snap} /></SnapSection>}
          <SnapSection title={t("management_review.snap.incidents_12m")} defaultOpen={false}><IncidentsBlock snap={snap} /></SnapSection>
          <SnapSection title={t("management_review.snap.pdca_task")} defaultOpen={false}><PdcaTasksBlock snap={snap} /></SnapSection>
          <SnapSection title={t("management_review.snap.docs_evidence")} defaultOpen={false}><DocumentsBlock snap={snap} approvedHere={approvedHere} /></SnapSection>
        </div>
      );
    case "rischi":
      return <RisksBlock snap={snap} />;
    case "miglioramento":
      return <OpportunitiesBlock snap={snap} />;
    default:
      return null;
  }
}

export const AGENDA_CODES_WITH_DATA = new Set(["azioni_precedenti", "prestazioni", "rischi", "miglioramento"]);
