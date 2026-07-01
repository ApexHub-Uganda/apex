import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { PageSkeleton } from './LoadingSkeleton';

export function ProtectedRoute({ children, roles = [] }) {
  const { isAuthenticated, loading, user } = useAuth();
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

  return children;
}

export default ProtectedRoute;