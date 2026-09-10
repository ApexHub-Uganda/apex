import { useEffect, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { FiArrowLeft, FiCheckSquare, FiMapPin, FiSave, FiUsers } from 'react-icons/fi';
import PageHeader from '../../components/PageHeader';
import ModuleEmptyState from '../../components/ModuleEmptyState';
import { classAttendanceService } from '../../services/moduleService';
import { usePermissions } from '../../hooks/usePermissions';
import { extractApiError, notify } from '../../utils/notify';
import { PageLoader } from '../../components/ApexLoader';
import { formatAccuracy, getAttendancePosition, isSecureGeolocationContext } from '../../utils/geolocation';

function nowDefaults() {
  const current = new Date();
  return {
    date: current.toISOString().slice(0, 10),
    check_in: current.toTimeString().slice(0, 5),
  };
}

export function ClassAttendance({ initialClassId = '' }) {
  const [searchParams] = useSearchParams();
  const classFromQuery = searchParams.get('class') || '';
  const { canWriteFeature } = usePermissions();
  const canMark = canWriteFeature('student_attendance');
  const defaults = useMemo(() => nowDefaults(), []);

  const [schoolClass, setSchoolClass] = useState(initialClassId || classFromQuery || '');
  const [stream, setStream] = useState('');
  const [date, setDate] = useState(defaults.date);
  const [checkIn, setCheckIn] = useState(defaults.check_in);
  const [presentMap, setPresentMap] = useState({});
  const [saving, setSaving] = useState(false);

  const queryParams = useMemo(() => ({
    school_class: schoolClass || undefined,
    stream: stream || undefined,
    date: date || undefined,
  }), [schoolClass, stream, date]);

  const { data: options, isLoading, isError, refetch } = useQuery({
    queryKey: ['class-attendance-options', queryParams],
    queryFn: () => classAttendanceService.getOptions(queryParams),
    staleTime: 30_000,
  });

  const classes = options?.classes || [];
  const streams = options?.streams || [];
  const requiresStream = Boolean(options?.requires_stream);
  const students = options?.students || [];
  const attendance = options?.attendance || {};
  const scopeMeta = options?.scope_meta;

  useEffect(() => {
    if (options?.defaults?.date && !date) {
      setDate(options.defaults.date);
    }
    if (options?.defaults?.check_in && !checkIn) {
      setCheckIn(String(options.defaults.check_in).slice(0, 5));
    }
  }, [options?.defaults, date, checkIn]);

  useEffect(() => {
    if (!students.length) {
      setPresentMap({});
      return;
    }
    const next = {};
    students.forEach((student) => {
      const existing = attendance[student.id];
      next[student.id] = existing ? existing.status !== 'absent' : true;
    });
    setPresentMap(next);
  }, [students, attendance]);

  useEffect(() => {
    if (!schoolClass && classes.length === 1) {
      setSchoolClass(classes[0].value);
    }
  }, [classes, schoolClass]);

  const selectedClass = classes.find((row) => row.value === schoolClass);
  const showClassPicker = !schoolClass && classes.length > 1;
  const showStreamPicker = schoolClass && requiresStream && !stream;
  const readyToMark = schoolClass && (!requiresStream || stream) && students.length > 0;

  const handleSelectClass = (classId) => {
    setSchoolClass(classId);
    setStream('');
    setPresentMap({});
  };

  const handleSelectStream = (streamId) => {
    setStream(streamId);
    setPresentMap({});
  };

  const toggleAll = (checked) => {
    const next = {};
    students.forEach((student) => {
      next[student.id] = checked;
    });
    setPresentMap(next);
  };

  const geofenceEnforced = Boolean(scopeMeta?.geofence_enforced);

  const handleSave = async () => {
    if (!schoolClass || !date) {
      notify.warning('Select a class and date.');
      return;
    }
    if (requiresStream && !stream) {
      notify.warning('Select a stream for this class.');
      return;
    }
    setSaving(true);
    try {
      let geoPayload = {};
      if (geofenceEnforced) {
        if (!isSecureGeolocationContext()) {
          throw new Error('Campus check needs HTTPS. Open this portal with https:// on your phone.');
        }
        notify.info('Getting a precise GPS fix for campus check… (may take up to ~30s outdoors)');
        const fix = await getAttendancePosition();
        geoPayload = {
          lat: fix.lat,
          lng: fix.lng,
          accuracy_m: fix.accuracy_m,
        };
      }
      const result = await classAttendanceService.saveBulk({
        school_class: schoolClass,
        stream: stream || undefined,
        date,
        check_in: checkIn,
        ...geoPayload,
        entries: students.map((student) => ({
          student: student.id,
          present: Boolean(presentMap[student.id]),
        })),
      });
      const accuracyNote = geoPayload.accuracy_m != null
        ? ` (GPS accuracy ${formatAccuracy(geoPayload.accuracy_m)})`
        : '';
      notify.success((result?.message || 'Attendance saved.') + accuracyNote);
      await refetch();
    } catch (err) {
      // Geolocation failures raise Error; API failures use axios response
      const msg = err?.response
        ? extractApiError(err, 'Unable to save attendance.')
        : (err?.message || extractApiError(err, 'Unable to save attendance.'));
      notify.error(msg);
    } finally {
      setSaving(false);
    }
  };

  const presentCount = students.filter((student) => presentMap[student.id]).length;

  return (
    <div>
      <div className="mb-3">
        <Link to="/school-admin/attendance" className="small text-decoration-none text-muted">
          <FiArrowLeft className="me-1" /> Attendance
        </Link>
      </div>

      <PageHeader
        title="Student Attendance"
        subtitle="Pick your class, choose a stream when the class has one, then mark students present with checkboxes."
        actions={readyToMark && canMark && (
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

      {geofenceEnforced && (
        <div className="alert alert-warning small mb-4 d-flex align-items-start gap-2">
          <FiMapPin className="mt-1 flex-shrink-0" />
          <div>
            <strong>Campus location required.</strong>{' '}
            Saving attendance will use your device GPS. You must be inside the school boundary
            {scopeMeta?.geofence?.buffer_meters != null
              ? ` (buffer ±${scopeMeta.geofence.buffer_meters} m)`
              : ''}
            .
          </div>
        </div>
      )}

      {scopeMeta?.is_teacher_scoped && (
        <div className="alert alert-info small mb-4">
          Showing only classes linked to your teaching assignments or class-teacher role.
        </div>
      )}

      {showClassPicker && (
        <div className="mb-4">
          <h5 className="fw-semibold mb-3">Choose a class</h5>
          {isLoading && !options ? (
            <PageLoader label="Loading classes…" compact />
          ) : classes.length === 0 ? (
            <div className="apex-card p-5">
              <ModuleEmptyState
                title="No classes available"
                message="You do not have any classes assigned for attendance marking yet."
              />
            </div>
          ) : (
            <div className="row g-3">
              {classes.map((classRow) => (
                <div className="col-md-6 col-lg-4" key={classRow.value}>
                  <button
                    type="button"
                    className={`assignment-workflow-card w-100 text-start border-0 bg-white ${schoolClass === classRow.value ? 'border border-primary' : ''}`}
                    onClick={() => handleSelectClass(classRow.value)}
                  >
                    <div className="apex-card p-4 h-100">
                      <div className="d-flex align-items-start gap-3">
                        <div className="assignment-workflow-icon">
                          <FiUsers size={20} />
                        </div>
                        <div>
                          <h5 className="fw-semibold mb-1">{classRow.label}</h5>
                          <p className="text-muted small mb-2">
                            {classRow.student_count} active student{classRow.student_count === 1 ? '' : 's'}
                            {classRow.has_streams ? ` · ${classRow.stream_count} stream${classRow.stream_count === 1 ? '' : 's'}` : ''}
                          </p>
                          {classRow.is_class_teacher && (
                            <span className="badge text-bg-primary-subtle border text-primary">Class teacher</span>
                          )}
                        </div>
                      </div>
                    </div>
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {schoolClass && (
        <div className="apex-card p-4 mb-4">
          <div className="d-flex flex-wrap align-items-center justify-content-between gap-2 mb-3">
            <div>
              <h5 className="fw-semibold mb-0">{selectedClass?.label || 'Selected class'}</h5>
              {classes.length > 1 && (
                <button
                  type="button"
                  className="btn btn-link btn-sm px-0"
                  onClick={() => { setSchoolClass(''); setStream(''); }}
                >
                  Change class
                </button>
              )}
            </div>
          </div>

          {showStreamPicker && (
            <div className="mb-3">
              <label className="form-label small fw-semibold">Stream</label>
              <div className="row g-2">
                {streams.map((streamRow) => (
                  <div className="col-md-6 col-lg-4" key={streamRow.value}>
                    <button
                      type="button"
                      className={`btn w-100 text-start ${stream === streamRow.value ? 'btn-primary' : 'btn-outline-secondary'}`}
                      onClick={() => handleSelectStream(streamRow.value)}
                    >
                      <div className="fw-semibold">{streamRow.label}</div>
                      <div className="small opacity-75">
                        {streamRow.student_count} student{streamRow.student_count === 1 ? '' : 's'}
                      </div>
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {stream && requiresStream && (
            <div className="mb-3">
              <span className="badge text-bg-light border me-2">
                Stream: {streams.find((row) => row.value === stream)?.label}
              </span>
              <button type="button" className="btn btn-link btn-sm px-0" onClick={() => setStream('')}>
                Change stream
              </button>
            </div>
          )}

          <div className="row g-3">
            <div className="col-md-4">
              <label className="form-label small fw-semibold" htmlFor="attendance-date">Date</label>
              <input
                id="attendance-date"
                type="date"
                className="form-control"
                value={date}
                onChange={(e) => setDate(e.target.value)}
              />
            </div>
            <div className="col-md-4">
              <label className="form-label small fw-semibold" htmlFor="attendance-time">Check-in time</label>
              <input
                id="attendance-time"
                type="time"
                className="form-control"
                value={checkIn}
                onChange={(e) => setCheckIn(e.target.value)}
              />
            </div>
            <div className="col-md-4 d-flex align-items-end">
              <div className="small text-muted">
                Defaults to the current date and time when you save.
              </div>
            </div>
          </div>
        </div>
      )}

      {isError && (
        <div className="alert alert-danger">Unable to load attendance data. Please try again.</div>
      )}

      {schoolClass && requiresStream && !stream && !isLoading && (
        <div className="apex-card p-5">
          <ModuleEmptyState
            icon={FiCheckSquare}
            title="Select a stream"
            message="This class is divided into streams. Choose the stream you are marking attendance for."
          />
        </div>
      )}

      {readyToMark && (
        <div className="apex-card p-0 overflow-hidden">
          <div className="p-4 border-bottom bg-light-subtle d-flex flex-wrap align-items-center justify-content-between gap-2">
            <div>
              <h5 className="fw-bold mb-1">Mark students present</h5>
              <p className="text-muted small mb-0">
                {presentCount} of {students.length} marked present
              </p>
            </div>
            {canMark && (
              <div className="d-flex gap-2">
                <button type="button" className="btn btn-outline-secondary btn-sm" onClick={() => toggleAll(true)}>
                  Check all
                </button>
                <button type="button" className="btn btn-outline-secondary btn-sm" onClick={() => toggleAll(false)}>
                  Uncheck all
                </button>
              </div>
            )}
          </div>

          <div className="apex-sheet-scroll">
            <table className="table table-hover mb-0 align-middle">
              <thead className="table-light">
                <tr>
                  <th style={{ width: 48 }}>#</th>
                  <th style={{ width: 56 }}>Present</th>
                  <th>Student</th>
                  <th>Admission</th>
                  <th>Stream</th>
                </tr>
              </thead>
              <tbody>
                {students.map((student, idx) => (
                  <tr key={student.id}>
                    <td className="text-muted">{idx + 1}</td>
                    <td>
                      <input
                        type="checkbox"
                        className="form-check-input"
                        disabled={!canMark}
                        checked={Boolean(presentMap[student.id])}
                        onChange={(e) => setPresentMap((prev) => ({
                          ...prev,
                          [student.id]: e.target.checked,
                        }))}
                        aria-label={`Mark ${student.full_name} present`}
                      />
                    </td>
                    <td className="fw-medium">{student.full_name}</td>
                    <td className="text-muted small">{student.admission_number}</td>
                    <td className="text-muted small">{student.stream_name || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {canMark && (
            <div className="p-3 border-top d-flex justify-content-end">
              <button
                type="button"
                className="btn btn-primary d-inline-flex align-items-center gap-1"
                onClick={handleSave}
                disabled={saving}
              >
                <FiSave size={16} /> {saving ? 'Saving…' : 'Save attendance'}
              </button>
            </div>
          )}
        </div>
      )}

      {schoolClass && (!requiresStream || stream) && !isLoading && students.length === 0 && (
        <div className="apex-card p-5">
          <ModuleEmptyState
            title="No active students"
            message="There are no active students in this class or stream."
          />
        </div>
      )}
    </div>
  );
}

export default ClassAttendance;