import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { FiArrowLeft, FiMail, FiPhone, FiUsers } from 'react-icons/fi';
import PageHeader from '../../components/PageHeader';
import DataTable from '../../components/DataTable';
import ModuleEmptyState from '../../components/ModuleEmptyState';
import StatusBadge from '../../components/StatusBadge';
import PersonAvatar from '../../components/PersonAvatar';
import { usersService } from '../../services/moduleService';
import { ROLE_LABELS } from '../../config/schoolRoles';

const TABS = [
  { key: 'staff', label: 'Staff', category: 'staff' },
  { key: 'parents', label: 'Parents', category: 'parents' },
  { key: 'learners', label: 'Learners', category: 'learners' },
];

function roleLabel(role) {
  return ROLE_LABELS[role] || (role || '—').replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

export function UserAccounts() {
  const [tab, setTab] = useState('staff');
  const [search, setSearch] = useState('');
  const activeTab = TABS.find((t) => t.key === tab) || TABS[0];

  const { data = [], isLoading, isError } = useQuery({
    queryKey: ['user-accounts', activeTab.category, search],
    queryFn: () => usersService.list({
      category: activeTab.category,
      page_size: 200,
      search: search.trim() || undefined,
    }),
  });

  const columns = useMemo(() => [
    {
      key: 'person',
      label: 'User',
      sortable: true,
      accessor: 'full_name',
      render: (row) => (
        <div className="d-flex align-items-center gap-2">
          <PersonAvatar person={row} size={36} />
          <div className="min-w-0">
            <div className="fw-semibold text-truncate">
              {row.full_name || `${row.first_name || ''} ${row.last_name || ''}`.trim() || '—'}
            </div>
            <div className="small text-muted text-truncate">{row.email || '—'}</div>
          </div>
        </div>
      ),
    },
    {
      key: 'role',
      label: 'Role',
      accessor: 'role',
      render: (row) => (
        <span className="badge text-bg-light border text-body-secondary">
          {roleLabel(row.effective_role || row.role)}
        </span>
      ),
    },
    {
      key: 'phone',
      label: 'Phone',
      accessor: 'phone',
      render: (row) => (row.phone
        ? <span className="d-inline-flex align-items-center gap-1"><FiPhone size={12} /> {row.phone}</span>
        : '—'),
    },
    {
      key: 'email_status',
      label: 'Email',
      render: (row) => (
        <span className="d-inline-flex align-items-center gap-1 small">
          <FiMail size={12} />
          {row.is_email_verified
            ? <span className="text-success">Verified</span>
            : <span className="text-muted">Unverified</span>}
        </span>
      ),
    },
    {
      key: 'status',
      label: 'Status',
      render: (row) => <StatusBadge status={row.is_active ? 'active' : 'inactive'} />,
    },
    {
      key: 'last_login',
      label: 'Last login',
      accessor: 'last_login_at',
      render: (row) => {
        if (!row.last_login_at) return '—';
        try {
          return new Date(row.last_login_at).toLocaleString();
        } catch {
          return row.last_login_at;
        }
      },
    },
  ], []);

  return (
    <div>
      <div className="mb-3">
        <Link to="/school-admin/core" className="small text-decoration-none text-muted">
          <FiArrowLeft className="me-1" /> Core Management
        </Link>
      </div>

      <PageHeader
        title="User Accounts"
        subtitle="Portal login accounts for staff, parents, and learners — switch categories with the tabs below"
      />

      <div className="apex-card p-3 p-md-4">
        <div className="d-flex flex-wrap align-items-center justify-content-between gap-2 mb-3">
          <ul className="nav nav-pills gap-1 mb-0">
            {TABS.map((item) => (
              <li className="nav-item" key={item.key}>
                <button
                  type="button"
                  className={`nav-link ${tab === item.key ? 'active' : ''}`}
                  onClick={() => setTab(item.key)}
                >
                  {item.label}
                </button>
              </li>
            ))}
          </ul>
          <div className="input-group input-group-sm" style={{ maxWidth: 280 }}>
            <span className="input-group-text bg-transparent"><FiUsers size={14} /></span>
            <input
              type="search"
              className="form-control"
              placeholder={`Search ${activeTab.label.toLowerCase()}…`}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
        </div>

        {isError ? (
          <div className="alert alert-danger mb-0">Unable to load user accounts.</div>
        ) : (
          <DataTable
            columns={columns}
            data={data}
            loading={isLoading}
            emptyState={(
              <ModuleEmptyState
                title={`No ${activeTab.label.toLowerCase()} accounts`}
                message={
                  activeTab.key === 'staff'
                    ? 'Staff portal accounts appear when staff are onboarded with portal access.'
                    : activeTab.key === 'parents'
                      ? 'Parent accounts appear when parents are given portal access.'
                      : 'Learner accounts appear when students are linked to portal logins.'
                }
              />
            )}
          />
        )}
      </div>
    </div>
  );
}

export default UserAccounts;
