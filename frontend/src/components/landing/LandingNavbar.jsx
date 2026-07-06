import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { AnimatePresence, motion } from 'framer-motion';
import { FiSun, FiMoon } from 'react-icons/fi';
import Logo from '../Logo';
import { NAV_LINKS } from '../../pages/landing/landingData';

export function LandingNavbar({ theme, onToggleTheme }) {
  const [scrolled, setScrolled] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 40);
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  useEffect(() => {
    document.body.style.overflow = menuOpen ? 'hidden' : '';
    return () => { document.body.style.overflow = ''; };
  }, [menuOpen]);

  const handleNavClick = () => setMenuOpen(false);

  return (
    <>
      <header
        className={`lp-navbar ${scrolled ? 'is-scrolled' : 'is-transparent'}`}
        role="banner"
      >
        <div className="lp-container lp-navbar-inner">
          <a href="#home" className="lp-logo-link" aria-label="Apex Hub home">
            <Logo size={36} />
          </a>

          <nav aria-label="Main navigation">
            <ul className="lp-nav-links d-none d-lg-flex">
              {NAV_LINKS.map((link) => (
                <li key={link.href}>
                  <a href={link.href}>{link.label}</a>
                </li>
              ))}
            </ul>
          </nav>

          <div className="lp-nav-actions">
            <button
              type="button"
              className="lp-btn lp-btn-ghost d-none d-md-inline-flex"
              onClick={onToggleTheme}
              aria-label={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
            >
              {theme === 'dark' ? <FiSun size={18} /> : <FiMoon size={18} />}
            </button>
            <Link to="/login" className="lp-btn lp-btn-secondary d-none d-md-inline-flex">Login</Link>
            <Link to="/login" className="lp-btn lp-btn-primary d-none d-md-inline-flex">Get Started</Link>
            {!menuOpen && (
              <button
                type="button"
                className="lp-hamburger d-lg-none"
                onClick={() => setMenuOpen(true)}
                aria-label="Open menu"
                aria-expanded={false}
              >
                <span /><span /><span />
              </button>
            )}
          </div>
        </div>
      </header>

      <AnimatePresence>
        {menuOpen && (
          <>
            <motion.button
              type="button"
              className="lp-mobile-menu-backdrop d-lg-none"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.25 }}
              onClick={() => setMenuOpen(false)}
              aria-label="Close menu"
            />
            <motion.nav
              className="lp-mobile-menu d-lg-none"
              initial={{ opacity: 0, x: '100%' }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: '100%' }}
              transition={{ duration: 0.3 }}
              aria-label="Mobile navigation"
            >
              <div className="lp-mobile-menu-header">
                <a href="#home" className="lp-mobile-menu-brand" onClick={handleNavClick}>
                  <Logo size={32} />
                </a>
                <button
                  type="button"
                  className="lp-hamburger is-open"
                  onClick={() => setMenuOpen(false)}
                  aria-label="Close menu"
                >
                  <span /><span /><span />
                </button>
              </div>
              <div className="lp-mobile-menu-links">
                {NAV_LINKS.map((link) => (
                  <a key={link.href} href={link.href} onClick={handleNavClick}>{link.label}</a>
                ))}
                <Link to="/login" onClick={handleNavClick}>Login</Link>
              </div>
              <div className="lp-mobile-menu-actions">
                <Link to="/login" className="lp-btn lp-btn-primary lp-mobile-menu-cta" onClick={handleNavClick}>
                  Get Started
                </Link>
              </div>
            </motion.nav>
          </>
        )}
      </AnimatePresence>
    </>
  );
}

export default LandingNavbar;