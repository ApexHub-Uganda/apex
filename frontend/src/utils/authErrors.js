export function getLoginErrorMessage(error) {
  if (!error) return 'Unable to sign in. Please try again.';

  if (!error.response) {
    return 'Cannot reach the server. Make sure the backend is running on port 8000.';
  }

  const { status, data } = error.response;

  if (status === 429) {
    return 'Too many login attempts. Please wait a minute and try again.';
  }

  const message =
    data?.error?.message ||
    data?.detail ||
    (typeof data === 'string' ? data : null);

  if (message) return message;

  if (status === 401 || status === 400) {
    return 'Invalid email or password.';
  }

  return 'Unable to sign in. Please try again.';
}