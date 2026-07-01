import { Outlet } from 'react-router-dom';
import { motion } from 'framer-motion';
import Logo from '../components/Logo';
import { useTheme } from '../hooks/useTheme';
import { FiSun, FiMoon } from 'react-icons/fi';

export function AuthLayout() {
  const { theme, toggleTheme } = useTheme();

  return (
    <div className="min-vh-100 position-relative d-flex align-items-center justify-content-center p-3">
      <div className="auth-bg">
        <div className="auth-bg-gradient" />
        <div className="auth-bg-orbs">
          <div className="auth-orb auth-orb-1" />
          <div className="auth-orb auth-orb-2" />
          <div className="auth-orb auth-orb-3" />
        </div>
      </div>

      <button
        className="btn btn-sm position-absolute apex-glass"
        onClick={toggleTheme}
        style={{ top: 20, right: 20, zIndex: 10, border: 'none' }}
        title="Toggle theme"
      >
        {theme === 'light' ? <FiMoon /> : <FiSun />}
      </button>

      <motion.div
        className="w-100"
        style={{ maxWidth: 440, zIndex: 1 }}
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <div className="text-center mb-4">
          <Logo size={48} className="justify-content-center" />
        </div>
        <Outlet />
      </motion.div>
    </div>
  );
}

export default AuthLayout;