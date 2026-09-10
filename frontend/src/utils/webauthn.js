/**
 * WebAuthn helpers — platform biometrics (fingerprint / Face ID / Windows Hello).
 * Converts server JSON (base64url) ↔ ArrayBuffer for navigator.credentials.
 */

function b64urlToBuffer(value) {
  if (!value) return new ArrayBuffer(0);
  if (value instanceof ArrayBuffer) return value;
  if (ArrayBuffer.isView(value)) {
    return value.buffer.slice(value.byteOffset, value.byteOffset + value.byteLength);
  }
  const str = String(value).replace(/-/g, '+').replace(/_/g, '/');
  const pad = '='.repeat((4 - (str.length % 4)) % 4);
  const binary = atob(str + pad);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) bytes[i] = binary.charCodeAt(i);
  return bytes.buffer;
}

function bufferToB64url(buffer) {
  const bytes = buffer instanceof ArrayBuffer
    ? new Uint8Array(buffer)
    : new Uint8Array(buffer.buffer || buffer);
  let binary = '';
  bytes.forEach((b) => { binary += String.fromCharCode(b); });
  return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/g, '');
}

export function isWebAuthnSupported() {
  return typeof window !== 'undefined'
    && window.PublicKeyCredential
    && typeof navigator.credentials?.create === 'function'
    && typeof navigator.credentials?.get === 'function'
    && window.isSecureContext;
}

/** Prefer platform authenticator (fingerprint) when available. */
export async function isPlatformAuthenticatorAvailable() {
  try {
    if (!window.PublicKeyCredential?.isUserVerifyingPlatformAuthenticatorAvailable) {
      return false;
    }
    return Boolean(await window.PublicKeyCredential.isUserVerifyingPlatformAuthenticatorAvailable());
  } catch {
    return false;
  }
}

function reviveCreateOptions(options) {
  const o = { ...options };
  o.challenge = b64urlToBuffer(o.challenge);
  if (o.user) {
    o.user = {
      ...o.user,
      id: typeof o.user.id === 'string' ? b64urlToBuffer(o.user.id) : o.user.id,
    };
  }
  if (Array.isArray(o.excludeCredentials)) {
    o.excludeCredentials = o.excludeCredentials.map((c) => ({
      ...c,
      id: b64urlToBuffer(c.id),
    }));
  }
  return o;
}

function reviveRequestOptions(options) {
  const o = { ...options };
  o.challenge = b64urlToBuffer(o.challenge);
  if (Array.isArray(o.allowCredentials)) {
    o.allowCredentials = o.allowCredentials.map((c) => ({
      ...c,
      id: b64urlToBuffer(c.id),
    }));
  }
  return o;
}

function serializeCredential(cred) {
  if (!cred) return null;
  const response = cred.response;
  const clientDataJSON = bufferToB64url(response.clientDataJSON);
  const out = {
    id: cred.id,
    rawId: bufferToB64url(cred.rawId),
    type: cred.type,
    clientExtensionResults: cred.getClientExtensionResults?.() || {},
    response: {},
  };
  if (response.attestationObject) {
    // Registration
    out.response = {
      clientDataJSON,
      attestationObject: bufferToB64url(response.attestationObject),
      transports: response.getTransports?.() || ['internal'],
    };
  } else {
    // Authentication
    out.response = {
      clientDataJSON,
      authenticatorData: bufferToB64url(response.authenticatorData),
      signature: bufferToB64url(response.signature),
      userHandle: response.userHandle ? bufferToB64url(response.userHandle) : null,
    };
  }
  return out;
}

/**
 * Enroll platform biometric (fingerprint preferred).
 * @param {object} options - from POST /auth/webauthn/register/options/
 */
export async function registerPlatformAuthenticator(options) {
  if (!isWebAuthnSupported()) {
    throw new Error(
      'This browser does not support secure biometrics (WebAuthn). Use a modern mobile browser on HTTPS.',
    );
  }
  const publicKey = reviveCreateOptions(options);
  let credential;
  try {
    credential = await navigator.credentials.create({ publicKey });
  } catch (err) {
    if (err?.name === 'NotAllowedError') {
      throw new Error('Biometric registration was cancelled or timed out. Try again.');
    }
    if (err?.name === 'InvalidStateError') {
      throw new Error('This fingerprint is already registered on this account.');
    }
    throw new Error(err?.message || 'Unable to register biometric.');
  }
  if (!credential) throw new Error('No biometric credential was created.');
  return serializeCredential(credential);
}

/**
 * Assert identity with platform biometric.
 * @param {object} options - from POST /auth/webauthn/authenticate/options/
 */
export async function assertPlatformAuthenticator(options) {
  if (!isWebAuthnSupported()) {
    throw new Error(
      'This browser does not support secure biometrics (WebAuthn). Use a modern mobile browser on HTTPS.',
    );
  }
  const publicKey = reviveRequestOptions(options);
  let credential;
  try {
    credential = await navigator.credentials.get({ publicKey });
  } catch (err) {
    if (err?.name === 'NotAllowedError') {
      throw new Error('Fingerprint verification was cancelled or timed out. Try again.');
    }
    throw new Error(err?.message || 'Biometric verification failed.');
  }
  if (!credential) throw new Error('No biometric assertion was returned.');
  return serializeCredential(credential);
}
