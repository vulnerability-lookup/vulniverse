/**
 * Record types explicitly named by GCVE-BCP-05.
 *
 * These are suggestions for the editor, not a closed enum:
 * unknown values remain valid.
 */
export const RECORD_TYPE_PRESETS = [
  "creation",
  "update",
  "analysis",
  "metadata",
  "reference",
  "comment",
  "statement",
  "remediation",
  "deprecation",
  "detection",
  "translation",
] as const;


/**
 * Recommended VXREF-derived relationship types.
 *
 * These are editor suggestions only. Unknown relationship values
 * remain allowed for forward compatibility.
 */
export const RELATIONSHIP_TYPE_PRESETS = [
  "possibly_related",
  "related",
  "not equal",
  "equal",
  "superset",
  "subset",
  "overlap",
  "opposes",
  "not_applicable",
] as const;
