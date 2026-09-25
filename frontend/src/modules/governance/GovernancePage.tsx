import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { type RoleAssignment } from "../../api/endpoints/governance";
import { usersApi } from "../../api/endpoints/users";
import { ModuleHelp } from "../../components/ui/ModuleHelp";
import { DocumentWorkflowSection } from "./DocumentWorkflowPage";
import { FrameworkGovernanceTab } from "./FrameworkGovernanceTab";
import { GoverningBodiesSection } from "./GoverningBodiesSection";
import { RiskAppetiteGovernanceTab } from "./RiskAppetiteGovernanceTab";
import { RoleCoverageMatrix, type AssignPrefill } from "./RoleCoverageMatrix";
import { RoleRequirementsPanel } from "./RoleRequirementsPanel";
import { useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { RoleAssignmentModal, SostituisciModal, TerminaModal } from "./roleAssignmentModals";

// ── Toast ─────────────────────────────────────────────────────────────────────

function Toast({ msg, onClose }: { msg: string; onClose: () => void }) {
  return (
    <div className="fixed bottom-6 right-6 z-50 bg-green-600 text-white px-5 py-3 rounded-lg shadow-lg flex items-center gap-3 max-w-sm">
      <span className="text-sm">{msg}</span>
      <button onClick={onClose} className="text-white/80 hover:text-white text-lg leading-none">×</button>
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export function GovernancePage() {
  const { t } = useTranslation();
  const [searchParams, setSearchParams] = useSearchParams();
  const tabParam = searchParams.get("tab");
  const resolveTab = (p: string | null) =>
    p === "workflow"
      ? "workflow"
      : p === "frameworks"
      ? "frameworks"
      : p === "risk-appetite"
      ? "risk-appetite"
      : p === "requirements"
      ? "requirements"
      : "roles";
  const [tab, setTab] = useState<
    "roles" | "workflow" | "frameworks" | "risk-appetite" | "requirements"
  >(resolveTab(tabParam));

  useEffect(() => {
    setTab(resolveTab(searchParams.get("tab")));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams]);

  const [showRoleModal, setShowRoleModal]         = useState(false);
  const [assignInitial, setAssignInitial]         = useState<Partial<Record<string, any>> | undefined>(undefined);
  const [terminaTarget, setTerminaTarget]         = useState<RoleAssignment | null>(null);
  const [sostituisciTarget, setSostituisciTarget] = useState<RoleAssignment | null>(null);
  const [toast, setToast]                         = useState<string | null>(null);

  const { data: users } = useQuery({
    queryKey: ["users"],
    queryFn: () => usersApi.list(),
    retry: false,
  });

  const userList = (users ?? []).map(u => ({
    id:    u.id,
    email: u.email,
    name:  `${u.first_name} ${u.last_name}`.trim() || u.username || u.email,
  }));

  function showToast(msg: string) {
    setToast(msg);
    setTimeout(() => setToast(null), 4000);
  }

  function openAssign(prefill?: AssignPrefill) {
    setAssignInitial(
      prefill
        ? { role: prefill.role, scope_type: prefill.scope_type, scope_id: prefill.scope_id ?? null }
        : undefined,
    );
    setShowRoleModal(true);
  }

  // I modali Termina/Sostituisci usano solo id, role e nome titolare: dalla
  // matrice costruiamo un assignment parziale a partire dal titolare della cella.
  const holderAsAssignment = (h: { id: string; role: string; user_name?: string | null }) =>
    ({ id: h.id, role: h.role, user_name: h.user_name ?? null } as unknown as RoleAssignment);

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">{t("governance.title")}</h2>
          <p className="text-sm text-gray-500 mt-1">{t("governance.subtitle")}</p>
        </div>
        <ModuleHelp
          title={t("governance.help.title")}
          description={t("governance.help.description")}
          steps={[
            t("governance.help.steps.assign_role"),
            t("governance.help.steps.replace_role"),
            t("governance.help.steps.terminate_role"),
            t("governance.help.steps.vacant_roles_alert"),
            t("governance.help.steps.link_nomination_doc"),
          ]}
          connections={[
            { module: "M02 RBAC",              relation: t("governance.help.connections.rbac") },
            { module: "M13 Management Review", relation: t("governance.help.connections.management_review") },
          ]}
          configNeeded={[t("governance.help.config.create_users_m02")]}
        />
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex gap-6">
          <button
            type="button"
            onClick={() => {
              setTab("roles");
              setSearchParams((prev) => {
                const next = new URLSearchParams(prev);
                next.delete("tab");
                return next;
              });
            }}
            className={
              tab === "roles"
                ? "border-primary-600 text-primary-700 whitespace-nowrap py-2 px-1 border-b-2 font-medium text-sm"
                : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 whitespace-nowrap py-2 px-1 border-b-2 font-medium text-sm"
            }
          >
            {t("governance.tabs.roles")}
          </button>
          <button
            type="button"
            onClick={() => {
              setTab("workflow");
              setSearchParams((prev) => {
                const next = new URLSearchParams(prev);
                next.set("tab", "workflow");
                return next;
              });
            }}
            className={
              tab === "workflow"
                ? "border-primary-600 text-primary-700 whitespace-nowrap py-2 px-1 border-b-2 font-medium text-sm"
                : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 whitespace-nowrap py-2 px-1 border-b-2 font-medium text-sm"
            }
          >
            {t("governance.tabs.workflow")}
          </button>
          <button
            type="button"
            onClick={() => {
              setTab("frameworks");
              setSearchParams((prev) => {
                const next = new URLSearchParams(prev);
                next.set("tab", "frameworks");
                return next;
              });
            }}
            className={
              tab === "frameworks"
                ? "border-primary-600 text-primary-700 whitespace-nowrap py-2 px-1 border-b-2 font-medium text-sm"
                : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 whitespace-nowrap py-2 px-1 border-b-2 font-medium text-sm"
            }
          >
            {t("governance.tabs.frameworks")}
          </button>
          <button
            type="button"
            onClick={() => {
              setTab("risk-appetite");
              setSearchParams((prev) => {
                const next = new URLSearchParams(prev);
                next.set("tab", "risk-appetite");
                return next;
              });
            }}
            className={
              tab === "risk-appetite"
                ? "border-primary-600 text-primary-700 whitespace-nowrap py-2 px-1 border-b-2 font-medium text-sm"
                : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 whitespace-nowrap py-2 px-1 border-b-2 font-medium text-sm"
            }
          >
            {t("governance.tabs.risk_appetite", { defaultValue: "Risk Appetite" })}
          </button>
          <button
            type="button"
            onClick={() => {
              setTab("requirements");
              setSearchParams((prev) => {
                const next = new URLSearchParams(prev);
                next.set("tab", "requirements");
                return next;
              });
            }}
            className={
              tab === "requirements"
                ? "border-primary-600 text-primary-700 whitespace-nowrap py-2 px-1 border-b-2 font-medium text-sm"
                : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 whitespace-nowrap py-2 px-1 border-b-2 font-medium text-sm"
            }
          >
            {t("governance.tabs.requirements", { defaultValue: "Ruoli obbligatori" })}
          </button>
        </nav>
      </div>

      {tab === "frameworks" ? (
        <FrameworkGovernanceTab />
      ) : tab === "workflow" ? (
        <div className="space-y-4">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h3 className="text-lg font-semibold text-gray-900">{t("governance.workflow.title")}</h3>
              <p className="text-sm text-gray-500 mt-1">
                {t("governance.workflow.subtitle")}
              </p>
            </div>
            <ModuleHelp
                title={t("governance.workflow.help.title")}
                description={t("governance.workflow.help.description")}
                steps={[
                  t("governance.workflow.help.steps.choose_type_and_scope"),
                  t("governance.workflow.help.steps.assign_creators"),
                  t("governance.workflow.help.steps.assign_reviewers"),
                  t("governance.workflow.help.steps.assign_approvers"),
                ]}
                connections={[
                  { module: "M07 Documenti", relation: t("governance.workflow.help.connections.documents") },
                  { module: "M00 Governance", relation: t("governance.workflow.help.connections.governance") },
                ]}
            />
          </div>
          <DocumentWorkflowSection embedded />
        </div>
      ) : tab === "risk-appetite" ? (
        <RiskAppetiteGovernanceTab />
      ) : tab === "requirements" ? (
        <RoleRequirementsPanel />
      ) : (
        <>
          {/* Matrice di copertura ruoli (ingloba gli alert vacanti / in scadenza) */}
          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <RoleCoverageMatrix
              onAssign={(prefill) => openAssign(prefill)}
              onReplace={(h) => setSostituisciTarget(holderAsAssignment(h))}
              onTerminate={(h) => setTerminaTarget(holderAsAssignment(h))}
            />
          </div>

          {/* Organi di governo: chi tiene e approva il riesame di direzione */}
          <GoverningBodiesSection users={userList.map(u => ({ id: u.id, label: `${u.name} (${u.email})` }))} />

          {/* Modali */}
          {showRoleModal && (
            <RoleAssignmentModal
              users={userList}
              initial={assignInitial}
              onClose={() => { setShowRoleModal(false); setAssignInitial(undefined); }}
            />
          )}
          {terminaTarget && (
            <TerminaModal
              assignment={terminaTarget}
              onClose={() => setTerminaTarget(null)}
              onSuccess={showToast}
            />
          )}
          {sostituisciTarget && (
            <SostituisciModal
              assignment={sostituisciTarget}
              users={userList}
              onClose={() => setSostituisciTarget(null)}
              onSuccess={showToast}
            />
          )}

          {toast && <Toast msg={toast} onClose={() => setToast(null)} />}
        </>
      )}
    </div>
  );
}
