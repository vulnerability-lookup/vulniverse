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


export function recordHasGcveId(
  record: CveRecord,
): boolean {
  return (
    record.containers?.cna?.x_gcve?.some(
      (entry) =>
        typeof entry.vulnId === "string" &&
        entry.vulnId.length > 0,
    ) ?? false
  );
}


export function getGcveVulnId(
  record: CveRecord,
): string | undefined {
  const entries = record.containers?.cna?.x_gcve;

  if (!Array.isArray(entries)) {
    return undefined;
  }

  const advisory = entries.find(
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
  record.containers ??= {};
  record.containers.cna ??= {};
  record.containers.cna.x_gcve ??= [];

  const entries = record.containers.cna.x_gcve;

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
