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
import Staff from './pages/school-admin/Staff';
import Classes from './pages/school-admin/Classes';
import Attendance from './pages/school-admin/Attendance';
import MarksEntry from './pages/school-admin/MarksEntry';
import Finance from './pages/school-admin/Finance';
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
        <Route path="staff" element={<Gated featureKey={SCHOOL_ROUTE_FEATURES.staff}><Staff /></Gated>} />
        <Route path="classes" element={<Gated featureKey={SCHOOL_ROUTE_FEATURES.classes}><Classes /></Gated>} />
        <Route path="attendance" element={<Gated featureKey={SCHOOL_ROUTE_FEATURES.attendance}><Attendance /></Gated>} />
        <Route path="examinations/marks" element={<Gated featureKey="marks_entry"><MarksEntry /></Gated>} />
        <Route path="finance" element={<Gated featureKey={SCHOOL_ROUTE_FEATURES.finance}><Finance /></Gated>} />
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
        <Route path="settings" element={<Gated featureKey={SCHOOL_ROUTE_FEATURES.settings}><SchoolAdminSettings /></Gated>} />
        <Route path="settings/permissions" element={<Gated featureKey="roles_permissions"><PermissionSettings /></Gated>} />
        <Route path="settings/plans" element={<Gated featureKey={SCHOOL_ROUTE_FEATURES['settings/plans']}><SchoolPlansAndSubscriptions /></Gated>} />
        {renderChildSubRoutes()}
        <Route path="profile" element={<Profile />} />
        <Route path="notifications" element={<Notifications />} />
        <Route path="upgrade" element={<PlanUpgrade />} />
      </Route>

      {/* Marketing landing — entry point for all visitors */}
      <Route path="/" element={(
        <Suspense fallback={(
          <div className="min-vh-100 d-flex align-items-center justify-content-center">
            <div className="spinner-border text-primary" role="status" />
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
            <div className="spinner-border text-primary" role="status" />
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