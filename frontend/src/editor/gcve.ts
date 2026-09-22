import type {
  GcveExtension,
  VulnerabilityRecord,
} from "./contracts";

export interface GcveOccurrence {
  path: Array<string | number>;
  extensions: GcveExtension[];
}

/**
 * x_gcve is valid wherever it appears — record root, containers.cna.x_gcve,
 * containers.adp[*].x_gcve, other nested x_ namespaces — per GCVE-BCP-05's
 * "location-agnostic" rule. Mirrors
 * backend/src/vulniverse_api/services/record_validation.py's
 * find_x_gcve_occurrences() exactly, so the frontend discovers the same
 * occurrences the backend already validates, rather than only the
 * top-level placement the editor's own generated form/new-record default
 * happens to use.
 */
export const KNOWN_GCVE_ENTRY_KEYS = new Set([
  "vulnId",
  "recordType",
  "relationships",
  "language",
]);

export function extraGcveEntryEntries(
  entry: Record<string, unknown>,
): Array<[string, unknown]> {
  return Object.entries(entry).filter(
    ([key]) => !KNOWN_GCVE_ENTRY_KEYS.has(key),
  );
}

export function extraGcveEntryFields(
  entry: Record<string, unknown>,
): Record<string, unknown> {
  return Object.fromEntries(extraGcveEntryEntries(entry));
}

export function findXGcveOccurrences(
  document: unknown,
  path: Array<string | number> = [],
): GcveOccurrence[] {
  const occurrences: GcveOccurrence[] = [];

  if (Array.isArray(document)) {
    document.forEach((item, index) => {
      occurrences.push(
        ...findXGcveOccurrences(item, [...path, index]),
      );
    });
  } else if (document && typeof document === "object") {
    for (const [key, value] of Object.entries(document as Record<string, unknown>)) {
      const childPath = [...path, key];

      if (key === "x_gcve" && Array.isArray(value)) {
        occurrences.push({ path: childPath, extensions: value as GcveExtension[] });
      }

      occurrences.push(
        ...findXGcveOccurrences(value, childPath),
      );
    }
  }

  return occurrences;
}

/**
 * True once the record already carries a real GCVE identifier —
 * cveMetadata.vulnId (Vulniverse's own convenience field), or a
 * non-empty vulnId on any x_gcve entry, wherever it appears (see
 * findXGcveOccurrences above). Used to stop a second GCVE ID from
 * being reserved for a record that already has one, e.g. a record
 * assembled elsewhere and pasted in with its identifier already set
 * — CnaPublicationPanel.vue's own publication.status alone wouldn't
 * catch that, since no reservation has been made through *this*
 * panel yet.
 */
export function recordHasGcveId(
  record: VulnerabilityRecord,
): boolean {
  if (typeof record.cveMetadata?.vulnId === "string" && record.cveMetadata.vulnId) {
    return true;
  }

  return findXGcveOccurrences(record).some((occurrence) =>
    occurrence.extensions.some((entry) => Boolean(entry?.vulnId)));
}
