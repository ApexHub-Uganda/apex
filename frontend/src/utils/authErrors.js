export function getLoginErrorMessage(error) {
  if (!error) return 'Unable to sign in. Please try again.';

  // Network / proxy down (backend not running, ngrok tunnel broken, etc.)
  if (!error.response) {
    if (error.code === 'ECONNABORTED') {
      return 'Sign-in timed out. Check that the backend is running and try again.';
    }
    return 'Cannot reach the API. Start the Django backend on port 8000 (and keep your ngrok tunnel pointing at the frontend).';
  }

  const { status, data, headers } = error.response;
  const contentType = String(headers?.['content-type'] || '');

  if (status === 429) {
    return 'Too many login attempts. Please wait a minute and try again.';
  }

  // Vite proxy 502/504 when Django is down
  if (status === 502 || status === 503 || status === 504) {
    return 'API gateway error — the backend is not reachable on port 8000. Start Django (python manage.py runserver 0.0.0.0:8000) and retry.';
  }

  // DisallowedHost / Django debug HTML
  if (
    (typeof data === 'string' && (data.includes('DisallowedHost') || data.includes('<!DOCTYPE')))
    || contentType.includes('text/html')
  ) {
    if (typeof data === 'string' && data.includes('DisallowedHost')) {
      return 'Server rejected this host. Add your ngrok domain to ALLOWED_HOSTS and restart Django.';
    }
    return 'The server returned an unexpected HTML error. Check the Django console for details.';
  }

  const message =
    data?.error?.message ||
    data?.message ||
    data?.detail ||
    data?.non_field_errors?.[0] ||
    data?.error?.details?.non_field_errors?.[0] ||
    (typeof data === 'string' && data.length < 300 ? data : null);

  if (message) return String(message);

  if (status === 401 || status === 400) {
    return 'Invalid email or password.';
  }

  return `Unable to sign in (HTTP ${status || '?'}). Please try again.`;
}