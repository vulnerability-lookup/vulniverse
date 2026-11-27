import type {
  EditorDocument,
} from "../../contracts";

export const ATTACK_TAXONOMY = "ATT&CK";
// The CVE schema requires a relationship name and value but defines
// neither; CNAs write e.g. "maps to" and the technique's name.
export const ATTACK_RELATIONSHIP = "maps to";

interface Relation {
  taxonomyId: string;
  relationshipName: string;
  relationshipValue: string;
}

interface Mapping {
  taxonomyName: string;
  taxonomyVersion?: string;
  taxonomyRelations: Relation[];
}

type Cna = Record<string, unknown> & {
  descriptions?: { lang?: string; value?: string }[];
  metrics?: Record<string, { baseSeverity?: string } | undefined>[];
  taxonomyMappings?: Mapping[];
};

function cnaOf(record: EditorDocument): Cna | null {
  const cna = (record.containers as { cna?: unknown } | undefined)?.cna;

  return cna && typeof cna === "object" && !Array.isArray(cna) ? cna as Cna : null;
}

export function isRejected(record: EditorDocument): boolean {
  return (record.cveMetadata as { state?: unknown } | undefined)?.state === "REJECTED";
}

// The models are English-only, so only an English description is sent.
export function englishDescription(record: EditorDocument): string {
  const description = cnaOf(record)?.descriptions?.find(
    (item) => /^en\b/i.test(item.lang ?? "") && item.value?.trim(),
  );

  return description?.value?.trim() ?? "";
}

// The record's own CVSS severity, newest version first, to compare the
// model's suggestion with.
export function cvssSeverity(record: EditorDocument): string | null {
  for (const key of ["cvssV4_0", "cvssV3_1", "cvssV3_0"]) {
    for (const metric of cnaOf(record)?.metrics ?? []) {
      const severity = metric[key]?.baseSeverity;

      if (severity) {
        return severity;
      }
    }
  }

  return null;
}

export function attackTechniqueIds(record: EditorDocument): Set<string> {
  return new Set(
    (cnaOf(record)?.taxonomyMappings ?? [])
      .filter((mapping) => mapping.taxonomyName === ATTACK_TAXONOMY)
      .flatMap((mapping) => mapping.taxonomyRelations ?? [])
      .map((relation) => relation.taxonomyId),
  );
}

// Adds the techniques the record doesn't have yet to its ATT&CK mapping
// (created if needed); returns how many were added.
export function addAttackTechniques(
  record: EditorDocument,
  techniques: { id: string; name: string }[],
): number {
  const cna = cnaOf(record);

  if (!cna || isRejected(record)) {
    return 0;
  }

  const existing = attackTechniqueIds(record);
  const added = techniques.filter((technique) => {
    if (existing.has(technique.id)) {
      return false;
    }

    existing.add(technique.id);
    return true;
  });

  if (added.length === 0) {
    return 0;
  }

  cna.taxonomyMappings ??= [];

  let mapping = cna.taxonomyMappings.find(
    (item) => item.taxonomyName === ATTACK_TAXONOMY,
  );

  if (!mapping) {
    mapping = { taxonomyName: ATTACK_TAXONOMY, taxonomyRelations: [] };
    cna.taxonomyMappings.push(mapping);
  }

  mapping.taxonomyRelations ??= [];
  mapping.taxonomyRelations.push(
    ...added.map((technique) => ({
      taxonomyId: technique.id,
      relationshipName: ATTACK_RELATIONSHIP,
      relationshipValue: technique.name.trim() || technique.id,
    })),
  );

  return added.length;
}
