import { Link } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { FiCheckCircle, FiLogIn, FiLogOut, FiMapPin, FiArrowRight } from 'react-icons/fi';
import { staffGeoAttendanceService } from '../services/moduleService';
import { getAttendancePosition } from '../utils/geolocation';
import { extractApiError, notify } from '../utils/notify';

/**
 * Compact staff GPS sign-in card for role dashboards.
 */
export function StaffSignInPanel() {
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ['staff-attendance-status'],
    queryFn: () => staffGeoAttendanceService.status(),
    staleTime: 15_000,
    refetchInterval: 60_000,
  });

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['staff-attendance-status'] });

  const checkIn = useMutation({
    mutationFn: async () => {
      notify.info('Getting a precise GPS fix…');
      const fix = await getAttendancePosition();
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
    onError: (err) => {
      notify.error(err?.response ? extractApiError(err, 'Sign-in failed.') : (err?.message || 'Sign-in failed.'));
    },
  });

  const checkOut = useMutation({
    mutationFn: async () => {
      let payload = {};
      try {
        const fix = await getAttendancePosition({ maxWaitMs: 8_000 });
        payload = { lat: fix.lat, lng: fix.lng, accuracy_m: fix.accuracy_m };
      } catch {
        // Backend decides if location is required on check-out
      }
      return staffGeoAttendanceService.checkOut(payload);
    },
    onSuccess: (res) => {
      notify.success(res?.message || 'Signed out.');
      invalidate();
    },
    onError: (err) => {
      notify.error(err?.response ? extractApiError(err, 'Sign-out failed.') : (err?.message || 'Sign-out failed.'));
    },
  });

  const busy = checkIn.isPending || checkOut.isPending;
  const canCheckIn = data?.has_staff_profile && !data?.checked_in;
  const canCheckOut = data?.has_staff_profile && data?.checked_in && !data?.checked_out;
  const geofenceOn = Boolean(data?.geofence?.is_enabled);

  return (
    <div className="apex-card p-4 h-100">
      <div className="d-flex align-items-center justify-content-between mb-3">
        <div>
          <h5 className="fw-bold mb-1">Staff sign-in</h5>
          <p className="text-muted small mb-0">
            {geofenceOn
              ? 'GPS check-in — you must be on campus'
              : 'Tap to sign in for today'}
          </p>
        </div>
        <Link to="/school-admin/attendance/staff" className="btn btn-sm btn-outline-primary">
          Open <FiArrowRight size={14} className="ms-1" />
        </Link>
      </div>

      {isLoading ? (
        <div className="py-3 text-center">
          <div className="spinner-border spinner-border-sm text-primary" role="status" />
        </div>
      ) : !data?.has_staff_profile ? (
        <p className="text-muted small mb-0">
          No staff profile is linked to this account. Ask admin/HR to connect your login.
        </p>
      ) : (
        <>
          <div className="d-flex flex-wrap align-items-center gap-2 mb-3">
            <span className={`badge ${data?.checked_out ? 'text-bg-secondary' : data?.checked_in ? 'text-bg-success' : 'text-bg-light border'}`}>
              {data?.checked_out
                ? 'Signed out'
                : data?.checked_in
                  ? `Signed in ${data.check_in || ''}`
                  : 'Not signed in'}
            </span>
            {geofenceOn && (
              <span className="small text-muted d-inline-flex align-items-center gap-1">
                <FiMapPin size={12} /> Campus geofence on
              </span>
            )}
          </div>

          <div className="d-flex flex-wrap gap-2">
            <button
              type="button"
              className="btn btn-primary btn-sm d-inline-flex align-items-center gap-1"
              disabled={busy || !canCheckIn}
              onClick={() => checkIn.mutate()}
            >
              <FiLogIn size={14} />
              {checkIn.isPending ? 'Signing in…' : 'Sign in'}
            </button>
            <button
              type="button"
              className="btn btn-outline-primary btn-sm d-inline-flex align-items-center gap-1"
              disabled={busy || !canCheckOut}
              onClick={() => checkOut.mutate()}
            >
              <FiLogOut size={14} />
              {checkOut.isPending ? 'Signing out…' : 'Sign out'}
            </button>
          </div>

          {data?.checked_in && !data?.checked_out && (
            <p className="text-success small mt-3 mb-0 d-flex align-items-center gap-1">
              <FiCheckCircle /> You are signed in for today.
            </p>
          )}
        </>
      )}
    </div>
  );
}

export default StaffSignInPanel;
