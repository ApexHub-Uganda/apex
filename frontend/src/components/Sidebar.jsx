import { NavLink, useLocation } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { FiChevronLeft, FiChevronRight } from 'react-icons/fi';
import { useState } from 'react';
import Logo from './Logo';

export function Sidebar({ items, collapsed: controlledCollapsed, onCollapsedChange }) {
  const [internalCollapsed, setInternalCollapsed] = useState(false);
  const collapsed = controlledCollapsed ?? internalCollapsed;
  const setCollapsed = onCollapsedChange ?? setInternalCollapsed;
  const location = useLocation();

  return (
    <>
      <AnimatePresence>
        {!collapsed && (
          <motion.div
            className="apex-sidebar-overlay d-lg-none"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setCollapsed(true)}
            style={{
              position: 'fixed',
              inset: 0,
              background: 'rgba(0,0,0,0.5)',
              zIndex: 1039,
            }}
          />
        )}
      </AnimatePresence>

      <motion.aside
        className="apex-sidebar"
        animate={{ width: collapsed ? 72 : 280 }}
        transition={{ duration: 0.25 }}
        style={{
          position: 'fixed',
          top: 0,
          left: 0,
          height: '100vh',
          width: collapsed ? 72 : 280,
          background: 'linear-gradient(180deg, var(--apex-primary) 0%, var(--apex-primary-dark) 100%)',
          zIndex: 1040,
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
        }}
      >
        <div className="p-3 d-flex align-items-center justify-content-between" style={{ minHeight: 64 }}>
          {!collapsed && <Logo size={36} showText />}
          {collapsed && <Logo size={36} showText={false} />}
          <button
            className="btn btn-sm text-white border-0 d-none d-lg-flex"
            onClick={() => setCollapsed(!collapsed)}
            style={{ background: 'rgba(255,255,255,0.1)' }}
          >
            {collapsed ? <FiChevronRight /> : <FiChevronLeft />}
          </button>
        </div>

        <nav className="flex-grow-1 overflow-auto px-2 py-2">
          {items.map((item) => {
            if (item.divider) {
              return !collapsed ? (
                <div key={item.label} className="text-white-50 small fw-bold text-uppercase px-3 py-2 mt-2" style={{ fontSize: '0.65rem', letterSpacing: '0.08em' }}>
                  {item.label}
                </div>
              ) : <hr key={item.label} className="border-white border-opacity-25 my-2" />;
            }

            const isActive = location.pathname === item.path || location.pathname.startsWith(item.path + '/');

            return (
              <NavLink
                key={item.path}
                to={item.path}
                className={`apex-sidebar-link d-flex align-items-center gap-3 px-3 py-2 mb-1 text-decoration-none ${isActive ? 'active' : ''}`}
                style={{
                  borderRadius: 10,
                  color: isActive ? '#fff' : 'rgba(255,255,255,0.75)',
                  background: isActive ? 'rgba(255,255,255,0.15)' : 'transparent',
                  transition: 'all 0.2s',
                  fontSize: '0.875rem',
                  fontWeight: isActive ? 600 : 500,
                }}
                title={collapsed ? item.label : undefined}
              >
                {item.icon && <span style={{ fontSize: '1.15rem', minWidth: 24 }}>{item.icon}</span>}
                {!collapsed && <span>{item.label}</span>}
                {!collapsed && item.badge && (
                  <span className="ms-auto badge rounded-pill" style={{ background: 'var(--apex-secondary)', fontSize: '0.65rem' }}>
                    {item.badge}
                  </span>
                )}
              </NavLink>
            );
          })}
        </nav>

        {!collapsed && (
          <div className="p-3 text-white-50 small text-center border-top border-white border-opacity-10">
            Apex Hub v1.0
          </div>
        )}
      </motion.aside>
    </>
  );
}

export default Sidebar;