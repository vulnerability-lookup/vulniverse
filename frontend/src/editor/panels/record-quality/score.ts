/*
 * Scores a CVE JSON 5 / GCVE record with Vulnerability-Lookup's
 * assigner-scorecard methodology v1: the same checks, weights and
 * grades as VL's scorer, ported from Vulniverse's former Python one.
 * __tests__/reference-scores.json holds that scorer's results; keep
 * them passing when changing anything here.
 *
 * Python's rules are kept where JavaScript differs: truthiness ({} and
 * [] are empty), lengths in code points, Unicode-aware \W, \b and \d.
 */

import type {
  EditorDocument,
  RecordQualityScore,
} from "../../contracts";

export const METHODOLOGY_VERSION = 1;

type Json = Record<string, unknown>;

interface Check {
  id: string;
  pillar: string;
  weight: number;
  rule: string;
}

const PILLARS: readonly [string, string][] = [
  ["describe", "Describe: can a reader tell what the vulnerability is?"],
  ["scope", "Scope: can a reader tell whether they are affected?"],
  ["assess", "Assess: can a reader tell how bad it is?"],
  ["act", "Act: can a reader tell what to do about it?"],
];

const CHECKS: readonly Check[] = [
  { id: "description", pillar: "describe", weight: 10, rule: "English description quality: full credit from 200 characters, 0.7 from 80, 0.4 from 40." },
  { id: "title", pillar: "describe", weight: 5, rule: "A non-placeholder title is present." },
  { id: "cwe", pillar: "describe", weight: 10, rule: "A CWE identifier is present in problemTypes; a meaningful free-text problem type receives partial credit." },
  { id: "affected", pillar: "scope", weight: 10, rule: "An affected entry identifies vendor and product; identifying only one receives partial credit." },
  { id: "versions", pillar: "scope", weight: 8, rule: "Affected versions or version bounds are stated; defaultStatus alone receives partial credit." },
  { id: "cpe", pillar: "scope", weight: 7, rule: "A CPE is stated in affected data or cpeApplicability." },
  { id: "severity", pillar: "assess", weight: 15, rule: "A CVSS v3/v4 vector, SSVC decision, or other vendor severity statement is present; CVSS v2 alone receives partial credit." },
  { id: "modern_severity", pillar: "assess", weight: 5, rule: "A CVSS v4 vector or SSVC decision is present." },
  { id: "impacts", pillar: "assess", weight: 5, rule: "An impact description or CAPEC identifier is present." },
  { id: "references", pillar: "act", weight: 7, rule: "At least one reference URL is present." },
  { id: "reference_tags", pillar: "act", weight: 5, rule: "At least one reference carries tags." },
  { id: "remediation", pillar: "act", weight: 8, rule: "A patch reference receives full credit; vendor-advisory, mitigation, or release-notes receives partial credit." },
  { id: "solutions", pillar: "act", weight: 5, rule: "At least one solution or workaround is present." },
];

const GRADES: readonly [string, number][] = [
  ["A", 90],
  ["B", 75],
  ["C", 60],
  ["D", 45],
  ["E", 0],
];

const CWE_ID = /^CWE-\p{Nd}+$/iu;

// Python's \W*, then a placeholder word ending at a Unicode word boundary.
const PLACEHOLDER =
  /^[^\p{L}\p{N}_]*(reserved|rejected|n\/?a|none|tbd|todo|placeholder|unknown)(?![\p{L}\p{N}_])/iu;

const NOT_A_VALUE = new Set(["", "n/a", "na", "none", "unknown", "unspecified", "-"]);

const REMEDIATION_TAGS = new Set(["vendor-advisory", "mitigation", "release-notes"]);

function isObject(value: unknown): value is Json {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

// Python's bool(): empty strings, lists, objects and 0 are false.
function truthy(value: unknown): boolean {
  if (Array.isArray(value)) return value.length > 0;
  if (isObject(value)) return Object.keys(value).length > 0;

  return Boolean(value);
}

function isRealValue(value: unknown): boolean {
  return typeof value === "string" && !NOT_A_VALUE.has(value.trim().toLowerCase());
}

// The normal array form, or a single object (VL tolerates both).
function objects(value: unknown): Json[] {
  if (isObject(value)) return [value];
  if (!Array.isArray(value)) return [];

  return value.filter(isObject);
}

function englishDescription(descriptions: unknown): string | null {
  if (!Array.isArray(descriptions)) return null;

  for (const description of descriptions) {
    if (!isObject(description)) continue;

    const value = description.value;
    const language = String(description.lang ?? "").toLowerCase();

    if (typeof value === "string" && value && language.startsWith("en")) {
      return value;
    }
  }

  return null;
}

function descriptionCredit(length: number): number {
  if (length >= 200) return 1;
  if (length >= 80) return 0.7;
  if (length >= 40) return 0.4;

  return 0;
}

function hasVector(cna: Json, keys: readonly string[]): boolean {
  return objects(cna.metrics).some((metric) =>
    keys.some((key) => {
      const value = metric[key];

      return isObject(value) && isRealValue(value.vectorString);
    }));
}

function otherMetrics(cna: Json): Json[] {
  return objects(cna.metrics).map((metric) => metric.other).filter(isObject);
}

function credits(record: EditorDocument): Record<string, number> {
  const containers = (record as Json).containers;
  const cna = isObject(containers) && isObject(containers.cna) ? containers.cna : {};
  const result: Record<string, number> = Object.fromEntries(CHECKS.map((check) => [check.id, 0]));

  // Describe
  const description = (englishDescription(cna.descriptions) ?? "").trim();
  result.description = descriptionCredit(PLACEHOLDER.test(description) ? 0 : [...description].length);
  result.title = isRealValue(cna.title) ? 1 : 0;

  const problems = objects(cna.problemTypes).flatMap((problem) => objects(problem.descriptions));

  if (problems.some((entry) => typeof entry.cweId === "string" && CWE_ID.test(entry.cweId.trim()))) {
    result.cwe = 1;
  } else if (problems.some((entry) => isRealValue(entry.description))) {
    result.cwe = 0.25;
  }

  // Scope
  const affected = objects(cna.affected);

  if (affected.some((entry) => isRealValue(entry.vendor) && isRealValue(entry.product))) {
    result.affected = 1;
  } else if (affected.some((entry) => isRealValue(entry.vendor) || isRealValue(entry.product))) {
    result.affected = 0.5;
  }

  const hasVersion = affected.some((entry) => objects(entry.versions).some((version) =>
    isRealValue(version.version) || isRealValue(version.lessThan) || isRealValue(version.lessThanOrEqual)));

  if (hasVersion) {
    result.versions = 1;
  } else if (affected.some((entry) => isRealValue(entry.defaultStatus))) {
    result.versions = 0.5;
  }

  const hasAffectedCpe = affected.some((entry) =>
    Array.isArray(entry.cpes) && entry.cpes.some(isRealValue));
  const hasApplicability = objects(cna.cpeApplicability).some((block) =>
    objects(block.nodes).some((node) =>
      objects(node.cpeMatch).some((match) => isRealValue(match.criteria))));

  result.cpe = hasAffectedCpe || hasApplicability ? 1 : 0;

  // Assess
  const hasSsvc = otherMetrics(cna).some((other) =>
    typeof other.type === "string" && other.type.trim().toLowerCase() === "ssvc");
  const hasOtherRating = otherMetrics(cna).some((other) =>
    truthy(other.content) || isRealValue(other.type));

  if (hasVector(cna, ["cvssV4_0", "cvssV3_1", "cvssV3_0"]) || hasSsvc || hasOtherRating) {
    result.severity = 1;
  } else if (hasVector(cna, ["cvssV2_0"])) {
    result.severity = 0.5;
  }

  result.modern_severity = hasSsvc || hasVector(cna, ["cvssV4_0"]) ? 1 : 0;
  result.impacts = objects(cna.impacts).some((impact) =>
    isRealValue(impact.capecId) || objects(impact.descriptions).length > 0) ? 1 : 0;

  // Act
  const references = objects(cna.references);
  const tags = references.flatMap((reference) => Array.isArray(reference.tags)
    ? reference.tags.filter((tag): tag is string => typeof tag === "string")
      .map((tag) => tag.trim().toLowerCase())
    : []);

  result.references = references.some((reference) => isRealValue(reference.url)) ? 1 : 0;
  result.reference_tags = tags.length > 0 ? 1 : 0;

  if (tags.some((tag) => tag.includes("patch"))) {
    result.remediation = 1;
  } else if (tags.some((tag) => REMEDIATION_TAGS.has(tag))) {
    result.remediation = 0.6;
  }

  result.solutions = objects(cna.solutions).length > 0 || objects(cna.workarounds).length > 0 ? 1 : 0;

  return result;
}

const round = (value: number): number => Math.round(value * 100) / 100;

function label(id: string): string {
  return id.split("_").map((word) => word.charAt(0).toUpperCase() + word.slice(1)).join(" ");
}

export function scoreRecordQuality(record: EditorDocument): RecordQualityScore {
  const credit = credits(record);
  const points = (check: Check): number => (credit[check.id] ?? 0) * check.weight;

  const score = round(CHECKS.reduce((sum, check) => sum + points(check), 0));

  return {
    score,
    grade: GRADES.find(([, minimum]) => score >= minimum)?.[0] ?? "E",
    methodologyVersion: METHODOLOGY_VERSION,
    pillars: PILLARS.map(([id, pillarLabel]) => {
      const checks = CHECKS.filter((check) => check.pillar === id);

      return {
        id,
        label: pillarLabel,
        points: round(checks.reduce((sum, check) => sum + points(check), 0)),
        maximum: checks.reduce((sum, check) => sum + check.weight, 0),
      };
    }),
    checks: CHECKS.map((check) => ({
      id: check.id,
      label: label(check.id),
      pillar: check.pillar,
      credit: credit[check.id] ?? 0,
      weight: check.weight,
      points: round(points(check)),
      rule: check.rule,
    })),
  };
}
