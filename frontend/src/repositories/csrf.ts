import { ApiError } from "@/shared/errors";

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

  // An HTML error page from a proxy, or the app's own index.html.
  if (!response.ok || !response.headers.get("Content-Type")?.includes("json")) {
    throw new ApiError(
      `The Vulniverse API didn't answer (${response.status} ${response.statusText}); is the backend running?`,
      response.status,
      null,
    );
  }

  const body = await response.json() as { csrfToken: string };

  return body.csrfToken;
}

export function getCsrfToken(apiRoot = "/api/v1"): Promise<string> {
  // A failed fetch isn't kept, so the next request tries again.
  cachedToken ??= fetchCsrfToken(apiRoot).catch((error: unknown) => {
    cachedToken = null;
    throw error;
  });

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
