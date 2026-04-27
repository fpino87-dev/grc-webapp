import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import {
  osintApi,
  type AlertSeverity,
  type FindingCode,
  type FindingStatus,
  type OsintFinding,
} from "../../api/endpoints/osint";

type Filter = "all" | AlertSeverity;

const SEVERITY_COLORS: Record<AlertSeverity, string> = {
  critical: "border-red-300 bg-red-50",
  warning: "border-orange-300 bg-orange-50",
  info: "border-gray-300 bg-gray-50",
};

const STATUS_BADGE: Record<FindingStatus, string> = {
  open: "bg-red-100 text-red-700",
  acknowledged: "bg-yellow-100 text-yellow-800",
  in_progress: "bg-blue-100 text-blue-700",
  resolved: "bg-green-100 text-green-700",
  accepted_risk: "bg-purple-100 text-purple-700",
};

function severityIcon(s: AlertSeverity): string {
  return s === "critical" ? "🔴" : s === "warning" ? "🟠" : "ℹ️";
}

function StatusPill({ status }: { status: FindingStatus }) {
  const { t } = useTranslation();
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${STATUS_BADGE[status]}`}>
      {t(`osint.remediation.status.${status}`, status)}
    </span>
  );
}

function FindingCard({
  finding,
  expanded,
  onToggle,
  onCreateTask,
  onUpdateStatus,
  selected,
  onSelectChange,
}: {
  finding: OsintFinding;
  expanded: boolean;
  onToggle: () => void;
  onCreateTask: () => void;
  onUpdateStatus: (s: FindingStatus) => void;
  selected: boolean;
  onSelectChange: (v: boolean) => void;
}) {
  const { t } = useTranslation();
  const pb = finding.playbook;

  return (
    <div className={`border rounded-lg overflow-hidden ${SEVERITY_COLORS[finding.severity]}`}>
      <div className="flex items-start gap-3 p-3">
        <input
          type="checkbox"
          checked={selected}
          onChange={e => onSelectChange(e.target.checked)}
          className="mt-1.5 h-4 w-4 rounded border-gray-300"
          onClick={e => e.stopPropagation()}
        />
        <div className="flex-1 min-w-0 cursor-pointer" onClick={onToggle}>
          <div className="flex items-center gap-2 flex-wrap">
            <span>{severityIcon(finding.severity)}</span>
            <span className="font-semibold text-sm text-gray-900">
              {pb?.title ?? finding.code}
            </span>
            <span className="text-xs text-gray-500 truncate max-w-[200px]">
              {finding.entity_display_name} · {finding.entity_domain}
            </span>
            {finding.is_nis2_critical && (
              <span className="text-orange-500 text-xs" title="NIS2 critico">★ NIS2</span>
            )}
            <StatusPill status={finding.status} />
          </div>
          <div className="text-xs text-gray-500 mt-1">
            {t("osint.remediation.first_seen")}: {new Date(finding.first_seen).toLocaleDateString("it-IT")}
            {finding.linked_task_id && (
              <span className="ml-2 text-blue-600">→ Task #{finding.linked_task_id.slice(0, 8)}</span>
            )}
          </div>
        </div>
        <button
          onClick={onToggle}
          className="text-xs text-gray-500 hover:text-gray-700"
        >
          {expanded ? "▲" : "▼"}
        </button>
      </div>

      {expanded && pb && (
        <div className="bg-white p-4 space-y-3 border-t">
          <Section title={t("osint.remediation.what")}>
            <p className="text-sm text-gray-700">{pb.what}</p>
          </Section>
          <Section title={t("osint.remediation.impact")}>
            <p className="text-sm text-gray-700">{pb.impact}</p>
          </Section>
          <Section title={t("osint.remediation.compliance")}>
            <ul className="text-xs space-y-0.5">
              {pb.compliance.map((c, i) => (
                <li key={i} className="text-gray-700">
                  <span className="font-mono bg-gray-100 px-1.5 py-0.5 rounded">{c.framework}</span>
                  {" "}— {c.control}
                </li>
              ))}
            </ul>
          </Section>
          <Section title={t("osint.remediation.fix_steps")}>
            <ol className="text-sm text-gray-800 space-y-1 list-decimal list-inside">
              {pb.fix_steps.map((s, i) => (
                <li key={i}>{s}</li>
              ))}
            </ol>
            {pb.fix_template && (
              <div className="mt-2 bg-gray-900 text-green-200 text-xs font-mono p-2 rounded relative">
                <button
                  onClick={() => navigator.clipboard.writeText(pb.fix_template!)}
                  className="absolute top-1 right-1 text-xs text-gray-300 hover:text-white"
                >
                  📋 copia
                </button>
                {pb.fix_template.replace("{domain}", finding.entity_domain)}
              </div>
            )}
          </Section>
          {pb.external_refs && pb.external_refs.length > 0 && (
            <Section title={t("osint.remediation.refs")}>
              <ul className="text-xs space-y-0.5">
                {pb.external_refs.map((r, i) => (
                  <li key={i}>
                    <a href={r.url} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">
                      {r.label} ↗
                    </a>
                  </li>
                ))}
              </ul>
            </Section>
          )}
          <div className="flex flex-wrap gap-2 pt-2 border-t">
            {!finding.linked_task_id && (
              <button
                onClick={onCreateTask}
                className="px-3 py-1.5 text-xs bg-primary-600 text-white rounded hover:bg-primary-700"
              >
                ✅ {t("osint.remediation.create_task")}
              </button>
            )}
            {finding.status !== "resolved" && (
              <button
                onClick={() => onUpdateStatus("resolved")}
                className="px-3 py-1.5 text-xs border border-green-300 text-green-700 rounded hover:bg-green-50"
              >
                {t("osint.remediation.mark_resolved")}
              </button>
            )}
            {finding.status === "open" && (
              <button
                onClick={() => onUpdateStatus("acknowledged")}
                className="px-3 py-1.5 text-xs border border-yellow-300 text-yellow-700 rounded hover:bg-yellow-50"
              >
                {t("osint.remediation.acknowledge")}
              </button>
            )}
            {finding.status !== "accepted_risk" && (
              <button
                onClick={() => onUpdateStatus("accepted_risk")}
                className="px-3 py-1.5 text-xs border border-purple-300 text-purple-700 rounded hover:bg-purple-50"
              >
                {t("osint.remediation.accept_risk")}
              </button>
            )}
            {pb.estimated_effort_h !== undefined && (
              <span className="ml-auto text-xs text-gray-500 self-center">
                ⏱ ~{pb.estimated_effort_h}h
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <p className="text-xs font-semibold text-gray-500 uppercase mb-1">{title}</p>
      {children}
    </div>
  );
}

export function OsintRemediationPage() {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [filter, setFilter] = useState<Filter>("all");
  const [groupBy, setGroupBy] = useState<"code" | "entity">("code");
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [showResolved, setShowResolved] = useState(false);

  const { data: summary } = useQuery({
    queryKey: ["osint-findings-summary"],
    queryFn: osintApi.findingsSummary,
    refetchInterval: 60_000,
  });

  const { data: findings = [], isLoading } = useQuery({
    queryKey: ["osint-findings", showResolved],
    queryFn: () => osintApi.findings(showResolved ? {} : { open_only: "1" }),
  });

  const filtered = useMemo(() => {
    return findings.filter(f => {
      if (filter !== "all" && f.severity !== filter) return false;
      return true;
    });
  }, [findings, filter]);

  const grouped = useMemo(() => {
    const map = new Map<string, OsintFinding[]>();
    for (const f of filtered) {
      const key = groupBy === "code" ? f.code : f.entity_domain;
      if (!map.has(key)) map.set(key, []);
      map.get(key)!.push(f);
    }
    // Sort gruppi per severità del primo elemento
    return Array.from(map.entries()).sort(([, a], [, b]) => {
      const order = { critical: 0, warning: 1, info: 2 };
      return order[a[0].severity] - order[b[0].severity];
    });
  }, [filtered, groupBy]);

  const updateMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: FindingStatus }) =>
      osintApi.updateFinding(id, { status }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["osint-findings"] });
      qc.invalidateQueries({ queryKey: ["osint-findings-summary"] });
    },
  });

  const taskMutation = useMutation({
    mutationFn: (id: string) => osintApi.createTaskFromFinding(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["osint-findings"] });
    },
  });

  const bulkTaskMutation = useMutation({
    mutationFn: (ids: string[]) => osintApi.bulkTaskFindings(ids),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["osint-findings"] });
      setSelected(new Set());
    },
  });

  function toggleExpanded(id: string) {
    setExpanded(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  }

  function toggleSelected(id: string, v: boolean) {
    setSelected(prev => {
      const next = new Set(prev);
      if (v) next.add(id); else next.delete(id);
      return next;
    });
  }

  return (
    <div className="p-4 sm:p-6 space-y-4 max-w-5xl">
      {/* Header */}
      <div className="flex items-center gap-3 flex-wrap">
        <Link to="/osint" className="text-sm text-gray-500 hover:text-gray-700">← {t("osint.title")}</Link>
        <span className="text-gray-300">/</span>
        <h1 className="text-xl font-bold text-gray-900">{t("osint.remediation.title", "Risoluzione")}</h1>
      </div>
      <p className="text-sm text-gray-500">
        {t("osint.remediation.subtitle", "Tutti i problemi rilevati con guida step-by-step alla risoluzione e mappatura ai controlli normativi.")}
      </p>

      {/* KPI */}
      {summary && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <KpiCard label={t("osint.remediation.kpi.critical")} value={summary.open_critical} valueClass="text-red-600" icon="🔴" />
          <KpiCard label={t("osint.remediation.kpi.warning")} value={summary.open_warning} valueClass="text-orange-600" icon="🟠" />
          <KpiCard label={t("osint.remediation.kpi.info")} value={summary.open_info} valueClass="text-gray-700" icon="ℹ️" />
          <KpiCard label={t("osint.remediation.kpi.resolved_7d")} value={summary.resolved_last_7d} valueClass="text-green-600" icon="✅" />
        </div>
      )}

      {/* Toolbar */}
      <div className="flex flex-wrap items-center gap-2">
        {(["all", "critical", "warning", "info"] as Filter[]).map(f => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-3 py-1 text-sm rounded-full border ${
              filter === f
                ? "bg-primary-600 text-white border-primary-600"
                : "bg-white text-gray-600 border-gray-300 hover:bg-gray-50"
            }`}
          >
            {t(`osint.remediation.filter.${f}`, f)}
          </button>
        ))}
        <span className="text-gray-300">|</span>
        <button
          onClick={() => setGroupBy(groupBy === "code" ? "entity" : "code")}
          className="text-xs text-gray-500 hover:text-gray-700"
        >
          {t("osint.remediation.group_by")}: {groupBy === "code" ? t("osint.remediation.group.code") : t("osint.remediation.group.entity")} ▼
        </button>
        <label className="text-xs text-gray-500 inline-flex items-center gap-1.5 ml-2">
          <input
            type="checkbox"
            checked={showResolved}
            onChange={e => setShowResolved(e.target.checked)}
            className="h-3.5 w-3.5 rounded border-gray-300"
          />
          {t("osint.remediation.show_resolved")}
        </label>

        <div className="ml-auto flex items-center gap-2">
          {selected.size > 0 && (
            <button
              onClick={() => bulkTaskMutation.mutate(Array.from(selected))}
              disabled={bulkTaskMutation.isPending}
              className="px-3 py-1.5 text-xs bg-primary-600 text-white rounded hover:bg-primary-700 disabled:opacity-50"
            >
              ✅ {t("osint.remediation.bulk_task", { count: selected.size })}
            </button>
          )}
          <a
            href="/api/v1/osint/findings/export/"
            target="_blank"
            rel="noopener noreferrer"
            className="px-3 py-1.5 text-xs border rounded hover:bg-gray-50"
          >
            ⬇ {t("osint.remediation.export_csv")}
          </a>
        </div>
      </div>

      {isLoading && <div className="text-gray-400 text-sm">{t("common.loading")}</div>}

      {!isLoading && filtered.length === 0 && (
        <div className="border rounded-xl p-8 text-center bg-white">
          <p className="text-3xl mb-2">🎉</p>
          <p className="text-gray-600 text-sm">{t("osint.remediation.empty")}</p>
        </div>
      )}

      <div className="space-y-4">
        {grouped.map(([key, items]) => (
          <div key={key}>
            <div className="flex items-center gap-2 mb-2">
              <h3 className="text-sm font-semibold text-gray-700 uppercase">
                {groupBy === "code"
                  ? items[0].playbook?.title ?? key
                  : key}
              </h3>
              <span className="text-xs text-gray-500">— {items.length}</span>
            </div>
            <div className="space-y-2">
              {items.map(f => (
                <FindingCard
                  key={f.id}
                  finding={f}
                  expanded={expanded.has(f.id)}
                  onToggle={() => toggleExpanded(f.id)}
                  onCreateTask={() => taskMutation.mutate(f.id)}
                  onUpdateStatus={s => updateMutation.mutate({ id: f.id, status: s })}
                  selected={selected.has(f.id)}
                  onSelectChange={v => toggleSelected(f.id, v)}
                />
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function KpiCard({ label, value, valueClass = "text-gray-900", icon = "" }: {
  label: string; value: number | string; valueClass?: string; icon?: string;
}) {
  return (
    <div className="bg-white border rounded-lg p-3 text-center">
      <div className={`text-2xl font-bold ${valueClass}`}>{icon} {value}</div>
      <div className="text-xs text-gray-500 mt-0.5">{label}</div>
    </div>
  );
}
