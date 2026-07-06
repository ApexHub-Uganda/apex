import { useEffect, useState } from 'react';
import Logo from '../Logo';

export function LandingLoader({ onComplete }) {
  const [done, setDone] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => {
      setDone(true);
      onComplete?.();
    }, 1400);
    return () => clearTimeout(timer);
  }, [onComplete]);

  return (
    <div className={`lp-loader ${done ? 'is-done' : ''}`} role="status" aria-label="Loading Apex Hub">
      <div className="lp-loader-logo">
        <Logo size={56} className="justify-content-center flex-column lp-loader-brand" />
        <div className="lp-loader-bar"><div className="lp-loader-bar-fill" /></div>
      </div>
    </div>
  );
}

export default LandingLoader;