import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  FiArrowLeft, FiCheckCircle, FiKey, FiLogIn, FiLogOut, FiMapPin, FiNavigation, FiRefreshCw, FiShield,
} from 'react-icons/fi';
import PageHeader from '../../components/PageHeader';
import SchoolBoundaryMap from '../../components/SchoolBoundaryMap';
import { staffGeoAttendanceService } from '../../services/moduleService';
import { webauthnService } from '../../services/authService';
import {
  accuracyQuality,
  formatAccuracy,
  getAttendancePosition,
  isSecureGeolocationContext,
} from '../../utils/geolocation';
import {
  assertPlatformAuthenticator,
  isPlatformAuthenticatorAvailable,
  isWebAuthnSupported,
  registerPlatformAuthenticator,
} from '../../utils/webauthn';
import { useLiveGeolocation } from '../../hooks/useLiveGeolocation';
import { extractApiError, notify } from '../../utils/notify';
import { ApexLoader } from '../../components/ApexLoader';

/**
 * Staff GPS check-in with:
 *  1) Live location (red pin)
 *  2) WebAuthn fingerprint / platform biometric ("verify it's you")
 *  3) Shared attendance across dual portal roles
 */
export function StaffAttendance() {
  const queryClient = useQueryClient();
  const [busy, setBusy] = useState(false);
  const [refiningMsg, setRefiningMsg] = useState('');
  const [enrolling, setEnrolling] = useState(false);

  const { data, isLoading, refetch } = useQuery({
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

  const live = useLiveGeolocation({ enabled: true });
  const liveFix = live.fix;
  const bestFix = live.best;

  const geofence = data?.geofence || {};
  const vertices = geofence.vertices || [];
  const quality = accuracyQuality(bestFix?.accuracy_m);
  const enrolled = Boolean(webauthn?.enrolled ?? data?.webauthn?.enrolled);
  const credentials = webauthn?.credentials || data?.webauthn?.credentials || [];

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['staff-attendance-status'] });
    queryClient.invalidateQueries({ queryKey: ['webauthn-status'] });
  };

  const resolveAttendanceFix = async () => {
    setRefiningMsg('Locking GPS…');
    const seed = live.getBest?.() || bestFix || liveFix;
    const fix = await getAttendancePosition({
      seedFix: seed,
      onUpdate: (partial) => {
        setRefiningMsg(
          `Refining GPS… ${formatAccuracy(partial.accuracy_m)}`
          + (partial.samples ? ` · ${partial.samples} samples` : ''),
        );
      },
    });
    setRefiningMsg('');
    return fix;
  };

  const enrollBiometric = async () => {
    setEnrolling(true);
    try {
      if (!isSecureGeolocationContext() || !isWebAuthnSupported()) {
        throw new Error('Biometrics need a modern browser on HTTPS.');
      }
      const platformOk = await isPlatformAuthenticatorAvailable();
      if (!platformOk) {
        notify.warning(
          'No fingerprint / Face ID / Windows Hello found. You can still try — your device may offer a PIN.',
        );
      }
      const options = await webauthnService.registerOptions();
      const credential = await registerPlatformAuthenticator(options);
      const result = await webauthnService.registerVerify({
        credential,
        device_label: 'This phone',
      });
      notify.success(result?.message || 'Fingerprint registered for attendance.');
      await refetchWebauthn();
      invalidate();
    } catch (err) {
      notify.error(err?.response ? extractApiError(err, 'Enrollment failed.') : (err?.message || 'Enrollment failed.'));
    } finally {
      setEnrolling(false);
    }
  };

  /** Location → biometric → server check-in */
  const runVerifiedCheckIn = async () => {
    if (!isSecureGeolocationContext()) {
      throw new Error('Open this portal with https:// on your phone for GPS and fingerprint.');
    }
    if (!enrolled) {
      const err = new Error(
        'Register your fingerprint first. This stops colleagues signing in for each other.',
      );
      err.code = 'not_enrolled';
      throw err;
    }

    notify.info('Step 1/2 — confirming you are on campus…');
    const fix = await resolveAttendanceFix();

    setRefiningMsg('Step 2/2 — verify it’s you (fingerprint)…');
    notify.info('Verify it’s you with fingerprint…');
    const authOptions = await webauthnService.authenticateOptions();
    const assertion = await assertPlatformAuthenticator(authOptions);

    return staffGeoAttendanceService.checkIn({
      lat: fix.lat,
      lng: fix.lng,
      accuracy_m: fix.accuracy_m,
      webauthn: assertion,
    });
  };

  const checkIn = useMutation({
    mutationFn: async () => {
      setBusy(true);
      return runVerifiedCheckIn();
    },
    onSuccess: (res) => {
      if (res?.already_checked_in) {
        notify.info(res?.message || 'Already signed in today (shared across your roles).');
      } else {
        notify.success(res?.message || 'Signed in.');
      }
      invalidate();
    },
    onError: (err) => {
      const code = err?.response?.data?.code || err?.code;
      if (code === 'not_enrolled') {
        notify.warning(err?.message || extractApiError(err, 'Enroll fingerprint first.'));
        return;
      }
      if (code === 'already_checked_in') {
        notify.info(extractApiError(err, 'Already signed in today.'));
        invalidate();
        return;
      }
      notify.error(err?.response ? extractApiError(err, 'Sign-in failed.') : (err?.message || 'Sign-in failed.'));
    },
    onSettled: () => {
      setBusy(false);
      setRefiningMsg('');
    },
  });

  const checkOut = useMutation({
    mutationFn: async () => {
      setBusy(true);
      let payload = {};
      try {
        const fix = await resolveAttendanceFix();
        payload = { lat: fix.lat, lng: fix.lng, accuracy_m: fix.accuracy_m };
      } catch {
        // optional GPS on checkout
      }
      return staffGeoAttendanceService.checkOut(payload);
    },
    onSuccess: (res) => {
      notify.success(res?.message || 'Signed out.');
      invalidate();
    },
    onError: (err) => notify.error(err?.response ? extractApiError(err, 'Sign-out failed.') : (err?.message || 'Sign-out failed.')),
    onSettled: () => {
      setBusy(false);
      setRefiningMsg('');
    },
  });

  const previewLocation = async () => {
    setBusy(true);
    try {
      const fix = await resolveAttendanceFix();
      const evaluation = await staffGeoAttendanceService.checkLocation({
        lat: fix.lat,
        lng: fix.lng,
        accuracy_m: fix.accuracy_m,
      });
      if (evaluation?.allowed) {
        notify.success(
          `${evaluation.reason || 'Within school perimeter.'} · ${formatAccuracy(fix.accuracy_m)}`,
        );
      } else {
        notify.error(evaluation?.reason || 'Outside school perimeter.');
      }
    } catch (err) {
      notify.error(err.message || extractApiError(err, 'Unable to read location.'));
    } finally {
      setBusy(false);
      setRefiningMsg('');
    }
  };

  if (isLoading) {
    return (
      <div className="py-5 text-center"><ApexLoader label="Loading attendance…" /></div>
    );
  }

  const canCheckIn = data?.has_staff_profile && !data?.checked_in;
  const canCheckOut = data?.has_staff_profile && data?.checked_in && !data?.checked_out;
  const alreadyIn = Boolean(data?.checked_in && !data?.checked_out);

  return (
    <div>
      <div className="mb-3">
        <Link to="/school-admin/attendance" className="small text-decoration-none text-muted">
          <FiArrowLeft className="me-1" /> Attendance
        </Link>
      </div>

      <PageHeader
        title="Staff attendance"
        subtitle="Location on campus, then fingerprint verification. One sign-in covers all your dual roles for the day."
        actions={(
          <button type="button" className="btn btn-outline-secondary btn-sm" onClick={() => refetch()}>
            <FiRefreshCw className="me-1" /> Refresh
          </button>
        )}
      />

      {!data?.has_staff_profile && (
        <div className="alert alert-warning">
          No staff HR profile is linked to your account. Ask admin to link your portal user to a staff record.
        </div>
      )}

      {!isSecureGeolocationContext() && (
        <div className="alert alert-danger">
          Use <strong>https://</strong> on your phone — GPS and fingerprint both require a secure site.
        </div>
      )}

      {alreadyIn && (
        <div className="alert alert-success d-flex align-items-start gap-2">
          <FiCheckCircle className="mt-1 flex-shrink-0" />
          <div>
            <strong>Already signed in today</strong>
            {data?.check_in ? ` at ${data.check_in}` : ''}.
            {' '}This check-in is shared across every portal role on your account
            (teacher, bursar, DoS, etc.) — switch roles freely without signing in again.
          </div>
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

            {/* Biometric enroll */}
            <div className="border rounded p-3 mb-3">
              <div className="d-flex align-items-center gap-2 mb-2">
                <FiKey className="text-primary" />
                <span className="fw-semibold small">Verify it&apos;s you</span>
                {enrolled ? (
                  <span className="badge text-bg-success-subtle border text-success ms-auto">Registered</span>
                ) : (
                  <span className="badge text-bg-warning-subtle border text-warning ms-auto">Required</span>
                )}
              </div>
              <p className="small text-muted mb-2">
                Fingerprint (or Face ID / Windows Hello) proves <strong>you</strong> are at the phone —
                not a colleague signing in for you.
              </p>
              {enrolled ? (
                <ul className="small text-muted mb-2 ps-3">
                  {credentials.map((c) => (
                    <li key={c.id}>{c.device_label || 'Device'}{c.last_used_at ? ` · last used ${String(c.last_used_at).slice(0, 10)}` : ''}</li>
                  ))}
                </ul>
              ) : null}
              <button
                type="button"
                className="btn btn-outline-primary btn-sm d-inline-flex align-items-center gap-1"
                disabled={enrolling || busy}
                onClick={enrollBiometric}
              >
                <FiShield size={14} />
                {enrolling ? 'Waiting for fingerprint…' : enrolled ? 'Add another device' : 'Register fingerprint'}
              </button>
            </div>

            {/* Live GPS */}
            <div className="border rounded p-3 mb-3 bg-light-subtle">
              <div className="d-flex justify-content-between align-items-center mb-2">
                <span className="small fw-semibold">Live GPS</span>
                <span className={`badge text-bg-${quality.tone}-subtle border text-${quality.tone}`}>
                  {live.isLocating ? 'Locating…' : quality.label}
                </span>
              </div>
              {live.error && !liveFix ? (
                <p className="small text-danger mb-0">{live.error}</p>
              ) : bestFix ? (
                <>
                  <div className="small text-muted">
                    {bestFix.lat.toFixed(5)}, {bestFix.lng.toFixed(5)}
                  </div>
                  <div className="fw-semibold">
                    Accuracy{' '}
                    <span className={Number(bestFix.accuracy_m) > 250 ? 'text-warning' : 'text-success'}>
                      {formatAccuracy(bestFix.accuracy_m)}
                    </span>
                  </div>
                </>
              ) : (
                <p className="small text-muted mb-0">Waiting for GPS…</p>
              )}
              {refiningMsg && <p className="small text-primary mb-0 mt-2">{refiningMsg}</p>}
            </div>

            <div className="d-grid gap-2">
              <button
                type="button"
                className="btn btn-primary d-inline-flex align-items-center justify-content-center gap-2"
                disabled={busy || !canCheckIn || !data?.has_staff_profile}
                onClick={() => checkIn.mutate()}
              >
                <FiLogIn size={16} />
                {busy && checkIn.isPending
                  ? 'Signing in…'
                  : alreadyIn
                    ? 'Already signed in'
                    : 'Sign in (location + fingerprint)'}
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

            <p className="small text-muted mt-3 mb-0">
              Flow: GPS on campus → fingerprint prompt → signed in for the day on every role.
            </p>
          </div>
        </div>

        <div className="col-lg-7">
          <div className="apex-card p-3 p-md-4">
            <h6 className="fw-semibold mb-2">Campus map</h6>
            {vertices.length >= 3 || liveFix ? (
              <SchoolBoundaryMap
                vertices={vertices}
                interactive={false}
                locateUser={false}
                showUserMarker
                userMarkerColor="red"
                userPosition={liveFix}
                fitUserWithBoundary
                followUser={Boolean(liveFix && vertices.length < 3)}
                height={380}
              />
            ) : (
              <div className="border rounded p-5 text-center text-muted small">
                {live.isLocating
                  ? 'Locating you on the map…'
                  : 'No school boundary polygon is configured yet.'}
                {data?.geofence && !vertices.length && (
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
