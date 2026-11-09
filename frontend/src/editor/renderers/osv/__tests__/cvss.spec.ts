import { describe, expect, it } from "vitest";

import { calculatorVersion, scoreHint } from "../cvss";

describe("calculatorVersion", () => {
  it("maps OSV types to calculator versions", () => {
    expect(calculatorVersion("CVSS_V2", "AV:N/AC:L/Au:N/C:P/I:P/A:P")).toBe("2.0");
    expect(calculatorVersion("CVSS_V3", "CVSS:3.0/AV:N")).toBe("3.0");
    expect(calculatorVersion("CVSS_V3", "CVSS:3.1/AV:N")).toBe("3.1");
    expect(calculatorVersion("CVSS_V3", "")).toBe("3.1");
    expect(calculatorVersion("CVSS_V4", "")).toBe("4.0");
    expect(calculatorVersion("Ubuntu", "medium")).toBeNull();
  });
});

describe("scoreHint", () => {
  it("scores a complete vector", () => {
    expect(scoreHint("CVSS_V3", "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"))
      .toEqual({ score: 9.8, severity: "CRITICAL" });
    expect(scoreHint("CVSS_V2", "AV:N/AC:L/Au:N/C:P/I:P/A:P")).toEqual({ score: 7.5, severity: null });
  });

  it("shows nothing for incomplete vectors or non-CVSS types", () => {
    expect(scoreHint("CVSS_V3", "CVSS:3.1/AV:N/AC:L")).toBeNull();
    expect(scoreHint("Ubuntu", "medium")).toBeNull();
  });
});
