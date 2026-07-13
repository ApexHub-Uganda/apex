import { FiEdit2 } from 'react-icons/fi';
import StatusBadge from '../components/StatusBadge';
import { PersonNameCell } from '../components/PersonAvatar';
import { COL_WIDTH, formatClassStream, nameColumn } from '../utils/tableDisplay';
import { getRoleLabel } from './schoolRoles';
export function buildStudentDirectoryColumns({ canManage, navigate }) {
  return [
    {
      key: 'admission_number',
      label: 'Adm. No.',
      accessor: 'admission_number',
      sortable: true,
      width: COL_WIDTH.admission,
    },
    nameColumn({
      key: 'full_name',
      label: 'Student',
      accessor: 'full_name',
      sortable: true,
      render: (row) => <PersonNameCell row={row} compact />,
    }),
    {
      key: 'class_name',
      label: 'Class',
      accessor: 'class_name',
      sortable: true,
      width: COL_WIDTH.class,
      sortValue: (row) => formatClassStream(row),
      render: (row) => {
        const text = formatClassStream(row);
        return <span className="apex-cell-truncate d-block" title={text}>{text}</span>;
      },
    },
    {
      key: 'profile',
      label: 'Profile',
      width: COL_WIDTH.badge,
      truncate: false,
      render: (row) => (
        row.is_profile_incomplete
          ? <span className="badge text-bg-warning-subtle border text-warning apex-table-badge">Incomplete</span>
          : <span className="badge text-bg-success-subtle border text-success apex-table-badge">Complete</span>
      ),
    },
    {
      key: 'status',
      label: 'Status',
      accessor: 'status',
      sortable: true,
      width: COL_WIDTH.status,
      truncate: false,
      render: (row) => <StatusBadge status={row.status} />,
    },
    ...(canManage ? [directoryActionColumn((row) => navigate(`/school-admin/students/${row.id}`))] : []),
  ];
}

export function buildStaffDirectoryColumns({ canManage, navigate }) {
  return [
    {
      key: 'employee_id',
      label: 'Emp. ID',
      accessor: 'employee_id',
      sortable: true,
      width: COL_WIDTH.employeeId,
    },
    nameColumn({
      key: 'full_name',
      label: 'Staff',
      accessor: 'full_name',
      sortable: true,
      render: (row) => <PersonNameCell row={row} compact />,
    }),
    {
      key: 'portal_role',
      label: 'Role',
      accessor: 'portal_role',
      sortable: true,
      width: COL_WIDTH.role,
      sortValue: (row) => row.role_label || getRoleLabel(row.portal_role),
      render: (row) => row.role_label || getRoleLabel(row.portal_role),
    },
    {
      key: 'department_name',
      label: 'Department',
      accessor: 'department_name',
      sortable: true,
      width: COL_WIDTH.department,
    },
    {
      key: 'status',
      label: 'Status',
      accessor: 'status',
      sortable: true,
      width: COL_WIDTH.status,
      truncate: false,
      render: (row) => <StatusBadge status={row.status} />,
    },
    ...(canManage ? [directoryActionColumn((row) => navigate(`/school-admin/hr/staffs/${row.id}`))] : []),
  ];
}

export function buildParentDirectoryColumns({ canManage, navigate }) {
  return [
    nameColumn({
      key: 'full_name',
      label: 'Parent / Guardian',
      accessor: 'full_name',
      sortable: true,
      render: (row) => <PersonNameCell row={row} compact />,
    }),
    {
      key: 'phone',
      label: 'Phone',
      accessor: 'phone',
      sortable: true,
      width: COL_WIDTH.phone,
    },
    {
      key: 'children_count',
      label: 'Learners',
      accessor: 'children_count',
      sortable: true,
      width: COL_WIDTH.count,
      render: (row) => (
        <span className="apex-table-count">{row.children_count ?? 0}</span>
      ),
    },
    {
      key: 'status',
      label: 'Fee payer',
      width: COL_WIDTH.badge,
      truncate: false,
      sortable: true,
      sortValue: (row) => (row.is_fee_payer ? 'yes' : 'no'),
      render: (row) => (
        row.is_fee_payer
          ? <span className="badge text-bg-success-subtle border text-success apex-table-badge">Yes</span>
          : <span className="text-muted small">—</span>
      ),
    },
    ...(canManage ? [directoryActionColumn((row) => navigate(`/school-admin/parents/${row.id}`))] : []),
  ];
}

export function buildClassStudentColumns({ showStream = false } = {}) {
  const cols = [
    {
      key: 'admission_number',
      label: 'Adm. No.',
      accessor: 'admission_number',
      sortable: true,
      width: COL_WIDTH.admission,
    },
    nameColumn({
      key: 'full_name',
      label: 'Student',
      accessor: 'full_name',
      sortable: true,
      render: (row) => <PersonNameCell row={row} compact />,
    }),
    {
      key: 'gender',
      label: 'Sex',
      accessor: 'gender',
      width: COL_WIDTH.badge,
      render: (row) => {
        const g = (row.gender || '').toLowerCase();
        if (g === 'male') return 'M';
        if (g === 'female') return 'F';
        return row.gender || '—';
      },
    },
  ];

  if (showStream) {
    cols.push({
      key: 'stream_name',
      label: 'Stream',
      accessor: 'stream_name',
      width: COL_WIDTH.stream,
    });
  }

  cols.push({
    key: 'status',
    label: 'Status',
    accessor: 'status',
    width: COL_WIDTH.status,
    truncate: false,
    render: (row) => <StatusBadge status={row.status} />,
  });

  return cols;
}

function directoryActionColumn(onOpen) {
  return {
    key: 'actions',
    label: '',
    width: COL_WIDTH.actions,
    truncate: false,
    render: (row) => (
      <div className="apex-table-row-actions">
        <button
          type="button"
          className="btn btn-sm btn-outline-secondary apex-table-open-btn"
          title="Open record"
          onClick={(e) => { e.stopPropagation(); onOpen(row); }}
        >
          <FiEdit2 size={13} />
        </button>
      </div>
    ),
  };
}