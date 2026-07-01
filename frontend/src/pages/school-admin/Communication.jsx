import ModulePage from '../../components/ModulePage';
import StatusBadge from '../../components/StatusBadge';
import { communicationService } from '../../services/moduleService';

const MOCK_COMMUNICATION = [
  { id: 1, subject: 'Parent-Teacher Meeting', recipients: 'All Parents', channel: 'Email', sent_at: '2026-06-28', status: 'active' },
  { id: 2, subject: 'Fee Reminder - July', recipients: 'Grade 10 Parents', channel: 'SMS', sent_at: '2026-06-25', status: 'active' },
  { id: 3, subject: 'Sports Day Announcement', recipients: 'All Students', channel: 'In-App', sent_at: '2026-06-20', status: 'active' },
  { id: 4, subject: 'Holiday Schedule', recipients: 'All Staff', channel: 'Email', sent_at: '-', status: 'pending' },
];

export function Communication() {
  return (
    <ModulePage
      title="Communication"
      subtitle="Send messages to parents, students, and staff"
      queryKey={['communication']}
      fetchData={() => communicationService.list()}
      mockData={MOCK_COMMUNICATION}
      onCreate={(data) => communicationService.create(data)}
      createLabel="Compose Message"
      columns={[
        { key: 'subject', label: 'Subject', accessor: 'subject', sortable: true },
        { key: 'recipients', label: 'Recipients', accessor: 'recipients' },
        { key: 'channel', label: 'Channel', accessor: 'channel' },
        { key: 'sent_at', label: 'Sent At', accessor: 'sent_at' },
        { key: 'status', label: 'Status', render: (row) => <StatusBadge status={row.status} /> },
      ]}
      formFields={[
        { name: 'subject', label: 'Subject', required: true },
        { name: 'message', label: 'Message', type: 'textarea', required: true },
        { name: 'recipients', label: 'Recipients', type: 'select', options: [
          { value: 'All Parents', label: 'All Parents' },
          { value: 'All Students', label: 'All Students' },
          { value: 'All Staff', label: 'All Staff' },
          { value: 'Grade 10 Parents', label: 'Grade 10 Parents' },
        ]},
        { name: 'channel', label: 'Channel', type: 'select', options: [
          { value: 'Email', label: 'Email' },
          { value: 'SMS', label: 'SMS' },
          { value: 'In-App', label: 'In-App' },
        ]},
      ]}
    />
  );
}

export default Communication;