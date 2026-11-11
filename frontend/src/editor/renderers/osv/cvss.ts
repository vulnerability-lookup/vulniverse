import {
  scoreVector,
} from "../common/cvss/score";

import type {
  CalculatorVersion,
} from "../common/cvss/score";


export type {
  CalculatorVersion,
};


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
 * missing.
 */
export function scoreHint(
  type: unknown,
  score: unknown,
): { score: number; severity: string | null } | null {
  const version = calculatorVersion(type, score);

  return version && typeof score === "string"
    ? scoreVector(version, score)
    : null;
}
