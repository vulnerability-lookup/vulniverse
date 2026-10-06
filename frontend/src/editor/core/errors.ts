export function normalizeError(
  error: unknown,
  fallbackMessage: string,
): Error {
  return error instanceof Error
    ? error
    : new Error(fallbackMessage);
}
