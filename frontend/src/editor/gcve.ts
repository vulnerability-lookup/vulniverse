import type {
  GcveExtension,
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
