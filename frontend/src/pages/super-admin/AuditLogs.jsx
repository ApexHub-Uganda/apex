import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { FiAlertTriangle, FiDownload, FiFilter, FiX } from 'react-icons/fi';
import PageHeader from '../../components/PageHeader';
import DataTable from '../../components/DataTable';
import Modal from '../../components/Modal';
import StatusBadge from '../../components/StatusBadge';
import { auditLogsService } from '../../services/moduleService';
import { extractApiError, notify } from '../../utils/notify';

const EMPTY_FILTERS = {
  created_after: '',
  created_before: '',
  category: '',
  action: '',
  tenant: '',
  status: '',
  search: '',
};

function statusBadgeVariant(label) {
  if (label === 'Success') return 'active';
  if (label === 'Failed') return 'suspended';
  return 'pending';
}

function formatTimestamp(value) {
  if (!value) return '—';
  const d = new Date(String(value).replace(' ', 'T'));
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function Truncate({ text, title, wrap = false }) {
  if (!text) return '—';
  return (
    <span className={wrap ? 'apex-cell-wrap' : 'apex-cell-truncate'} title={title || text}>
      {text}
    </span>
  );
}

export function AuditLogs() {
  const [filters, setFilters] = useState(EMPTY_FILTERS);
  const [selectedLog, setSelectedLog] = useState(null);
  const [exporting, setExporting] = useState(false);
  const [exportingId, setExportingId] = useState(null);

  const queryParams = useMemo(() => {
    const params = { page_size: 100, ordering: '-created_at' };
    Object.entries(filters).forEach(([key, value]) => {
      if (value) params[key] = value;
    });
    return params;
  }, [filters]);

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['audit-logs', queryParams],
    queryFn: () => auditLogsService.list(queryParams),
  });

  const { data: filterOptions } = useQuery({
    queryKey: ['audit-log-filter-options'],
    queryFn: () => auditLogsService.filterOptions(),
  });

  const { data: logDetail, isLoading: detailLoading } = useQuery({
    queryKey: ['audit-log-detail', selectedLog?.id],
    queryFn: () => auditLogsService.get(selectedLog.id),
    enabled: !!selectedLog?.id,
  });

  const activeFilterCount = Object.values(filters).filter(Boolean).length;

  const handleFilterChange = (key, value) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
  };

  const clearFilters = () => setFilters(EMPTY_FILTERS);

  const handleExportList = async () => {
    setExporting(true);
    try {
      await auditLogsService.exportListPdf(queryParams);
      notify.success('Audit log export downloaded.');
    } catch (err) {
      notify.error(extractApiError(err, 'Unable to export audit logs.'));
    } finally {
      setExporting(false);
    }
  };

  const handleExportDetail = async (id) => {
    setExportingId(id);
    try {
      await auditLogsService.exportPdf(id);
      notify.success('Audit log PDF downloaded.');
    } catch (err) {
      notify.error(extractApiError(err, 'Unable to export audit log.'));
    } finally {
      setExportingId(null);
    }
  };

  if (isError) {
    return (
      <div>
        <PageHeader title="Audit Logs" subtitle="Track all platform activities and changes" />
        <div className="apex-card p-5 text-center">
          <FiAlertTriangle size={32} className="text-warning mb-3" />
          <h5 className="fw-bold">Unable to load audit logs</h5>
          <button className="btn btn-primary btn-sm mt-2" onClick={() => refetch()}>Retry</button>
        </div>
      </div>
    );
  }

  const detail = logDetail || selectedLog;

  return (
    <div>
      <PageHeader
        title="Audit Logs"
        subtitle="Track platform activities — filter, inspect details, and export reports"
        actions={
          <button
            className="btn btn-outline-primary d-flex align-items-center gap-2"
            onClick={handleExportList}
            disabled={exporting || !data?.length}
          >
            <FiDownload size={14} />
            {exporting ? 'Exporting...' : 'Export PDF'}
          </button>
        }
      />

      <div className="apex-card p-3 mb-4">
        <div className="d-flex align-items-center gap-2 mb-3">
          <FiFilter size={16} style={{ color: 'var(--apex-primary)' }} />
          <span className="fw-semibold small">Filters</span>
          {activeFilterCount > 0 && (
            <span className="badge rounded-pill" style={{ background: 'var(--apex-primary)' }}>
              {activeFilterCount} active
            </span>
          )}
          {activeFilterCount > 0 && (
            <button className="btn btn-sm btn-link text-decoration-none ms-auto" onClick={clearFilters}>
              <FiX size={14} className="me-1" /> Clear all
            </button>
          )}
        </div>
        <div className="row g-2">
          <div className="col-md-6 col-lg-3">
            <label className="form-label small text-muted mb-1">From date</label>
            <input
              type="date"
              className="form-control form-control-sm"
              value={filters.created_after}
              onChange={(e) => handleFilterChange('created_after', e.target.value)}
            />
          </div>
          <div className="col-md-6 col-lg-3">
            <label className="form-label small text-muted mb-1">To date</label>
            <input
              type="date"
              className="form-control form-control-sm"
              value={filters.created_before}
              onChange={(e) => handleFilterChange('created_before', e.target.value)}
            />
          </div>
          <div className="col-md-6 col-lg-2">
            <label className="form-label small text-muted mb-1">Category</label>
            <select
              className="form-select form-select-sm"
              value={filters.category}
              onChange={(e) => handleFilterChange('category', e.target.value)}
            >
              <option value="">All categories</option>
              {(filterOptions?.categories || []).map((opt) => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </div>
          <div className="col-md-6 col-lg-2">
            <label className="form-label small text-muted mb-1">Action</label>
            <select
              className="form-select form-select-sm"
              value={filters.action}
              onChange={(e) => handleFilterChange('action', e.target.value)}
            >
              <option value="">All actions</option>
              {(filterOptions?.actions || []).map((action) => (
                <option key={action} value={action}>{action}</option>
              ))}
            </select>
          </div>
          <div className="col-md-6 col-lg-2">
            <label className="form-label small text-muted mb-1">Status</label>
            <select
              className="form-select form-select-sm"
              value={filters.status}
              onChange={(e) => handleFilterChange('status', e.target.value)}
            >
              <option value="">All statuses</option>
              {(filterOptions?.statuses || []).map((opt) => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </div>
          <div className="col-md-6 col-lg-4">
            <label className="form-label small text-muted mb-1">School</label>
            <select
              className="form-select form-select-sm"
              value={filters.tenant}
              onChange={(e) => handleFilterChange('tenant', e.target.value)}
            >
              <option value="">All schools / platform</option>
              {(filterOptions?.schools || []).map((school) => (
                <option key={school.id} value={school.id}>{school.name}</option>
              ))}
            </select>
          </div>
          <div className="col-md-6 col-lg-4">
            <label className="form-label small text-muted mb-1">Search</label>
            <input
              type="text"
              className="form-control form-control-sm"
              placeholder="Description, user, resource..."
              value={filters.search}
              onChange={(e) => handleFilterChange('search', e.target.value)}
            />
          </div>
        </div>
      </div>

      <DataTable
        compact
        columns={[
          {
            key: 'timestamp',
            label: 'When',
            accessor: 'timestamp',
            sortable: true,
            width: '11%',
            render: (row) => <span className="text-nowrap">{formatTimestamp(row.timestamp)}</span>,
          },
          {
            key: 'category_label',
            label: 'Category',
            accessor: 'category_label',
            width: '11%',
            render: (row) => <Truncate text={row.category_label} />,
          },
          {
            key: 'action',
            label: 'Action',
            width: '9%',
            render: (row) => <Truncate text={row.action} />,
          },
          {
            key: 'user',
            label: 'User',
            width: '16%',
            render: (row) => <Truncate text={row.user} />,
          },
          {
            key: 'summary',
            label: 'Summary',
            width: '44%',
            render: (row) => (
              <Truncate
                text={row.summary}
                title={`${row.tenant_name || 'Platform'} — ${row.summary}`}
                wrap
              />
            ),
          },
          {
            key: 'status_label',
            label: 'Status',
            width: '9%',
            render: (row) => (
              <StatusBadge status={statusBadgeVariant(row.status_label)} label={row.status_label} />
            ),
          },
        ]}
        data={data || []}
        loading={isLoading}
        searchable={false}
        onRowClick={(row) => setSelectedLog(row)}
        emptyMessage="No audit logs match your filters."
        pageSize={15}
      />

      <Modal
        show={!!selectedLog}
        onHide={() => setSelectedLog(null)}
        title="Audit Log Details"
        size="lg"
        footer={(
          <button
            className="btn btn-primary d-flex align-items-center gap-2 ms-auto"
            onClick={() => handleExportDetail(selectedLog.id)}
            disabled={exportingId === selectedLog?.id}
          >
            <FiDownload size={14} />
            {exportingId === selectedLog?.id ? 'Exporting...' : 'Download PDF'}
          </button>
        )}
      >
        {detailLoading && !detail ? (
          <p className="text-muted mb-0">Loading details...</p>
        ) : (
          <div className="d-flex flex-column gap-3">
            <div className="row g-3">
              <div className="col-md-6">
                <div className="small text-muted">Log ID</div>
                <div className="fw-semibold text-break">{detail?.id}</div>
              </div>
              <div className="col-md-6">
                <div className="small text-muted">Timestamp</div>
                <div className="fw-semibold">{detail?.timestamp}</div>
              </div>
              <div className="col-md-6">
                <div className="small text-muted">User</div>
                <div className="fw-semibold">{detail?.user}</div>
              </div>
              <div className="col-md-6">
                <div className="small text-muted">School / Scope</div>
                <div className="fw-semibold">{detail?.tenant_name || 'Platform'}</div>
              </div>
              <div className="col-md-4">
                <div className="small text-muted">Action</div>
                <code>{detail?.action}</code>
              </div>
              <div className="col-md-4">
                <div className="small text-muted">Category</div>
                <div className="fw-semibold">{detail?.category_label}</div>
              </div>
              <div className="col-md-4">
                <div className="small text-muted">Status</div>
                <StatusBadge status={statusBadgeVariant(detail?.status_label)} label={detail?.status_label} />
              </div>
              <div className="col-md-6">
                <div className="small text-muted">Resource Type</div>
                <div className="fw-semibold">{detail?.resource_type}</div>
              </div>
              <div className="col-md-6">
                <div className="small text-muted">Resource ID</div>
                <div className="fw-semibold">{detail?.resource_id || '—'}</div>
              </div>
              <div className="col-md-6">
                <div className="small text-muted">IP Address</div>
                <div className="fw-semibold">{detail?.ip || detail?.ip_address || '—'}</div>
              </div>
              <div className="col-md-6">
                <div className="small text-muted">HTTP Status</div>
                <div className="fw-semibold">{detail?.status_code ?? '—'}</div>
              </div>
            </div>

            <div>
              <div className="small text-muted mb-1">Description</div>
              <div className="p-3 rounded-3" style={{ background: 'var(--apex-bg)' }}>
                {detail?.description || detail?.summary || '—'}
              </div>
            </div>

            <div>
              <div className="small text-muted mb-1">Request</div>
              <div className="p-3 rounded-3 small" style={{ background: 'var(--apex-bg)' }}>
                <div><strong>Method:</strong> {detail?.request_method || '—'}</div>
                <div><strong>Path:</strong> {detail?.request_path || '—'}</div>
                <div className="mt-2"><strong>User Agent:</strong></div>
                <div className="text-muted">{detail?.user_agent || '—'}</div>
              </div>
            </div>

            <div>
              <div className="small text-muted mb-1">Changes</div>
              <pre
                className="p-3 rounded-3 mb-0 small"
                style={{ background: 'var(--apex-bg)', maxHeight: 200, overflow: 'auto' }}
              >
                {JSON.stringify(detail?.changes || {}, null, 2)}
              </pre>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}

export default AuditLogs;