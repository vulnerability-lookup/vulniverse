import { describe, expect, it } from "vitest";

import { matchingOptions } from "../suggestions";

describe("matchingOptions", () => {
  const options = ["custom", "git", "maven", "semver"];

  it("shows all options for an empty field or an exact match", () => {
    expect(matchingOptions(options, "")).toEqual(options);
    expect(matchingOptions(options, "Semver")).toEqual(options);
  });

  it("filters by what's typed, in any case", () => {
    expect(matchingOptions(options, "VE")).toEqual(["maven", "semver"]);
    expect(matchingOptions(options, "npm")).toEqual([]);
  });
});
