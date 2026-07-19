import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  FiArrowRight, FiBookOpen, FiCheckCircle, FiClipboard, FiUsers,
} from 'react-icons/fi';
import WorkspaceShell, { WorkspaceSection } from '../../components/WorkspaceShell';
import ModuleEmptyState from '../../components/ModuleEmptyState';
import { academicWorkspaceService } from '../../services/moduleService';
import { usePermissions } from '../../hooks/usePermissions';

function StatTile({ label, value, accent = 'primary' }) {
  return (
    <div className={`apex-card p-3 border-start border-3 border-${accent}`}>
      <div className="text-muted small">{label}</div>
      <div className="fs-4 fw-bold">{value ?? 0}</div>
    </div>
  );
}

function QueueList({ title, items, emptyMessage, actionLabel, onAction }) {
  if (!items?.length) {
    return <p className="text-muted small mb-0">{emptyMessage}</p>;
  }
  return (
    <div className="list-group list-group-flush">
      {items.map((item) => (
        <div key={item.id} className="list-group-item px-0 d-flex align-items-center justify-content-between gap-2">
          <div>
            <div className="fw-semibold">{item.name}</div>
            <div className="small text-muted">
              {[item.subject, item.school_class, item.term].filter(Boolean).join(' · ')}
            </div>
          </div>
          {onAction && (
            <button type="button" className="btn btn-sm btn-outline-primary" onClick={() => onAction(item)}>
              {actionLabel}
            </button>
          )}
        </div>
      ))}
    </div>
  );
}

export function AcademicRoleWorkspace({
  title,
  subtitle,
  backTo = '/school-admin/academics',
  backLabel = 'Academics',
  featureKey,
}) {
  const { canReadFeature } = usePermissions();
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['academic-workspace', featureKey],
    queryFn: () => academicWorkspaceService.get(),
    staleTime: 30_000,
  });

  const counts = data?.counts || {};
  const queues = data?.queues || {};
  const quickLinks = (data?.quick_links || []).filter(
    (link) => canReadFeature(link.feature_key),
  );

  if (isLoading) {
    return (
      <div className="py-5 text-center">
        <div className="spinner-border text-primary" role="status" />
      </div>
    );
  }

  if (isError) {
    return (
      <WorkspaceShell backTo={backTo} backLabel={backLabel} title={title} subtitle={subtitle}>
        <div className="alert alert-danger">Unable to load workspace data.</div>
      </WorkspaceShell>
    );
  }

  return (
    <WorkspaceShell
      backTo={backTo}
      backLabel={backLabel}
      title={title}
      subtitle={subtitle}
      actions={(
        <button type="button" className="btn btn-outline-secondary btn-sm" onClick={() => refetch()}>
          Refresh
        </button>
      )}
    >
      <div className="row g-3 mb-4">
        {counts.assigned_classes != null && (
          <div className="col-6 col-md-3">
            <StatTile label="Assigned classes" value={counts.assigned_classes} />
          </div>
        )}
        {counts.draft_marks != null && (
          <div className="col-6 col-md-3">
            <StatTile label="Draft marks" value={counts.draft_marks} accent="warning" />
          </div>
        )}
        {counts.pending_approval != null && (
          <div className="col-6 col-md-3">
            <StatTile label="Pending approval" value={counts.pending_approval} accent="info" />
          </div>
        )}
        {counts.lesson_sessions_today != null && (
          <div className="col-6 col-md-3">
            <StatTile label="Lessons today" value={counts.lesson_sessions_today} accent="success" />
          </div>
        )}
      </div>

      {quickLinks.length > 0 && (
        <WorkspaceSection title="Quick actions" icon={FiArrowRight} className="mb-4">
          <div className="d-flex flex-wrap gap-2">
            {quickLinks.map((link) => (
              <Link key={link.path} to={link.path} className="btn btn-outline-primary btn-sm">
                {link.label}
              </Link>
            ))}
          </div>
        </WorkspaceSection>
      )}

      {(counts.teaching_assignments != null || counts.open_exam_sessions != null || counts.department_subjects != null) && (
        <div className="row g-3 mb-4">
          {counts.teaching_assignments != null && (
            <div className="col-6 col-md-3"><StatTile label="Teaching assignments" value={counts.teaching_assignments} /></div>
          )}
          {counts.open_exam_sessions != null && (
            <div className="col-6 col-md-3"><StatTile label="Open exam sessions" value={counts.open_exam_sessions} accent="info" /></div>
          )}
          {counts.department_subjects != null && (
            <div className="col-6 col-md-3"><StatTile label="Dept subjects" value={counts.department_subjects} /></div>
          )}
          {counts.department_classes != null && (
            <div className="col-6 col-md-3"><StatTile label="Dept classes" value={counts.department_classes} accent="success" /></div>
          )}
        </div>
      )}

      {queues.marks_approval?.length > 0 && canReadFeature('marks_approval') && (
        <WorkspaceSection
          title="Marks awaiting approval"
          description="Review and approve submitted mark sheets for your scope."
          icon={FiCheckCircle}
          className="mb-4"
        >
          <QueueList
            items={queues.marks_approval}
            emptyMessage="No marks pending approval."
            actionLabel="Open"
            onAction={() => { window.location.href = '/school-admin/examinations/approval'; }}
          />
          <Link to="/school-admin/examinations/approval" className="btn btn-primary btn-sm mt-3">
            Open full approval queue <FiArrowRight size={14} />
          </Link>
        </WorkspaceSection>
      )}

      {queues.draft_assessments?.length > 0 && canReadFeature('assessment_management') && (
        <WorkspaceSection
          title="Draft assessments"
          description="Publish assessments before teachers can enter marks."
          icon={FiClipboard}
          className="mb-4"
        >
          <QueueList
            items={queues.draft_assessments}
            emptyMessage="No draft assessments."
            actionLabel="Manage"
            onAction={() => { window.location.href = '/school-admin/examinations/assessments'; }}
          />
          <Link to="/school-admin/examinations/assessments" className="btn btn-outline-primary btn-sm mt-3">
            Manage assessments <FiArrowRight size={14} />
          </Link>
        </WorkspaceSection>
      )}

      {data?.is_class_teacher && canReadFeature('class_teacher_tools') && (
        <WorkspaceSection title="Class teacher tools" icon={FiUsers} className="mb-4">
          <div className="d-flex flex-wrap gap-2">
            <Link to="/school-admin/academics/class-notices" className="btn btn-outline-secondary btn-sm">
              Class notices
            </Link>
            <Link to="/school-admin/academics/discipline" className="btn btn-outline-secondary btn-sm">
              Discipline remarks
            </Link>
            <Link to="/school-admin/examinations/class-report-cards" className="btn btn-outline-secondary btn-sm">
              Class report cards
            </Link>
            <Link to="/school-admin/attendance" className="btn btn-outline-secondary btn-sm">
              Class attendance
            </Link>
          </div>
        </WorkspaceSection>
      )}

      <WorkspaceSection title="Operations map" icon={FiBookOpen}>
        <div className="row g-2">
          {[
            canReadFeature('marks_entry') && { label: 'Enter marks', path: '/school-admin/examinations/marks' },
            canReadFeature('marks_approval') && { label: 'Approve marks', path: '/school-admin/examinations/approval' },
            canReadFeature('teacher_assignments') && { label: 'Teaching assignments', path: '/school-admin/academics/subject-assignments' },
            canReadFeature('timetables') && { label: 'Timetable wizard', path: '/school-admin/academics/timetable/wizard' },
            canReadFeature('examination_sessions') && { label: 'Exam sessions', path: '/school-admin/examinations/sessions' },
            canReadFeature('report_cards') && { label: 'Report cards', path: '/school-admin/examinations/report-cards' },
          ].filter(Boolean).map((item) => (
            <div key={item.path} className="col-md-4">
              <Link to={item.path} className="btn btn-light border w-100 text-start btn-sm">
                {item.label} <FiArrowRight className="float-end mt-1" size={14} />
              </Link>
            </div>
          ))}
        </div>
      </WorkspaceSection>
    </WorkspaceShell>
  );
}

export default AcademicRoleWorkspace;