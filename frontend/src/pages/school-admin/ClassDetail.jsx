import { useMemo, useState } from 'react';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useAuth } from '../../hooks/useAuth';
import {
  FiAward, FiBookOpen, FiChevronRight, FiEdit2, FiPlus, FiTrash2, FiUpload, FiUserPlus, FiUsers,
} from 'react-icons/fi';
import StudentBulkImportWizard from '../../components/StudentBulkImportWizard';
import { studentBulkImport } from '../../services/bulkImportService';
import WorkspaceShell, { WorkspaceSection } from '../../components/WorkspaceShell';
import DataTable from '../../components/DataTable';
import { Modal } from '../../components/Modal';
import ModuleEmptyState from '../../components/ModuleEmptyState';
import {
  academicYearsService, classesService, streamsService, studentsService,
} from '../../services/moduleService';
import { usePermissions } from '../../hooks/usePermissions';
import { alert, extractApiError, notify } from '../../utils/notify';
import { buildClassStudentColumns } from '../../config/directoryTableColumns.jsx';
import { ApexLoader } from '../../components/ApexLoader';

const PREFECT_ROLES = [
  { value: 'head', label: 'Head Prefect' },
  { value: 'deputy', label: 'Deputy Prefect' },
  { value: 'prefect', label: 'Prefect' },
];

const LEVEL_LABELS = {
  pre_primary: 'Pre-Primary',
  primary: 'Primary',
  junior_secondary: 'Junior Secondary',
  senior_secondary: 'Senior Secondary',
  tertiary: 'Tertiary',
};

const LEVEL_OPTIONS = [
  { value: '', label: 'Select level' },
  { value: 'pre_primary', label: 'Pre-Primary' },
  { value: 'primary', label: 'Primary' },
  { value: 'junior_secondary', label: 'Junior Secondary' },
  { value: 'senior_secondary', label: 'Senior Secondary' },
  { value: 'tertiary', label: 'Tertiary' },
];

const CURRICULUM_OPTIONS = [
  { value: 'uneb', label: 'UNEB (Uganda)' },
  { value: 'uganda_cbe', label: 'Uganda Competence-Based' },
  { value: 'igcse', label: 'IGCSE' },
  { value: 'ace', label: 'ACE' },
  { value: 'cbc', label: 'CBC (Kenya)' },
  { value: '844', label: '8-4-4' },
  { value: 'other', label: 'Other' },
];

const EMPTY_CLASS_FORM = {
  name: '', code: '', academic_year: '', level_type: '', curriculum: 'uneb',
  section: '', class_teacher: '', capacity: 40, room: '',
};

function InfoCard({ label, value, hint }) {
  return (
    <div className="class-hub-info-card">
      <div className="text-muted small">{label}</div>
      <div className="fw-semibold">{value || '—'}</div>
      {hint ? <div className="text-muted small mt-1">{hint}</div> : null}
    </div>
  );
}

export function ClassDetail() {
  const { classId } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const streamId = searchParams.get('stream') || '';
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { isSchoolAdmin } = useAuth();
  const { canReadFeature, canWriteFeature } = usePermissions();
  const canViewHub = canReadFeature('classes');

  const [showPrefectModal, setShowPrefectModal] = useState(false);
  const [showStreamModal, setShowStreamModal] = useState(false);
  const [showStudentImport, setShowStudentImport] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [classForm, setClassForm] = useState(EMPTY_CLASS_FORM);
  const [prefectForm, setPrefectForm] = useState({ student: '', role: 'prefect' });
  const [streamForm, setStreamForm] = useState({ name: '', capacity: 40 });
  const [saving, setSaving] = useState(false);

  const { data: hub, isLoading, isError } = useQuery({
    queryKey: ['class-hub', classId, streamId],
    queryFn: () => classesService.getHub(classId, streamId ? { stream: streamId } : {}),
    enabled: Boolean(classId),
  });

  const { data: years = [] } = useQuery({
    queryKey: ['academic-years'],
    queryFn: () => academicYearsService.list(),
    enabled: showEditModal,
  });

  const { data: formOptions } = useQuery({
    queryKey: ['classes-form-options'],
    queryFn: () => classesService.formOptions(),
    enabled: showEditModal,
  });

  const teachers = formOptions?.teachers || [];

  const { data: classStudents = [] } = useQuery({
    queryKey: ['class-students-options', classId, streamId],
    queryFn: () => studentsService.list({
      school_class: classId,
      ...(streamId ? { stream: streamId } : {}),
      status: 'active',
    }),
    enabled: Boolean(classId) && showPrefectModal,
  });

  const studentColumns = useMemo(
    () => buildClassStudentColumns({ showStream: Boolean(hub?.has_streams) }),
    [hub?.has_streams],
  );

  const selectStream = (nextStreamId) => {
    if (!nextStreamId) {
      setSearchParams({});
      return;
    }
    setSearchParams({ stream: nextStreamId });
  };

  const handleAddPrefect = async ({ addAnother = false } = {}) => {
    if (!prefectForm.student) {
      notify.error('Select a student.');
      return;
    }
    setSaving(true);
    try {
      await classesService.addPrefect(classId, {
        student: prefectForm.student,
        role: prefectForm.role,
        stream: streamId || undefined,
      });
      notify.success('Class prefect appointed.');
      if (!addAnother) {
        setShowPrefectModal(false);
      }
      setPrefectForm({ student: '', role: 'prefect' });
      await queryClient.invalidateQueries({ queryKey: ['class-hub', classId] });
      await queryClient.invalidateQueries({ queryKey: ['classes-overview'] });
    } catch (err) {
      notify.error(extractApiError(err, 'Unable to appoint prefect.'));
    } finally {
      setSaving(false);
    }
  };

  const openEditModal = async () => {
    try {
      const detail = await classesService.get(classId);
      setClassForm({
        name: detail.name || '',
        code: detail.code || '',
        academic_year: detail.academic_year || '',
        level_type: detail.level_type || '',
        curriculum: detail.curriculum || 'cbc',
        section: detail.section || '',
        class_teacher: detail.class_teacher || '',
        capacity: detail.capacity || 40,
        room: detail.room || '',
      });
      setShowEditModal(true);
    } catch (err) {
      notify.error(extractApiError(err, 'Unable to load class details.'));
    }
  };

  const handleSaveClass = async () => {
    setSaving(true);
    try {
      await classesService.update(classId, {
        ...classForm,
        class_teacher: classForm.class_teacher || null,
      });
      notify.success('Class updated.');
      setShowEditModal(false);
      await queryClient.invalidateQueries({ queryKey: ['class-hub', classId] });
      await queryClient.invalidateQueries({ queryKey: ['classes-overview'] });
      await queryClient.invalidateQueries({ queryKey: ['classes'] });
    } catch (err) {
      notify.error(extractApiError(err, 'Unable to save class.'));
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteClass = async () => {
    const preview = await classesService.getDeletionPreview(classId);
    if (!preview?.can_delete) {
      notify.error(preview?.blockers?.[0] || 'This class cannot be deleted right now.');
      return;
    }

    const result = await alert.delete(`class "${hub.name}"`);
    if (!result.isConfirmed) return;

    setSaving(true);
    try {
      await classesService.delete(classId);
      notify.success('Class deleted.');
      await queryClient.invalidateQueries({ queryKey: ['classes-overview'] });
      navigate('/school-admin/classes');
    } catch (err) {
      notify.error(extractApiError(err, 'Unable to delete class.'));
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteStream = async (stream) => {
    const result = await alert.delete(`stream "${stream.name}"`);
    if (!result.isConfirmed) return;

    setSaving(true);
    try {
      await streamsService.delete(stream.id);
      notify.success('Stream deleted.');
      if (streamId === stream.id) {
        setSearchParams({});
      }
      await queryClient.invalidateQueries({ queryKey: ['class-hub', classId] });
      await queryClient.invalidateQueries({ queryKey: ['classes-overview'] });
    } catch (err) {
      notify.error(extractApiError(err, 'Unable to delete stream.'));
    } finally {
      setSaving(false);
    }
  };

  const handleRemovePrefect = async (prefectId) => {
    setSaving(true);
    try {
      await classesService.removePrefect(classId, prefectId);
      notify.success('Class prefect removed.');
      await queryClient.invalidateQueries({ queryKey: ['class-hub', classId] });
    } catch (err) {
      notify.error(extractApiError(err, 'Unable to remove prefect.'));
    } finally {
      setSaving(false);
    }
  };

  const handleAddStream = async () => {
    if (!streamForm.name.trim()) {
      notify.error('Stream name is required.');
      return;
    }
    setSaving(true);
    try {
      await streamsService.create({
        name: streamForm.name.trim(),
        school_class: classId,
        capacity: Number(streamForm.capacity) || 40,
      });
      notify.success('Stream created.');
      setShowStreamModal(false);
      setStreamForm({ name: '', capacity: 40 });
      await queryClient.invalidateQueries({ queryKey: ['class-hub', classId] });
      await queryClient.invalidateQueries({ queryKey: ['classes-overview'] });
    } catch (err) {
      notify.error(extractApiError(err, 'Unable to create stream.'));
    } finally {
      setSaving(false);
    }
  };

  const prefects = hub?.prefects || [];
  const appointedStudentIds = useMemo(
    () => new Set(prefects.map((prefect) => prefect.student_id)),
    [prefects],
  );
  const availableStudents = useMemo(
    () => classStudents.filter((student) => !appointedStudentIds.has(student.id)),
    [classStudents, appointedStudentIds],
  );

  if (isLoading) {
    return (
      <div className="py-5 text-center">
        <ApexLoader label="Loading…" />
      </div>
    );
  }

  if (!canViewHub) {
    return (
      <WorkspaceShell backTo="/school-admin/classes" backLabel="Classes" title="Access denied">
        <div className="alert alert-warning">You do not have permission to view class details.</div>
      </WorkspaceShell>
    );
  }

  if (isError || !hub) {
    return (
      <WorkspaceShell backTo="/school-admin/classes" backLabel="Classes" title="Class not found">
        <div className="alert alert-danger">Unable to load this class.</div>
      </WorkspaceShell>
    );
  }

  const permissions = hub.permissions || {};
  const canManageClass = isSchoolAdmin
    || canWriteFeature('classes')
    || Boolean(permissions.can_write_class ?? hub.can_manage_class);
  const canManageStreams = isSchoolAdmin
    || canWriteFeature('classes')
    || Boolean(permissions.can_manage_streams ?? canManageClass);
  const canManagePrefects = Boolean(permissions.can_manage_prefects ?? hub.can_manage_prefects);
  const canEnrollStudents = isSchoolAdmin
    || Boolean(permissions.can_enroll_students ?? hub.can_enroll_students);

  const streams = hub.streams || [];
  const selectedStream = streams.find((row) => String(row.id) === String(streamId));
  const requiresStreamForEnrollment = hub.has_streams && !streamId;

  const classReturnPath = `/school-admin/classes/${classId}${streamId ? `?stream=${streamId}` : ''}`;

  const buildStudentEnrollUrl = () => {
    const params = new URLSearchParams({
      school_class: classId,
      class_name: hub.name,
      return_to: classReturnPath,
    });
    if (streamId) {
      params.set('stream', streamId);
      params.set('stream_name', selectedStream?.name || hub.selected_stream_name || '');
    }
    return `/school-admin/students/new?${params.toString()}`;
  };

  return (
    <WorkspaceShell
      backTo="/school-admin/classes"
      backLabel="Classes"
      title={hub.scope_label || hub.name}
      subtitle={`${hub.code} · ${hub.academic_year_name}`}
      actions={(
        <div className="d-flex flex-wrap gap-2">
          {canManageClass && (
            <button
              type="button"
              className="btn btn-outline-primary btn-sm d-inline-flex align-items-center gap-1"
              onClick={openEditModal}
            >
              <FiEdit2 size={14} /> Edit class
            </button>
          )}
          {canManageClass && (
            <button
              type="button"
              className="btn btn-outline-danger btn-sm d-inline-flex align-items-center gap-1"
              onClick={handleDeleteClass}
              disabled={saving}
            >
              <FiTrash2 size={14} /> Delete class
            </button>
          )}
        </div>
      )}
    >
      {hub.has_streams && (
        <div className="class-hub-stream-tabs mb-4">
          <button
            type="button"
            className={`class-hub-stream-tab ${!streamId ? 'is-active' : ''}`}
            onClick={() => selectStream('')}
          >
            Whole class
          </button>
          {streams.map((stream) => (
            <button
              key={stream.id}
              type="button"
              className={`class-hub-stream-tab ${String(streamId) === String(stream.id) ? 'is-active' : ''}`}
              onClick={() => selectStream(stream.id)}
            >
              {stream.name}
              <span className="text-muted ms-1">({stream.student_count})</span>
            </button>
          ))}
          {canManageStreams && (
            <button
              type="button"
              className="class-hub-stream-tab class-hub-stream-tab-add"
              onClick={() => setShowStreamModal(true)}
            >
              <FiPlus size={14} /> Add stream
            </button>
          )}
        </div>
      )}

      <div className="row g-3 mb-4">
        <div className="col-md-3">
          <InfoCard label="Class Teacher" value={hub.class_teacher?.display || 'Not assigned'} />
        </div>
        <div className="col-md-3">
          <InfoCard label="Room" value={hub.room_display || 'Not assigned'} />
        </div>
        <div className="col-md-3">
          <InfoCard
            label="Students"
            value={hub.student_count ?? 0}
            hint={`Capacity ${hub.capacity || '—'}`}
          />
        </div>
        <div className="col-md-3">
          <InfoCard
            label="Level"
            value={LEVEL_LABELS[hub.level_type] || hub.level_type || '—'}
            hint={hub.curriculum ? hub.curriculum.toUpperCase() : undefined}
          />
        </div>
      </div>

      <div className="row g-4">
        <div className="col-lg-5">
          <WorkspaceSection
            title="Class Prefects"
            description={prefects.length ? 'Student leaders for this class or stream' : 'No prefects appointed yet'}
            icon={FiAward}
            actions={canManagePrefects && (
              <button
                type="button"
                className="btn btn-sm btn-primary d-inline-flex align-items-center gap-1"
                onClick={() => setShowPrefectModal(true)}
                disabled={!availableStudents.length && showPrefectModal}
              >
                <FiPlus size={14} /> Add prefect
              </button>
            )}
          >
            {prefects.length ? (
              <div className="list-group list-group-flush">
                {prefects.map((prefect) => (
                  <div key={prefect.id} className="list-group-item d-flex align-items-center justify-content-between px-0">
                    <div>
                      <div className="fw-medium">{prefect.student_name}</div>
                      <div className="text-muted small">
                        {prefect.role_display}
                        {prefect.stream_name ? ` · ${prefect.stream_name}` : ''}
                        {prefect.admission_number ? ` · ${prefect.admission_number}` : ''}
                      </div>
                    </div>
                    {canManagePrefects && (
                      <button
                        type="button"
                        className="btn btn-sm btn-outline-danger"
                        disabled={saving}
                        onClick={() => handleRemovePrefect(prefect.id)}
                      >
                        <FiTrash2 size={14} />
                      </button>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <ModuleEmptyState
                title="No prefects yet"
                message={
                  canManagePrefects
                    ? 'Appoint multiple head, deputy, or class prefects from the student list.'
                    : 'Prefects can be appointed by the class teacher, Director of Studies, or school admin.'
                }
                actionLabel={canManagePrefects && availableStudents.length ? 'Add prefect' : undefined}
                onAction={canManagePrefects && availableStudents.length ? () => setShowPrefectModal(true) : undefined}
              />
            )}
          </WorkspaceSection>
        </div>

        <div className="col-lg-7">
          <WorkspaceSection
            title="Class List"
            description={`${hub.student_count ?? 0} active student${hub.student_count === 1 ? '' : 's'}`}
            icon={FiUsers}
            actions={(
              <div className="d-flex flex-wrap gap-2">
                {canEnrollStudents && !requiresStreamForEnrollment && (
                  <>
                    <button
                      type="button"
                      className="btn btn-sm btn-primary d-inline-flex align-items-center gap-1"
                      onClick={() => navigate(buildStudentEnrollUrl())}
                    >
                      <FiUserPlus size={14} /> Add student
                    </button>
                    <button
                      type="button"
                      className="btn btn-sm btn-outline-primary d-inline-flex align-items-center gap-1"
                      onClick={() => setShowStudentImport(true)}
                    >
                      <FiUpload size={14} /> Import students
                    </button>
                  </>
                )}
                <Link to={`/school-admin/students?school_class=${classId}${streamId ? `&stream=${streamId}` : ''}`} className="btn btn-sm btn-outline-secondary">
                  Open in Students <FiChevronRight size={14} />
                </Link>
              </div>
            )}
          >
            {(hub.students || []).length ? (
              <DataTable
                columns={studentColumns}
                data={hub.students}
                embedded
                searchPlaceholder="Search class list…"
                onRowClick={(row) => navigate(`/school-admin/students/${row.id}`)}
                emptyState={<ModuleEmptyState title="No students" message="No active students in this scope." />}
              />
            ) : (
              <ModuleEmptyState
                title="No students enrolled"
                message={
                  requiresStreamForEnrollment
                    ? 'Select a stream above before enrolling students into this class.'
                    : canEnrollStudents
                      ? 'Add students one at a time or import many using the minimal Excel template.'
                      : 'Students assigned to this class or stream will appear here.'
                }
                actionLabel={
                  canEnrollStudents && !requiresStreamForEnrollment
                    ? 'Add student'
                    : undefined
                }
                onAction={
                  canEnrollStudents && !requiresStreamForEnrollment
                    ? () => navigate(buildStudentEnrollUrl())
                    : undefined
                }
              />
            )}
          </WorkspaceSection>
        </div>
      </div>

      {hub.has_streams && canManageStreams && streamId && (
        <WorkspaceSection
          title="Manage stream"
          description="Remove this stream when it is no longer needed"
          icon={FiBookOpen}
          className="mt-4"
          actions={(
            <button
              type="button"
              className="btn btn-sm btn-outline-danger"
              onClick={() => handleDeleteStream(streams.find((row) => row.id === streamId))}
              disabled={saving}
            >
              <FiTrash2 size={14} /> Delete stream
            </button>
          )}
        >
          <p className="text-muted small mb-0">
            Deleting a stream is only allowed when no students remain assigned to it.
          </p>
        </WorkspaceSection>
      )}

      {!hub.has_streams && canManageStreams && (
        <WorkspaceSection
          title="Streams"
          description="Divide this class into streams when needed"
          icon={FiBookOpen}
          className="mt-4"
          actions={(
            <button type="button" className="btn btn-sm btn-outline-primary" onClick={() => setShowStreamModal(true)}>
              <FiPlus size={14} /> Add stream
            </button>
          )}
        >
          <p className="text-muted small mb-0">
            This class has no streams yet. Add streams such as East, West, A, or B to organize students underneath the class.
          </p>
        </WorkspaceSection>
      )}

      <Modal
        show={showPrefectModal}
        onHide={() => setShowPrefectModal(false)}
        title="Appoint class prefect"
        footer={(
          <div className="d-flex gap-2 ms-auto">
            <button
              type="button"
              className="btn btn-outline-primary"
              onClick={() => handleAddPrefect({ addAnother: true })}
              disabled={saving || !availableStudents.length}
            >
              {saving ? 'Saving…' : 'Save & add another'}
            </button>
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => handleAddPrefect()}
              disabled={saving || !availableStudents.length}
            >
              {saving ? 'Saving…' : 'Appoint prefect'}
            </button>
          </div>
        )}
      >
        <div className="row g-3">
          <div className="col-12">
            <label className="form-label small fw-medium">Student *</label>
            <select
              className="form-select"
              value={prefectForm.student}
              onChange={(e) => setPrefectForm({ ...prefectForm, student: e.target.value })}
            >
              <option value="">Select student</option>
              {availableStudents.map((student) => (
                <option key={student.id} value={student.id}>
                  {student.full_name} ({student.admission_number})
                </option>
              ))}
            </select>
            {!availableStudents.length && (
              <div className="form-text">All students in this scope already have a prefect appointment.</div>
            )}
          </div>
          <div className="col-12">
            <label className="form-label small fw-medium">Role</label>
            <select
              className="form-select"
              value={prefectForm.role}
              onChange={(e) => setPrefectForm({ ...prefectForm, role: e.target.value })}
            >
              {PREFECT_ROLES.map((role) => (
                <option key={role.value} value={role.value}>{role.label}</option>
              ))}
            </select>
          </div>
        </div>
      </Modal>

      {requiresStreamForEnrollment && canEnrollStudents && (
        <div className="alert alert-info py-2 small mt-3">
          This class has streams. Select a stream tab above to enroll students into the correct group.
        </div>
      )}

      <StudentBulkImportWizard
        show={showStudentImport}
        onHide={() => setShowStudentImport(false)}
        importService={studentBulkImport}
        title="Import students into class"
        presetClassId={classId}
        presetStreamId={streamId}
        presetClassName={hub.name}
        presetStreamName={selectedStream?.name || ''}
        presetRequiresStream={hub.has_streams && Boolean(streamId)}
        onSuccess={(result) => {
          notify.success(result?.message || 'Students imported successfully.');
          queryClient.invalidateQueries({ queryKey: ['class-hub', classId] });
          queryClient.invalidateQueries({ queryKey: ['classes-overview'] });
          queryClient.invalidateQueries({ queryKey: ['students'] });
        }}
      />

      <Modal
        show={showEditModal}
        onHide={() => setShowEditModal(false)}
        title="Edit class"
        size="lg"
        footer={(
          <button type="button" className="btn btn-primary ms-auto" onClick={handleSaveClass} disabled={saving}>
            {saving ? 'Saving…' : 'Save class'}
          </button>
        )}
      >
        <div className="row g-3">
          <div className="col-md-6">
            <label className="form-label small fw-medium">Class Name *</label>
            <input className="form-control" value={classForm.name} onChange={(e) => setClassForm({ ...classForm, name: e.target.value })} />
          </div>
          <div className="col-md-6">
            <label className="form-label small fw-medium">Class Code *</label>
            <input className="form-control" value={classForm.code} onChange={(e) => setClassForm({ ...classForm, code: e.target.value })} />
          </div>
          <div className="col-md-6">
            <label className="form-label small fw-medium">Academic Year *</label>
            <select className="form-select" value={classForm.academic_year} onChange={(e) => setClassForm({ ...classForm, academic_year: e.target.value })}>
              <option value="">Select year</option>
              {years.map((year) => (
                <option key={year.id} value={year.id}>{year.name}{year.is_current ? ' (current)' : ''}</option>
              ))}
            </select>
          </div>
          <div className="col-md-6">
            <label className="form-label small fw-medium">Class Teacher</label>
            <select className="form-select" value={classForm.class_teacher} onChange={(e) => setClassForm({ ...classForm, class_teacher: e.target.value })}>
              <option value="">Not assigned</option>
              {teachers.map((teacher) => (
                <option key={teacher.value} value={teacher.value}>{teacher.label}</option>
              ))}
            </select>
          </div>
          <div className="col-md-4">
            <label className="form-label small fw-medium">Level</label>
            <select className="form-select" value={classForm.level_type} onChange={(e) => setClassForm({ ...classForm, level_type: e.target.value })}>
              {LEVEL_OPTIONS.map((option) => (
                <option key={option.value || 'na'} value={option.value}>{option.label}</option>
              ))}
            </select>
          </div>
          <div className="col-md-4">
            <label className="form-label small fw-medium">Curriculum</label>
            <select className="form-select" value={classForm.curriculum} onChange={(e) => setClassForm({ ...classForm, curriculum: e.target.value })}>
              {CURRICULUM_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>{option.label}</option>
              ))}
            </select>
          </div>
          <div className="col-md-4">
            <label className="form-label small fw-medium">Section</label>
            <input className="form-control" value={classForm.section} onChange={(e) => setClassForm({ ...classForm, section: e.target.value })} />
          </div>
          <div className="col-md-4">
            <label className="form-label small fw-medium">Capacity</label>
            <input type="number" className="form-control" value={classForm.capacity} onChange={(e) => setClassForm({ ...classForm, capacity: Number(e.target.value) })} />
          </div>
          <div className="col-md-8">
            <label className="form-label small fw-medium">Room</label>
            <input className="form-control" value={classForm.room} onChange={(e) => setClassForm({ ...classForm, room: e.target.value })} />
          </div>
        </div>
      </Modal>

      <Modal
        show={showStreamModal}
        onHide={() => setShowStreamModal(false)}
        title="Add stream"
        footer={(
          <button type="button" className="btn btn-primary ms-auto" onClick={handleAddStream} disabled={saving}>
            {saving ? 'Saving…' : 'Create stream'}
          </button>
        )}
      >
        <div className="row g-3">
          <div className="col-12">
            <label className="form-label small fw-medium">Stream name *</label>
            <input
              className="form-control"
              value={streamForm.name}
              onChange={(e) => setStreamForm({ ...streamForm, name: e.target.value })}
              placeholder="e.g. East, A, Science"
            />
          </div>
          <div className="col-12">
            <label className="form-label small fw-medium">Capacity</label>
            <input
              type="number"
              className="form-control"
              value={streamForm.capacity}
              onChange={(e) => setStreamForm({ ...streamForm, capacity: Number(e.target.value) })}
            />
          </div>
        </div>
      </Modal>
    </WorkspaceShell>
  );
}

export default ClassDetail;