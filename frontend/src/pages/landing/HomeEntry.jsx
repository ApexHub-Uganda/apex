import { Navigate } from 'react-router-dom';
import { useAuthContext } from '../../context/AuthContext';
import LandingPage from './LandingPage';

/** Public home — redirects authenticated users to their portal. */
export function HomeEntry() {
  const { isAuthenticated, loading, isSuperAdmin, isSchoolPortalUser } = useAuthContext();

  if (loading) {
    return <LandingPage />;
  }

  if (isAuthenticated) {
    if (isSuperAdmin) {
      return <Navigate to="/super-admin" replace />;
    }
    if (isSchoolPortalUser) {
      return <Navigate to="/school-admin" replace />;
    }
  }

  return <LandingPage />;
}

export default HomeEntry;