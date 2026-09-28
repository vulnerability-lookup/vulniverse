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
  "extensions",
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

export type JsonSchemaLike = Record<string, unknown>;

/**
 * Finds the map of registered GCVE extension id -> JSON Schema
 * embedded in an authoring schema (see
 * scripts/generate_editor_schemas.py's add_gcve_extension_schemas(),
 * which injects schemas/extensions/gcve/registry.json's schemas into
 * every x_gcve occurrence it finds in the schema tree). Walks
 * generically for the same reason that Python function does: x_gcve
 * appears at more than one location (record root, containers.cna),
 * and all of them get the identical injected map, so the first one
 * found is enough.
 */
export function findGcveExtensionSchemas(
  schemaNode: unknown,
): Record<string, JsonSchemaLike> {
  if (Array.isArray(schemaNode)) {
    for (const item of schemaNode) {
      const found = findGcveExtensionSchemas(item);

      if (Object.keys(found).length > 0) {
        return found;
      }
    }

    return {};
  }

  if (schemaNode && typeof schemaNode === "object") {
    const node = schemaNode as Record<string, unknown>;
    const properties = node.properties as Record<string, unknown> | undefined;
    const xGcve = properties?.x_gcve as Record<string, unknown> | undefined;
    const items = xGcve?.items as Record<string, unknown> | undefined;
    const itemProperties = items?.properties as Record<string, unknown> | undefined;
    const extensions = itemProperties?.extensions as Record<string, unknown> | undefined;
    const extensionProperties = extensions?.properties as
      | Record<string, JsonSchemaLike>
      | undefined;

    if (extensionProperties) {
      return extensionProperties;
    }

    for (const value of Object.values(node)) {
      const found = findGcveExtensionSchemas(value);

      if (Object.keys(found).length > 0) {
        return found;
      }
    }
  }

  return {};
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
