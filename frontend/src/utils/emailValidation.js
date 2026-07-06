const BLOCKED_DOMAINS = new Set([
  'example.com', 'example.org', 'example.net', 'test.com', 'test.org',
  'localhost', 'local', 'invalid', 'domain.com', 'email.com',
  'mail.com', 'fake.com', 'dummy.com', 'sample.com', 'placeholder.com',
  'yopmail.com', 'mailinator.com', 'guerrillamail.com', 'tempmail.com',
  '10minutemail.com', 'throwaway.email', 'sharklasers.com',
]);

const BLOCKED_TLDS = new Set(['test', 'invalid', 'localhost', 'local']);

const DUMMY_LOCAL_PARTS = new Set([
  'test', 'dummy', 'fake', 'example', 'sample', 'placeholder', 'noreply',
  'no-reply', 'donotreply', 'do-not-reply', 'null', 'void', 'none',
  'user', 'username', 'email', 'mail', 'asdf', 'qwerty', 'aaa', 'bbb',
]);

const EMAIL_PATTERN = /^[a-zA-Z0-9](?:[a-zA-Z0-9._%+-]*[a-zA-Z0-9])?@[a-zA-Z0-9](?:[a-zA-Z0-9-]*[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]*[a-zA-Z0-9])?)+$/;

const DUMMY_DOMAIN_PATTERN = /^(?:test\.|.*\.test$|localhost|127\.0\.0\.1)$/i;

export function validateDeliverableEmail(value, { required = true } = {}) {
  const email = (value || '').trim();
  if (!email) return required ? 'Email is required.' : null;
  if (email.length > 254) return 'Email address is too long.';
  if (!EMAIL_PATTERN.test(email)) return 'Enter a valid email address (e.g. name@school.edu).';

  const at = email.lastIndexOf('@');
  const local = email.slice(0, at).toLowerCase();
  const domain = email.slice(at + 1).toLowerCase();
  const tld = domain.split('.').pop();

  if (BLOCKED_DOMAINS.has(domain)) {
    return `"${domain}" is not allowed. Use a real mailbox you can access.`;
  }
  if (BLOCKED_TLDS.has(tld)) return 'Use a real email domain, not a test or placeholder TLD.';
  if ((tld || '').length < 2) return 'Email domain must include a valid top-level domain (e.g. .com, .ug).';
  if (DUMMY_DOMAIN_PATTERN.test(domain)) {
    return 'Use a real email address, not a demo or placeholder domain.';
  }
  if (/^staff\d*$/i.test(local) && domain.endsWith('.ug')) {
    return "Use each staff member's real work email, not generated demo addresses.";
  }
  if (local === 'parent' && domain.length < 8) {
    return "Use the parent's real email address.";
  }
  if (DUMMY_LOCAL_PARTS.has(local) && BLOCKED_DOMAINS.has(domain)) {
    return 'Placeholder email addresses are not allowed.';
  }
  return null;
}

export function emailValidationRules({ required = true, label = 'Email' } = {}) {
  return {
    required: required ? `${label} is required.` : false,
    validate: (value) => {
      const err = validateDeliverableEmail(value, { required });
      return err || true;
    },
  };
}

/** Format-only rules for auth flows (login) where legacy accounts may exist. */
export function emailFormatRules({ required = true, label = 'Email' } = {}) {
  return {
    required: required ? `${label} is required.` : false,
    validate: (value) => {
      const trimmed = (value || '').trim();
      if (!trimmed) return required ? `${label} is required.` : true;
      if (!EMAIL_PATTERN.test(trimmed)) return 'Enter a valid email address (e.g. name@school.edu).';
      return true;
    },
  };
}

export default validateDeliverableEmail;