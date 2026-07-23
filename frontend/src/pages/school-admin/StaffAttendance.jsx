import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { FiArrowLeft, FiCheckCircle, FiLogIn, FiLogOut, FiMapPin, FiNavigation } from 'react-icons/fi';
import PageHeader from '../../components/PageHeader';
import SchoolBoundaryMap from '../../components/SchoolBoundaryMap';
import { staffGeoAttendanceService } from '../../services/moduleService';
import { formatAccuracy, getAttendancePosition, getCurrentPosition } from '../../utils/geolocation';
import { extractApiError, notify } from '../../utils/notify';
import { ApexLoader } from '../../components/ApexLoader';

/**
 * Staff self check-in / check-out using free browser GPS + school geofence.
 */
export function StaffAttendance() {
  const queryClient = useQueryClient();
  const [busy, setBusy] = useState(false);
  const [lastFix, setLastFix] = useState(null);

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['staff-attendance-status'],
    queryFn: () => staffGeoAttendanceService.status(),
    staleTime: 15_000,
    refetchInterval: 60_000,
  });

  const geofence = data?.geofence || {};
  const vertices = geofence.vertices || [];

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['staff-attendance-status'] });

  const checkIn = useMutation({
    mutationFn: async () => {
      setBusy(true);
      notify.info('Getting a precise GPS fix… (usually a few seconds)');
      const fix = await getAttendancePosition({
        onUpdate: (partial) => setLastFix(partial),
      });
      setLastFix(fix);
      return staffGeoAttendanceService.checkIn({
        lat: fix.lat,
        lng: fix.lng,
        accuracy_m: fix.accuracy_m,
      });
    },
    onSuccess: (res) => {
      notify.success(res?.message || 'Signed in.');
      invalidate();
    },
    onError: (err) => notify.error(err?.response ? extractApiError(err, 'Sign-in failed.') : (err?.message || 'Sign-in failed.')),
    onSettled: () => setBusy(false),
  });

  const checkOut = useMutation({
    mutationFn: async () => {
      setBusy(true);
      let payload = {};
      try {
        const fix = await getAttendancePosition({
          maxWaitMs: 8_000,
          onUpdate: (partial) => setLastFix(partial),
        });
        setLastFix(fix);
        payload = { lat: fix.lat, lng: fix.lng, accuracy_m: fix.accuracy_m };
      } catch {
        // Check-out can proceed without GPS if geofence is off; backend decides
      }
      return staffGeoAttendanceService.checkOut(payload);
    },
    onSuccess: (res) => {
      notify.success(res?.message || 'Signed out.');
      invalidate();
    },
    onError: (err) => notify.error(err?.response ? extractApiError(err, 'Sign-out failed.') : (err?.message || 'Sign-out failed.')),
    onSettled: () => setBusy(false),
  });

  const previewLocation = async () => {
    setBusy(true);
    try {
      notify.info('Refining GPS accuracy…');
      const fix = await getAttendancePosition({
        onUpdate: (partial) => setLastFix(partial),
      });
      setLastFix(fix);
      const evaluation = await staffGeoAttendanceService.checkLocation({
        lat: fix.lat,
        lng: fix.lng,
        accuracy_m: fix.accuracy_m,
      });
      if (evaluation?.allowed) {
        notify.success(
          `${evaluation.reason || 'Within school perimeter.'} · accuracy ${formatAccuracy(fix.accuracy_m)}`,
        );
      } else {
        notify.error(evaluation?.reason || 'Outside school perimeter.');
      }
    } catch (err) {
      notify.error(err.message || extractApiError(err, 'Unable to read location.'));
    } finally {
      setBusy(false);
    }
  };

  if (isLoading) {
    return (
      <div className="py-5 text-center"><ApexLoader label="Loading attendance…" /></div>
    );
  }

  const canCheckIn = data?.has_staff_profile && !data?.checked_in;
  const canCheckOut = data?.has_staff_profile && data?.checked_in && !data?.checked_out;

  return (
    <div>
      <div className="mb-3">
        <Link to="/school-admin/attendance" className="small text-decoration-none text-muted">
          <FiArrowLeft className="me-1" /> Attendance
        </Link>
      </div>

      <PageHeader
        title="Staff attendance"
        subtitle="Sign in with your phone’s GPS. When the school boundary is enabled, you must be on campus."
        actions={(
          <button type="button" className="btn btn-outline-secondary btn-sm" onClick={() => refetch()}>
            Refresh
          </button>
        )}
      />

      {!data?.has_staff_profile && (
        <div className="alert alert-warning">
          No staff HR profile is linked to your account. Ask admin to link your portal user to a staff record.
        </div>
      )}

      <div className="row g-4">
        <div className="col-lg-5">
          <div className="apex-card p-4">
            <h6 className="fw-semibold mb-3">Today — {data?.date}</h6>
            <div className="mb-3">
              <div className="small text-muted">Status</div>
              <div className="fw-semibold">
                {data?.checked_out
                  ? 'Signed out'
                  : data?.checked_in
                    ? 'Signed in'
                    : 'Not signed in'}
              </div>
            </div>
            <div className="row g-2 mb-3">
              <div className="col-6">
                <div className="small text-muted">Check-in</div>
                <div className="fw-medium">{data?.check_in || '—'}</div>
              </div>
              <div className="col-6">
                <div className="small text-muted">Check-out</div>
                <div className="fw-medium">{data?.check_out || '—'}</div>
              </div>
            </div>

            {geofence?.is_enabled ? (
              <div className="alert alert-info small py-2">
                <FiMapPin className="me-1" />
                Campus geofence is <strong>on</strong>
                {geofence.buffer_meters != null ? ` (buffer ±${geofence.buffer_meters} m)` : ''}.
              </div>
            ) : (
              <div className="alert alert-secondary small py-2">
                Campus geofence is not enforced yet. Admin can set it under Settings → School boundary.
              </div>
            )}

            {lastFix && (
              <div className="small text-muted mb-3">
                Last GPS: {lastFix.lat.toFixed(5)}, {lastFix.lng.toFixed(5)} · accuracy{' '}
                <strong className={Number(lastFix.accuracy_m) > 280 ? 'text-warning' : 'text-success'}>
                  {formatAccuracy(lastFix.accuracy_m)}
                </strong>
                {busy && Number(lastFix.accuracy_m) > 80 ? (
                  <span className="ms-1">(refining…)</span>
                ) : null}
              </div>
            )}
            <p className="small text-muted mb-3">
              Tip: use <strong>High accuracy / GPS</strong> location mode, allow <strong>precise location</strong>,
              and stand outdoors for a few seconds. The first reading is often ±1000–2000 m; we wait for a sharper fix.
            </p>

            <div className="d-grid gap-2">
              <button
                type="button"
                className="btn btn-primary d-inline-flex align-items-center justify-content-center gap-2"
                disabled={busy || !canCheckIn}
                onClick={() => checkIn.mutate()}
              >
                <FiLogIn size={16} />
                {busy && checkIn.isPending ? 'Signing in…' : 'Sign in'}
              </button>
              <button
                type="button"
                className="btn btn-outline-primary d-inline-flex align-items-center justify-content-center gap-2"
                disabled={busy || !canCheckOut}
                onClick={() => checkOut.mutate()}
              >
                <FiLogOut size={16} />
                {busy && checkOut.isPending ? 'Signing out…' : 'Sign out'}
              </button>
              <button
                type="button"
                className="btn btn-outline-secondary btn-sm d-inline-flex align-items-center justify-content-center gap-2"
                disabled={busy}
                onClick={previewLocation}
              >
                <FiNavigation size={14} />
                Check if I&apos;m inside campus
              </button>
            </div>

            {data?.checked_in && !data?.checked_out && (
              <p className="text-success small mt-3 mb-0 d-flex align-items-center gap-1">
                <FiCheckCircle /> You are signed in for today.
              </p>
            )}
          </div>
        </div>

        <div className="col-lg-7">
          <div className="apex-card p-3 p-md-4">
            <h6 className="fw-semibold mb-3">Campus map</h6>
            {vertices.length >= 3 ? (
              <SchoolBoundaryMap
                vertices={vertices}
                interactive={false}
                locateUser={false}
                showUserMarker={false}
                height={360}
              />
            ) : (
              <div className="border rounded p-5 text-center text-muted small">
                No school boundary polygon is configured yet.
                {data?.geofence && (
                  <div className="mt-2">
                    <Link to="/school-admin/settings/school-boundary">Set school boundary</Link>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default StaffAttendance;
