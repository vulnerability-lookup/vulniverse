import { describe, expect, it } from "vitest";

import { summary, withFields, withKind, withUpperBound } from "../versions";

describe("version entries", () => {
  it("switches between a single version and a range, keeping what fits", () => {
    const single = { version: "2.0", status: "affected", versionType: "semver" };
    const range = withKind(single, true);

    expect(range).toEqual({ ...single, lessThan: "" });
    expect(withKind({ ...range, lessThan: "2.4", changes: [{ at: "2.1", status: "unaffected" }] }, false))
      .toEqual(single);
  });

  it("moves the upper bound between below and up to and including", () => {
    expect(withUpperBound({ version: "1", lessThan: "2" }, "lessThanOrEqual"))
      .toEqual({ version: "1", lessThanOrEqual: "2" });
  });

  it("drops an emptied optional field, but keeps an emptied range bound", () => {
    expect(withFields({ version: "1", versionType: "semver" }, { versionType: "" })).toEqual({ version: "1" });
    expect(withFields({ version: "1", lessThan: "2" }, { lessThan: "" })).toEqual({ version: "1", lessThan: "" });
  });

  it("summarizes an entry for its card header", () => {
    expect(summary({ version: "2.4.1", status: "unaffected" })).toBe("unaffected · 2.4.1");
    expect(summary({
      version: "2.0", status: "affected", versionType: "semver", lessThan: "2.4.1",
      changes: [{ at: "2.3.5", status: "unaffected" }],
    })).toBe("affected · 2.0 ≤ v < 2.4.1 (semver) · 1 status change");
  });
});
