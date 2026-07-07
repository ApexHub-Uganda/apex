import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { FiArrowLeft } from 'react-icons/fi';
import PageHeader from '../../components/PageHeader';
import ModuleEmptyState from '../../components/ModuleEmptyState';
import { financeAnalyticsService } from '../../services/moduleService';

const formatUGX = (amount) => {
  const n = Number(amount);
  if (Number.isNaN(n)) return '—';
  return `UGX ${n.toLocaleString('en-UG', { minimumFractionDigits: 0 })}`;
};

export function FinanceAnalytics() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['finance-analytics'],
    queryFn: () => financeAnalyticsService.get(),
    staleTime: 30_000,
  });

  const summary = data?.summary || {};
  const methods = data?.collections_by_method || [];
  const monthly = data?.monthly_collections || [];

  return (
    <div>
      <div className="mb-3">
        <Link to="/school-admin/finance" className="small text-decoration-none text-muted">
          <FiArrowLeft className="me-1" /> Finance
        </Link>
      </div>

      <PageHeader title="Finance Analytics" subtitle="Collection KPIs and revenue trends" />

      {isError && <div className="alert alert-danger">Unable to load finance analytics.</div>}

      {isLoading ? (
        <div className="py-5 text-center"><div className="spinner-border text-primary" role="status" /></div>
      ) : (
        <>
          <div className="row g-3 mb-4">
            {[
              { label: 'Total Collected', value: formatUGX(summary.total_collected) },
              { label: 'Collected Today', value: formatUGX(summary.collected_today) },
              { label: 'This Month', value: formatUGX(summary.collected_this_month) },
              { label: 'Outstanding', value: formatUGX(summary.outstanding_balance) },
              { label: 'Debtors', value: summary.debtor_count ?? 0 },
              { label: 'Open Invoices', value: summary.open_invoices ?? 0 },
            ].map((card) => (
              <div key={card.label} className="col-md-4 col-lg-2">
                <div className="apex-card p-3 h-100">
                  <div className="small text-muted">{card.label}</div>
                  <div className="fw-semibold fs-5 mt-1">{card.value}</div>
                </div>
              </div>
            ))}
          </div>

          <div className="row g-3">
            <div className="col-lg-6">
              <div className="apex-card p-3 p-md-4">
                <h6 className="fw-semibold mb-3">Collections by Method</h6>
                {methods.length === 0 ? (
                  <ModuleEmptyState title="No payment data" message="Approved payments will appear here." />
                ) : (
                  <div className="table-responsive">
                    <table className="table table-sm mb-0">
                      <thead><tr><th>Method</th><th>Total</th><th>Count</th></tr></thead>
                      <tbody>
                        {methods.map((row) => (
                          <tr key={row.payment_method}>
                            <td className="text-capitalize">{row.payment_method}</td>
                            <td>{formatUGX(row.total)}</td>
                            <td>{row.count}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </div>
            <div className="col-lg-6">
              <div className="apex-card p-3 p-md-4">
                <h6 className="fw-semibold mb-3">Monthly Collections</h6>
                {monthly.length === 0 ? (
                  <ModuleEmptyState title="No trend data" message="Monthly collection trends will build over time." />
                ) : (
                  <div className="table-responsive">
                    <table className="table table-sm mb-0">
                      <thead><tr><th>Month</th><th>Total</th><th>Payments</th></tr></thead>
                      <tbody>
                        {monthly.map((row) => (
                          <tr key={row.month}>
                            <td>{row.month}</td>
                            <td>{formatUGX(row.total)}</td>
                            <td>{row.count}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

export default FinanceAnalytics;