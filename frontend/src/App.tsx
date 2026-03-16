import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { useAuthStore } from "./store/auth";
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

function PrivateRoute({ children }: { children: React.ReactNode }) {
  const token = useAuthStore((s) => s.token);
  if (!token) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export function App() {
  return (
    <BrowserRouter>
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
          <Route path="controls" element={<ControlsList />} />
          <Route path="gap-analysis" element={<GapAnalysisPage />} />
          <Route path="incidents" element={<IncidentsList />} />
          <Route path="plants" element={<PlantsList />} />
          <Route path="governance" element={<GovernancePage />} />
          <Route path="assets" element={<AssetsPage />} />
          <Route path="risk" element={<RiskPage />} />
          <Route path="tasks" element={<TasksPage />} />
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
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
