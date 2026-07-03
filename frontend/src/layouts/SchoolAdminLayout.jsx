import { useState, useMemo } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import Sidebar from '../components/Sidebar';
import Navbar from '../components/Navbar';
import PendingApproval from '../pages/shared/PendingApproval';
import SchoolSuspended from '../pages/shared/SchoolSuspended';
import SchoolContextBanner from '../components/SchoolContextBanner';
import { buildSchoolAdminNav } from '../config/navigation';
import { useAuth } from '../hooks/useAuth';
import { useTenant } from '../hooks/useTenant';

export function SchoolAdminLayout() {
  const location = useLocation();
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const { user } = useAuth();
  const { tenant, loading: tenantLoading, moduleMenu, isSuspended } = useTenant();

  // Prefer live tenant context from DB over stale JWT user profile.
  const isPendingApproval = !isSuspended && (tenant
    ? tenant.is_verified === false && (tenant.status === 'pending' || !tenant.status)
    : Boolean(user?.tenant_is_verified === false || user?.tenant_status === 'pending'));

  const isSchoolSuspended = isSuspended
    || tenant?.is_suspended
    || tenant?.status === 'suspended'
    || user?.tenant_is_suspended
    || user?.tenant_status === 'suspended';

  const navItems = useMemo(() => buildSchoolAdminNav(moduleMenu), [moduleMenu]);
  const hasModules = (moduleMenu?.length ?? 0) > 0;
  const planSlug = tenant?.subscription?.plan_slug || user?.tenant_plan_slug;
  const planName = tenant?.subscription?.plan_name;
  const planBranding = planSlug || planName
    ? { planSlug, planName }
    : null;

  return (
    <div className={`apex-layout ${isSchoolSuspended ? 'is-school-suspended' : ''}`}>
      <Sidebar
        items={navItems}
        collapsed={sidebarCollapsed}
        mobileOpen={mobileOpen}
        disabled={isSchoolSuspended}
        planBranding={planBranding}
        onCollapsedChange={(val) => {
          if (window.innerWidth < 992) {
            setMobileOpen(!val);
          } else {
            setSidebarCollapsed(val);
          }
        }}
      />
      <div className="apex-main">
        <Navbar
          sidebarCollapsed={sidebarCollapsed}
          onMenuClick={() => setMobileOpen((open) => !open)}
          suspended={isSchoolSuspended}
        />
        {isSchoolSuspended && (
          <div className="school-suspended-banner" role="alert">
            Your school has been temporarily suspended! Contact admin to verify issue.
          </div>
        )}
        <main className={`apex-content ${isSchoolSuspended ? 'is-school-suspended' : ''}`}>
          <AnimatePresence mode="wait">
            <motion.div
              key={location.pathname}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.2 }}
            >
              {tenantLoading && !tenant ? (
                <div className="py-5 text-center">
                  <div className="spinner-border text-primary" role="status" />
                </div>
              ) : (
                <>
                  {!isSchoolSuspended && <SchoolContextBanner />}
                  {isSchoolSuspended ? (
                    <SchoolSuspended />
                  ) : isPendingApproval && !hasModules ? (
                    <PendingApproval />
                  ) : isPendingApproval ? (
                    <>
                      <div className="alert alert-warning small mb-3">
                        Your school account is awaiting final approval, but your assigned plan modules are available below.
                      </div>
                      <Outlet />
                    </>
                  ) : (
                    <Outlet />
                  )}
                </>
              )}
            </motion.div>
          </AnimatePresence>
        </main>
      </div>
    </div>
  );
}

export default SchoolAdminLayout;