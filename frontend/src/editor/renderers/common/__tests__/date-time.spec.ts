import { describe, expect, it } from "vitest";

import { fromPickerValue, toPickerValue } from "../date-time";

describe("toPickerValue", () => {
  it("keeps seconds and drops fractions and the Z", () => {
    expect(toPickerValue("2026-12-28T23:59:59.123Z")).toBe("2026-12-28T23:59:59");
    expect(toPickerValue("2026-12-28T23:59:59Z")).toBe("2026-12-28T23:59:59");
  });

  it("fills in seconds the stored value left out", () => {
    expect(toPickerValue("2026-12-28T23:59Z")).toBe("2026-12-28T23:59:00");
  });

  it("returns empty for missing or unparsable values", () => {
    expect(toPickerValue(undefined)).toBe("");
    expect(toPickerValue("yesterday")).toBe("");
    expect(toPickerValue(42)).toBe("");
  });
});

describe("fromPickerValue", () => {
  it("stores the picker value as UTC with seconds", () => {
    expect(fromPickerValue("2026-12-27T23:59:59")).toBe("2026-12-27T23:59:59Z");
  });

  it("adds the :00 browsers omit for whole minutes", () => {
    expect(fromPickerValue("2026-12-27T23:59")).toBe("2026-12-27T23:59:00Z");
  });

  it("unsets the field when the picker is cleared", () => {
    expect(fromPickerValue("")).toBeUndefined();
  });

  it("round-trips an unedited value with seconds", () => {
    expect(fromPickerValue(toPickerValue("2026-12-28T23:59:59Z"))).toBe("2026-12-28T23:59:59Z");
  });
});
