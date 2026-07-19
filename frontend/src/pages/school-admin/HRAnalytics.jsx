import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { FiArrowLeft } from 'react-icons/fi';
import PageHeader from '../../components/PageHeader';
import { hrAnalyticsService } from '../../services/moduleService';
import { usePermissions } from '../../hooks/usePermissions';
import { ApexLoader } from '../../components/ApexLoader';

function StatCard({ label, value }) {
  return (
    <div className="apex-card p-3">
      <div className="text-muted small">{label}</div>
      <div className="fs-4 fw-bold">{value ?? 0}</div>
    </div>
  );
}

export function HRAnalytics() {
  const { canReadFeature } = usePermissions();
  const { data, isLoading, isError } = useQuery({
    queryKey: ['hr-analytics'],
    queryFn: () => hrAnalyticsService.get(),
    enabled: canReadFeature('hr_analytics'),
  });

  const summary = data?.summary || {};
  const leaveByType = data?.leave_by_type || [];
  const staffByStatus = data?.staff_by_status || [];

  return (
    <div>
      <div className="mb-3">
        <Link to="/school-admin/hr" className="small text-decoration-none text-muted">
          <FiArrowLeft className="me-1" /> Human Resources
        </Link>
      </div>

      <PageHeader title="HR Analytics" subtitle="Staff, leave, and performance KPIs" />

      {isError && <div className="alert alert-danger">Unable to load HR analytics.</div>}

      {isLoading ? (
        <div className="py-5 text-center"><ApexLoader label="Loading…" /></div>
      ) : (
        <>
          <div className="row g-3 mb-4">
            {Object.entries(summary).map(([key, value]) => (
              <div key={key} className="col-6 col-md-3">
                <StatCard label={key.replace(/_/g, ' ')} value={value} />
              </div>
            ))}
          </div>

          <div className="row g-3">
            <div className="col-md-6">
              <div className="apex-card p-3">
                <h6 className="fw-semibold mb-3">Leave by type</h6>
                {leaveByType.length === 0 ? (
                  <p className="small text-muted mb-0">No leave data.</p>
                ) : (
                  <table className="table table-sm mb-0">
                    <tbody>
                      {leaveByType.map((row) => (
                        <tr key={row.leave_type}>
                          <td className="text-capitalize">{row.leave_type}</td>
                          <td className="text-end">{row.count}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            </div>
            <div className="col-md-6">
              <div className="apex-card p-3">
                <h6 className="fw-semibold mb-3">Staff by status</h6>
                {staffByStatus.length === 0 ? (
                  <p className="small text-muted mb-0">No staff data.</p>
                ) : (
                  <table className="table table-sm mb-0">
                    <tbody>
                      {staffByStatus.map((row) => (
                        <tr key={row.status}>
                          <td className="text-capitalize">{row.status}</td>
                          <td className="text-end">{row.count}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

export default HRAnalytics;