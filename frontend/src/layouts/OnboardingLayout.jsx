import { Link, Outlet } from 'react-router-dom';
import { FiMoon, FiSun } from 'react-icons/fi';
import Logo from '../components/Logo';
import { useTheme } from '../hooks/useTheme';

export function OnboardingLayout() {
  const { theme, toggleTheme } = useTheme();

  return (
    <div className="onboarding-layout min-vh-100 d-flex flex-column">
      <header className="onboarding-header">
        <div className="container-xl d-flex align-items-center justify-content-between py-3">
          <Logo size={40} />
          <div className="d-flex align-items-center gap-2">
            <Link to="/login" className="btn btn-sm btn-outline-secondary d-none d-sm-inline-flex">
              Sign in
            </Link>
            <button
              type="button"
              className="btn btn-sm btn-outline-secondary border-0"
              onClick={toggleTheme}
              title="Toggle theme"
            >
              {theme === 'light' ? <FiMoon size={16} /> : <FiSun size={16} />}
            </button>
          </div>
        </div>
      </header>

      <main className="onboarding-main flex-grow-1">
        <Outlet />
      </main>

      <footer className="onboarding-footer py-4">
        <div className="container-xl text-center text-muted small">
          © {new Date().getFullYear()} Apex Hub · School management made simple
        </div>
      </footer>
    </div>
  );
}

export default OnboardingLayout;