import { describe, expect, it } from "vitest";

import type { CveRecord, Patch2VulnResult } from "../../../contracts";
import { recordFromResult } from "../apply";

const generated = {
  record: {
    dataType: "CVE_RECORD",
    dataVersion: "5.2",
    cveMetadata: { cveId: "CVE-0000-0000", state: "PUBLISHED" },
    containers: {
      cna: {
        title: "Buffer overflow in widget",
        providerMetadata: { orgId: "patch2vuln" },
        x_gcve: [{ vulnId: "GCVE-0-2026-0001", recordType: "advisory" }],
      },
    },
  },
  osv: { id: "OSV-GENERATED", summary: "Buffer overflow in widget", details: "Details." },
  analysis: null,
} as unknown as Patch2VulnResult;

describe("recordFromResult", () => {
  it("fills a new CVE record with the generated CNA fields, not its metadata", () => {
    const record = recordFromResult("cve-5.2.0", generated) as CveRecord;

    expect(record.containers?.cna?.title).toBe("Buffer overflow in widget");
    expect(record.containers?.cna?.providerMetadata).toBeUndefined();
    expect(record.cveMetadata?.cveId).not.toBe("CVE-0000-0000");
  });

  it("merges the generated GCVE entries into a GCVE record", () => {
    const record = recordFromResult("gcve-bcp-05-1.7", generated) as CveRecord;

    expect(record.containers?.cna?.x_gcve).toEqual(
      expect.arrayContaining([expect.objectContaining({ vulnId: "GCVE-0-2026-0001" })]),
    );
  });

  it("uses the OSV rendering for an OSV record, keeping its own id", () => {
    const record = recordFromResult("osv-1.9.2", generated) as Record<string, unknown>;

    expect(record.summary).toBe("Buffer overflow in widget");
    expect(record.details).toBe("Details.");
    expect(record.id).not.toBe("OSV-GENERATED");
  });

  it("doesn't share objects with the result", () => {
    const record = recordFromResult("cve-5.2.0", generated) as CveRecord;

    record.containers!.cna!.title = "Changed";

    expect(generated.record.containers?.cna?.title).toBe("Buffer overflow in widget");
  });
});
