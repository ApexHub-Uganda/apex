import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { useMaintenance } from '../hooks/useMaintenance';
import { PageSkeleton } from './LoadingSkeleton';

export function ProtectedRoute({ children, roles = [] }) {
  const { isAuthenticated, loading, user } = useAuth();
  const { maintenanceMode } = useMaintenance();
  const location = useLocation();

  if (loading) {
    return (
      <div className="p-4">
        <PageSkeleton />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (roles.length > 0 && !roles.includes(user?.role)) {
    const redirect = user?.role === 'super_admin' ? '/super-admin' : '/school-admin';
    return <Navigate to={redirect} replace />;
  }

  if (maintenanceMode && user?.role !== 'super_admin') {
    return <Navigate to="/maintenance" replace />;
  }

  return children;
}

export default ProtectedRoute;