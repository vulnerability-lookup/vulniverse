/**
 * Mirrors backend/src/vulniverse_api/api/records.py's
 * PLACEHOLDER_PREFIX/is_placeholder_identifier() — the identifier
 * create_record() assigns to a record saved with no vulnId/cveId
 * yet. A real CVE/GCVE identifier can never start with this (their
 * formats are fixed: "CVE-YYYY-NNNN", "GCVE-N-YYYY-NNNNN"), so
 * checking the prefix is unambiguous.
 */
const PLACEHOLDER_PREFIX = "draft-";

export function isPlaceholderIdentifier(identifier: string): boolean {
  return identifier.startsWith(PLACEHOLDER_PREFIX);
}

/** A placeholder identifier is a real, usable address (fetch/save
 * both work against it) — this is purely cosmetic, so a reader
 * doesn't mistake it for an assigned CVE/GCVE identifier.
 */
export function displayIdentifier(identifier: string | null): string {
  if (!identifier) {
    return "New vulnerability record";
  }

  return isPlaceholderIdentifier(identifier)
    ? "Unassigned identifier"
    : identifier;
}
