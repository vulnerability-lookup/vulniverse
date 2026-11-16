import { describe, expect, it } from "vitest";

import {
  CVSS3_METRICS,
  buildVectorString,
  cveMetricFieldValues,
  parseVectorString,
  unknownVectorParts,
} from "../cvss-calculator";

describe("unknownVectorParts", () => {
  const vector = "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H/E:P/RL:O";

  it("returns the metrics the calculator has no dropdown for", () => {
    expect(unknownVectorParts(CVSS3_METRICS, vector)).toEqual(["E:P", "RL:O"]);
  });

  it("returns nothing for a pure base vector or an empty string", () => {
    expect(unknownVectorParts(CVSS3_METRICS, "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H")).toEqual([]);
    expect(unknownVectorParts(CVSS3_METRICS, "")).toEqual([]);
  });

  it("round-trips a vector with temporal metrics unchanged", () => {
    const rebuilt = [
      buildVectorString(CVSS3_METRICS, parseVectorString(CVSS3_METRICS, vector), "CVSS:3.1"),
      ...unknownVectorParts(CVSS3_METRICS, vector),
    ].join("/");

    expect(rebuilt).toBe(vector);
  });
});

describe("cveMetricFieldValues", () => {
  it("rewrites only the mirroring fields a record already has, in the schema's words", () => {
    expect(cveMetricFieldValues(
      "cvssV3_1",
      "CVSS:3.1/AV:A/AC:L/PR:N/UI:R/S:C/C:H/I:H/A:H",
      { attackVector: "NETWORK", userInteraction: "NONE", baseScore: 10 },
    )).toEqual({ attackVector: "ADJACENT_NETWORK", userInteraction: "REQUIRED" });

    expect(cveMetricFieldValues(
      "cvssV4_0",
      "CVSS:4.0/AV:A/AC:L/AT:P/PR:N/UI:P/VC:H/VI:H/VA:H/SC:N/SI:N/SA:N",
      { attackVector: "NETWORK", attackRequirements: "NONE" },
    )).toEqual({ attackVector: "ADJACENT", attackRequirements: "PRESENT" });

    expect(cveMetricFieldValues("cvssV2_0", "AV:A/AC:M/Au:S/C:P/I:N/A:C", { accessVector: "LOCAL", authentication: "NONE" }))
      .toEqual({ accessVector: "ADJACENT_NETWORK", authentication: "SINGLE" });
  });
});
