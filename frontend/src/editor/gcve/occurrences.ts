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

/**
 * The real GCVE-BCP-05 identifier, read from wherever x_gcve actually
 * appears in the record — mirrors the backend's gcve_vuln_id()
 * (api/records.py) exactly, so both ends agree on which value wins.
 * cveMetadata.vulnId is deliberately not consulted here: it's a
 * derived mirror (see setGcveVulnId below), never an independent
 * source of truth.
 */
export function getGcveVulnId(
  record: CveRecord,
): string | undefined {
  for (const occurrence of findXGcveOccurrences(record)) {
    for (const entry of occurrence.extensions) {
      if (typeof entry?.vulnId === "string" && entry.vulnId) {
        return entry.vulnId;
      }
    }
  }

  return undefined;
}

/**
 * Sets the GCVE identifier the one place it actually belongs per the
 * GCVE-BCP-05 schema — the first x_gcve entry found anywhere in the
 * record, or a freshly-created one under containers.cna.x_gcve if
 * none exists yet (same location CnaPublicationPanel's reservation
 * flow already used). cveMetadata.vulnId is also mirrored alongside
 * it: non-standard and not part of the CVE 5.2.0 schema, but some
 * hosts (e.g. Vulnerability-Lookup) key their own save/routing off it
 * — see api/records.py's extract_identifier(). Never set directly by
 * UI; always derived from here.
 */
export function setGcveVulnId(
  record: CveRecord,
  value: string,
): void {
  const [firstOccurrence] = findXGcveOccurrences(record);

  let entries: GcveExtension[];

  if (firstOccurrence) {
    entries = firstOccurrence.extensions;
  } else {
    record.containers ??= {};
    record.containers.cna ??= {};
    record.containers.cna.x_gcve ??= [];

    entries = record.containers.cna.x_gcve as GcveExtension[];
  }

  const [firstEntry] = entries;

  if (firstEntry) {
    firstEntry.vulnId = value;
  } else {
    entries.push({ vulnId: value, recordType: "advisory" });
  }

  record.cveMetadata ??= {};
  record.cveMetadata.vulnId = value;
}
