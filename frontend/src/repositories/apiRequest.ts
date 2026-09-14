import { getCsrfToken } from "./csrf";
import { RepositoryError } from "./RepositoryError";

const MUTATING_METHODS = new Set(["POST", "PUT", "PATCH", "DELETE"]);

/*
 * A minimal fetch wrapper for standalone-app-only endpoints that aren't
 * part of the EditorRepository contract (auth, per-user CNA
 * credentials) — HttpRepository.request() covers the contract itself
 * and has its own RecordValidationError handling this doesn't need.
 */
export async function apiRequest<T>(
  path: string,
  init: RequestInit = {},
  apiRoot = "/api/v1",
): Promise<T> {
  const headers = new Headers(init.headers);

  headers.set("Accept", "application/json");

  if (init.body !== undefined) {
    headers.set("Content-Type", "application/json");
  }

  const method = (init.method ?? "GET").toUpperCase();

  if (MUTATING_METHODS.has(method)) {
    headers.set("X-CSRFToken", await getCsrfToken(apiRoot));
  }

  const response = await fetch(`${apiRoot}${path}`, {
    ...init,
    headers,
    credentials: "same-origin",
  });

  const body = await response.json().catch(() => null);

  if (!response.ok) {
    throw new RepositoryError(
      body?.message ?? `${response.status} ${response.statusText}`,
      response.status,
      body,
    );
  }

  return body as T;
}
