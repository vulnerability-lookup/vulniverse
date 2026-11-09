import { describe, expect, it } from "vitest";

import { singleKeyChoices } from "../testers";

const branch = (key: string) => ({
  type: "object" as const,
  properties: { [key]: { type: "string" as const } },
  required: [key],
});

describe("singleKeyChoices", () => {
  it("lists the keys of OSV-style event branches", () => {
    expect(singleKeyChoices({ oneOf: [branch("introduced"), branch("fixed")] }))
      .toEqual(["introduced", "fixed"]);
  });

  it("rejects branches that are not a single required key", () => {
    expect(singleKeyChoices({ oneOf: [branch("a"), { properties: { b: {}, c: {} } }] })).toEqual([]);
    expect(singleKeyChoices({ oneOf: [{ properties: { a: {} } }] })).toEqual([]);
    expect(singleKeyChoices({ type: "object" })).toEqual([]);
    expect(singleKeyChoices(undefined)).toEqual([]);
  });
});
