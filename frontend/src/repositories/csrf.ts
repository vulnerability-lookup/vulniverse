/*
 * Flask-WTF's CSRFProtect expects an X-CSRFToken header on every
 * state-changing request (matching Vulnerability-Lookup's own frontend
 * convention — see repository.js there). The token itself comes from
 * GET /auth/csrf-token and is exempt from the login gate, since it has
 * to be fetchable before a session even exists (register/login).
 */
let cachedToken: Promise<string> | null = null;

async function fetchCsrfToken(apiRoot: string): Promise<string> {
  const response = await fetch(`${apiRoot}/auth/csrf-token`, {
    credentials: "same-origin",
  });

  const body = await response.json() as { csrfToken: string };

  return body.csrfToken;
}

export function getCsrfToken(apiRoot = "/api/v1"): Promise<string> {
  cachedToken ??= fetchCsrfToken(apiRoot);

  return cachedToken;
}

/*
 * Flask-WTF ties a CSRF token to the session it was issued in — call
 * this after logout so the next mutating request fetches a fresh token
 * for whatever session (or lack of one) comes next.
 */
export function clearCsrfToken(): void {
  cachedToken = null;
}
