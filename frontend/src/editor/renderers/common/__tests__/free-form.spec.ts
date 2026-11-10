import { describe, expect, it } from "vitest";

import { undeclaredEntries, withUndeclaredEntries } from "../free-form";

const data = { cwe_ids: ["CWE-22"], x_gcve: [{ vulnId: "GCVE-1-2026-0001" }] };

describe("undeclaredEntries", () => {
  it("leaves out the keys edited elsewhere", () => {
    expect(undeclaredEntries(data, ["x_gcve"])).toEqual({ cwe_ids: ["CWE-22"] });
  });

  it("is undefined when nothing else is there", () => {
    expect(undeclaredEntries({ x_gcve: [] }, ["x_gcve"])).toBeUndefined();
    expect(undeclaredEntries(undefined, ["x_gcve"])).toBeUndefined();
  });

  it("shows everything when no key is declared", () => {
    expect(undeclaredEntries(data, [])).toEqual(data);
  });
});

describe("withUndeclaredEntries", () => {
  it("keeps the declared keys while replacing the rest", () => {
    expect(withUndeclaredEntries(data, ["x_gcve"], { ssvc: { decision: "Track" } })).toEqual({
      x_gcve: [{ vulnId: "GCVE-1-2026-0001" }],
      ssvc: { decision: "Track" },
    });
  });

  it("keeps only the declared keys when the box is emptied", () => {
    expect(withUndeclaredEntries(data, ["x_gcve"], undefined)).toEqual({ x_gcve: data.x_gcve });
  });

  it("unsets the field when nothing is left", () => {
    expect(withUndeclaredEntries({ cwe_ids: [] }, ["x_gcve"], undefined)).toBeUndefined();
    expect(withUndeclaredEntries(undefined, [], undefined)).toBeUndefined();
  });
});
