import type {
  CveRecord,
  EditorDocument,
  Patch2VulnResult,
} from "../../contracts";

import {
  mergeGcveExtensions,
} from "../../gcve";

import {
  getEditorProfile,
} from "../../profiles";

// Supported CNA fields for selective merging.
export const CVE_FIELDS = [
  { id: "title", label: "Title" },
  { id: "descriptions", label: "Descriptions" },
  { id: "affected", label: "Affected products" },
  { id: "problemTypes", label: "CWE classifications" },
  { id: "metrics", label: "CVSS metrics" },
  { id: "solutions", label: "Solutions" },
  { id: "references", label: "References" },
  { id: "impacts", label: "Impacts / CAPEC" },
  { id: "credits", label: "Credits" },
  { id: "cpeApplicability", label: "CPE applicability" },
  { id: "x_gcve", label: "GCVE metadata / AI provenance" },
] as const;

// Top-level OSV fields. id, schema_version, modified, published and
// withdrawn are never offered: they belong to this record, not to the
// generated one.
export const OSV_FIELDS = [
  { id: "summary", label: "Summary" },
  { id: "details", label: "Details" },
  { id: "aliases", label: "Aliases" },
  { id: "affected", label: "Affected packages" },
  { id: "severity", label: "Severity (CVSS)" },
  { id: "references", label: "References" },
  { id: "credits", label: "Credits" },
  { id: "database_specific", label: "Database specific (CWE, CAPEC, SSVC, GCVE)" },
] as const;

// Provider and lifecycle metadata belong to the record, not the analysis.
const PROTECTED_FIELDS = new Set([
  "providerMetadata",
  "datePublic",
  "dateUpdated",
  "dateAssigned",
  "rejectedReasons",
  "replacedBy",
]);

/** Copies the given CNA fields of a generated CVE record into `current`;
 * returns how many were applied. */
export function applyCveFields(
  current: CveRecord,
  generated: CveRecord,
  fields: readonly string[],
): number {
  current.containers ??= {};
  current.containers.cna ??= {};

  const source = generated.containers?.cna ?? {};
  const target = current.containers.cna;

  let count = 0;

  for (const field of fields) {
    // GCVE entries are merged, not replaced.
    if (field === "x_gcve") {
      if (mergeGcveExtensions(current, source.x_gcve ?? [])) {
        count++;
      }

      continue;
    }

    if (
      PROTECTED_FIELDS.has(field)
      || !Object.prototype.hasOwnProperty.call(source, field)
      || source[field] === undefined
    ) {
      continue;
    }

    // Works with Vue proxies and creates missing fields.
    target[field] = JSON.parse(JSON.stringify(source[field]));

    count++;
  }

  return count;
}

/** Copies the given top-level fields of a generated OSV record. */
export function applyOsvFields(
  target: Record<string, unknown>,
  generated: Record<string, unknown>,
  fields: readonly string[],
): number {
  let count = 0;

  for (const field of fields) {
    if (generated[field] === undefined) {
      continue;
    }

    target[field] = JSON.parse(JSON.stringify(generated[field]));

    count++;
  }

  return count;
}

/** A new record of the profile, filled with everything Patch2Vuln
 * generated, as the panel's "apply" with every field selected would. */
export function recordFromResult(
  profileId: string,
  result: Patch2VulnResult,
): EditorDocument {
  const profile = getEditorProfile(profileId);
  const document = profile.createEmptyDocument();

  if (profile.id.startsWith("osv-")) {
    applyOsvFields(
      document as Record<string, unknown>,
      (result.osv ?? {}) as Record<string, unknown>,
      OSV_FIELDS.map((field) => field.id),
    );
  } else {
    applyCveFields(
      document as CveRecord,
      result.record,
      CVE_FIELDS.map((field) => field.id),
    );
  }

  return document;
}
