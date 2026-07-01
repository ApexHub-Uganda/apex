import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import PageHeader from '../../components/PageHeader';
import DataTable from '../../components/DataTable';
import { attendanceService } from '../../services/moduleService';

const MOCK_ATTENDANCE = [
  { id: 1, date: '2026-06-30', class: 'Grade 10-A', present: 30, absent: 2, late: 0, rate: 93.8 },
  { id: 2, date: '2026-06-30', class: 'Grade 9-B', present: 26, absent: 2, late: 0, rate: 92.9 },
  { id: 3, date: '2026-06-30', class: 'Grade 11-A', present: 28, absent: 2, late: 0, rate: 93.3 },
  { id: 4, date: '2026-06-29', class: 'Grade 10-A', present: 31, absent: 1, late: 0, rate: 96.9 },
];

export function Attendance() {
  const [dateFilter, setDateFilter] = useState('');

  const { data, isLoading } = useQuery({
    queryKey: ['attendance', dateFilter],
    queryFn: async () => {
      try {
        const result = await attendanceService.list({ date: dateFilter });
        return result?.results || result || [];
      } catch {
        return MOCK_ATTENDANCE;
      }
    },
  });

  return (
    <div>
      <PageHeader
        title="Attendance"
        subtitle="Track and manage daily attendance records"
        actions={<button className="btn btn-primary btn-sm">Mark Attendance</button>}
      />
      <DataTable
        columns={[
          { key: 'date', label: 'Date', accessor: 'date', sortable: true },
          { key: 'class', label: 'Class', accessor: 'class' },
          { key: 'present', label: 'Present', accessor: 'present' },
          { key: 'absent', label: 'Absent', accessor: 'absent' },
          { key: 'late', label: 'Late', accessor: 'late' },
          { key: 'rate', label: 'Rate', render: (row) => (
            <span className={row.rate >= 90 ? 'text-success fw-semibold' : 'text-warning fw-semibold'}>
              {row.rate}%
            </span>
          )},
        ]}
        data={data || []}
        loading={isLoading}
        filters={
          <input
            type="date"
            className="form-control form-control-sm"
            style={{ width: 160 }}
            value={dateFilter}
            onChange={(e) => setDateFilter(e.target.value)}
          />
        }
      />
    </div>
  );
}

export default Attendance;