// govrico - Governance, Risk & Compliance Platform
// Copyright (C) 2025 govrico
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU Affero General Public License as published
// by the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
// GNU Affero General Public License for more details.
//
// You should have received a copy of the GNU Affero General Public License
// along with this program. If not, see <https://www.gnu.org/licenses/>.

import { useEffect, useState } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { useAuthStore } from "./store/auth";
import { applyScale, useUiStore } from "./store/ui";
import { refreshTokenApi } from "./api/endpoints/auth";
import { Shell } from "./components/layout/Shell";
import { LoginPage } from "./pages/LoginPage";
import { Dashboard } from "./modules/dashboard/Dashboard";
import { ControlsList } from "./modules/controls/ControlsList";
import { GapAnalysisPage } from "./modules/controls/GapAnalysisPage";
import { IncidentsList } from "./modules/incidents/IncidentsList";
import { PlantsList } from "./modules/plants/PlantsList";
import { GovernancePage } from "./modules/governance/GovernancePage";
import { AssetsPage } from "./modules/assets/AssetsPage";
import { RiskPage } from "./modules/risk/RiskPage";
import { TasksPage } from "./modules/tasks/TasksPage";
import { ChecklistTemplateList } from "./modules/checklist/ChecklistTemplateList";
import { ChecklistTemplateForm } from "./modules/checklist/ChecklistTemplateForm";
import { ChecklistRunList } from "./modules/checklist/ChecklistRunList";
import { ChecklistRunDetail } from "./modules/checklist/ChecklistRunDetail";
import { KpiDashboard } from "./modules/tasks/kpi/KpiDashboard";
import { KpiDefinitionList } from "./modules/tasks/kpi/KpiDefinitionList";
import { KpiDefinitionForm } from "./modules/tasks/kpi/KpiDefinitionForm";
import { DocumentsPage } from "./modules/documents/DocumentsPage";
import { ReportingPage } from "./modules/reporting/ReportingPage";
import { UsersPage } from "./modules/users/UsersPage";
import { BiaPage } from "./modules/bia/BiaPage";
import { SuppliersPage } from "./modules/suppliers/SuppliersPage";
import { BcpPage } from "./modules/bcp/BcpPage";
import { LessonsPage } from "./modules/lessons/LessonsPage";
import { TrainingPage } from "./modules/training/TrainingPage";
import { AuditPrepPage } from "./modules/auditprep/AuditPrepPage";
import { PdcaPage } from "./modules/pdca/PdcaPage";
import { ManagementReviewPage } from "./modules/managementreview/ManagementReviewPage";
import { AuditTrailPage } from "./modules/audittrail/AuditTrailPage";
import { ActivitySchedulePage } from "./modules/schedule/ActivitySchedulePage";
import { RequiredDocumentsPage } from "./modules/schedule/RequiredDocumentsPage";
import { SchedulePolicyPage } from "./modules/schedule/SchedulePolicyPage";
import { CompetencyPage } from "./modules/competency/CompetencyPage";
import { EmailSettingsPage } from "./modules/settings/EmailSettingsPage";
import { NotificationSettingsPage } from "./modules/settings/NotificationSettingsPage";
import { AiSettingsPage } from "./modules/settings/AiSettingsPage";
import { MfaSettingsPage } from "./modules/settings/MfaSettingsPage";
import { BackupsPage } from "./modules/backups/BackupsPage";
import { CockpitPage } from "./modules/cockpit/CockpitPage";
import { OsintDashboard } from "./modules/osint/OsintDashboard";
import { OsintSettingsPage } from "./modules/osint/OsintSettings";
import { OsintSubdomainsPage } from "./modules/osint/OsintSubdomainsPage";
import { OsintRemediationPage } from "./modules/osint/OsintRemediationPage";

/**
 * Applica la scala UI memorizzata per il monitor corrente e la riapplica
 * quando la finestra cambia schermo (lo spostamento su un monitor con
 * risoluzione/DPR diversi genera un resize e cambia la firma schermo).
 */
function UiScaleManager() {
  useEffect(() => {
    const sync = () => applyScale(useUiStore.getState().refreshSignature());
    sync();
    window.addEventListener("resize", sync);
    return () => window.removeEventListener("resize", sync);
  }, []);
  return null;
}

function PrivateRoute({ children }: { children: React.ReactNode }) {
  const token = useAuthStore((s) => s.token);
  const user = useAuthStore((s) => s.user);
  // newfix #6 — l'access token vive solo in memoria: dopo un F5 e' null anche
  // se la sessione e' valida (cookie httpOnly grc_refresh, 7 giorni). Se c'e'
  // un utente persistito, riotteniamo l'access in silenzio prima di decidere
  // se mandare al login.
  const [bootstrapping, setBootstrapping] = useState(!token && !!user);

  useEffect(() => {
    if (token || !user) return;
    let cancelled = false;
    refreshTokenApi()
      .then((data) => { if (!cancelled) useAuthStore.getState().setToken(data.access); })
      .catch(() => { if (!cancelled) useAuthStore.getState().logout(); })
      .finally(() => { if (!cancelled) setBootstrapping(false); });
    return () => { cancelled = true; };
  }, [token, user]);

  if (token) return <>{children}</>;
  if (bootstrapping) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="w-8 h-8 border-4 border-primary-600 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }
  return <Navigate to="/login" replace />;
}

export function App() {
  return (
    <BrowserRouter>
      <UiScaleManager />
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/"
          element={
            <PrivateRoute>
              <Shell />
            </PrivateRoute>
          }
        >
          <Route index element={<Dashboard />} />
          <Route path="cockpit" element={<CockpitPage />} />
          <Route path="controls" element={<ControlsList />} />
          <Route path="gap-analysis" element={<GapAnalysisPage />} />
          <Route path="incidents" element={<IncidentsList />} />
          <Route path="plants" element={<PlantsList />} />
          <Route path="governance" element={<GovernancePage />} />
          <Route path="governance/workflow-documenti" element={<Navigate to="/governance?tab=workflow" replace />} />
          <Route path="assets" element={<AssetsPage />} />
          <Route path="risk" element={<RiskPage />} />
          <Route path="tasks" element={<TasksPage />} />
          <Route path="checklists/templates" element={<ChecklistTemplateList />} />
          <Route path="checklists/templates/new" element={<ChecklistTemplateForm />} />
          <Route path="checklists/templates/:id/edit" element={<ChecklistTemplateForm />} />
          <Route path="checklists/runs" element={<ChecklistRunList />} />
          <Route path="checklists/runs/:id" element={<ChecklistRunDetail />} />
          <Route path="kpi" element={<KpiDashboard />} />
          <Route path="kpi/definitions" element={<KpiDefinitionList />} />
          <Route path="kpi/definitions/new" element={<KpiDefinitionForm />} />
          <Route path="kpi/definitions/:id/edit" element={<KpiDefinitionForm />} />
          <Route path="documents" element={<DocumentsPage />} />
          <Route path="reporting" element={<ReportingPage />} />
          <Route path="users" element={<UsersPage />} />
          <Route path="bia" element={<BiaPage />} />
          <Route path="suppliers" element={<SuppliersPage />} />
          <Route path="bcp" element={<BcpPage />} />
          <Route path="lessons" element={<LessonsPage />} />
          <Route path="training" element={<TrainingPage />} />
          <Route path="audit-prep" element={<AuditPrepPage />} />
          <Route path="pdca" element={<PdcaPage />} />
          <Route path="management-review" element={<ManagementReviewPage />} />
          <Route path="audit-trail" element={<AuditTrailPage />} />
          <Route path="schedule/activity" element={<ActivitySchedulePage />} />
          <Route path="schedule/documents" element={<RequiredDocumentsPage />} />
          <Route path="schedule/policy" element={<SchedulePolicyPage />} />
          <Route path="competency" element={<CompetencyPage />} />
          <Route path="settings/email" element={<EmailSettingsPage />} />
          <Route path="settings/notifications" element={<NotificationSettingsPage />} />
          <Route path="settings/ai" element={<AiSettingsPage />} />
          <Route path="settings/mfa" element={<MfaSettingsPage />} />
          <Route path="settings/backups" element={<BackupsPage />} />
          <Route path="osint" element={<OsintDashboard />} />
          <Route path="osint/settings" element={<OsintSettingsPage />} />
          <Route path="osint/subdomains" element={<OsintSubdomainsPage />} />
          <Route path="osint/remediation" element={<OsintRemediationPage />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
