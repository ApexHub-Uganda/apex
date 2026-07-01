import ModulePage from '../../components/ModulePage';
import StatusBadge from '../../components/StatusBadge';
import { subscriptionsService } from '../../services/moduleService';

const formatDate = (value) => {
  if (!value) return '—';
  return new Date(value).toLocaleDateString();
};

export function Subscriptions() {
  return (
    <ModulePage
      title="Subscriptions"
      subtitle="Monitor school subscription status and billing"
      queryKey={['subscriptions']}
      fetchData={() => subscriptionsService.list({ page_size: 100 })}
      readOnly
      columns={[
        { key: 'school', label: 'School', accessor: 'school', sortable: true },
        { key: 'plan', label: 'Plan', accessor: 'plan' },
        { key: 'amount', label: 'Amount', render: (row) => `$${Number(row.amount || 0).toFixed(2)}/mo` },
        { key: 'billing_cycle', label: 'Billing', accessor: 'billing_cycle' },
        { key: 'status', label: 'Status', render: (row) => <StatusBadge status={row.status} /> },
        { key: 'next_billing', label: 'Next Billing', render: (row) => formatDate(row.next_billing) },
        { key: 'auto_renew', label: 'Auto Renew', render: (row) => (row.auto_renew ? 'Yes' : 'No') },
      ]}
      extraActions={(row, { refetch }) => (
        <>
          {row.status !== 'active' && (
            <button
              className="btn btn-sm btn-outline-success"
              onClick={async () => { await subscriptionsService.activate(row.id); refetch(); }}
            >
              Activate
            </button>
          )}
          {row.status === 'active' && (
            <button
              className="btn btn-sm btn-outline-warning"
              onClick={async () => { await subscriptionsService.suspend(row.id); refetch(); }}
            >
              Suspend
            </button>
          )}
        </>
      )}
    />
  );
}

export default Subscriptions;