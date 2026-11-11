import {
  CVSS2_METRICS,
  CVSS3_METRICS,
  CVSS4_ENVIRONMENTAL_METRICS,
  CVSS4_METRICS,
  CVSS4_SUPPLEMENTAL_METRICS,
  CVSS4_THREAT_METRICS,
  calculateCvss2BaseScore,
  calculateCvss3BaseScore,
  calculateCvss4BaseScore,
  parseVectorString,
  severityFor3x,
} from "./cvss-calculator";


export type CalculatorVersion = "2.0" | "3.0" | "3.1" | "4.0";


/**
 * The base score of a complete CVSS vector. null when a base metric is
 * missing, so a half-typed vector never yields a misleading number.
 * CVSS 2.0 has no official qualitative rating, so its severity is null.
 */
export function scoreVector(
  version: CalculatorVersion,
  vector: string,
): { score: number; severity: string | null } | null {
  const base = version === "2.0"
    ? CVSS2_METRICS
    : version === "4.0" ? CVSS4_METRICS : CVSS3_METRICS;

  const present = new Set(vector.split("/").map((part) => part.split(":")[0]));

  if (!base.every((def) => present.has(def.key))) {
    return null;
  }

  const metrics = version === "4.0"
    ? [...base, ...CVSS4_THREAT_METRICS, ...CVSS4_ENVIRONMENTAL_METRICS, ...CVSS4_SUPPLEMENTAL_METRICS]
    : base;

  const selection = parseVectorString(metrics, vector);

  const value = version === "2.0"
    ? calculateCvss2BaseScore(selection)
    : version === "4.0"
      ? calculateCvss4BaseScore(selection)
      : calculateCvss3BaseScore(selection, version);

  if (value === null) {
    return null;
  }

  return { score: value, severity: version === "2.0" ? null : severityFor3x(value) };
}
