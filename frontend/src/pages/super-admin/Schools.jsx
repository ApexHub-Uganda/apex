import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  FiGrid, FiGlobe, FiChevronRight, FiAlertTriangle, FiSearch, FiBell, FiCheck,
} from 'react-icons/fi';
import PageHeader from '../../components/PageHeader';
import StatusBadge from '../../components/StatusBadge';
import { PageSkeleton } from '../../components/LoadingSkeleton';
import { platformNotificationsService, schoolsService } from '../../services/moduleService';
import { extractApiError, notify } from '../../utils/notify';

const formatDate = (value) => {
  if (!value) return '—';
  return new Date(value).toLocaleDateString();
};

export function Schools() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [search, setSearch] = useState('');

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['schools'],
    queryFn: () => schoolsService.list({ page_size: 100, ordering: '-created_at' }),
  });

  const { data: summary } = useQuery({
    queryKey: ['platform-notifications-summary'],
    queryFn: () => platformNotificationsService.getSummary(),
  });

  const approveMutation = useMutation({
    mutationFn: (id) => platformNotificationsService.approve(id),
    onSuccess: (data) => {
      notify.success(data?.message || 'School approved successfully.');
      queryClient.invalidateQueries({ queryKey: ['platform-notifications-summary'] });
      queryClient.invalidateQueries({ queryKey: ['notification-feed'] });
      queryClient.invalidateQueries({ queryKey: ['schools'] });
    },
    onError: (err) => notify.error(extractApiError(err, 'Unable to approve school.')),
  });

  const pendingNotifications = summary?.recent || [];
  const pendingCount = summary?.pending_count ?? 0;

  const schools = useMemo(() => {
    const list = data || [];
    const term = search.trim().toLowerCase();
    if (!term) return list;
    return list.filter(
      (school) =>
        school.name?.toLowerCase().includes(term) ||
        school.country?.toLowerCase().includes(term),
    );
  }, [data, search]);

  if (isLoading) return <PageSkeleton />;

  if (isError) {
    return (
      <div className="apex-card p-5 text-center">
        <FiAlertTriangle size={32} className="text-warning mb-3" />
        <h5 className="fw-bold">Unable to load schools</h5>
        <button className="btn btn-primary btn-sm mt-2" onClick={() => refetch()}>Retry</button>
      </div>
    );
  }

  return (
    <div>
      <PageHeader
        title="Schools"
        subtitle="Select a school to view profile and subscription details"
        actions={
          pendingCount > 0 ? (
            <button
              type="button"
              className="btn btn-sm btn-warning d-flex align-items-center gap-1"
              onClick={() => navigate('/super-admin/notifications')}
            >
              <FiBell size={14} />
              {pendingCount} pending approval{pendingCount !== 1 ? 's' : ''}
            </button>
          ) : null
        }
      />

      {pendingNotifications.length > 0 && (
        <motion.div
          className="apex-card p-4 mb-4"
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          style={{ borderLeft: '4px solid var(--apex-secondary)' }}
        >
          <div className="d-flex align-items-center justify-content-between mb-3">
            <div className="d-flex align-items-center gap-2">
              <FiBell style={{ color: 'var(--apex-secondary)' }} />
              <h6 className="fw-bold mb-0">New Registrations</h6>
            </div>
            <button
              type="button"
              className="btn btn-sm btn-link text-decoration-none"
              onClick={() => navigate('/super-admin/notifications')}
            >
              View all
            </button>
          </div>
          <div className="d-flex flex-column gap-2">
            {pendingNotifications.map((item) => (
              <div
                key={item.id}
                className="d-flex flex-column flex-md-row align-items-md-center justify-content-between gap-2 p-3 rounded-3"
                style={{ background: 'rgba(255, 127, 80, 0.06)' }}
              >
                <div>
                  <div className="fw-semibold small">{item.school_name || item.title}</div>
                  <div className="text-muted" style={{ fontSize: '0.75rem' }}>
                    {item.message}
                  </div>
                  <div className="text-muted" style={{ fontSize: '0.7rem' }}>
                    {formatDate(item.created_at)}
                    {item.metadata?.plan_name && ` · ${item.metadata.plan_name}`}
                  </div>
                </div>
                <div className="d-flex gap-2">
                  <button
                    type="button"
                    className="btn btn-sm btn-success d-flex align-items-center gap-1"
                    disabled={approveMutation.isPending}
                    onClick={() => approveMutation.mutate(item.id)}
                  >
                    <FiCheck size={14} />
                    Approve
                  </button>
                  <button
                    type="button"
                    className="btn btn-sm btn-outline-primary"
                    onClick={() => navigate(`/super-admin/schools/${item.school_id || item.tenant}`)}
                  >
                    Review
                  </button>
                </div>
              </div>
            ))}
          </div>
        </motion.div>
      )}

      <div className="apex-card p-3 mb-4">
        <div className="position-relative">
          <FiSearch
            className="position-absolute"
            style={{ left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--apex-text-muted)' }}
          />
          <input
            type="text"
            className="form-control ps-5"
            placeholder="Search by school name or country..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      </div>

      {schools.length === 0 ? (
        <div className="apex-card p-5 text-center text-muted">
          No schools found.
        </div>
      ) : (
        <div className="row g-3">
          {schools.map((school, index) => (
            <div key={school.id} className="col-md-6 col-xl-4">
              <motion.button
                type="button"
                className="apex-card p-4 w-100 text-start border-0 h-100"
                style={{ cursor: 'pointer' }}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.03 }}
                onClick={() => navigate(`/super-admin/schools/${school.id}`)}
              >
                <div className="d-flex align-items-center justify-content-between gap-3">
                  <div className="d-flex align-items-start gap-3">
                    <div
                      className="rounded-3 d-flex align-items-center justify-content-center flex-shrink-0"
                      style={{
                        width: 44,
                        height: 44,
                        background: 'rgba(15, 118, 110, 0.1)',
                        color: 'var(--apex-primary)',
                      }}
                    >
                      <FiGrid size={20} />
                    </div>
                    <div>
                      <h6 className="fw-bold mb-1">{school.name}</h6>
                      <div className="d-flex align-items-center gap-1 text-muted small mb-1">
                        <FiGlobe size={14} />
                        <span>{school.country || '—'}</span>
                      </div>
                      {school.status && (
                        <StatusBadge status={school.status} />
                      )}
                    </div>
                  </div>
                  <FiChevronRight style={{ color: 'var(--apex-text-muted)' }} />
                </div>
              </motion.button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default Schools;