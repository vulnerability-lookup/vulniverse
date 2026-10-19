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
  if (
    typeof record.cveMetadata
      ?.vulnId === "string" &&
    record.cveMetadata.vulnId
  ) {
    return true;
  }

  return findXGcveOccurrences(
    record,
  ).some(
    (occurrence) =>
      occurrence.extensions.some(
        (entry) =>
          Boolean(entry?.vulnId),
      ),
  );
}
