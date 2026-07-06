import { NavLink, useLocation } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { FiChevronLeft, FiChevronRight, FiChevronDown } from 'react-icons/fi';
import { useState, useEffect, useCallback, useRef, useId } from 'react';
import Logo from './Logo';
import PlanNameWithBadge from './PlanNameWithBadge';

export const SIDEBAR_WIDTH_EXPANDED = 280;
export const SIDEBAR_WIDTH_COLLAPSED = 72;

const MOBILE_BREAKPOINT = 992;
const FLYOUT_CLOSE_DELAY_MS = 320;

function useIsMobile() {
  const [isMobile, setIsMobile] = useState(
    () => typeof window !== 'undefined' && window.innerWidth < MOBILE_BREAKPOINT,
  );

  useEffect(() => {
    const onResize = () => setIsMobile(window.innerWidth < MOBILE_BREAKPOINT);
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, []);

  return isMobile;
}

function findActiveParentPath(pathname, items, getSubLinks) {
  for (const item of items) {
    if (item.divider || !item.path) continue;
    const subLinks = getSubLinks(item);
    if (subLinks.length === 0) continue;
    if (pathname === item.path || pathname.startsWith(`${item.path}/`)) {
      return item.path;
    }
  }
  return null;
}

function CollapsedFlyout({
  item,
  subLinks,
  location,
  anchorRef,
  onClose,
  onHoverStart,
  onHoverEnd,
}) {
  const [top, setTop] = useState(0);
  const flyoutRef = useRef(null);

  useEffect(() => {
    if (!anchorRef.current) return;
    const rect = anchorRef.current.getBoundingClientRect();
    const maxTop = window.innerHeight - 320;
    setTop(Math.min(rect.top, maxTop));
  }, [anchorRef]);

  useEffect(() => {
    const handlePointer = (event) => {
      if (
        flyoutRef.current?.contains(event.target)
        || anchorRef.current?.contains(event.target)
      ) return;
      onClose();
    };
    const handleKey = (event) => {
      if (event.key === 'Escape') onClose();
    };
    document.addEventListener('mousedown', handlePointer);
    document.addEventListener('touchstart', handlePointer);
    document.addEventListener('keydown', handleKey);
    return () => {
      document.removeEventListener('mousedown', handlePointer);
      document.removeEventListener('touchstart', handlePointer);
      document.removeEventListener('keydown', handleKey);
    };
  }, [anchorRef, onClose]);

  return (
    <motion.div
      ref={flyoutRef}
      className="apex-sidebar-flyout"
      role="menu"
      initial={{ opacity: 0, x: -6 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -6 }}
      transition={{ duration: 0.16, ease: [0.4, 0, 0.2, 1] }}
      style={{ top }}
      onMouseEnter={onHoverStart}
      onMouseLeave={onHoverEnd}
    >
      <div className="apex-sidebar-flyout-title">{item.label}</div>
      <div className="apex-sidebar-flyout-links">
        {subLinks.map((child) => {
          const childActive = location.pathname === child.path
            || location.pathname.startsWith(`${child.path}/`);
          const ChildIcon = child.icon;
          return (
              <NavLink
                key={`${item.path}-${child.feature_key}`}
                to={child.path}
                role="menuitem"
                className={`apex-sidebar-flyout-link ${childActive ? 'active' : ''}`}
                onClick={onClose}
              >
                {ChildIcon && (
                  <span className="apex-sidebar-flyout-link-icon">
                    {typeof ChildIcon === 'function' ? <ChildIcon size={14} /> : ChildIcon}
                  </span>
                )}
                <span>{child.label}</span>
              </NavLink>
          );
        })}
      </div>
    </motion.div>
  );
}

function DisabledNavLink({ className, children, title }) {
  return (
    <span className={`${className} is-disabled`} aria-disabled="true" title={title}>
      {children}
    </span>
  );
}

function NavItem({
  item,
  collapsed,
  isMobile,
  location,
  expandedKeys,
  onParentToggle,
  flyoutPath,
  onFlyoutOpen,
  onFlyoutClose,
  onFlyoutHoverStart,
  onFlyoutHoverEnd,
  onLeafNavigate,
  disabled = false,
  getSubLinks,
}) {
  const itemRef = useRef(null);
  const submenuId = useId();

  if (item.divider) {
    return !collapsed ? (
      <div className="apex-sidebar-divider">{item.label}</div>
    ) : <hr className="apex-sidebar-divider-line" />;
  }

  const subLinks = getSubLinks(item);
  const hasChildren = subLinks.length > 0;
  const isParentActive = location.pathname === item.path
    || location.pathname.startsWith(`${item.path}/`);
  const isChildActive = subLinks.some(
    (child) => location.pathname === child.path || location.pathname.startsWith(`${child.path}/`),
  );
  const isActive = isParentActive || isChildActive;
  const isExpanded = !collapsed && expandedKeys.has(item.path);
  const showFlyout = collapsed && !isMobile && hasChildren && flyoutPath === item.path;

  const handleParentClick = () => {
    if (disabled || !hasChildren) return;
    onParentToggle(item.path);
  };

  const handleParentKeyDown = (event) => {
    if (disabled || !hasChildren) return;
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      onParentToggle(item.path);
    }
  };

  const openFlyout = () => {
    if (disabled || !(collapsed && !isMobile && hasChildren)) return;
    onFlyoutHoverStart();
    onFlyoutOpen(item.path);
  };

  const parentContent = (
    <>
      {item.icon && <span className="apex-sidebar-link-icon">{item.icon}</span>}
      {!collapsed && <span className="apex-sidebar-link-label">{item.label}</span>}
      {!collapsed && item.badge != null && item.badge > 0 && (
        <span className="apex-sidebar-badge">{item.badge}</span>
      )}
      {!collapsed && hasChildren && (
        <span className={`apex-sidebar-chevron ${isExpanded ? 'is-expanded' : ''}`} aria-hidden>
          <FiChevronDown size={16} />
        </span>
      )}
    </>
  );

  return (
    <div
      ref={itemRef}
      className={`apex-sidebar-item ${isActive ? 'is-active' : ''} ${isExpanded ? 'is-expanded' : ''} ${disabled ? 'is-disabled' : ''}`}
    >
      {disabled ? (
        <DisabledNavLink
          className={`apex-sidebar-link ${isActive ? 'active' : ''}`}
          title={item.label}
        >
          {parentContent}
        </DisabledNavLink>
      ) : hasChildren && !collapsed ? (
        <button
          type="button"
          className={`apex-sidebar-link apex-sidebar-parent ${isActive ? 'active' : ''}`}
          onClick={handleParentClick}
          onKeyDown={handleParentKeyDown}
          aria-expanded={isExpanded}
          aria-controls={submenuId}
          title={item.label}
        >
          {parentContent}
        </button>
      ) : hasChildren && collapsed ? (
        <button
          type="button"
          className={`apex-sidebar-link ${isActive ? 'active' : ''}`}
          title={item.label}
          aria-label={item.label}
          aria-expanded={showFlyout}
          aria-haspopup="menu"
          onMouseEnter={openFlyout}
          onMouseLeave={onFlyoutHoverEnd}
          onFocus={openFlyout}
          onClick={() => (showFlyout ? onFlyoutClose() : onFlyoutOpen(item.path))}
        >
          {parentContent}
        </button>
      ) : (
        <NavLink
          to={item.path}
          className={({ isActive: linkActive }) => (
            `apex-sidebar-link ${linkActive || isActive ? 'active' : ''}`
          )}
          title={collapsed ? item.label : undefined}
          onClick={onLeafNavigate}
        >
          {parentContent}
        </NavLink>
      )}

      <div
        id={submenuId}
        className={`apex-sidebar-submenu ${isExpanded ? 'is-expanded' : ''}`}
        aria-hidden={!isExpanded}
      >
        <div className="apex-sidebar-submenu-inner">
          {subLinks.map((child) => {
            const childPath = child.path;
            const childActive = location.pathname === childPath
              || location.pathname.startsWith(`${childPath}/`);
            const ChildIcon = child.icon;
            if (disabled) {
              return (
                <DisabledNavLink
                  key={`${item.path}-${child.feature_key}`}
                  className={`apex-sidebar-sublink ${childActive ? 'active' : ''}`}
                  title={child.label}
                >
                  {ChildIcon && (
                    <span className="apex-sidebar-sublink-icon">
                      {typeof ChildIcon === 'function' ? <ChildIcon size={14} /> : ChildIcon}
                    </span>
                  )}
                  <span>{child.label}</span>
                </DisabledNavLink>
              );
            }
            return (
              <NavLink
                key={`${item.path}-${child.feature_key}`}
                to={childPath}
                className={`apex-sidebar-sublink ${childActive ? 'active' : ''}`}
                onClick={onLeafNavigate}
              >
                {ChildIcon && (
                  <span className="apex-sidebar-sublink-icon">
                    {typeof ChildIcon === 'function' ? <ChildIcon size={14} /> : ChildIcon}
                  </span>
                )}
                <span>{child.label}</span>
              </NavLink>
            );
          })}
        </div>
      </div>

      <AnimatePresence>
        {showFlyout && !disabled && (
          <CollapsedFlyout
            item={item}
            subLinks={subLinks}
            location={location}
            anchorRef={itemRef}
            onClose={onFlyoutClose}
            onHoverStart={onFlyoutHoverStart}
            onHoverEnd={onFlyoutHoverEnd}
          />
        )}
      </AnimatePresence>
    </div>
  );
}

export function Sidebar({
  items,
  collapsed: controlledCollapsed,
  onCollapsedChange,
  mobileOpen = false,
  disabled = false,
  planBranding = null,
  getSubLinks: getSubLinksProp,
}) {
  const [internalCollapsed, setInternalCollapsed] = useState(false);
  const collapsed = controlledCollapsed ?? internalCollapsed;
  const setCollapsed = onCollapsedChange ?? setInternalCollapsed;
  const location = useLocation();
  const isMobile = useIsMobile();
  const [expandedKeys, setExpandedKeys] = useState(() => new Set());
  const [flyoutPath, setFlyoutPath] = useState(null);
  const sidebarRef = useRef(null);
  const flyoutCloseTimerRef = useRef(null);
  const lastPathnameRef = useRef(location.pathname);
  const resolveSubLinks = useCallback(
    (item) => {
      if (getSubLinksProp) return getSubLinksProp(item);
      return item.children || [];
    },
    [getSubLinksProp],
  );

  const lastActiveParentRef = useRef(findActiveParentPath(location.pathname, items, resolveSubLinks));

  const showCollapsed = isMobile ? false : collapsed;
  const sidebarWidth = isMobile
    ? (mobileOpen ? SIDEBAR_WIDTH_EXPANDED : 0)
    : (collapsed ? SIDEBAR_WIDTH_COLLAPSED : SIDEBAR_WIDTH_EXPANDED);

  useEffect(() => {
    document.documentElement.style.setProperty(
      '--apex-sidebar-current-width',
      `${isMobile ? 0 : (collapsed ? SIDEBAR_WIDTH_COLLAPSED : SIDEBAR_WIDTH_EXPANDED)}px`,
    );
  }, [collapsed, isMobile]);

  useEffect(() => {
    const activeParent = findActiveParentPath(location.pathname, items, resolveSubLinks);
    const pathChanged = lastPathnameRef.current !== location.pathname;
    const prevActiveParent = lastActiveParentRef.current;

    if (!pathChanged) {
      if (activeParent) {
        setExpandedKeys((prev) => (prev.size === 0 ? new Set([activeParent]) : prev));
      }
      lastActiveParentRef.current = activeParent;
      return;
    }

    if (isMobile) {
      setCollapsed(true);
      setFlyoutPath(null);
    }

    if (!activeParent) {
      setExpandedKeys(new Set());
    } else if (prevActiveParent !== activeParent) {
      setExpandedKeys((prev) => (prev.size === 0 ? new Set([activeParent]) : prev));
    }

    lastPathnameRef.current = location.pathname;
    lastActiveParentRef.current = activeParent;
  }, [location.pathname, items, resolveSubLinks, isMobile, setCollapsed]);

  useEffect(() => {
    setFlyoutPath(null);
  }, [collapsed, location.pathname]);

  const onParentToggle = useCallback((path) => {
    setExpandedKeys((prev) => {
      if (prev.has(path)) return new Set();
      return new Set([path]);
    });
  }, []);

  const cancelFlyoutClose = useCallback(() => {
    if (flyoutCloseTimerRef.current) {
      clearTimeout(flyoutCloseTimerRef.current);
      flyoutCloseTimerRef.current = null;
    }
  }, []);

  const scheduleFlyoutClose = useCallback(() => {
    cancelFlyoutClose();
    flyoutCloseTimerRef.current = setTimeout(() => {
      setFlyoutPath(null);
      flyoutCloseTimerRef.current = null;
    }, FLYOUT_CLOSE_DELAY_MS);
  }, [cancelFlyoutClose]);

  const onFlyoutOpen = useCallback((path) => {
    cancelFlyoutClose();
    setFlyoutPath(path);
  }, [cancelFlyoutClose]);

  const onFlyoutClose = useCallback(() => {
    cancelFlyoutClose();
    setFlyoutPath(null);
  }, [cancelFlyoutClose]);

  useEffect(() => () => cancelFlyoutClose(), [cancelFlyoutClose]);

  const closeSidebar = useCallback(() => {
    setCollapsed(true);
  }, [setCollapsed]);

  const onLeafNavigate = useCallback(() => {
    setExpandedKeys(new Set());
    onFlyoutClose();
    if (isMobile) closeSidebar();
  }, [isMobile, closeSidebar, onFlyoutClose]);

  return (
    <>
      <AnimatePresence>
        {isMobile && mobileOpen && (
          <motion.div
            className="apex-sidebar-overlay"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            onClick={closeSidebar}
            aria-hidden
          />
        )}
      </AnimatePresence>

      <motion.aside
        ref={sidebarRef}
        className={`apex-sidebar ${showCollapsed ? 'is-collapsed' : ''} ${isMobile ? 'is-mobile' : ''} ${disabled ? 'is-disabled' : ''}`}
        animate={{
          width: sidebarWidth,
          x: isMobile && !mobileOpen ? -SIDEBAR_WIDTH_EXPANDED : 0,
        }}
        transition={{ duration: 0.28, ease: [0.4, 0, 0.2, 1] }}
        onMouseEnter={() => {
          if (showCollapsed && !isMobile) cancelFlyoutClose();
        }}
        onMouseLeave={() => {
          if (showCollapsed && !isMobile && flyoutPath) scheduleFlyoutClose();
        }}
      >
        <div className="apex-sidebar-header">
          {!showCollapsed && <Logo size={36} showText />}
          {showCollapsed && <Logo size={36} showText={false} />}
          {isMobile ? (
            <button
              type="button"
              className="apex-sidebar-collapse-btn"
              onClick={closeSidebar}
              aria-label="Close menu"
            >
              <FiChevronLeft size={18} />
            </button>
          ) : (
            <button
              type="button"
              className="apex-sidebar-collapse-btn"
              onClick={() => setCollapsed(!collapsed)}
              aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            >
              {collapsed ? <FiChevronRight size={18} /> : <FiChevronLeft size={18} />}
            </button>
          )}
        </div>

        {planBranding && !showCollapsed && (
          <div className="apex-sidebar-plan">
            <div className="apex-sidebar-plan-chip apex-faint-outline-chip">
              <PlanNameWithBadge
                planSlug={planBranding.planSlug}
                planName={planBranding.planName}
                size="sm"
              />
            </div>
          </div>
        )}

        <nav className="apex-sidebar-nav" aria-label="Main navigation">
          {items.map((item) => (
            <NavItem
              key={item.path || item.label}
              item={item}
              collapsed={showCollapsed}
              isMobile={isMobile}
              location={location}
              expandedKeys={expandedKeys}
              onParentToggle={onParentToggle}
              flyoutPath={flyoutPath}
              onFlyoutOpen={onFlyoutOpen}
              onFlyoutClose={onFlyoutClose}
              onFlyoutHoverStart={cancelFlyoutClose}
              onFlyoutHoverEnd={scheduleFlyoutClose}
              onLeafNavigate={onLeafNavigate}
              disabled={disabled}
              getSubLinks={resolveSubLinks}
            />
          ))}
        </nav>

        {!showCollapsed && (
          <div className="apex-sidebar-footer">
            Apex Hub v1.0
          </div>
        )}
      </motion.aside>
    </>
  );
}

export default Sidebar;