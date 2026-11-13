/*
 * Read-only views of a CSAF 2.1 document for CsafPreviewSection.vue.
 * Every helper tolerates incomplete drafts: wrong types read as empty.
 */

export type AnyRecord = Record<string, unknown>;


export function obj(
  value: unknown,
): AnyRecord {
  return typeof value === "object" && value !== null && !Array.isArray(value)
    ? value as AnyRecord
    : {};
}


export function list(
  value: unknown,
): AnyRecord[] {
  return Array.isArray(value)
    ? value.filter((item): item is AnyRecord => typeof item === "object" && item !== null)
    : [];
}


export function strings(
  value: unknown,
): string[] {
  return Array.isArray(value)
    ? value.filter((item): item is string => typeof item === "string" && item !== "")
    : [];
}


export function text(
  value: unknown,
): string {
  return typeof value === "string" ? value : "";
}


/** "known_not_affected" → "Known not affected". */
export function label(
  value: string,
): string {
  const words = value.replace(/_/g, " ");

  return words.charAt(0).toUpperCase() + words.slice(1);
}


// Spec order: affected first, then not affected, fixed, the rest.
export const PRODUCT_STATUSES = [
  "first_affected",
  "known_affected",
  "last_affected",
  "known_not_affected",
  "first_fixed",
  "fixed",
  "recommended",
  "under_investigation",
  "unknown",
] as const;


export interface Score {
  kind: string;
  value: string;
  detail: string;
}


/** One line per score of a metric's content (CVSS, EPSS, SSVC, …). */
export function scores(
  content: AnyRecord,
): Score[] {
  const result: Score[] = [];

  // Newest first; the name used while a draft has no version yet.
  for (const [key, fallback] of [["cvss_v4", "4.0"], ["cvss_v3", "3"], ["cvss_v2", "2.0"]] as const) {
    const cvss = obj(content[key]);

    if (Object.keys(cvss).length) {
      result.push({
        kind: `CVSS ${text(cvss.version) || fallback}`,
        value: [cvss.baseScore, text(cvss.baseSeverity)].filter((part) => part !== undefined && part !== "").join(" "),
        detail: text(cvss.vectorString),
      });
    }
  }

  const epss = obj(content.epss);

  if (Object.keys(epss).length) {
    result.push({
      kind: "EPSS",
      value: `probability ${text(epss.probability)}`,
      detail: `percentile ${text(epss.percentile)}`,
    });
  }

  if (text(content.qualitative_severity_rating)) {
    result.push({ kind: "Severity", value: text(content.qualitative_severity_rating), detail: "" });
  }

  const ssvc = obj(content.ssvc_v2);

  if (Object.keys(ssvc).length) {
    result.push({
      kind: "SSVC",
      value: list(ssvc.selections)
        .map((selection) => `${text(selection.key)}: ${strings(list(selection.values).map((value) => value.key)).join("/")}`)
        .join(", "),
      detail: text(ssvc.timestamp),
    });
  }

  return result;
}
