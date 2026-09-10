/**
 * Browser GPS helpers (free, no API key).
 *
 * Mobile browsers often return a coarse first fix (~500–2000 m from cell/Wi‑Fi)
 * before the GNSS chip locks. Attendance must:
 *  - never prefer a stale/cached network fix
 *  - watch continuously and keep the best sample
 *  - wait long enough for real GPS outdoors
 */

export const GEO_DEFAULTS = {
  /** Resolve immediately once accuracy is at or below this (metres). */
  targetAccuracyM: 50,
  /** Prefer to wait until at least this good before early accept after min wait. */
  goodAccuracyM: 100,
  /** After max wait, still accept a fix at or below this (metres). */
  acceptAccuracyM: 250,
  /** Hard cap — refuse to use a fix worse than this even after waiting. */
  maxAcceptableAccuracyM: 750,
  /** Max time to wait for a better fix (ms) — phones need longer cold starts. */
  maxWaitMs: 35_000,
  /** Minimum settle so the first coarse network fix is not used alone (ms). */
  minWaitMs: 2_500,
  /** Ignore coarse samples for early-exit until this many ms have elapsed. */
  coarseGraceMs: 8_000,
  /** Treat accuracy worse than this as "network-only" until GPS improves. */
  coarseThresholdM: 500,
  enableHighAccuracy: true,
  timeoutMs: 25_000,
  /** Map preview may use a short cache; attendance must use 0. */
  maximumAgeMs: 10_000,
};

function unsupportedError() {
  return new Error('Geolocation is not supported on this device/browser.');
}

function geoErrorMessage(err) {
  const messages = {
    1: 'Location permission denied. Allow Precise Location for this site (not approximate) and try again.',
    2: 'Location unavailable. Turn on GPS / Location Services (High accuracy), then try outdoors.',
    3: 'Location request timed out. Move outdoors with a clearer sky and try again.',
  };
  return messages[err?.code] || err?.message || 'Unable to read GPS location.';
}

export function normalizePosition(pos) {
  if (!pos?.coords) {
    throw new Error('Invalid geolocation reading.');
  }
  return {
    lat: pos.coords.latitude,
    lng: pos.coords.longitude,
    accuracy_m: pos.coords.accuracy,
    altitude: pos.coords.altitude,
    heading: pos.coords.heading,
    speed: pos.coords.speed,
    timestamp: pos.timestamp,
  };
}

export function formatAccuracy(m) {
  if (m == null || Number.isNaN(Number(m))) return '—';
  const n = Number(m);
  if (n < 1000) return `±${Math.round(n)} m`;
  return `±${(n / 1000).toFixed(1)} km`;
}

/** Human-readable GPS quality for UI. */
export function accuracyQuality(m) {
  const n = Number(m);
  if (!Number.isFinite(n)) return { level: 'unknown', label: 'Unknown', tone: 'secondary' };
  if (n <= 40) return { level: 'excellent', label: 'Excellent', tone: 'success' };
  if (n <= 100) return { level: 'good', label: 'Good', tone: 'success' };
  if (n <= 250) return { level: 'fair', label: 'Fair', tone: 'warning' };
  if (n <= 750) return { level: 'weak', label: 'Weak', tone: 'warning' };
  return { level: 'poor', label: 'Too coarse', tone: 'danger' };
}

export function isSecureGeolocationContext() {
  if (typeof window === 'undefined') return true;
  // Browsers only expose reliable GPS on secure origins (HTTPS or localhost)
  return Boolean(window.isSecureContext);
}

/**
 * Fast single reading — map preview only.
 * Never use this alone for attendance sign-in.
 */
export function getCurrentPosition(options = {}) {
  return new Promise((resolve, reject) => {
    if (!navigator?.geolocation) {
      reject(unsupportedError());
      return;
    }
    if (!isSecureGeolocationContext()) {
      reject(new Error(
        'Location requires a secure connection (HTTPS). Open the school portal with https:// on your phone.',
      ));
      return;
    }
    const {
      enableHighAccuracy = GEO_DEFAULTS.enableHighAccuracy,
      timeout = GEO_DEFAULTS.timeoutMs,
      maximumAge = GEO_DEFAULTS.maximumAgeMs,
      ...rest
    } = options;

    navigator.geolocation.getCurrentPosition(
      (pos) => resolve(normalizePosition(pos)),
      (err) => reject(new Error(geoErrorMessage(err))),
      {
        enableHighAccuracy,
        timeout,
        maximumAge,
        ...rest,
      },
    );
  });
}

/**
 * Continuous live GPS for map preview + attendance warm-up.
 * Returns { stop } — call stop() on unmount.
 *
 * @param {(fix: object) => void} onUpdate
 * @param {(err: Error) => void} [onError]
 * @param {object} [options]
 */
export function startLiveLocationWatch(onUpdate, onError, options = {}) {
  if (!navigator?.geolocation) {
    onError?.(unsupportedError());
    return { stop() {} };
  }
  if (!isSecureGeolocationContext()) {
    onError?.(new Error(
      'Location requires HTTPS. Open this site with https:// on your phone.',
    ));
    return { stop() {} };
  }

  const {
    enableHighAccuracy = true,
    timeout = 30_000,
    maximumAge = 0,
  } = options;

  let stopped = false;
  let best = null;

  const handlePos = (pos) => {
    if (stopped) return;
    try {
      const fix = normalizePosition(pos);
      const acc = Number(fix.accuracy_m);
      const ranked = { ...fix, accuracy_m: Number.isFinite(acc) ? acc : 99999 };
      if (!best || ranked.accuracy_m <= best.accuracy_m) {
        best = ranked;
      }
      // Always report latest for map pin; include best so callers can prefer sharpest
      onUpdate?.({
        ...ranked,
        best_accuracy_m: best.accuracy_m,
        best_lat: best.lat,
        best_lng: best.lng,
        best: best,
      });
    } catch {
      // ignore
    }
  };

  const handleErr = (err) => {
    if (stopped) return;
    // Keep watching after transient errors if we already have a fix
    if (best) return;
    onError?.(new Error(geoErrorMessage(err)));
  };

  // Kickstart without any cache — critical for mobile
  navigator.geolocation.getCurrentPosition(handlePos, () => {}, {
    enableHighAccuracy: true,
    timeout: 20_000,
    maximumAge: 0,
  });

  const watchId = navigator.geolocation.watchPosition(handlePos, handleErr, {
    enableHighAccuracy,
    timeout,
    maximumAge,
  });

  return {
    stop() {
      stopped = true;
      try {
        navigator.geolocation.clearWatch(watchId);
      } catch {
        // ignore
      }
    },
    getBest() {
      return best;
    },
  };
}

/**
 * Progressive GPS for attendance: watch + keep best until sharp enough.
 * Never uses a cached/stale position (maximumAge always 0).
 */
export function getBestPosition(options = {}) {
  const {
    targetAccuracyM = GEO_DEFAULTS.targetAccuracyM,
    goodAccuracyM = GEO_DEFAULTS.goodAccuracyM,
    acceptAccuracyM = GEO_DEFAULTS.acceptAccuracyM,
    maxAcceptableAccuracyM = GEO_DEFAULTS.maxAcceptableAccuracyM,
    maxWaitMs = GEO_DEFAULTS.maxWaitMs,
    minWaitMs = GEO_DEFAULTS.minWaitMs,
    coarseGraceMs = GEO_DEFAULTS.coarseGraceMs,
    coarseThresholdM = GEO_DEFAULTS.coarseThresholdM,
    enableHighAccuracy = true,
    timeout = GEO_DEFAULTS.timeoutMs,
    /** Initial best from an already-running live watch (optional). */
    seedFix = null,
    onUpdate,
    signal,
  } = options;

  return new Promise((resolve, reject) => {
    if (!navigator?.geolocation) {
      reject(unsupportedError());
      return;
    }
    if (!isSecureGeolocationContext()) {
      reject(new Error(
        'Location requires a secure connection (HTTPS). Open the school portal with https:// on your phone.',
      ));
      return;
    }

    let settled = false;
    let watchId = null;
    let best = null;
    let samples = 0;
    const startedAt = Date.now();
    let timer = null;

    const cleanup = () => {
      if (watchId != null) {
        try {
          navigator.geolocation.clearWatch(watchId);
        } catch {
          // ignore
        }
        watchId = null;
      }
      if (timer) clearTimeout(timer);
      if (signal) signal.removeEventListener('abort', onAbort);
    };

    const finishOk = (fix) => {
      if (settled) return;
      settled = true;
      cleanup();
      resolve({ ...fix, samples });
    };

    const finishErr = (err) => {
      if (settled) return;
      settled = true;
      cleanup();
      reject(err instanceof Error ? err : new Error(String(err)));
    };

    const onAbort = () => finishErr(new Error('Location request cancelled.'));
    if (signal) {
      if (signal.aborted) {
        finishErr(new Error('Location request cancelled.'));
        return;
      }
      signal.addEventListener('abort', onAbort, { once: true });
    }

    const consider = (fix) => {
      if (settled) return;
      if (!fix || fix.lat == null || fix.lng == null) return;

      samples += 1;
      const acc = Number(fix.accuracy_m);
      const ranked = {
        ...fix,
        accuracy_m: Number.isFinite(acc) ? acc : 99999,
      };

      if (!best || ranked.accuracy_m < best.accuracy_m) {
        best = ranked;
      }

      try {
        onUpdate?.({ ...best, samples, elapsed_ms: Date.now() - startedAt });
      } catch {
        // ignore
      }

      const elapsed = Date.now() - startedAt;
      if (elapsed < minWaitMs) return;

      // Early success: sharp GPS lock
      if (best.accuracy_m <= targetAccuracyM) {
        finishOk(best);
        return;
      }

      // After grace period, accept "good enough" without waiting full timeout
      if (elapsed >= coarseGraceMs && best.accuracy_m <= goodAccuracyM && samples >= 2) {
        finishOk(best);
      }
    };

    if (seedFix?.lat != null && seedFix?.lng != null) {
      consider(seedFix);
    }

    const onPos = (pos) => {
      try {
        consider(normalizePosition(pos));
      } catch {
        // ignore bad sample
      }
    };

    const onErr = (err) => {
      if (best) return;
      finishErr(new Error(geoErrorMessage(err)));
    };

    // Fresh-only kickstart (NO maximumAge cache — that was causing ±2 km)
    navigator.geolocation.getCurrentPosition(onPos, () => {}, {
      enableHighAccuracy: true,
      timeout: Math.min(timeout, 15_000),
      maximumAge: 0,
    });

    watchId = navigator.geolocation.watchPosition(onPos, onErr, {
      enableHighAccuracy,
      timeout,
      maximumAge: 0,
    });

    timer = setTimeout(() => {
      if (settled) return;
      if (best && Number.isFinite(best.accuracy_m)) {
        if (best.accuracy_m <= acceptAccuracyM) {
          finishOk(best);
          return;
        }
        if (best.accuracy_m <= maxAcceptableAccuracyM) {
          finishOk(best);
          return;
        }
        // Still very coarse after long wait
        if (best.accuracy_m > coarseThresholdM) {
          finishErr(new Error(
            `GPS is still too coarse (${formatAccuracy(best.accuracy_m)}) after ${Math.round(maxWaitMs / 1000)}s. `
            + 'On your phone: set Location mode to High accuracy / Precise, allow Precise location for this browser, '
            + 'stand outdoors, and keep this page open until the red pin accuracy drops below ±250 m.',
          ));
          return;
        }
        finishOk(best);
        return;
      }
      finishErr(new Error(
        'Could not get a GPS fix. Enable Location Services, allow Precise location, and try outdoors on HTTPS.',
      ));
    }, maxWaitMs);
  });
}

/**
 * Attendance sign-in / class marking — long refine, no stale cache.
 */
export function getAttendancePosition(options = {}) {
  return getBestPosition({
    targetAccuracyM: GEO_DEFAULTS.targetAccuracyM,
    goodAccuracyM: GEO_DEFAULTS.goodAccuracyM,
    acceptAccuracyM: GEO_DEFAULTS.acceptAccuracyM,
    maxAcceptableAccuracyM: GEO_DEFAULTS.maxAcceptableAccuracyM,
    maxWaitMs: GEO_DEFAULTS.maxWaitMs,
    minWaitMs: GEO_DEFAULTS.minWaitMs,
    coarseGraceMs: GEO_DEFAULTS.coarseGraceMs,
    enableHighAccuracy: true,
    ...options,
  });
}
