import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { FiArrowLeft, FiSave } from 'react-icons/fi';
import PageHeader from '../../components/PageHeader';
import ModuleEmptyState from '../../components/ModuleEmptyState';
import {
  classesService,
  lessonAttendanceBulkService,
  studentsService,
  subjectsService,
} from '../../services/moduleService';
import { usePermissions } from '../../hooks/usePermissions';
import { extractApiError, notify } from '../../utils/notify';

const STATUS_OPTIONS = [
  { value: 'present', label: 'Present' },
  { value: 'absent', label: 'Absent' },
  { value: 'late', label: 'Late' },
  { value: 'excused', label: 'Excused' },
];

export function LessonAttendance() {
  const { canWriteFeature } = usePermissions();
  const canMark = canWriteFeature('lesson_attendance');
  const today = useMemo(() => new Date().toISOString().slice(0, 10), []);
  const [schoolClass, setSchoolClass] = useState('');
  const [subject, setSubject] = useState('');
  const [date, setDate] = useState(today);
  const [statuses, setStatuses] = useState({});
  const [saving, setSaving] = useState(false);

  const { data: classes = [] } = useQuery({
    queryKey: ['lesson-attendance-classes'],
    queryFn: () => classesService.list(),
    staleTime: 60_000,
  });

  const { data: subjects = [] } = useQuery({
    queryKey: ['lesson-attendance-subjects'],
    queryFn: () => subjectsService.list(),
    staleTime: 60_000,
  });

  const { data: students = [], isLoading: studentsLoading } = useQuery({
    queryKey: ['lesson-attendance-students', schoolClass],
    queryFn: () => studentsService.list({ school_class: schoolClass, status: 'active' }),
    enabled: Boolean(schoolClass),
    staleTime: 30_000,
  });

  const handleSave = async () => {
    if (!schoolClass || !subject || !date) {
      notify.warning('Select class, subject, and date.');
      return;
    }
    setSaving(true);
    try {
      const entries = students.map((s) => ({
        student: s.id,
        status: statuses[s.id] || 'present',
      }));
      const result = await lessonAttendanceBulkService.save({
        school_class: schoolClass,
        subject,
        date,
        entries,
      });
      notify.success(result?.message || 'Lesson attendance saved.');
    } catch (err) {
      notify.error(extractApiError(err, 'Unable to save attendance.'));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div>
      <div className="mb-3">
        <Link to="/school-admin/attendance" className="small text-decoration-none text-muted">
          <FiArrowLeft className="me-1" /> Attendance
        </Link>
      </div>

      <PageHeader
        title="Lesson Attendance"
        subtitle="Mark attendance per subject lesson session"
        actions={canMark && students.length > 0 && (
          <button
            type="button"
            className="btn btn-primary btn-sm d-inline-flex align-items-center gap-1"
            onClick={handleSave}
            disabled={saving}
          >
            <FiSave size={14} /> {saving ? 'Saving…' : 'Save attendance'}
          </button>
        )}
      />

      <div className="apex-card p-4 mb-4">
        <div className="row g-3">
          <div className="col-md-4">
            <label className="form-label small fw-semibold" htmlFor="lesson-class">Class</label>
            <select
              id="lesson-class"
              className="form-select"
              value={schoolClass}
              onChange={(e) => { setSchoolClass(e.target.value); setStatuses({}); }}
            >
              <option value="">Select class…</option>
              {classes.map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
          </div>
          <div className="col-md-4">
            <label className="form-label small fw-semibold" htmlFor="lesson-subject">Subject</label>
            <select
              id="lesson-subject"
              className="form-select"
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
            >
              <option value="">Select subject…</option>
              {subjects.map((s) => (
                <option key={s.id} value={s.id}>{s.name}</option>
              ))}
            </select>
          </div>
          <div className="col-md-4">
            <label className="form-label small fw-semibold" htmlFor="lesson-date">Date</label>
            <input
              id="lesson-date"
              type="date"
              className="form-control"
              value={date}
              onChange={(e) => setDate(e.target.value)}
            />
          </div>
        </div>
      </div>

      {!schoolClass ? (
        <div className="apex-card p-5">
          <ModuleEmptyState title="Select a class" message="Choose a class and subject to mark lesson attendance." />
        </div>
      ) : studentsLoading ? (
        <div className="py-5 text-center"><div className="spinner-border text-primary" role="status" /></div>
      ) : students.length === 0 ? (
        <div className="apex-card p-5">
          <ModuleEmptyState title="No students" message="No active students in this class." />
        </div>
      ) : (
        <div className="apex-card p-0 overflow-hidden">
          <div className="table-responsive">
            <table className="table table-hover mb-0 align-middle">
              <thead className="table-light">
                <tr>
                  <th>#</th>
                  <th>Student</th>
                  <th>Admission</th>
                  <th style={{ width: 160 }}>Status</th>
                </tr>
              </thead>
              <tbody>
                {students.map((student, idx) => (
                  <tr key={student.id}>
                    <td className="text-muted">{idx + 1}</td>
                    <td className="fw-medium">{student.full_name}</td>
                    <td className="text-muted small">{student.admission_number}</td>
                    <td>
                      <select
                        className="form-select form-select-sm"
                        disabled={!canMark}
                        value={statuses[student.id] || 'present'}
                        onChange={(e) => setStatuses((p) => ({ ...p, [student.id]: e.target.value }))}
                      >
                        {STATUS_OPTIONS.map((o) => (
                          <option key={o.value} value={o.value}>{o.label}</option>
                        ))}
                      </select>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

export default LessonAttendance;