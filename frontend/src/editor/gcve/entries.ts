export const KNOWN_GCVE_ENTRY_KEYS =
  new Set([
    "vulnId",
    "recordType",
    "relationships",
    "language",
    "extensions",
  ]);


export function extraGcveEntryEntries(
  entry: Record<string, unknown>,
): Array<[string, unknown]> {
  return Object.entries(entry).filter(
    ([key]) =>
      !KNOWN_GCVE_ENTRY_KEYS.has(key),
  );
}


export function extraGcveEntryFields(
  entry: Record<string, unknown>,
): Record<string, unknown> {
  return Object.fromEntries(
    extraGcveEntryEntries(entry),
  );
}
