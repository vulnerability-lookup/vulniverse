import type {
  GcveExtension,
  CveRecord
} from "../contracts";


export interface GcveOccurrence {
  path: Array<string | number>;
  extensions: GcveExtension[];
}


export function findXGcveOccurrences(
  document: unknown,
  path: Array<string | number> = [],
): GcveOccurrence[] {
  const occurrences:
    GcveOccurrence[] = [];

  if (Array.isArray(document)) {
    document.forEach(
      (item, index) => {
        occurrences.push(
          ...findXGcveOccurrences(
            item,
            [...path, index],
          ),
        );
      },
    );

    return occurrences;
  }

  if (
    document &&
    typeof document === "object"
  ) {
    for (
      const [key, value]
      of Object.entries(
        document as
          Record<string, unknown>,
      )
    ) {
      const childPath = [
        ...path,
        key,
      ];

      if (
        key === "x_gcve" &&
        Array.isArray(value)
      ) {
        occurrences.push({
          path: childPath,

          extensions:
            value as
              GcveExtension[],
        });
      }

      occurrences.push(
        ...findXGcveOccurrences(
          value,
          childPath,
        ),
      );
    }
  }

  return occurrences;
}


export function getGcveEntries(
  record: CveRecord,
): GcveExtension[] {
  const entries = record.containers?.cna?.x_gcve;

  return Array.isArray(entries) ? entries : [];
}

export function ensureGcveEntries(
  record: CveRecord,
): GcveExtension[] {
  record.containers ??= {};
  record.containers.cna ??= {};
  record.containers.cna.x_gcve ??= [];

  return record.containers.cna.x_gcve;
}

export function recordHasGcveId(
  record: CveRecord,
): boolean {
  return getGcveEntries(record).some(
    (entry) =>
      typeof entry.vulnId === "string" &&
      entry.vulnId.length > 0,
  );
}


export function getGcveVulnId(
  record: CveRecord,
): string | undefined {
  const advisory = getGcveEntries(record).find(
    (entry) =>
      entry.recordType === "advisory" &&
      typeof entry.vulnId === "string" &&
      entry.vulnId.length > 0,
  );

  return advisory?.vulnId;
}

/**
 * Sets the GCVE identifier in containers.cna.x_gcve.
 *
 * If an advisory entry already exists, its identifier is updated.
 * Otherwise, a new advisory entry is created.
 *
 * Other GCVE extension entries are preserved.
 */
export function setGcveVulnId(
  record: CveRecord,
  value: string,
): void {
  const entries = ensureGcveEntries(record);

  const advisory = entries.find(
    (entry) => entry.recordType === "advisory",
  );

  if (advisory) {
    advisory.vulnId = value;
  } else {
    entries.push({
      vulnId: value,
      recordType: "advisory",
    });
  }
}

/**
 * Merges generated GCVE extension entries (e.g. Patch2Vuln's output)
 * into the record's own containers.cna.x_gcve, in place.
 *
 * - At most one "advisory" entry is kept: an existing advisory is
 *   always reused (preserving its own vulnId) rather than replaced,
 *   since only one is allowed per record.
 * - Any other record type is matched by (recordType, vulnId); no
 *   match means the generated entry is appended as-is.
 * - A matched existing entry has its `extensions` merged shallowly
 *   (generated values win on conflict); every other field on the
 *   existing entry is left untouched.
 *
 * Returns false (nothing merged) if `generated` is empty.
 */
export function mergeGcveExtensions(
  record: CveRecord,
  generated: GcveExtension[],
): boolean {
  if (!Array.isArray(generated) || generated.length === 0) {
    return false;
  }

  const entries = ensureGcveEntries(record);

  for (const source of generated) {
    const incoming = JSON.parse(
      JSON.stringify(source),
    ) as GcveExtension;

    const existing = entries.find((entry) => {
      if (incoming.recordType === "advisory") {
        // Only one advisory is allowed.
        // Reuse the existing advisory regardless of its vulnId.
        return entry.recordType === "advisory";
      }

      return (
        entry.recordType === incoming.recordType &&
        entry.vulnId === incoming.vulnId
      );
    });

    if (!existing) {
      // No existing entry: include the complete generated entry.
      entries.push(incoming);
      continue;
    }

    // Preserve existing GCVE metadata and unrelated extensions.
    const oldExtensions =
      existing.extensions &&
      typeof existing.extensions === "object" &&
      !Array.isArray(existing.extensions)
        ? existing.extensions as Record<string, unknown>
        : {};

    const newExtensions =
      incoming.extensions &&
      typeof incoming.extensions === "object" &&
      !Array.isArray(incoming.extensions)
        ? incoming.extensions as Record<string, unknown>
        : {};

    existing.extensions = {
      ...oldExtensions,
      ...newExtensions,
    };
  }

  return true;
}
