import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { controlsApi } from "../../api/endpoints/controls";
import { useAuthStore } from "../../store/auth";
import type { Tab } from "./drawer/shared";
import { useDetailInfo } from "./drawer/useDetailInfo";
import { TabCosa } from "./drawer/TabCosa";
import { TabValutazione } from "./drawer/TabValutazione";
import { TabDocEvidence } from "./drawer/TabDocEvidence";
import { TabStorico } from "./drawer/TabStorico";

interface Props {
  instanceId: string | null;
  onClose: () => void;
}

export function ControlDetailDrawer({ instanceId, onClose }: Props) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const user = useAuthStore(s => s.user);
  const [tab, setTab] = useState<Tab>("cosa");
  const { data: info, isLoading } = useDetailInfo(instanceId);
  const open = !!instanceId;

  // C10: l'eliminazione (soft delete) dell'istanza vive qui, non più su ogni
  // riga della lista. Il backend la consente solo sui controlli non valutati,
  // salvo super admin — rispecchiamo la stessa regola nella UI.
  const isSuperAdmin = user?.role === "super_admin";
  const canDelete = !!info && (info.current_status === "non_valutato" || isSuperAdmin);

  const deleteMutation = useMutation({
    mutationFn: () => controlsApi.deleteInstance(instanceId!),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["controls"] });
      onClose();
    },
    onError: (e: any) => {
      window.alert(e?.response?.data?.detail || t("common.error"));
    },
  });

  const tabs: [Tab, string][] = [
    ["cosa",        t("controls.drawer.tabs.about")],
    ["valutazione", t("controls.drawer.tabs.evaluation")],
    ["docevidence", t("controls.drawer.tabs.documents_evidence")],
    ["storico",     t("controls.drawer.tabs.history")],
  ];

  return (
    <>
      {open && <div className="fixed inset-0 bg-black/30 z-40" onClick={onClose} />}
      <div
        className={`fixed top-0 right-0 h-full z-50 bg-white shadow-2xl flex flex-col transition-transform duration-300 ease-in-out ${open ? "translate-x-0" : "translate-x-full"}`}
        style={{ width: "50vw", minWidth: 520 }}
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100 shrink-0 bg-gradient-to-r from-slate-700 to-slate-800">
          <div>
            <h2 className="text-white font-semibold text-base">{t("controls.drawer.title")}</h2>
            <p className="text-slate-300 text-xs mt-0.5">
              {isLoading ? t("common.loading") : info ? `${info.control_id} — ${info.framework}` : "—"}
            </p>
          </div>
          <button onClick={onClose} className="text-white/80 hover:text-white w-8 h-8 flex items-center justify-center rounded hover:bg-white/10 text-xl">×</button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-gray-200 shrink-0">
          {tabs.map(([key, label]) => (
            <button
              key={key}
              onClick={() => setTab(key)}
              className={`flex-1 py-2.5 text-xs font-medium transition-colors ${
                tab === key
                  ? "border-b-2 border-slate-700 text-slate-800 bg-slate-50"
                  : "text-gray-500 hover:text-gray-700 hover:bg-gray-50"
              }`}
            >
              {label}
              {key === "docevidence" && info && !info.requirements.satisfied && (
                <span className="ml-1 inline-flex w-2 h-2 bg-red-500 rounded-full" />
              )}
              {key === "valutazione" && info && info.suggested_status !== info.current_status && (
                <span className="ml-1 inline-flex w-2 h-2 bg-indigo-400 rounded-full" />
              )}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-5 py-4">
          {isLoading && <div className="text-center text-gray-400 py-8">{t("common.loading")}</div>}
          {!isLoading && info && (
            <>
              {tab === "cosa"        && <TabCosa info={info} />}
              {tab === "valutazione" && (
                <TabValutazione
                  key={instanceId}
                  instanceId={instanceId!}
                  requirements={info.requirements}
                  currentStatus={info.current_status}
                  suggestedStatus={info.suggested_status}
                  suggestedStatusReason={info.suggested_status_reason}
                  evidenceRequirement={info.evidence_requirement}
                  applicability={info.applicability}
                  exclusionJustification={info.exclusion_justification}
                  naJustification={info.na_justification ?? ""}
                  calcMaturityLevel={info.calc_maturity_level}
                  maturityLevelOverride={info.maturity_level_override}
                  framework={info.framework}
                  approvedInSoa={info.approved_in_soa}
                  soaApprovedAt={info.soa_approved_at}
                  soaApprovedByName={info.soa_approved_by_name}
                  needsRevaluation={info.needs_revaluation}
                  needsRevaluationSince={info.needs_revaluation_since}
                  initialNotes={info.notes}
                  linkedAssets={info.linked_assets ?? []}
                  availableAssets={info.available_assets ?? []}
                />
              )}
              {tab === "docevidence" && (
                <TabDocEvidence
                  instanceId={instanceId!}
                  evidences={info.current_evidences}
                  documents={info.linked_documents}
                  requirements={info.requirements}
                  evidenceRequirement={info.evidence_requirement}
                />
              )}
              {tab === "storico"     && <TabStorico history={info.evaluation_history} />}
            </>
          )}
        </div>

        {/* Footer — danger zone (C10) */}
        {info && (
          <div className="shrink-0 border-t border-gray-100 px-5 py-3 bg-gray-50 flex items-center justify-between gap-3">
            <p className="text-[11px] text-gray-500 leading-tight">
              {canDelete
                ? t("controls.drawer.delete.hint")
                : t("controls.drawer.delete.restricted")}
            </p>
            <button
              type="button"
              title={t("controls.actions.delete_title")}
              disabled={!canDelete || deleteMutation.isPending}
              onClick={() => {
                if (!window.confirm(t("controls.actions.delete_confirm", { id: info.control_id }))) return;
                deleteMutation.mutate();
              }}
              className="shrink-0 text-xs font-medium text-red-600 hover:text-red-800 border border-red-200 hover:border-red-300 rounded px-3 py-1.5 disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:text-red-600"
            >
              🗑 {t("controls.drawer.delete.button")}
            </button>
          </div>
        )}
      </div>
    </>
  );
}
