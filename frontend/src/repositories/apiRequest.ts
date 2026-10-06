import { getCsrfToken } from "./csrf";
import { ApiError } from "@/shared/errors";

const MUTATING_METHODS = new Set(["POST", "PUT", "PATCH", "DELETE"]);

/*
 * A minimal fetch wrapper shared by every HTTP call in the app —
 * standalone-app-only endpoints that aren't part of the
 * EditorRepository contract (auth, per-user CNA credentials) call this
 * directly; HttpRepository.request() also delegates to it for the
 * contract's own endpoints, translating the ApiError this throws into
 * the editor's own EditorRepositoryError/RecordValidationError at that
 * boundary (see HttpRepository.ts) — this function itself only ever
 * knows about generic HTTP/API semantics, never the editor's.
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
    throw new ApiError(
      body?.message ?? `${response.status} ${response.statusText}`,
      response.status,
      body,
    );
  }

  return body as T;
}
