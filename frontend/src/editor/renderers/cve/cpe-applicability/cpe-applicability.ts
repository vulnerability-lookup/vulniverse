/*
 * Pure data helpers for the CPE applicability builder
 * (CpeApplicabilityRenderer.vue / CpeConditionDialog.vue) — kept free
 * of Vue so the trickiest part (the version-constraint <-> raw schema
 * field conversion) is easy to reason about and test in isolation,
 * same idea as cvss-calculator.ts next to it.
 *
 * Schema shape (schemas/upstream/cve/5.2.0/CVE_Record_Format_bundled.json,
 * $defs cpeApplicabilityElement/cpe_node/cpe_match):
 *
 *   cpeApplicability: CpeStatement[]
 *   CpeStatement  = { operator?: "AND" | "OR"; negate?: boolean; nodes: CpeGroup[] }
 *   CpeGroup      = { operator: "AND" | "OR"; negate?: boolean; cpeMatch: CpeMatch[] }
 *   CpeMatch      = {
 *     vulnerable: boolean;
 *     criteria: string;
 *     matchCriteriaId?: string;
 *     versionStartIncluding?: string;
 *     versionStartExcluding?: string;
 *     versionEndIncluding?: string;
 *     versionEndExcluding?: string;
 *   }
 *
 * The schema never enforces that only one of versionStart{Including,
 * Excluding} (or the two versionEnd* fields) is set at a time — that's
 * on the UI to guarantee by construction, which is what
 * toVersionFields/fromVersionFields below exist for.
 */

export interface CpeMatch {
  vulnerable: boolean;
  criteria: string;
  matchCriteriaId?: string;
  versionStartIncluding?: string;
  versionStartExcluding?: string;
  versionEndIncluding?: string;
  versionEndExcluding?: string;
}

export interface CpeGroup {
  operator: "AND" | "OR";
  negate?: boolean;
  cpeMatch: CpeMatch[];
}

export interface CpeStatement {
  operator?: "AND" | "OR";
  negate?: boolean;
  nodes: CpeGroup[];
}

export type VersionBound = {
  value: string;
  inclusive: boolean;
};

export type VersionConstraintUi =
  | { mode: "any" }
  | { mode: "exact"; value: string }
  | { mode: "range"; from?: VersionBound; to?: VersionBound };

type VersionFields = Pick<
  CpeMatch,
  | "versionStartIncluding"
  | "versionStartExcluding"
  | "versionEndIncluding"
  | "versionEndExcluding"
>;

/*
 * "Exact version" has no dedicated schema field — it's represented as
 * an inclusive-inclusive single-point range (versionStartIncluding ===
 * versionEndIncluding === the value). Schema-legal, and recognized
 * symmetrically by fromVersionFields below so a record authored this
 * way round-trips as "Exact version" rather than "Range".
 */
export function toVersionFields(
  ui: VersionConstraintUi,
): VersionFields {
  if (ui.mode === "any") {
    return {};
  }

  if (ui.mode === "exact") {
    return {
      versionStartIncluding: ui.value,
      versionEndIncluding: ui.value,
    };
  }

  const fields: VersionFields = {};

  if (ui.from) {
    if (ui.from.inclusive) {
      fields.versionStartIncluding = ui.from.value;
    } else {
      fields.versionStartExcluding = ui.from.value;
    }
  }

  if (ui.to) {
    if (ui.to.inclusive) {
      fields.versionEndIncluding = ui.to.value;
    } else {
      fields.versionEndExcluding = ui.to.value;
    }
  }

  return fields;
}

export function fromVersionFields(
  match: VersionFields,
): VersionConstraintUi {
  const hasStart =
    match.versionStartIncluding !== undefined
    || match.versionStartExcluding !== undefined;

  const hasEnd =
    match.versionEndIncluding !== undefined
    || match.versionEndExcluding !== undefined;

  if (!hasStart && !hasEnd) {
    return { mode: "any" };
  }

  if (
    match.versionStartIncluding !== undefined
    && match.versionEndIncluding !== undefined
    && match.versionStartIncluding === match.versionEndIncluding
    && match.versionStartExcluding === undefined
    && match.versionEndExcluding === undefined
  ) {
    return { mode: "exact", value: match.versionStartIncluding };
  }

  const from: VersionBound | undefined =
    match.versionStartIncluding !== undefined
      ? { value: match.versionStartIncluding, inclusive: true }
      : match.versionStartExcluding !== undefined
        ? { value: match.versionStartExcluding, inclusive: false }
        : undefined;

  const to: VersionBound | undefined =
    match.versionEndIncluding !== undefined
      ? { value: match.versionEndIncluding, inclusive: true }
      : match.versionEndExcluding !== undefined
        ? { value: match.versionEndExcluding, inclusive: false }
        : undefined;

  return { mode: "range", from, to };
}

/*
 * Best-effort CPE 2.3 "application" criteria placeholder from free-text
 * vendor/product names — not a real CPE dictionary lookup (none exists
 * in this repo), just a starting point the user is expected to verify.
 */
export function slugForCpe(
  value: string | undefined,
): string {
  const slug = (value ?? "")
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "");

  return slug || "*";
}

export interface AffectedVersionEntry {
  version?: string;
  status?: string;
  lessThan?: string;
  lessThanOrEqual?: string;
}

export interface AffectedEntry {
  vendor?: string;
  product?: string;
  versions?: AffectedVersionEntry[];
}

export interface GeneratedCondition {
  vulnerable: true;
  criteria: string;
  versionConstraint: VersionConstraintUi;
  /** Set when the mapping from affected.versions[] was ambiguous, so the UI can flag it. */
  approximate: boolean;
}

/*
 * Maps one affected[] entry's versions[] to a best-effort version
 * constraint. Only the simplest, unambiguous shapes are mapped
 * precisely (a single exact affected version; a single affected
 * version with lessThan/lessThanOrEqual) — anything else (multiple
 * ranges, "unaffected" entries mixed in, no versions at all) falls
 * back to "any version" with approximate: true so the caller can
 * surface a hint that this needs manual review.
 */
function versionConstraintFromAffected(
  versions: AffectedVersionEntry[] | undefined,
): { constraint: VersionConstraintUi; approximate: boolean } {
  const affected = (versions ?? []).filter(
    (entry) => (entry.status ?? "affected") === "affected",
  );

  if (affected.length !== 1) {
    return { constraint: { mode: "any" }, approximate: affected.length > 1 };
  }

  const entry = affected[0]!;

  if (!entry.version) {
    return { constraint: { mode: "any" }, approximate: true };
  }

  if (entry.lessThan) {
    return {
      constraint: {
        mode: "range",
        from: { value: entry.version, inclusive: true },
        to: { value: entry.lessThan, inclusive: false },
      },
      approximate: false,
    };
  }

  if (entry.lessThanOrEqual) {
    return {
      constraint: {
        mode: "range",
        from: { value: entry.version, inclusive: true },
        to: { value: entry.lessThanOrEqual, inclusive: true },
      },
      approximate: false,
    };
  }

  return {
    constraint: { mode: "exact", value: entry.version },
    approximate: false,
  };
}

export function generateConditionsFromAffected(
  affected: AffectedEntry[],
): GeneratedCondition[] {
  return affected
    .filter((entry) => entry.vendor || entry.product)
    .map((entry) => {
      const { constraint, approximate } = versionConstraintFromAffected(entry.versions);

      return {
        vulnerable: true as const,
        criteria: `cpe:2.3:a:${slugForCpe(entry.vendor)}:${slugForCpe(entry.product)}:*:*:*:*:*:*:*:*`,
        versionConstraint: constraint,
        approximate,
      };
    });
}
