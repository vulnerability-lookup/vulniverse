import { describe, expect, it } from "vitest";

import { differences, vulnerabilityIds } from "../compare";

const theirs = {
  cve: "CVE-2026-12345",
  title: "Stored XSS",
  notes: [{ category: "description", text: "Public description." }],
  cwes: [{ id: "CWE-79", name: "XSS", version: "4.20" }],
  disclosure_date: "2026-11-10T08:00:00Z",
  references: [{ category: "external", url: "https://a.example" }, { category: "external", url: "https://b.example" }],
  metrics: [{ content: { cvss_v3: { vectorString: "CVSS:3.1/AV:N" } }, products: ["CSAFPID-0001"] }],
};

describe("vulnerabilityIds", () => {
  it("finds the CVE and GCVE IDs", () => {
    expect(vulnerabilityIds({
      cve: "CVE-2026-12345",
      ids: [{ system_name: "GCVE", text: "GCVE-1-2026-00042" }, { system_name: "Github Issue", text: "x/y#1" }],
    })).toEqual(["CVE-2026-12345", "GCVE-1-2026-00042"]);
  });
});

describe("differences", () => {
  it("ignores the order of CVSS metrics", () => {
    const reordered = structuredClone(theirs);
    reordered.metrics[0]!.content.cvss_v3.vectorString = "CVSS:3.1/AC:L/AV:L/UI:R";
    const ours = structuredClone(theirs);
    ours.metrics[0]!.content.cvss_v3.vectorString = "CVSS:3.1/AV:L/AC:L/UI:R";

    expect(differences(ours, reordered)).toEqual([]);

    ours.metrics[0]!.content.cvss_v3.vectorString = "CVSS:3.1/AV:L/AC:L/UI:R/E:F";
    expect(differences(ours, reordered).map((difference) => difference.field)).toEqual(["cvss"]);
  });

  it("is empty when the advisory matches", () => {
    expect(differences(structuredClone(theirs), theirs)).toEqual([]);
  });

  it("lists what differs and takes the public values over", () => {
    const ours: Record<string, any> = { // eslint-disable-line @typescript-eslint/no-explicit-any -- JSON document
      title: "Old title",
      notes: [{ category: "summary", text: "Kept." }],
      references: [{ category: "external", url: "https://a.example" }],
      metrics: [{ content: { cvss_v3: { vectorString: "CVSS:3.1/AV:L" } }, products: ["CSAFPID-0003"] }],
    };

    const found = differences(ours, theirs);

    expect(found.map((difference) => difference.field)).toEqual(
      ["title", "description", "cve", "cwes", "disclosure_date", "references", "cvss"],
    );

    found.forEach((difference) => difference.apply?.(ours));

    expect(ours.title).toBe("Stored XSS");
    expect(ours.notes).toEqual([{ category: "summary", text: "Kept." }, { category: "description", title: "Vulnerability description", text: "Public description." }]);
    expect(ours.references.map((reference: { url: string }) => reference.url)).toEqual(["https://a.example", "https://b.example"]);
    // Scores are only shown: they refer to the public record's own products.
    expect(ours.metrics[0].content.cvss_v3.vectorString).toBe("CVSS:3.1/AV:L");
    expect(differences(ours, theirs).map((difference) => difference.field)).toEqual(["cvss"]);
  });
});
