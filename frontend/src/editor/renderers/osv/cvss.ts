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
} from "../common/cvss/cvss-calculator";


export type CalculatorVersion = "2.0" | "3.0" | "3.1" | "4.0";


/**
 * The calculator version for an OSV severity entry, or null when its
 * type isn't CVSS (e.g. "Ubuntu"). CVSS_V3 covers 3.0 and 3.1, told
 * apart by the vector's own prefix.
 */
export function calculatorVersion(
  type: unknown,
  score: unknown,
): CalculatorVersion | null {
  if (type === "CVSS_V2") return "2.0";
  if (type === "CVSS_V4") return "4.0";

  if (type === "CVSS_V3") {
    return typeof score === "string" && score.startsWith("CVSS:3.0/")
      ? "3.0"
      : "3.1";
  }

  return null;
}


/**
 * The base score of a complete CVSS vector, for display only (OSV
 * stores no score). null when the type isn't CVSS or a base metric is
 * missing, so a half-typed vector never shows a misleading number.
 */
export function scoreHint(
  type: unknown,
  score: unknown,
): { score: number; severity: string | null } | null {
  const version = calculatorVersion(type, score);

  if (!version || typeof score !== "string") {
    return null;
  }

  const base = version === "2.0"
    ? CVSS2_METRICS
    : version === "4.0" ? CVSS4_METRICS : CVSS3_METRICS;

  const present = new Set(score.split("/").map((part) => part.split(":")[0]));

  if (!base.every((def) => present.has(def.key))) {
    return null;
  }

  const metrics = version === "4.0"
    ? [...base, ...CVSS4_THREAT_METRICS, ...CVSS4_ENVIRONMENTAL_METRICS, ...CVSS4_SUPPLEMENTAL_METRICS]
    : base;

  const selection = parseVectorString(metrics, score);

  const value = version === "2.0"
    ? calculateCvss2BaseScore(selection)
    : version === "4.0"
      ? calculateCvss4BaseScore(selection)
      : calculateCvss3BaseScore(selection, version);

  if (value === null) {
    return null;
  }

  // CVSS 2.0 has no official qualitative rating.
  return { score: value, severity: version === "2.0" ? null : severityFor3x(value) };
}
