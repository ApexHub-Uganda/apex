import ModulePage from '../../components/ModulePage';
import StatusBadge from '../../components/StatusBadge';
import { broadcastService } from '../../services/moduleService';

export function Broadcast() {
  return (
    <ModulePage
      title="Broadcast"
      subtitle="Send announcements to schools and users"
      queryKey={['broadcasts']}
      fetchData={() => broadcastService.list({ page_size: 50 })}
      onCreate={(data) => broadcastService.create({
        title: data.title,
        message: data.message,
        audience: data.audience,
        status: data.status || 'draft',
        severity: data.severity || 'info',
        starts_at: data.starts_at || new Date().toISOString(),
        is_active: data.status === 'sent',
      })}
      onUpdate={(id, data) => broadcastService.update(id, data)}
      onDelete={(id) => broadcastService.delete(id)}
      createLabel="New Broadcast"
      columns={[
        { key: 'title', label: 'Title', accessor: 'title', sortable: true },
        { key: 'audience', label: 'Audience', render: (row) => row.audience_display || row.audience },
        { key: 'severity', label: 'Severity', accessor: 'severity' },
        { key: 'status', label: 'Status', render: (row) => <StatusBadge status={row.status} /> },
        { key: 'sent_at', label: 'Sent At', render: (row) => row.sent_at_display || '—' },
      ]}
      formFields={[
        { name: 'title', label: 'Title', required: true },
        { name: 'message', label: 'Message', type: 'textarea', required: true },
        { name: 'audience', label: 'Audience', type: 'select', required: true, options: [
          { value: 'all', label: 'All Schools' },
          { value: 'trial', label: 'Trial Plans' },
          { value: 'basic', label: 'Basic Plans' },
          { value: 'premium', label: 'Premium Plans' },
          { value: 'premium_plus', label: 'Premium Plus Plans' },
          { value: 'active', label: 'Active Schools Only' },
        ]},
        { name: 'severity', label: 'Severity', type: 'select', options: [
          { value: 'info', label: 'Info' },
          { value: 'warning', label: 'Warning' },
          { value: 'critical', label: 'Critical' },
        ]},
        { name: 'status', label: 'Status', type: 'select', options: [
          { value: 'draft', label: 'Draft' },
          { value: 'scheduled', label: 'Scheduled' },
          { value: 'sent', label: 'Send Now' },
        ]},
        { name: 'starts_at', label: 'Schedule At', type: 'datetime-local' },
      ]}
    />
  );
}

export default Broadcast;