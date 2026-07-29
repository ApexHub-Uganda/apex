import { useEffect, useRef, useState } from 'react';
import { startLiveLocationWatch } from '../utils/geolocation';

/**
 * Continuous GPS for staff attendance map + warm sign-in.
 * Starts on mount when `enabled` is true.
 */
export function useLiveGeolocation({ enabled = true } = {}) {
  const [fix, setFix] = useState(null);
  const [best, setBest] = useState(null);
  const [error, setError] = useState(null);
  const [status, setStatus] = useState(enabled ? 'locating' : 'idle');
  const watcherRef = useRef(null);

  useEffect(() => {
    if (!enabled) {
      setStatus('idle');
      return undefined;
    }

    setStatus('locating');
    setError(null);

    const watcher = startLiveLocationWatch(
      (update) => {
        setFix(update);
        if (update.best) setBest(update.best);
        setStatus('ok');
      },
      (err) => {
        setError(err?.message || 'Unable to read location.');
        setStatus('error');
      },
      { enableHighAccuracy: true, maximumAge: 0, timeout: 30_000 },
    );
    watcherRef.current = watcher;

    return () => {
      watcher.stop();
      watcherRef.current = null;
    };
  }, [enabled]);

  return {
    /** Latest raw reading (for live red pin). */
    fix,
    /** Sharpest reading seen so far (prefer for sign-in). */
    best: best || fix,
    error,
    status,
    isLocating: status === 'locating',
    hasFix: Boolean(fix?.lat != null),
    getBest: () => watcherRef.current?.getBest?.() || best || fix,
  };
}

export default useLiveGeolocation;
