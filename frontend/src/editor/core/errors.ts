export class EditorRepositoryError
  extends Error {
  constructor(
    message: string,
    public readonly status?: number,
    public readonly details?: unknown,
  ) {
    super(message);

    this.name =
      "EditorRepositoryError";
  }
}


export function normalizeError(
  error: unknown,
  fallbackMessage: string,
): Error {
  return error instanceof Error
    ? error
    : new Error(fallbackMessage);
}
