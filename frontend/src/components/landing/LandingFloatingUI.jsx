import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { FiArrowUp, FiCalendar } from 'react-icons/fi';

const COOKIE_KEY = 'apex_cookie_consent';

export function LandingFloatingUI() {
  const [progress, setProgress] = useState(0);
  const [showTop, setShowTop] = useState(false);
  const [showCookie, setShowCookie] = useState(false);

  useEffect(() => {
    if (!localStorage.getItem(COOKIE_KEY)) setShowCookie(true);

    const onScroll = () => {
      const { scrollTop, scrollHeight, clientHeight } = document.documentElement;
      const max = scrollHeight - clientHeight;
      setProgress(max > 0 ? scrollTop / max : 0);
      setShowTop(scrollTop > 600);
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  const acceptCookies = () => {
    localStorage.setItem(COOKIE_KEY, '1');
    setShowCookie(false);
  };

  return (
    <>
      <div
        className="lp-scroll-progress"
        style={{ width: `${progress * 100}%` }}
        aria-hidden
      />
      <Link to="/register" className="lp-fab-demo" aria-label="Book a demo">
        <FiCalendar size={16} /> Book a Demo
      </Link>
      <button
        type="button"
        className={`lp-back-top ${showTop ? 'is-visible' : ''}`}
        onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
        aria-label="Back to top"
      >
        <FiArrowUp size={20} />
      </button>
      {showCookie && (
        <div className="lp-cookie" role="dialog" aria-label="Cookie consent">
          <p className="small mb-0 flex-grow-1">
            We use cookies to improve your experience. By continuing, you agree to our cookie policy.
          </p>
          <button type="button" className="lp-btn lp-btn-primary btn-sm" onClick={acceptCookies}>
            Accept
          </button>
        </div>
      )}
    </>
  );
}

export default LandingFloatingUI;