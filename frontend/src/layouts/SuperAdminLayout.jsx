import { useState } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import Sidebar from '../components/Sidebar';
import Navbar from '../components/Navbar';
import { superAdminNav } from '../config/navigation';
import MaintenanceBanner from '../components/MaintenanceBanner';

export function SuperAdminLayout() {
  const location = useLocation();
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <div className="apex-layout">
      <Sidebar
        items={superAdminNav}
        collapsed={sidebarCollapsed}
        mobileOpen={mobileOpen}
        onCollapsedChange={(val) => {
          if (window.innerWidth < 992) {
            setMobileOpen(!val);
          } else {
            setSidebarCollapsed(val);
          }
        }}
      />
      <div className="apex-main">
        <MaintenanceBanner />
        <Navbar
          sidebarCollapsed={sidebarCollapsed}
          mobileMenuOpen={mobileOpen}
          onMenuClick={() => setMobileOpen(!mobileOpen)}
        />
        <main className={`apex-content${location.pathname.includes('/plans/') && (location.pathname.endsWith('/edit') || location.pathname.endsWith('/new')) ? ' is-plan-editor' : ''}`}>
          <AnimatePresence mode="wait">
            <motion.div
              key={location.pathname}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.2 }}
            >
              <Outlet />
            </motion.div>
          </AnimatePresence>
        </main>
      </div>
    </div>
  );
}

export default SuperAdminLayout;