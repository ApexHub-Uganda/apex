import { lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ThemeProvider } from './context/ThemeContext';
import { AuthProvider } from './context/AuthContext';
import { TenantProvider } from './context/TenantContext';
import ProtectedRoute from './components/ProtectedRoute';

import AuthLayout from './layouts/AuthLayout';
import OnboardingLayout from './layouts/OnboardingLayout';
import SuperAdminLayout from './layouts/SuperAdminLayout';
import SchoolAdminLayout from './layouts/SchoolAdminLayout';

import Login from './pages/auth/Login';
import Register from './pages/auth/Register';
import RegistrationWelcome from './pages/auth/RegistrationWelcome';
import ForgotPassword from './pages/auth/ForgotPassword';
import ResetPassword from './pages/auth/ResetPassword';

import SuperAdminDashboard from './pages/super-admin/Dashboard';
import Schools from './pages/super-admin/Schools';
import SchoolDetail from './pages/super-admin/SchoolDetail';
import PlansAndSubscriptions from './pages/super-admin/PlansAndSubscriptions';
import BillingOperations from './pages/super-admin/BillingOperations';
import Analytics from './pages/super-admin/Analytics';
import AuditLogs from './pages/super-admin/AuditLogs';
import Broadcast from './pages/super-admin/Broadcast';
import SuperAdminSettings from './pages/super-admin/Settings';
import PlanEditor from './pages/super-admin/PlanEditor';
import NotificationsTodos from './pages/super-admin/NotificationsTodos';
import Advertise from './pages/super-admin/Advertise';

import SchoolAdminDashboard from './pages/school-admin/Dashboard';
import PlanUpgrade from './pages/school-admin/PlanUpgrade';
import Students from './pages/school-admin/Students';
import StudentWorkspace from './pages/school-admin/StudentWorkspace';
import Parents from './pages/school-admin/Parents';
import ParentWorkspace from './pages/school-admin/ParentWorkspace';
import Terms from './pages/school-admin/Terms';
import SubjectAssignments from './pages/school-admin/SubjectAssignments';
import Assignments from './pages/school-admin/Assignments';
import Grading from './pages/school-admin/Grading';
import GradeCalculation from './pages/school-admin/GradeCalculation';
import Staff from './pages/school-admin/Staff';
import Classes from './pages/school-admin/Classes';
import ClassDetail from './pages/school-admin/ClassDetail';
import Attendance from './pages/school-admin/Attendance';
import MarksEntry from './pages/school-admin/MarksEntry';
import MarksApproval from './pages/school-admin/MarksApproval';
import Assessments from './pages/school-admin/Assessments';
import LessonAttendance from './pages/school-admin/LessonAttendance';
import TeacherWorkspace from './pages/school-admin/TeacherWorkspace';
import HoDWorkspace from './pages/school-admin/HoDWorkspace';
import DoSWorkspace from './pages/school-admin/DoSWorkspace';
import ClassTeacherWorkspace from './pages/school-admin/ClassTeacherWorkspace';
import Finance from './pages/school-admin/Finance';
import BursarWorkspace from './pages/school-admin/BursarWorkspace';
import AssistantBursarWorkspace from './pages/school-admin/AssistantBursarWorkspace';
import FinanceApproval from './pages/school-admin/FinanceApproval';
import FinanceAnalytics from './pages/school-admin/FinanceAnalytics';
import FinanceReports from './pages/school-admin/FinanceReports';
import ParentFeeStatements from './pages/school-admin/ParentFeeStatements';
import FinanceBilling from './pages/school-admin/FinanceBilling';
import PromotionWizard from './pages/school-admin/PromotionWizard';
import AcademicReportCards from './pages/school-admin/AcademicReportCards';
import DoSOps from './pages/school-admin/DoSOps';
import Library from './pages/school-admin/Library';
import Hostel from './pages/school-admin/Hostel';
import Transport from './pages/school-admin/Transport';
import Inventory from './pages/school-admin/Inventory';
import HR from './pages/school-admin/HR';
import HRStaffs from './pages/school-admin/HRStaffs';
import StaffWorkspace from './pages/school-admin/StaffWorkspace';
import Payroll from './pages/school-admin/Payroll';
import Reports from './pages/school-admin/Reports';
import Communication from './pages/school-admin/Communication';
import SchoolAdminSettings from './pages/school-admin/Settings';
import PermissionSettings from './pages/school-admin/PermissionSettings';
import SchoolPlansAndSubscriptions from './pages/school-admin/PlansAndSubscriptions';
import UserAccounts from './pages/school-admin/UserAccounts';
import Campuses from './pages/school-admin/Campuses';
import TimetableWizard from './pages/school-admin/TimetableWizard';
import ResultsAccessPolicyPage from './pages/school-admin/ResultsAccessPolicy';
import ParentAcademics from './pages/school-admin/ParentAcademics';
import { SCHOOL_PORTAL_ROLES } from './config/schoolRoles';

import Profile from './pages/shared/Profile';
import Notifications from './pages/shared/Notifications';
import PendingApproval from './pages/shared/PendingApproval';
import Maintenance from './pages/shared/Maintenance';
import { MaintenanceProvider } from './context/MaintenanceContext';
import FeatureGate from './components/FeatureGate';
import AppToaster from './components/AppToaster';
import { SCHOOL_ROUTE_FEATURES } from './config/featureRoutes';
import { renderModuleHubRoutes, renderChildSubRoutes } from './config/schoolAdminRoutes';
import { ApexLoader } from './components/ApexLoader';
const HomeEntry = lazy(() => import('./pages/landing/HomeEntry'));
const TermsPage = lazy(() => import('./pages/landing/TermsPage'));

const Gated = ({ featureKey, children }) => (
  <FeatureGate featureKey={featureKey}>{children}</FeatureGate>
);

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
      staleTime: 30000,
    },
  },
});

function AppRoutes() {
  return (
    <Routes>
      {/* Auth routes */}
      <Route element={<AuthLayout />}>
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/forgot-password" element={<ForgotPassword />} />
        <Route path="/reset-password" element={<ResetPassword />} />
      </Route>

      <Route element={<OnboardingLayout />}>
        <Route path="/register/welcome" element={<RegistrationWelcome />} />
      </Route>

      <Route path="/maintenance" element={<Maintenance />} />

      {/* Super Admin portal */}
      <Route
        path="/super-admin"
        element={
          <ProtectedRoute roles={['super_admin']}>
            <SuperAdminLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<SuperAdminDashboard />} />
        <Route path="notifications" element={<NotificationsTodos />} />
        <Route path="notifications/advertise" element={<Advertise />} />
        <Route path="schools" element={<Schools />} />
        <Route path="schools/:schoolId" element={<SchoolDetail />} />
        <Route path="plans/new" element={<PlanEditor />} />
        <Route path="plans/:planId/edit" element={<PlanEditor />} />
        <Route path="plans" element={<PlansAndSubscriptions />} />
        <Route path="billing" element={<BillingOperations />} />
        <Route path="subscriptions" element={<Navigate to="/super-admin/plans" replace />} />
        <Route path="analytics" element={<Analytics />} />
        <Route path="audit-logs" element={<AuditLogs />} />
        <Route path="broadcast" element={<Broadcast />} />
        <Route path="settings" element={<SuperAdminSettings />} />
        <Route path="profile" element={<Profile />} />
      </Route>

      {/* School portal (admin, staff, parent — capped at school admin privileges) */}
      <Route
        path="/school-admin"
        element={
          <ProtectedRoute roles={SCHOOL_PORTAL_ROLES} portal={true}>
            <SchoolAdminLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<SchoolAdminDashboard />} />
        {renderModuleHubRoutes()}
        <Route path="students" element={<Gated featureKey={SCHOOL_ROUTE_FEATURES.students}><Students /></Gated>} />
        <Route path="students/new" element={<Gated featureKey="student_management"><StudentWorkspace /></Gated>} />
        <Route path="students/:studentId" element={<Gated featureKey="student_management"><StudentWorkspace /></Gated>} />
        <Route path="parents" element={<Gated featureKey="parent_management"><Parents /></Gated>} />
        <Route path="parents/new" element={<Gated featureKey="parent_management"><ParentWorkspace /></Gated>} />
        <Route path="parents/:parentId" element={<Gated featureKey="parent_management"><ParentWorkspace /></Gated>} />
        <Route path="academics/terms" element={<Gated featureKey="terms"><Terms /></Gated>} />
        <Route
          path="academics/subject-assignments"
          element={(
            <Gated featureKeys={['subject_assignment', 'teacher_assignments']}>
              <SubjectAssignments />
            </Gated>
          )}
        />
        <Route path="staff" element={<Gated featureKey={SCHOOL_ROUTE_FEATURES.staff}><Staff /></Gated>} />
        <Route path="classes" element={<Gated featureKey={SCHOOL_ROUTE_FEATURES.classes}><Classes /></Gated>} />
        <Route path="classes/:classId" element={<Gated featureKey={SCHOOL_ROUTE_FEATURES.classes}><ClassDetail /></Gated>} />
        <Route path="attendance" element={<Gated featureKey={SCHOOL_ROUTE_FEATURES.attendance}><Attendance /></Gated>} />
        <Route path="academics/teacher" element={<Gated featureKey="teacher_workspace"><TeacherWorkspace /></Gated>} />
        <Route path="academics/hod" element={<Gated featureKey="hod_workspace"><HoDWorkspace /></Gated>} />
        <Route path="academics/dos" element={<Gated featureKey="dos_workspace"><DoSWorkspace /></Gated>} />
        <Route path="academics/class-teacher" element={<Gated featureKey="class_teacher_tools"><ClassTeacherWorkspace /></Gated>} />
        <Route path="academics/grading" element={<Gated featureKey="grading"><Grading /></Gated>} />
        <Route
          path="academics/assignments"
          element={(
            <Gated featureKeys={['marks_entry', 'grade_calculation', 'assignments']}>
              <Assignments />
            </Gated>
          )}
        />
        <Route path="academics/assignments/marks" element={<Gated featureKey="marks_entry"><MarksEntry context="assignments" /></Gated>} />
        <Route path="academics/assignments/grades" element={<Gated featureKey="grade_calculation"><GradeCalculation context="assignments" /></Gated>} />
        <Route path="examinations/marks" element={<Gated featureKey="marks_entry"><MarksEntry /></Gated>} />
        <Route path="examinations/grades" element={<Gated featureKey="grade_calculation"><GradeCalculation /></Gated>} />
        <Route path="examinations/approval" element={<Gated featureKey="marks_approval"><MarksApproval /></Gated>} />
        <Route path="examinations/assessments" element={<Gated featureKey="assessment_management"><Assessments /></Gated>} />
        <Route path="attendance/lessons" element={<Gated featureKey="lesson_attendance"><LessonAttendance /></Gated>} />
        <Route path="finance" element={<Gated featureKey="student_billing"><FinanceBilling /></Gated>} />
        <Route path="finance/bursar" element={<Gated featureKey="bursar_workspace"><BursarWorkspace /></Gated>} />
        <Route path="finance/assistant" element={<Gated featureKey="assistant_bursar_workspace"><AssistantBursarWorkspace /></Gated>} />
        <Route path="finance/approval" element={<Gated featureKey="transaction_approval"><FinanceApproval /></Gated>} />
        <Route path="finance/payments" element={<Gated featureKey="payment_recording"><Finance /></Gated>} />
        <Route path="finance/analytics" element={<Gated featureKey="finance_analytics"><FinanceAnalytics /></Gated>} />
        <Route path="finance/reports" element={<Gated featureKey="financial_reports"><FinanceReports /></Gated>} />
        <Route path="finance/statements" element={<Gated featureKey="parent_fee_statements"><ParentFeeStatements /></Gated>} />
        <Route path="finance/results-access" element={<Gated featureKeys={['bursar_workspace', 'assistant_bursar_workspace']}><ResultsAccessPolicyPage /></Gated>} />
        <Route path="parent/academics" element={<ParentAcademics />} />
        <Route path="parent/results" element={<ParentAcademics />} />
        <Route path="library" element={<Gated featureKey={SCHOOL_ROUTE_FEATURES.library}><Library /></Gated>} />
        <Route path="hostel" element={<Gated featureKey={SCHOOL_ROUTE_FEATURES.hostel}><Hostel /></Gated>} />
        <Route path="transport" element={<Gated featureKey={SCHOOL_ROUTE_FEATURES.transport}><Transport /></Gated>} />
        <Route path="inventory" element={<Gated featureKey={SCHOOL_ROUTE_FEATURES.inventory}><Inventory /></Gated>} />
        <Route path="hr" element={<Gated featureKey={SCHOOL_ROUTE_FEATURES.hr}><HR /></Gated>} />
        <Route path="hr/staffs" element={<Gated featureKey="staff_management"><HRStaffs /></Gated>} />
        <Route path="hr/staffs/new" element={<Gated featureKey="staff_management"><StaffWorkspace /></Gated>} />
        <Route path="hr/staffs/:staffId" element={<Gated featureKey="staff_management"><StaffWorkspace /></Gated>} />
        <Route path="payroll" element={<Gated featureKey={SCHOOL_ROUTE_FEATURES.payroll}><Payroll /></Gated>} />
        <Route path="reports" element={<Gated featureKey={SCHOOL_ROUTE_FEATURES.reports}><Reports /></Gated>} />
        <Route path="communication" element={<Gated featureKey={SCHOOL_ROUTE_FEATURES.communication}><Communication /></Gated>} />
        {/* Settings / permissions / plans are core school-admin surfaces — not plan SKUs */}
        <Route
          path="settings"
          element={(
            <ProtectedRoute roles={['school_admin']}>
              <SchoolAdminSettings />
            </ProtectedRoute>
          )}
        />
        <Route
          path="settings/permissions"
          element={(
            <ProtectedRoute roles={['school_admin']}>
              <PermissionSettings />
            </ProtectedRoute>
          )}
        />
        <Route
          path="settings/plans"
          element={(
            <ProtectedRoute roles={['school_admin']}>
              <SchoolPlansAndSubscriptions />
            </ProtectedRoute>
          )}
        />
        <Route path="core/user-accounts" element={<Gated featureKey="user_accounts"><UserAccounts /></Gated>} />
        <Route path="core/campuses" element={<Gated featureKey="multi_campus_support"><Campuses /></Gated>} />
        <Route path="academics/timetable/wizard" element={<Gated featureKey="timetables"><TimetableWizard /></Gated>} />
        <Route path="academics/promotion" element={<Gated featureKey="student_promotion"><PromotionWizard /></Gated>} />
        <Route path="academics/report-cards" element={<Gated featureKeys={['report_cards', 'class_report_cards', 'result_processing']}><AcademicReportCards /></Gated>} />
        <Route path="academics/dos-ops" element={<Gated featureKey="dos_workspace"><DoSOps /></Gated>} />
        <Route path="examinations/report-cards" element={<Navigate to="/school-admin/academics/report-cards" replace />} />
        <Route path="examinations/class-report-cards" element={<Navigate to="/school-admin/academics/report-cards" replace />} />
        <Route path="examinations/results" element={<Navigate to="/school-admin/academics/report-cards" replace />} />
        {renderChildSubRoutes()}
        <Route path="profile" element={<Profile />} />
        <Route path="notifications" element={<Notifications />} />
        <Route path="upgrade" element={<PlanUpgrade />} />
      </Route>

      {/* Marketing landing — entry point for all visitors */}
      <Route path="/" element={(
        <Suspense fallback={(
          <div className="min-vh-100 d-flex align-items-center justify-content-center">
            <ApexLoader label="Loading…" />
          </div>
        )}
        >
          <HomeEntry />
        </Suspense>
      )}
      />
      <Route path="/terms" element={(
        <Suspense fallback={(
          <div className="min-vh-100 d-flex align-items-center justify-content-center">
            <ApexLoader label="Loading…" />
          </div>
        )}
        >
          <TermsPage />
        </Suspense>
      )}
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <AppToaster />
        <BrowserRouter>
          <AuthProvider>
            <MaintenanceProvider>
              <TenantProvider>
                <AppRoutes />
              </TenantProvider>
            </MaintenanceProvider>
          </AuthProvider>
        </BrowserRouter>
      </ThemeProvider>
    </QueryClientProvider>
  );
}

