import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { FiTool } from 'react-icons/fi';
import { useAuth } from '../../hooks/useAuth';

export function Maintenance() {
  const { logout, isAuthenticated } = useAuth();

  const handleSignOut = async () => {
    await logout();
  };

  return (
    <div className="maintenance-page d-flex align-items-center justify-content-center min-vh-100 p-4">
      <motion.div
        className="apex-card p-5 text-center maintenance-card"
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <div className="maintenance-icon mb-3">
          <FiTool size={36} />
        </div>
        <h1 className="fw-bold h4 mb-2">Under maintenance</h1>
        <p className="text-muted mb-4">
          Apex Hub is currently under maintenance. Please try again later.
        </p>
        {isAuthenticated ? (
          <button type="button" className="btn btn-outline-secondary btn-sm" onClick={handleSignOut}>
            Sign out
          </button>
        ) : (
          <Link to="/login" className="btn btn-outline-secondary btn-sm">
            Back to login
          </Link>
        )}
      </motion.div>
    </div>
  );
}

export default Maintenance;