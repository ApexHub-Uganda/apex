import { Navigate } from 'react-router-dom';

/** Legacy route — staff management lives under Human Resources. */
export function Staff() {
  return <Navigate to="/school-admin/hr/staffs" replace />;
}

export default Staff;