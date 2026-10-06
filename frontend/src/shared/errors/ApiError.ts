/*
 * Generic HTTP/API-level failure (401/403/404/409/500/...) — shared
 * application infrastructure, not an editor concept. Anything outside
 * the editor (auth, admin pages, CNA credentials) throws/catches this
 * directly; HttpRepository is the one place that translates it into
 * the editor's own EditorRepositoryError (see editor/core/errors.ts).
 */
export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly details?: unknown,
  ) {
    super(message);

    this.name = "ApiError";
  }
}
