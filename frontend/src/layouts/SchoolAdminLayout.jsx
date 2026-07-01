import { useState, useMemo } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import Sidebar from '../components/Sidebar';
import Navbar from '../components/Navbar';
import PendingApproval from '../pages/shared/PendingApproval';
import SchoolContextBanner from '../components/SchoolContextBanner';
import { buildSchoolAdminNav } from '../config/navigation';
import { useAuth } from '../hooks/useAuth';
import { useTenant } from '../hooks/useTenant';

export function SchoolAdminLayout() {
  const location = useLocation();
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const { user } = useAuth();
  const { tenant, loading: tenantLoading, navigationMenu } = useTenant();

  const isPendingApproval = user
    && (user.tenant_is_verified === false || user.tenant_status === 'pending'
      || (tenant && !tenant.is_verified));

  const navItems = useMemo(() => buildSchoolAdminNav(navigationMenu), [navigationMenu]);

  return (
    <div className="apex-layout">
      <Sidebar
        items={navItems}
        collapsed={mobileOpen ? false : sidebarCollapsed}
        onCollapsedChange={(val) => {
          if (window.innerWidth < 992) {
            setMobileOpen(!val);
          } else {
            setSidebarCollapsed(val);
          }
        }}
      />
      <div className="apex-main" style={{ marginLeft: sidebarCollapsed ? 72 : 280 }}>
        <Navbar
          sidebarCollapsed={sidebarCollapsed}
          onMenuClick={() => setMobileOpen(!mobileOpen)}
        />
        <main className="apex-content">
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
              ) : isPendingApproval ? (
                <PendingApproval />
              ) : (
                <>
                  <SchoolContextBanner />
                  <Outlet />
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