import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { FiArrowRight, FiUsers } from 'react-icons/fi';
import { classAttendanceService } from '../services/moduleService';
import ModuleEmptyState from './ModuleEmptyState';

export function TeacherAttendancePanel() {
  const { data: options, isLoading } = useQuery({
    queryKey: ['class-attendance-dashboard'],
    queryFn: () => classAttendanceService.getOptions(),
    staleTime: 60_000,
  });

  const classes = options?.classes || [];

  return (
    <div className="apex-card p-4 h-100">
      <div className="d-flex align-items-center justify-content-between mb-3">
        <div>
          <h5 className="fw-bold mb-1">Mark Student Attendance</h5>
          <p className="text-muted small mb-0">Choose a class to record today&apos;s attendance</p>
        </div>
        <Link to="/school-admin/attendance" className="btn btn-sm btn-outline-primary">
          Open <FiArrowRight size={14} className="ms-1" />
        </Link>
      </div>

      {isLoading ? (
        <div className="py-4 text-center"><div className="spinner-border spinner-border-sm text-primary" role="status" /></div>
      ) : classes.length === 0 ? (
        <ModuleEmptyState
          title="No classes assigned"
          message="Your teaching assignments do not include any classes for attendance marking yet."
        />
      ) : (
        <div className="row g-2">
          {classes.map((classRow) => (
            <div className="col-sm-6" key={classRow.value}>
              <Link
                to={`/school-admin/attendance?class=${classRow.value}`}
                className="text-decoration-none"
              >
                <div className="border rounded-3 p-3 h-100 bg-light-subtle teacher-attendance-class-card">
                  <div className="d-flex align-items-start gap-2">
                    <span className="assignment-workflow-icon flex-shrink-0">
                      <FiUsers size={16} />
                    </span>
                    <div>
                      <div className="fw-semibold small">{classRow.label}</div>
                      <div className="text-muted" style={{ fontSize: '0.75rem' }}>
                        {classRow.student_count} students
                        {classRow.has_streams ? ` · ${classRow.stream_count} streams` : ''}
                      </div>
                    </div>
                  </div>
                </div>
              </Link>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default TeacherAttendancePanel;