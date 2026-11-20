import { describe, expect, it } from "vitest";

import type { CveRecord } from "../../../contracts";
import { setAtPath } from "../../../core/changes";
import { upstreamDifferences } from "../upstream-diff";

const record = (cna: Record<string, unknown>, cveMetadata = {}): CveRecord =>
  ({ cveMetadata, containers: { cna } }) as CveRecord;

describe("upstream differences", () => {
  it("finds none when the published record is the same", () => {
    const local = record({ title: "Bug", affected: [{ vendor: "Acme" }] }, { state: "PUBLISHED" });
    // Key order doesn't count.
    const published = record({ affected: [{ vendor: "Acme" }], title: "Bug" }, { state: "PUBLISHED" });

    expect(upstreamDifferences(local, published)).toEqual([]);
  });

  it("compares cveMetadata too", () => {
    const local = record({}, { state: "PUBLISHED" });
    const published = record({}, { state: "PUBLISHED", vulnId: "gcve-1-2026-0007" });

    expect(upstreamDifferences(local, published)).toEqual([
      { path: "cveMetadata.vulnId", local: undefined, published: "gcve-1-2026-0007" },
    ]);
  });

  it("compares providerMetadata too", () => {
    const local = record({ providerMetadata: { orgId: "x" } });
    const published = record({ providerMetadata: { orgId: "x", dateUpdated: "now" } });

    expect(upstreamDifferences(local, published)).toEqual([
      { path: "containers.cna.providerMetadata.dateUpdated", local: undefined, published: "now" },
    ]);
  });

  it("lists each changed, added and removed field once, with both values", () => {
    const local = record({ title: "New title", affected: [{ vendor: "Acme", product: "Widget" }] });
    const published = record({ title: "Old title", affected: [{ vendor: "Acme" }], problemTypes: [] });

    expect(upstreamDifferences(local, published)).toEqual([
      { path: "containers.cna.affected.0.product", local: "Widget", published: undefined },
      { path: "containers.cna.problemTypes", local: undefined, published: [] },
      { path: "containers.cna.title", local: "New title", published: "Old title" },
    ]);
  });
});

describe("taking over upstream values", () => {
  it("sets, adds and removes values by path", () => {
    const record: Record<string, unknown> = { containers: { cna: { title: "Mine", affected: [{ vendor: "A" }, { vendor: "B" }] } } };

    setAtPath(record, "containers.cna.title", "Theirs");
    setAtPath(record, "containers.cna.problemTypes.0.descriptions.0.lang", "en");
    setAtPath(record, "containers.cna.affected.0", undefined);

    expect(record).toEqual({
      containers: {
        cna: {
          title: "Theirs",
          affected: [{ vendor: "B" }],
          problemTypes: [{ descriptions: [{ lang: "en" }] }],
        },
      },
    });
  });

  it("leaves no difference once every upstream value is taken over", () => {
    const local = record({ title: "Mine", affected: [{ vendor: "A", product: "P" }] }, { state: "PUBLISHED" });
    const published = record({ title: "Theirs", affected: [{ vendor: "A" }] }, { state: "PUBLISHED", vulnId: "x" });

    for (const difference of upstreamDifferences(local, published)) {
      setAtPath(local as Record<string, unknown>, difference.path, difference.published);
    }

    expect(upstreamDifferences(local, published)).toEqual([]);
  });
});
