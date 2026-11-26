import { describe, expect, it } from "vitest";

import { getGcveVulnId } from "../occurrences";

function recordWith(...entries: { vulnId: string; recordType: string }[]) {
  return { containers: { cna: { x_gcve: entries } } };
}

describe("getGcveVulnId", () => {
  it("prefers the advisory's vulnId", () => {
    expect(getGcveVulnId(recordWith(
      { vulnId: "GCVE-0-2026-0002", recordType: "update" },
      { vulnId: "GCVE-0-2026-0001", recordType: "advisory" },
    ))).toBe("GCVE-0-2026-0001");
  });

  it("uses a standalone non-advisory record's only entry", () => {
    expect(getGcveVulnId(recordWith(
      { vulnId: "GCVE-0-2026-0002", recordType: "update" },
    ))).toBe("GCVE-0-2026-0002");
  });

  it("has none for several entries without an advisory", () => {
    expect(getGcveVulnId(recordWith(
      { vulnId: "GCVE-0-2026-0002", recordType: "update" },
      { vulnId: "GCVE-0-2026-0003", recordType: "update" },
    ))).toBeUndefined();
  });
});
