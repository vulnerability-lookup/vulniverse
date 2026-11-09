/** Heading text for a record: its CVE/GCVE/OSV identifier, or what
 * state it's in when it doesn't have one yet. */
export function displayIdentifier(
  vulnerabilityId: string | null,
  saved: boolean,
): string {
  if (vulnerabilityId) {
    return vulnerabilityId;
  }

  return saved ? "Unassigned identifier" : "New vulnerability record";
}
