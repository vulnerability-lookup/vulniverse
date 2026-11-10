import { describe, expect, it } from "vitest";

import {
  CVSS3_METRICS,
  buildVectorString,
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
