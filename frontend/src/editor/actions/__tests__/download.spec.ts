import { describe, expect, it } from "vitest";

import { recordName } from "../download";

const context = (record: object, identifier: string | null = null) =>
  ({ record, identifier, profile: "cve-5.2.0", isDraft: true }) as Parameters<typeof recordName>[0];

describe("recordName", () => {
  it("prefers the record's own vulnerability ID over its storage identifier", () => {
    expect(recordName(context({ cveMetadata: { cveId: "CVE-2021-44228" } }, "42"))).toBe("CVE-2021-44228");
    expect(recordName(context({
      cveMetadata: { cveId: "CVE-2021-44228" },
      containers: { cna: { x_gcve: [{ vulnId: "GCVE-1-2026-0001", recordType: "advisory" }] } },
    }))).toBe("GCVE-1-2026-0001");
    expect(recordName(context({ id: "GHSA-xxxx-yyyy" }))).toBe("GHSA-xxxx-yyyy");
  });

  it("falls back to the identifier, then to 'record', and keeps names file-safe", () => {
    expect(recordName(context({}, "42"))).toBe("42");
    expect(recordName(context({}))).toBe("record");
    expect(recordName(context({ id: "a/b c" }))).toBe("a_b_c");
  });
});
