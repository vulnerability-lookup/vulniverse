import type {
  JsonSchema,
} from "@jsonforms/core";

import {
  scoreVector,
} from "../common/cvss/score";

import type {
  CalculatorVersion,
} from "../common/cvss/score";


const CALCULATOR_VERSIONS: readonly string[] = ["2.0", "3.0", "3.1", "4.0"];

// The fields FIRST's CVSS schemas require; the rest restate the vector.
const KEPT_FIELDS = ["version", "vectorString", "baseScore", "baseSeverity"];

export type CvssObject = Record<string, unknown>;


/**
 * The CVSS versions a FIRST CVSS object schema accepts, read from its
 * `version` enum: ["2.0"] for cvss_v2, ["3.0", "3.1"] for cvss_v3 (a
 * oneOf of both), ["4.0"] for cvss_v4. [] for any other schema.
 */
export function cvssVersions(
  schema: JsonSchema | undefined,
): CalculatorVersion[] {
  const branches = schema?.oneOf ?? (schema ? [schema] : []);

  const versions = branches.flatMap((branch) => {
    const properties = branch.properties;

    return properties?.vectorString && Array.isArray(properties.version?.enum)
      ? properties.version.enum
      : [];
  });

  return versions.length > 0 && versions.every((version) => CALCULATOR_VERSIONS.includes(version))
    ? versions as CalculatorVersion[]
    : [];
}


/** The allowed version a vector's "CVSS:x.y/" prefix names, if any. */
export function prefixVersion(
  vector: unknown,
  versions: CalculatorVersion[],
): CalculatorVersion | undefined {
  const prefix = typeof vector === "string"
    ? /^CVSS:(\d\.\d)\//.exec(vector)?.[1]
    : undefined;

  return versions.find((version) => version === prefix);
}


/** The version of `data`: its own, the vector's prefix, or the newest allowed. */
export function versionOf(
  data: CvssObject | undefined,
  versions: CalculatorVersion[],
): CalculatorVersion {
  const own = data?.version;

  if (typeof own === "string" && versions.includes(own as CalculatorVersion)) {
    return own as CalculatorVersion;
  }

  return prefixVersion(data?.vectorString, versions) ?? versions[versions.length - 1]!;
}


/** The fields beyond the required ones, e.g. attackVector or temporalScore. */
export function extraFields(
  data: CvssObject | undefined,
): string[] {
  return Object.keys(data ?? {}).filter((key) => !KEPT_FIELDS.includes(key));
}


/**
 * The CVSS object for a vector: version, vectorString and the base score
 * and severity computed from it. While the vector is incomplete the
 * previous score is kept. The optional per-metric fields are dropped, as
 * they would contradict a changed vector (CSAF's mandatory tests check
 * that they agree).
 */
export function cvssObject(
  version: CalculatorVersion,
  vectorString: string,
  previous: CvssObject | undefined,
): CvssObject {
  const computed = scoreVector(version, vectorString);
  const previousScore = typeof previous?.baseScore === "number" ? previous.baseScore : 0;
  const baseScore = computed?.score ?? previousScore;

  if (version === "2.0") {
    return { version, vectorString, baseScore };
  }

  const previousSeverity = typeof previous?.baseSeverity === "string"
    ? previous.baseSeverity
    : "NONE";

  return {
    version,
    vectorString,
    baseScore,
    baseSeverity: computed?.severity ?? previousSeverity,
  };
}
