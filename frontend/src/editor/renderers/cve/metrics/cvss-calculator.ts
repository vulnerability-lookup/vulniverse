/*
 * Base-metric CVSS scoring for 2.0, 3.0/3.1, and 4.0.
 *
 * 2.0/3.x use the official closed-form formulas from the published
 * CVSS specifications
 *
 * 4.0's score isn't a closed-form formula — it's looked up against
 * an official ~270-entry equivalence-class table derived from FIRST's
 * own expert-elicitation study. The calculateCvss4BaseScore below is a direct
 * port of FIRST's own reference implementation (published at
 * https://www.first.org/cvss/cvss-v4.0.json, as vendored/adapted by
 * Vulnogram at default/cvss4/static/cvss40.js), restricted to the
 * Base metric group only
 */

export interface MetricOption {
  key: string;
  label: string;
  weight: number;
}

export interface MetricDefinition {
  key: string;
  label: string;
  options: MetricOption[];
}

function metric(
  key: string,
  label: string,
  options: MetricOption[],
): MetricDefinition {
  return { key, label, options };
}

export const CVSS2_METRICS: MetricDefinition[] = [
  metric("AV", "Access Vector", [
    { key: "L", label: "Local", weight: 0.395 },
    { key: "A", label: "Adjacent Network", weight: 0.646 },
    { key: "N", label: "Network", weight: 1.0 },
  ]),
  metric("AC", "Access Complexity", [
    { key: "H", label: "High", weight: 0.35 },
    { key: "M", label: "Medium", weight: 0.61 },
    { key: "L", label: "Low", weight: 0.71 },
  ]),
  metric("Au", "Authentication", [
    { key: "M", label: "Multiple", weight: 0.45 },
    { key: "S", label: "Single", weight: 0.56 },
    { key: "N", label: "None", weight: 0.704 },
  ]),
  metric("C", "Confidentiality Impact", [
    { key: "N", label: "None", weight: 0 },
    { key: "P", label: "Partial", weight: 0.275 },
    { key: "C", label: "Complete", weight: 0.660 },
  ]),
  metric("I", "Integrity Impact", [
    { key: "N", label: "None", weight: 0 },
    { key: "P", label: "Partial", weight: 0.275 },
    { key: "C", label: "Complete", weight: 0.660 },
  ]),
  metric("A", "Availability Impact", [
    { key: "N", label: "None", weight: 0 },
    { key: "P", label: "Partial", weight: 0.275 },
    { key: "C", label: "Complete", weight: 0.660 },
  ]),
];

// PR's weight depends on Scope, so its options are resolved per
// selection rather than being a static table like the others.
const CVSS3_PR_UNCHANGED: MetricOption[] = [
  { key: "N", label: "None", weight: 0.85 },
  { key: "L", label: "Low", weight: 0.62 },
  { key: "H", label: "High", weight: 0.27 },
];

const CVSS3_PR_CHANGED: MetricOption[] = [
  { key: "N", label: "None", weight: 0.85 },
  { key: "L", label: "Low", weight: 0.68 },
  { key: "H", label: "High", weight: 0.50 },
];

export const CVSS3_METRICS: MetricDefinition[] = [
  metric("AV", "Attack Vector", [
    { key: "N", label: "Network", weight: 0.85 },
    { key: "A", label: "Adjacent", weight: 0.62 },
    { key: "L", label: "Local", weight: 0.55 },
    { key: "P", label: "Physical", weight: 0.2 },
  ]),
  metric("AC", "Attack Complexity", [
    { key: "L", label: "Low", weight: 0.77 },
    { key: "H", label: "High", weight: 0.44 },
  ]),
  metric("PR", "Privileges Required", CVSS3_PR_UNCHANGED),
  metric("UI", "User Interaction", [
    { key: "N", label: "None", weight: 0.85 },
    { key: "R", label: "Required", weight: 0.62 },
  ]),
  metric("S", "Scope", [
    { key: "U", label: "Unchanged", weight: 0 },
    { key: "C", label: "Changed", weight: 0 },
  ]),
  metric("C", "Confidentiality Impact", [
    { key: "N", label: "None", weight: 0 },
    { key: "L", label: "Low", weight: 0.22 },
    { key: "H", label: "High", weight: 0.56 },
  ]),
  metric("I", "Integrity Impact", [
    { key: "N", label: "None", weight: 0 },
    { key: "L", label: "Low", weight: 0.22 },
    { key: "H", label: "High", weight: 0.56 },
  ]),
  metric("A", "Availability Impact", [
    { key: "N", label: "None", weight: 0 },
    { key: "L", label: "Low", weight: 0.22 },
    { key: "H", label: "High", weight: 0.56 },
  ]),
];

export const CVSS3_METRIC_ORDER = ["AV", "AC", "PR", "UI", "S", "C", "I", "A"];

export const CVSS4_METRICS: MetricDefinition[] = [
  metric("AV", "Attack Vector", [
    { key: "N", label: "Network", weight: 0 },
    { key: "A", label: "Adjacent", weight: 0 },
    { key: "L", label: "Local", weight: 0 },
    { key: "P", label: "Physical", weight: 0 },
  ]),
  metric("AC", "Attack Complexity", [
    { key: "L", label: "Low", weight: 0 },
    { key: "H", label: "High", weight: 0 },
  ]),
  metric("AT", "Attack Requirements", [
    { key: "N", label: "None", weight: 0 },
    { key: "P", label: "Present", weight: 0 },
  ]),
  metric("PR", "Privileges Required", [
    { key: "N", label: "None", weight: 0 },
    { key: "L", label: "Low", weight: 0 },
    { key: "H", label: "High", weight: 0 },
  ]),
  metric("UI", "User Interaction", [
    { key: "N", label: "None", weight: 0 },
    { key: "P", label: "Passive", weight: 0 },
    { key: "A", label: "Active", weight: 0 },
  ]),
  metric("VC", "Vulnerable System Confidentiality", [
    { key: "H", label: "High", weight: 0 },
    { key: "L", label: "Low", weight: 0 },
    { key: "N", label: "None", weight: 0 },
  ]),
  metric("VI", "Vulnerable System Integrity", [
    { key: "H", label: "High", weight: 0 },
    { key: "L", label: "Low", weight: 0 },
    { key: "N", label: "None", weight: 0 },
  ]),
  metric("VA", "Vulnerable System Availability", [
    { key: "H", label: "High", weight: 0 },
    { key: "L", label: "Low", weight: 0 },
    { key: "N", label: "None", weight: 0 },
  ]),
  metric("SC", "Subsequent System Confidentiality", [
    { key: "H", label: "High", weight: 0 },
    { key: "L", label: "Low", weight: 0 },
    { key: "N", label: "None", weight: 0 },
  ]),
  metric("SI", "Subsequent System Integrity", [
    { key: "H", label: "High", weight: 0 },
    { key: "L", label: "Low", weight: 0 },
    { key: "N", label: "None", weight: 0 },
  ]),
  metric("SA", "Subsequent System Availability", [
    { key: "H", label: "High", weight: 0 },
    { key: "L", label: "Low", weight: 0 },
    { key: "N", label: "None", weight: 0 },
  ]),
];

// Optional CVSS 4.0 groups. Every option list starts with "X" (Not
// Defined) as the default so adding these doesn't change the score
// for anyone who leaves them untouched
export const CVSS4_THREAT_METRICS: MetricDefinition[] = [
  metric("E", "Exploit Maturity", [
    { key: "X", label: "Not Defined", weight: 0 },
    { key: "A", label: "Attacked", weight: 0 },
    { key: "P", label: "Proof-of-Concept", weight: 0 },
    { key: "U", label: "Unreported", weight: 0 },
  ]),
];

export const CVSS4_ENVIRONMENTAL_METRICS: MetricDefinition[] = [
  metric("CR", "Confidentiality Requirement", [
    { key: "X", label: "Not Defined", weight: 0 },
    { key: "H", label: "High", weight: 0 },
    { key: "M", label: "Medium", weight: 0 },
    { key: "L", label: "Low", weight: 0 },
  ]),
  metric("IR", "Integrity Requirement", [
    { key: "X", label: "Not Defined", weight: 0 },
    { key: "H", label: "High", weight: 0 },
    { key: "M", label: "Medium", weight: 0 },
    { key: "L", label: "Low", weight: 0 },
  ]),
  metric("AR", "Availability Requirement", [
    { key: "X", label: "Not Defined", weight: 0 },
    { key: "H", label: "High", weight: 0 },
    { key: "M", label: "Medium", weight: 0 },
    { key: "L", label: "Low", weight: 0 },
  ]),
  metric("MAV", "Modified Attack Vector", [
    { key: "X", label: "Not Defined", weight: 0 },
    { key: "N", label: "Network", weight: 0 },
    { key: "A", label: "Adjacent", weight: 0 },
    { key: "L", label: "Local", weight: 0 },
    { key: "P", label: "Physical", weight: 0 },
  ]),
  metric("MAC", "Modified Attack Complexity", [
    { key: "X", label: "Not Defined", weight: 0 },
    { key: "L", label: "Low", weight: 0 },
    { key: "H", label: "High", weight: 0 },
  ]),
  metric("MAT", "Modified Attack Requirements", [
    { key: "X", label: "Not Defined", weight: 0 },
    { key: "N", label: "None", weight: 0 },
    { key: "P", label: "Present", weight: 0 },
  ]),
  metric("MPR", "Modified Privileges Required", [
    { key: "X", label: "Not Defined", weight: 0 },
    { key: "N", label: "None", weight: 0 },
    { key: "L", label: "Low", weight: 0 },
    { key: "H", label: "High", weight: 0 },
  ]),
  metric("MUI", "Modified User Interaction", [
    { key: "X", label: "Not Defined", weight: 0 },
    { key: "N", label: "None", weight: 0 },
    { key: "P", label: "Passive", weight: 0 },
    { key: "A", label: "Active", weight: 0 },
  ]),
  metric("MVC", "Modified Vulnerable System Confidentiality", [
    { key: "X", label: "Not Defined", weight: 0 },
    { key: "H", label: "High", weight: 0 },
    { key: "L", label: "Low", weight: 0 },
    { key: "N", label: "None", weight: 0 },
  ]),
  metric("MVI", "Modified Vulnerable System Integrity", [
    { key: "X", label: "Not Defined", weight: 0 },
    { key: "H", label: "High", weight: 0 },
    { key: "L", label: "Low", weight: 0 },
    { key: "N", label: "None", weight: 0 },
  ]),
  metric("MVA", "Modified Vulnerable System Availability", [
    { key: "X", label: "Not Defined", weight: 0 },
    { key: "H", label: "High", weight: 0 },
    { key: "L", label: "Low", weight: 0 },
    { key: "N", label: "None", weight: 0 },
  ]),
  metric("MSC", "Modified Subsequent System Confidentiality", [
    { key: "X", label: "Not Defined", weight: 0 },
    { key: "H", label: "High", weight: 0 },
    { key: "L", label: "Low", weight: 0 },
    { key: "N", label: "None", weight: 0 },
  ]),
  metric("MSI", "Modified Subsequent System Integrity", [
    { key: "X", label: "Not Defined", weight: 0 },
    { key: "S", label: "Safety", weight: 0 },
    { key: "H", label: "High", weight: 0 },
    { key: "L", label: "Low", weight: 0 },
    { key: "N", label: "None", weight: 0 },
  ]),
  metric("MSA", "Modified Subsequent System Availability", [
    { key: "X", label: "Not Defined", weight: 0 },
    { key: "S", label: "Safety", weight: 0 },
    { key: "H", label: "High", weight: 0 },
    { key: "L", label: "Low", weight: 0 },
    { key: "N", label: "None", weight: 0 },
  ]),
];

// Supplemental group — purely informational, never affects the
// score (the reference implementation's Score() never reads these).
// U's option keys are the literal words the vector string uses
// (e.g. "U:Amber"), not single-letter codes like every other metric.
export const CVSS4_SUPPLEMENTAL_METRICS: MetricDefinition[] = [
  metric("S", "Safety", [
    { key: "X", label: "Not Defined", weight: 0 },
    { key: "N", label: "Negligible", weight: 0 },
    { key: "P", label: "Present", weight: 0 },
  ]),
  metric("AU", "Automatable", [
    { key: "X", label: "Not Defined", weight: 0 },
    { key: "N", label: "No", weight: 0 },
    { key: "Y", label: "Yes", weight: 0 },
  ]),
  metric("R", "Recovery", [
    { key: "X", label: "Not Defined", weight: 0 },
    { key: "A", label: "Automatic", weight: 0 },
    { key: "U", label: "User", weight: 0 },
    { key: "I", label: "Irrecoverable", weight: 0 },
  ]),
  metric("V", "Value Density", [
    { key: "X", label: "Not Defined", weight: 0 },
    { key: "D", label: "Diffuse", weight: 0 },
    { key: "C", label: "Concentrated", weight: 0 },
  ]),
  metric("RE", "Vulnerability Response Effort", [
    { key: "X", label: "Not Defined", weight: 0 },
    { key: "L", label: "Low", weight: 0 },
    { key: "M", label: "Moderate", weight: 0 },
    { key: "H", label: "High", weight: 0 },
  ]),
  metric("U", "Provider Urgency", [
    { key: "X", label: "Not Defined", weight: 0 },
    { key: "Clear", label: "Clear", weight: 0 },
    { key: "Green", label: "Green", weight: 0 },
    { key: "Amber", label: "Amber", weight: 0 },
    { key: "Red", label: "Red", weight: 0 },
  ]),
];

export type MetricSelection = Record<string, string>;

function weightOf(
  def: MetricDefinition,
  selection: MetricSelection,
  overrideOptions?: MetricOption[],
): number {
  const options = overrideOptions ?? def.options;
  const selectedKey = selection[def.key];
  const option = options.find((candidate) => candidate.key === selectedKey);

  return option?.weight ?? 0;
}

export function defaultSelection(
  metrics: MetricDefinition[],
): MetricSelection {
  const selection: MetricSelection = {};

  for (const def of metrics) {
    selection[def.key] = def.options[0]!.key;
  }

  return selection;
}

/**
 * Builds a vector string from the given metrics/selection. A metric
 * whose value is "X" (Not Defined) is omitted entirely — this only
 * ever applies to CVSS 4.0's optional Threat/Environmental groups,
 * since no 2.0/3.x metric offers "X" as an option.
 */
export function buildVectorString(
  metrics: MetricDefinition[],
  selection: MetricSelection,
  prefix?: string,
): string {
  const parts = metrics
    .map((def) => ({ key: def.key, value: selection[def.key] ?? def.options[0]!.key }))
    .filter((part) => part.value !== "X")
    .map((part) => `${part.key}:${part.value}`);

  return prefix ? `${prefix}/${parts.join("/")}` : parts.join("/");
}

/**
 * Parses a vector string produced by buildVectorString (or an
 * equivalent official one) back into a MetricSelection, ignoring any
 * "CVSS:x.y" prefix and any metrics not in the known set (e.g.
 * temporal/environmental) — used to preselect the calculator's
 * dropdowns from a vectorString already on the record, best-effort.
 */
export function parseVectorString(
  metrics: MetricDefinition[],
  vectorString: string,
): MetricSelection {
  const selection = defaultSelection(metrics);

  for (const part of vectorString.split("/")) {
    const [key, value] = part.split(":");

    if (!key || !value) {
      continue;
    }

    const def = metrics.find((candidate) => candidate.key === key);
    const validOption = def?.options.some((option) => option.key === value);

    if (def && validOption) {
      selection[key] = value;
    }
  }

  return selection;
}

function round1(value: number): number {
  return Math.round(value * 10) / 10;
}

export function calculateCvss2BaseScore(
  selection: MetricSelection,
): number {
  const av = weightOf(CVSS2_METRICS[0]!, selection);
  const ac = weightOf(CVSS2_METRICS[1]!, selection);
  const au = weightOf(CVSS2_METRICS[2]!, selection);
  const c = weightOf(CVSS2_METRICS[3]!, selection);
  const i = weightOf(CVSS2_METRICS[4]!, selection);
  const a = weightOf(CVSS2_METRICS[5]!, selection);

  const impact = 10.41 * (1 - (1 - c) * (1 - i) * (1 - a));
  const fImpact = impact === 0 ? 0 : 1.176;
  const exploitability = 20 * av * ac * au;

  return round1(
    (0.6 * impact + 0.4 * exploitability - 1.5) * fImpact,
  );
}

/*
 * The official "round up to the nearest 0.1" function from the CVSS
 * 3.x specification's reference implementation — a plain
 * Math.ceil(x*10)/10 suffers from floating-point representation
 * error at exact boundaries (e.g. treating 4.0 as 4.000000001 and
 * rounding it up to 4.1), which this integer-based version avoids.
 */
function roundUp(input: number): number {
  const intInput = Math.round(input * 100000);

  if (intInput % 10000 === 0) {
    return intInput / 100000;
  }

  return (Math.floor(intInput / 10000) + 1) / 10;
}

export function calculateCvss3BaseScore(
  selection: MetricSelection,
  cvssVersion: "3.0" | "3.1",
): number {
  const scopeChanged = selection.S === "C";

  const prOptions = scopeChanged ? CVSS3_PR_CHANGED : CVSS3_PR_UNCHANGED;
  const avDef = CVSS3_METRICS.find((m) => m.key === "AV")!;
  const acDef = CVSS3_METRICS.find((m) => m.key === "AC")!;
  const prDef = CVSS3_METRICS.find((m) => m.key === "PR")!;
  const uiDef = CVSS3_METRICS.find((m) => m.key === "UI")!;
  const cDef = CVSS3_METRICS.find((m) => m.key === "C")!;
  const iDef = CVSS3_METRICS.find((m) => m.key === "I")!;
  const aDef = CVSS3_METRICS.find((m) => m.key === "A")!;

  const av = weightOf(avDef, selection);
  const ac = weightOf(acDef, selection);
  const pr = weightOf(prDef, selection, prOptions);
  const ui = weightOf(uiDef, selection);
  const c = weightOf(cDef, selection);
  const i = weightOf(iDef, selection);
  const a = weightOf(aDef, selection);

  const iss = 1 - (1 - c) * (1 - i) * (1 - a);

  const iscBase = scopeChanged
    ? cvssVersion === "3.1"
      ? 7.52 * (iss - 0.029) - 3.25 * Math.pow(iss * 0.9731 - 0.02, 13)
      : 7.52 * (iss - 0.029) - 3.25 * Math.pow(iss - 0.02, 15)
    : 6.42 * iss;

  if (iscBase <= 0) {
    return 0;
  }

  const exploitability = 8.22 * av * ac * pr * ui;

  return scopeChanged
    ? roundUp(Math.min(1.08 * (iscBase + exploitability), 10))
    : roundUp(Math.min(iscBase + exploitability, 10));
}

export function severityFor3x(
  baseScore: number,
): string {
  if (baseScore === 0) return "NONE";
  if (baseScore < 4.0) return "LOW";
  if (baseScore < 7.0) return "MEDIUM";
  if (baseScore < 9.0) return "HIGH";
  return "CRITICAL";
}

// --- CVSS 4.0 base score (ported from FIRST's reference implementation) ---

const CVSS4_HIGHEST_SEVERITY_VECTORS: Record<number, Record<number, string[]>> = {
  1: {
    0: ["AV:N/PR:N/UI:N"],
    1: ["AV:A/PR:N/UI:N", "AV:N/PR:L/UI:N", "AV:N/PR:N/UI:P"],
    2: ["AV:P/PR:N/UI:N", "AV:A/PR:L/UI:P"],
  },
  2: {
    0: ["AC:L/AT:N"],
    1: ["AC:H/AT:N", "AC:L/AT:P"],
  },
  4: {
    0: ["SC:H/SI:S/SA:S"],
    1: ["SC:H/SI:H/SA:H"],
    2: ["SC:L/SI:L/SA:L"],
  },
};

// EQ3-EQ6 are jointly determined (Table 30) — keyed [eq3][eq6].
const CVSS4_HIGHEST_SEVERITY_VECTORS_EQ3_EQ6: Record<number, Record<number, string[]>> = {
  0: {
    0: ["VC:H/VI:H/VA:H/CR:H/IR:H/AR:H"],
    1: ["VC:H/VI:H/VA:L/CR:M/IR:M/AR:H", "VC:H/VI:H/VA:H/CR:M/IR:M/AR:M"],
  },
  1: {
    0: ["VC:L/VI:H/VA:H/CR:H/IR:H/AR:H", "VC:H/VI:L/VA:H/CR:H/IR:H/AR:H"],
    1: [
      "VC:L/VI:H/VA:L/CR:H/IR:M/AR:H",
      "VC:L/VI:H/VA:H/CR:H/IR:M/AR:M",
      "VC:H/VI:L/VA:H/CR:M/IR:H/AR:M",
      "VC:H/VI:L/VA:L/CR:M/IR:H/AR:H",
      "VC:L/VI:L/VA:H/CR:H/IR:H/AR:M",
    ],
  },
  2: {
    1: ["VC:L/VI:L/VA:L/CR:H/IR:H/AR:H"],
  },
};

const CVSS4_SEVERITY_INDEX: Record<string, string[]> = {
  AV: ["N", "A", "L", "P"],
  AC: ["L", "H"],
  AT: ["N", "P"],
  PR: ["N", "L", "H"],
  UI: ["N", "P", "A"],
  VC: ["H", "L", "N"],
  VI: ["H", "L", "N"],
  VA: ["H", "L", "N"],
  SC: ["H", "L", "N"],
  SI: ["S", "H", "L", "N"],
  SA: ["S", "H", "L", "N"],
  CR: ["H", "M", "L"],
  IR: ["H", "M", "L"],
  AR: ["H", "M", "L"],
};

const CVSS4_DEPTH: Record<number, Record<number, number>> = {
  1: { 0: 0, 1: 3, 2: 4 },
  2: { 0: 0, 1: 1 },
  4: { 0: 5, 1: 4, 2: 3 },
};

// [eq3][eq6]
const CVSS4_DEPTH_EQ3_EQ6: Record<number, Record<number, number>> = {
  0: { 0: 6, 1: 5 },
  1: { 0: 7, 1: 7 },
  2: { 1: 9 },
};

// MacroVectors maximum score given each equivalence set (Table 20).
const CVSS4_MACROVECTOR_SCORES: Record<string, number> = {
  "000000": 10, "000001": 9.9, "000010": 9.8, "000011": 9.5, "000020": 9.5, "000021": 9.2,
  "000100": 10, "000101": 9.6, "000110": 9.3, "000111": 8.7, "000120": 9.1, "000121": 8.1,
  "000200": 9.3, "000201": 9, "000210": 8.9, "000211": 8, "000220": 8.1, "000221": 6.8,
  "001000": 9.8, "001001": 9.5, "001010": 9.5, "001011": 9.2, "001020": 9, "001021": 8.4,
  "001100": 9.3, "001101": 9.2, "001110": 8.9, "001111": 8.1, "001120": 8.1, "001121": 6.5,
  "001200": 8.8, "001201": 8, "001210": 7.8, "001211": 7, "001220": 6.9, "001221": 4.8,
  "002001": 9.2, "002011": 8.2, "002021": 7.2, "002101": 7.9, "002111": 6.9, "002121": 5,
  "002201": 6.9, "002211": 5.5, "002221": 2.7,
  "010000": 9.9, "010001": 9.7, "010010": 9.5, "010011": 9.2, "010020": 9.2, "010021": 8.5,
  "010100": 9.5, "010101": 9.1, "010110": 9, "010111": 8.3, "010120": 8.4, "010121": 7.1,
  "010200": 9.2, "010201": 8.1, "010210": 8.2, "010211": 7.1, "010220": 7.2, "010221": 5.3,
  "011000": 9.5, "011001": 9.3, "011010": 9.2, "011011": 8.5, "011020": 8.5, "011021": 7.3,
  "011100": 9.2, "011101": 8.2, "011110": 8, "011111": 7.2, "011120": 7, "011121": 5.9,
  "011200": 8.4, "011201": 7, "011210": 7.1, "011211": 5.2, "011220": 5, "011221": 3,
  "012001": 8.6, "012011": 7.5, "012021": 5.2, "012101": 7.1, "012111": 5.2, "012121": 2.9,
  "012201": 6.3, "012211": 2.9, "012221": 1.7,
  "100000": 9.8, "100001": 9.5, "100010": 9.4, "100011": 8.7, "100020": 9.1, "100021": 8.1,
  "100100": 9.4, "100101": 8.9, "100110": 8.6, "100111": 7.4, "100120": 7.7, "100121": 6.4,
  "100200": 8.7, "100201": 7.5, "100210": 7.4, "100211": 6.3, "100220": 6.3, "100221": 4.9,
  "101000": 9.4, "101001": 8.9, "101010": 8.8, "101011": 7.7, "101020": 7.6, "101021": 6.7,
  "101100": 8.6, "101101": 7.6, "101110": 7.4, "101111": 5.8, "101120": 5.9, "101121": 5,
  "101200": 7.2, "101201": 5.7, "101210": 5.7, "101211": 5.2, "101220": 5.2, "101221": 2.5,
  "102001": 8.3, "102011": 7, "102021": 5.4, "102101": 6.5, "102111": 5.8, "102121": 2.6,
  "102201": 5.3, "102211": 2.1, "102221": 1.3,
  "110000": 9.5, "110001": 9, "110010": 8.8, "110011": 7.6, "110020": 7.6, "110021": 7,
  "110100": 9, "110101": 7.7, "110110": 7.5, "110111": 6.2, "110120": 6.1, "110121": 5.3,
  "110200": 7.7, "110201": 6.6, "110210": 6.8, "110211": 5.9, "110220": 5.2, "110221": 3,
  "111000": 8.9, "111001": 7.8, "111010": 7.6, "111011": 6.7, "111020": 6.2, "111021": 5.8,
  "111100": 7.4, "111101": 5.9, "111110": 5.7, "111111": 5.7, "111120": 4.7, "111121": 2.3,
  "111200": 6.1, "111201": 5.2, "111210": 5.7, "111211": 2.9, "111220": 2.4, "111221": 1.6,
  "112001": 7.1, "112011": 5.9, "112021": 3, "112101": 5.8, "112111": 2.6, "112121": 1.5,
  "112201": 2.3, "112211": 1.3, "112221": 0.6,
  "200000": 9.3, "200001": 8.7, "200010": 8.6, "200011": 7.2, "200020": 7.5, "200021": 5.8,
  "200100": 8.6, "200101": 7.4, "200110": 7.4, "200111": 6.1, "200120": 5.6, "200121": 3.4,
  "200200": 7, "200201": 5.4, "200210": 5.2, "200211": 4, "200220": 4, "200221": 2.2,
  "201000": 8.5, "201001": 7.5, "201010": 7.4, "201011": 5.5, "201020": 6.2, "201021": 5.1,
  "201100": 7.2, "201101": 5.7, "201110": 5.5, "201111": 4.1, "201120": 4.6, "201121": 1.9,
  "201200": 5.3, "201201": 3.6, "201210": 3.4, "201211": 1.9, "201220": 1.9, "201221": 0.8,
  "202001": 6.4, "202011": 5.1, "202021": 2, "202101": 4.7, "202111": 2.1, "202121": 1.1,
  "202201": 2.4, "202211": 0.9, "202221": 0.4,
  "210000": 8.8, "210001": 7.5, "210010": 7.3, "210011": 5.3, "210020": 6, "210021": 5,
  "210100": 7.3, "210101": 5.5, "210110": 5.9, "210111": 4, "210120": 4.1, "210121": 2,
  "210200": 5.4, "210201": 4.3, "210210": 4.5, "210211": 2.2, "210220": 2, "210221": 1.1,
  "211000": 7.5, "211001": 5.5, "211010": 5.8, "211011": 4.5, "211020": 4, "211021": 2.1,
  "211100": 6.1, "211101": 5.1, "211110": 4.8, "211111": 1.8, "211120": 2, "211121": 0.9,
  "211200": 4.6, "211201": 1.8, "211210": 1.7, "211211": 0.7, "211220": 0.8, "211221": 0.2,
  "212001": 5.3, "212011": 2.4, "212021": 1.4, "212101": 2.4, "212111": 1.2, "212121": 0.5,
  "212201": 1, "212211": 0.3, "212221": 0.1,
};

function cvss4SeverityDistance(
  metric: string,
  vecVal: string | undefined,
  mxVal: string | undefined,
): number {
  const values = CVSS4_SEVERITY_INDEX[metric]!;

  return values.indexOf(vecVal ?? "") - values.indexOf(mxVal ?? "");
}

function cvss4PartialValue(
  partial: string,
  metric: string,
): string | undefined {
  for (const part of partial.split("/")) {
    const [key, value] = part.split(":");

    if (key === metric) {
      return value;
    }
  }

  return undefined;
}

const CVSS4_MODIFIABLE_BASE_METRICS = [
  "AV", "AC", "AT", "PR", "UI", "VC", "VI", "VA", "SC", "SI", "SA",
];

/**
 * Resolves a metric's effective value, mirroring the reference
 * implementation's getReal(): a base metric's Modified (M*)
 * counterpart wins if it's set to anything but "Not Defined"; CR/IR/
 * AR and E fall back to their spec-defined defaults (High and
 * Attacked respectively) when "Not Defined" or absent, rather than
 * being treated as literally blank.
 */
function cvss4Real(
  selection: MetricSelection,
  metric: string,
): string {
  if (CVSS4_MODIFIABLE_BASE_METRICS.includes(metric)) {
    const modified = selection[`M${metric}`];

    if (modified && modified !== "X") {
      return modified;
    }

    return selection[metric] ?? "";
  }

  const value = selection[metric];

  if (value && value !== "X") {
    return value;
  }

  if (metric === "CR" || metric === "IR" || metric === "AR") {
    return "H";
  }

  if (metric === "E") {
    return "A";
  }

  return value ?? "";
}

function cvss4Macrovector(
  selection: MetricSelection,
): string {
  const av = cvss4Real(selection, "AV");
  const ac = cvss4Real(selection, "AC");
  const at = cvss4Real(selection, "AT");
  const pr = cvss4Real(selection, "PR");
  const ui = cvss4Real(selection, "UI");
  const vc = cvss4Real(selection, "VC");
  const vi = cvss4Real(selection, "VI");
  const va = cvss4Real(selection, "VA");
  const sc = cvss4Real(selection, "SC");
  const si = cvss4Real(selection, "SI");
  const sa = cvss4Real(selection, "SA");
  const cr = cvss4Real(selection, "CR");
  const ir = cvss4Real(selection, "IR");
  const ar = cvss4Real(selection, "AR");
  const e = cvss4Real(selection, "E");

  let eq1: string;
  if (av === "N" && pr === "N" && ui === "N") {
    eq1 = "0";
  } else if (av === "P" || !(av === "N" || pr === "N" || ui === "N")) {
    eq1 = "2";
  } else {
    eq1 = "1";
  }

  const eq2 = ac === "L" && at === "N" ? "0" : "1";

  let eq3: string;
  if (vc === "H" && vi === "H") {
    eq3 = "0";
  } else if (vc === "H" || vi === "H" || va === "H") {
    eq3 = "1";
  } else {
    eq3 = "2";
  }

  let eq4: string;
  if (si === "S" || sa === "S") {
    eq4 = "0";
  } else if (sc === "H" || si === "H" || sa === "H") {
    eq4 = "1";
  } else {
    eq4 = "2";
  }

  let eq5: string;
  if (e === "A" || e === "X") {
    eq5 = "0";
  } else if (e === "P") {
    eq5 = "1";
  } else {
    eq5 = "2";
  }

  const crh = cr === "H";
  const irh = ir === "H";
  const arh = ar === "H";
  const eq6 =
    (crh && vc === "H") || (irh && vi === "H") || (arh && va === "H")
      ? "0"
      : "1";

  return eq1 + eq2 + eq3 + eq4 + eq5 + eq6;
}

/**
 * CVSS 4.0 score, ported from FIRST's reference implementation — see
 * the module-level comment above for provenance and verification.
 * Covers the Base, Threat, and Environmental metric groups (not
 * Supplemental, which never affects the score).
 */
export function calculateCvss4BaseScore(
  selection: MetricSelection,
): number {
  if (
    ["VC", "VI", "VA", "SC", "SI", "SA"].every(
      (key) => cvss4Real(selection, key) === "N",
    )
  ) {
    return 0.0;
  }

  const mv = cvss4Macrovector(selection);
  const eq1 = Number(mv[0]);
  const eq2 = Number(mv[1]);
  const eq3 = Number(mv[2]);
  const eq4 = Number(mv[3]);
  const eq5 = Number(mv[4]);
  const eq6 = Number(mv[5]);
  const eqsv = CVSS4_MACROVECTOR_SCORES[mv]!;

  let lower = 0;

  let eq1nlm = NaN;
  if (eq1 < 2) {
    eq1nlm = CVSS4_MACROVECTOR_SCORES[`${eq1 + 1}${eq2}${eq3}${eq4}${eq5}${eq6}`]!;
    lower++;
  }

  let eq2nlm = NaN;
  if (eq2 < 1) {
    eq2nlm = CVSS4_MACROVECTOR_SCORES[`${eq1}${eq2 + 1}${eq3}${eq4}${eq5}${eq6}`]!;
    lower++;
  }

  let eq4nlm = NaN;
  if (eq4 < 2) {
    eq4nlm = CVSS4_MACROVECTOR_SCORES[`${eq1}${eq2}${eq3}${eq4 + 1}${eq5}${eq6}`]!;
    lower++;
  }

  let eq5nlm = NaN;
  if (eq5 < 2) {
    eq5nlm = CVSS4_MACROVECTOR_SCORES[`${eq1}${eq2}${eq3}${eq4}${eq5 + 1}${eq6}`]!;
    lower++;
  }

  // EQ3 and EQ6 are jointly determined — a plain +1 on either can
  // land on a combination the table doesn't define, so each case is
  // handled explicitly (per the reference implementation).
  let eq3eq6nlm = NaN;
  if (eq3 === 1 && eq6 === 1) {
    eq3eq6nlm = CVSS4_MACROVECTOR_SCORES[`${eq1}${eq2}${eq3 + 1}${eq4}${eq5}${eq6}`]!;
    lower++;
  } else if (eq3 === 0 && eq6 === 1) {
    eq3eq6nlm = CVSS4_MACROVECTOR_SCORES[`${eq1}${eq2}${eq3 + 1}${eq4}${eq5}${eq6}`]!;
    lower++;
  } else if (eq3 === 1 && eq6 === 0) {
    eq3eq6nlm = CVSS4_MACROVECTOR_SCORES[`${eq1}${eq2}${eq3}${eq4}${eq5}${eq6 + 1}`]!;
    lower++;
  } else if (eq3 === 0 && eq6 === 0) {
    eq3eq6nlm = Math.max(
      CVSS4_MACROVECTOR_SCORES[`${eq1}${eq2}${eq3 + 1}${eq4}${eq5}${eq6}`]!,
      CVSS4_MACROVECTOR_SCORES[`${eq1}${eq2}${eq3}${eq4}${eq5}${eq6 + 1}`]!,
    );
    lower++;
  }

  const msd = (nlm: number): number => {
    const value = Math.abs(nlm - eqsv);

    return isNaN(value) ? 0 : value;
  };

  let eq1msd = msd(eq1nlm);
  let eq2msd = msd(eq2nlm);
  let eq3eq6msd = msd(eq3eq6nlm);
  let eq4msd = msd(eq4nlm);
  let eq5msd = msd(eq5nlm);

  let eq1svdst = 0;
  let eq2svdst = 0;
  let eq3eq6svdst = 0;
  let eq4svdst = 0;
  // EQ5 has only one dimension (Exploit Maturity), so whichever
  // value it holds, that value's own bucket vector *is* the highest
  // one in that bucket — the severity distance to it is always 0.
  const eq5svdst = 0;

  search:
  for (const eq1mx of CVSS4_HIGHEST_SEVERITY_VECTORS[1]![eq1]!) {
    for (const eq2mx of CVSS4_HIGHEST_SEVERITY_VECTORS[2]![eq2]!) {
      for (const eq3eq6mx of CVSS4_HIGHEST_SEVERITY_VECTORS_EQ3_EQ6[eq3]![eq6]!) {
        for (const eq4mx of CVSS4_HIGHEST_SEVERITY_VECTORS[4]![eq4]!) {
          const partial = [eq1mx, eq2mx, eq3eq6mx, eq4mx].join("/");

          const distances = {
            AV: cvss4SeverityDistance("AV", cvss4Real(selection, "AV"), cvss4PartialValue(partial, "AV")),
            PR: cvss4SeverityDistance("PR", cvss4Real(selection, "PR"), cvss4PartialValue(partial, "PR")),
            UI: cvss4SeverityDistance("UI", cvss4Real(selection, "UI"), cvss4PartialValue(partial, "UI")),
            AC: cvss4SeverityDistance("AC", cvss4Real(selection, "AC"), cvss4PartialValue(partial, "AC")),
            AT: cvss4SeverityDistance("AT", cvss4Real(selection, "AT"), cvss4PartialValue(partial, "AT")),
            VC: cvss4SeverityDistance("VC", cvss4Real(selection, "VC"), cvss4PartialValue(partial, "VC")),
            VI: cvss4SeverityDistance("VI", cvss4Real(selection, "VI"), cvss4PartialValue(partial, "VI")),
            VA: cvss4SeverityDistance("VA", cvss4Real(selection, "VA"), cvss4PartialValue(partial, "VA")),
            SC: cvss4SeverityDistance("SC", cvss4Real(selection, "SC"), cvss4PartialValue(partial, "SC")),
            SI: cvss4SeverityDistance("SI", cvss4Real(selection, "SI"), cvss4PartialValue(partial, "SI")),
            SA: cvss4SeverityDistance("SA", cvss4Real(selection, "SA"), cvss4PartialValue(partial, "SA")),
            CR: cvss4SeverityDistance("CR", cvss4Real(selection, "CR"), cvss4PartialValue(partial, "CR")),
            IR: cvss4SeverityDistance("IR", cvss4Real(selection, "IR"), cvss4PartialValue(partial, "IR")),
            AR: cvss4SeverityDistance("AR", cvss4Real(selection, "AR"), cvss4PartialValue(partial, "AR")),
          };

          if (Object.values(distances).some((distance) => distance < 0)) {
            continue;
          }

          eq1svdst = distances.AV + distances.PR + distances.UI;
          eq2svdst = distances.AC + distances.AT;
          eq3eq6svdst =
            distances.VC + distances.VI + distances.VA
            + distances.CR + distances.IR + distances.AR;
          eq4svdst = distances.SC + distances.SI + distances.SA;

          break search;
        }
      }
    }
  }

  const eq1prop = eq1svdst / (CVSS4_DEPTH[1]![eq1]! + 1);
  const eq2prop = eq2svdst / (CVSS4_DEPTH[2]![eq2]! + 1);
  const eq3eq6prop = eq3eq6svdst / (CVSS4_DEPTH_EQ3_EQ6[eq3]![eq6]! + 1);
  const eq4prop = eq4svdst / (CVSS4_DEPTH[4]![eq4]! + 1);
  const eq5prop = eq5svdst / 2;

  eq1msd *= eq1prop;
  eq2msd *= eq2prop;
  eq3eq6msd *= eq3eq6prop;
  eq4msd *= eq4prop;
  eq5msd *= eq5prop;

  const mean =
    lower === 0
      ? 0
      : (eq1msd + eq2msd + eq3eq6msd + eq4msd + eq5msd) / lower;

  return round1(eqsv - mean);
}
