import { describe, expect, it } from "vitest";

import {
  CVSS2_METRICS,
  CVSS3_METRICS,
  CVSS4_ENVIRONMENTAL_METRICS,
  CVSS4_METRICS,
  CVSS4_SUPPLEMENTAL_METRICS,
  CVSS4_THREAT_METRICS,
} from "../cvss-calculator";
import { metricHelp } from "../cvss-help";

const VERSIONS = [
  ["2.0", CVSS2_METRICS],
  ["3.1", CVSS3_METRICS],
  ["4.0", [...CVSS4_METRICS, ...CVSS4_THREAT_METRICS, ...CVSS4_ENVIRONMENTAL_METRICS, ...CVSS4_SUPPLEMENTAL_METRICS]],
] as const;

describe("metricHelp", () => {
  it.each(VERSIONS)("explains every metric and option of CVSS %s", (version, metrics) => {
    const missing = metrics.flatMap((def) => {
      const help = metricHelp(version, def.key);

      return help
        ? def.options.filter((option) => !help.values[option.key]).map((option) => `${def.key}:${option.key}`)
        : [def.key];
    });

    expect(missing).toEqual([]);
  });

  it("words Modified metrics as the base metric in your environment", () => {
    expect(metricHelp("4.0", "MAV")?.question).toMatch(/^In your environment: how close/);
  });
});
