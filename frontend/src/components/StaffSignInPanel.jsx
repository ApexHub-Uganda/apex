import { Link } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { FiCheckCircle, FiKey, FiLogIn, FiLogOut, FiMapPin, FiArrowRight } from 'react-icons/fi';
import { staffGeoAttendanceService } from '../services/moduleService';
import { webauthnService } from '../services/authService';
import { formatAccuracy, getAttendancePosition, isSecureGeolocationContext } from '../utils/geolocation';
import { assertPlatformAuthenticator, isWebAuthnSupported, registerPlatformAuthenticator } from '../utils/webauthn';
import { useLiveGeolocation } from '../hooks/useLiveGeolocation';
import { extractApiError, notify } from '../utils/notify';

/**
 * Compact staff sign-in for role dashboards.
 * Check-in is shared across dual roles; biometric required after GPS.
 */
export function StaffSignInPanel() {
  const queryClient = useQueryClient();
  const live = useLiveGeolocation({ enabled: true });

  const { data, isLoading } = useQuery({
    queryKey: ['staff-attendance-status'],
    queryFn: () => staffGeoAttendanceService.status(),
    staleTime: 15_000,
    refetchInterval: 60_000,
  });

  const { data: webauthn, refetch: refetchWebauthn } = useQuery({
    queryKey: ['webauthn-status'],
    queryFn: () => webauthnService.status(),
    staleTime: 30_000,
  });

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['staff-attendance-status'] });
    queryClient.invalidateQueries({ queryKey: ['webauthn-status'] });
  };

  const enrolled = Boolean(webauthn?.enrolled ?? data?.webauthn?.enrolled);

  const resolveFix = async () => {
    if (!isSecureGeolocationContext()) {
      throw new Error('Use https:// on your phone for GPS and fingerprint.');
    }
    return getAttendancePosition({
      seedFix: live.getBest?.() || live.best || live.fix,
    });
  };

  const checkIn = useMutation({
    mutationFn: async () => {
      if (!enrolled) {
        notify.info('Register fingerprint first…');
        const options = await webauthnService.registerOptions();
        const credential = await registerPlatformAuthenticator(options);
        await webauthnService.registerVerify({ credential, device_label: 'This device' });
        await refetchWebauthn();
      }
      notify.info('Confirming location, then fingerprint…');
      const fix = await resolveFix();
      const authOptions = await webauthnService.authenticateOptions();
      const assertion = await assertPlatformAuthenticator(authOptions);
      return staffGeoAttendanceService.checkIn({
        lat: fix.lat,
        lng: fix.lng,
        accuracy_m: fix.accuracy_m,
        webauthn: assertion,
      });
    },
    onSuccess: (res) => {
      if (res?.already_checked_in) {
        notify.info(res?.message || 'Already signed in today across your roles.');
      } else {
        notify.success(res?.message || 'Signed in.');
      }
      invalidate();
    },
    onError: (err) => {
      const code = err?.response?.data?.code;
      if (code === 'already_checked_in') {
        notify.info(extractApiError(err, 'Already signed in today.'));
        invalidate();
        return;
      }
      notify.error(err?.response ? extractApiError(err, 'Sign-in failed.') : (err?.message || 'Sign-in failed.'));
    },
  });

  const checkOut = useMutation({
    mutationFn: async () => {
      let payload = {};
      try {
        const fix = await resolveFix();
        payload = { lat: fix.lat, lng: fix.lng, accuracy_m: fix.accuracy_m };
      } catch {
        // optional
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
  const alreadyIn = Boolean(data?.checked_in && !data?.checked_out);

  return (
    <div className="apex-card p-4 h-100">
      <div className="d-flex align-items-center justify-content-between mb-3">
        <div>
          <h5 className="fw-bold mb-1">Staff sign-in</h5>
          <p className="text-muted small mb-0">
            {geofenceOn
              ? 'Location + fingerprint · shared across dual roles'
              : 'Fingerprint-verified sign-in for today'}
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
                <FiMapPin size={12} /> Campus on
              </span>
            )}
            <span className={`small d-inline-flex align-items-center gap-1 ${enrolled ? 'text-success' : 'text-warning'}`}>
              <FiKey size={12} />
              {enrolled ? 'Biometric ready' : 'Enroll biometric'}
            </span>
            {live.best?.accuracy_m != null && (
              <span className="small text-muted">GPS {formatAccuracy(live.best.accuracy_m)}</span>
            )}
          </div>

          {alreadyIn && (
            <p className="small text-success mb-3">
              Already signed in for today — switching roles will not ask you to sign in again.
            </p>
          )}

          <div className="d-flex flex-wrap gap-2">
            <button
              type="button"
              className="btn btn-primary btn-sm d-inline-flex align-items-center gap-1"
              disabled={busy || !canCheckIn}
              onClick={() => checkIn.mutate()}
            >
              <FiLogIn size={14} />
              {checkIn.isPending ? 'Signing in…' : alreadyIn ? 'Signed in' : 'Sign in'}
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
          {!isWebAuthnSupported() && (
            <p className="small text-warning mt-2 mb-0">
              This browser may not support fingerprint verification. Prefer Chrome/Safari on HTTPS.
            </p>
          )}
        </>
      )}
    </div>
  );
}

export default StaffSignInPanel;
