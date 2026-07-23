/**
 * Browser GPS helpers (free, no API key).
 *
 * Phones often return a coarse first fix (~500–2000 m from Wi‑Fi/cell) before
 * true GPS locks. For attendance we wait briefly for a sharper reading while
 * still resolving as soon as accuracy is good enough (low latency).
 */

export const GEO_DEFAULTS = {
  /** Resolve immediately once accuracy is at or below this (metres). */
  targetAccuracyM: 80,
  /** After max wait, still accept a fix at or below this (metres). */
  acceptAccuracyM: 280,
  /** Hard cap — refuse to use a fix worse than this even after waiting. */
  maxAcceptableAccuracyM: 500,
  /** Max time to wait for a better fix (ms). */
  maxWaitMs: 12_000,
  /** Minimum settle time so the first coarse IP fix is not used alone (ms). */
  minWaitMs: 600,
  /** High-accuracy GPS (uses hardware GPS / Wi‑Fi when available). */
  enableHighAccuracy: true,
  /** Single-shot timeout for getCurrentPosition (ms). */
  timeoutMs: 15_000,
  /** Allow a recent cached fix for instant UI (ms). Check-in still refines. */
  maximumAgeMs: 15_000,
};

function unsupportedError() {
  return new Error('Geolocation is not supported on this device/browser.');
}

function geoErrorMessage(err) {
  const messages = {
    1: 'Location permission denied. Allow precise location for this site and try again.',
    2: 'Location unavailable. Turn on GPS / Location Services and try outdoors.',
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

/**
 * Fast single reading — good for map centering / preview.
 * Uses a short-lived cache so the map feels instant on phones.
 */
export function getCurrentPosition(options = {}) {
  return new Promise((resolve, reject) => {
    if (!navigator?.geolocation) {
      reject(unsupportedError());
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
 * Progressive GPS: stream fixes via watchPosition and return the best reading.
 *
 * Latency strategy:
 *  1. Kick off watch immediately (and a parallel getCurrentPosition for a quick first sample).
 *  2. As soon as accuracy ≤ targetAccuracyM (after a tiny minWait), resolve.
 *  3. Otherwise keep the best sample until maxWaitMs, then accept if ≤ acceptAccuracyM.
 *  4. If still worse than maxAcceptableAccuracyM, reject with a clear message.
 *
 * @param {object} options
 * @param {(fix: object) => void} [options.onUpdate] live progress (accuracy improving)
 * @param {AbortSignal} [options.signal] cancel early
 */
export function getBestPosition(options = {}) {
  const {
    targetAccuracyM = GEO_DEFAULTS.targetAccuracyM,
    acceptAccuracyM = GEO_DEFAULTS.acceptAccuracyM,
    maxAcceptableAccuracyM = GEO_DEFAULTS.maxAcceptableAccuracyM,
    maxWaitMs = GEO_DEFAULTS.maxWaitMs,
    minWaitMs = GEO_DEFAULTS.minWaitMs,
    enableHighAccuracy = GEO_DEFAULTS.enableHighAccuracy,
    timeout = GEO_DEFAULTS.timeoutMs,
    maximumAge = 0, // prefer fresh readings for attendance
    onUpdate,
    signal,
  } = options;

  return new Promise((resolve, reject) => {
    if (!navigator?.geolocation) {
      reject(unsupportedError());
      return;
    }

    let settled = false;
    let watchId = null;
    let best = null;
    const startedAt = Date.now();

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
      resolve(fix);
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

      const acc = Number(fix.accuracy_m);
      const ranked = {
        ...fix,
        accuracy_m: Number.isFinite(acc) ? acc : 99999,
      };

      if (!best || ranked.accuracy_m < best.accuracy_m) {
        best = ranked;
      }

      try {
        onUpdate?.(best);
      } catch {
        // ignore UI callback errors
      }

      const elapsed = Date.now() - startedAt;
      // Resolve ASAP once GPS is sharp enough (and past a tiny settle window)
      if (
        elapsed >= minWaitMs
        && Number.isFinite(best.accuracy_m)
        && best.accuracy_m <= targetAccuracyM
      ) {
        finishOk(best);
      }
    };

    const onPos = (pos) => {
      try {
        consider(normalizePosition(pos));
      } catch (err) {
        // ignore bad sample
      }
    };

    const onErr = (err) => {
      // If we already have a usable sample, keep waiting for better; only fail if none
      if (best) return;
      finishErr(new Error(geoErrorMessage(err)));
    };

    // Parallel warm sample for lowest first latency
    navigator.geolocation.getCurrentPosition(onPos, () => {}, {
      enableHighAccuracy,
      timeout: Math.min(timeout, 8_000),
      maximumAge: Math.max(maximumAge, 5_000),
    });

    watchId = navigator.geolocation.watchPosition(onPos, onErr, {
      enableHighAccuracy,
      timeout,
      maximumAge,
    });

    const timer = setTimeout(() => {
      if (settled) return;
      if (best && Number.isFinite(best.accuracy_m)) {
        if (best.accuracy_m <= acceptAccuracyM) {
          finishOk(best);
          return;
        }
        if (best.accuracy_m <= maxAcceptableAccuracyM) {
          // Borderline — still send; backend applies final policy
          finishOk(best);
          return;
        }
        finishErr(new Error(
          `GPS accuracy is still too low (${formatAccuracy(best.accuracy_m)}) after waiting. `
          + 'Turn on Location / GPS, set location mode to High accuracy, step outdoors, '
          + 'and wait a few seconds for the blue accuracy circle to shrink, then try again.',
        ));
        return;
      }
      finishErr(new Error(
        'Could not get a GPS fix in time. Enable location services and try outdoors.',
      ));
    }, maxWaitMs);
  });
}

/**
 * Attendance-oriented helper: progressive GPS with sensible school defaults.
 * Prefer this over getCurrentPosition for check-in / class marking.
 */
export function getAttendancePosition(options = {}) {
  return getBestPosition({
    targetAccuracyM: GEO_DEFAULTS.targetAccuracyM,
    acceptAccuracyM: GEO_DEFAULTS.acceptAccuracyM,
    maxAcceptableAccuracyM: GEO_DEFAULTS.maxAcceptableAccuracyM,
    maxWaitMs: GEO_DEFAULTS.maxWaitMs,
    minWaitMs: GEO_DEFAULTS.minWaitMs,
    enableHighAccuracy: true,
    maximumAge: 0,
    ...options,
  });
}
