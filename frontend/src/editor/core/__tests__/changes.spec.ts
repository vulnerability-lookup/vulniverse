import { describe, expect, it } from "vitest";

import { changedPaths, countChanges, diffPaths } from "../changes";

describe("changedPaths", () => {
  const original = {
    cveMetadata: { cveId: "CVE-2026-0001", state: "PUBLISHED" },
    containers: { cna: { title: "XSS", affected: [{ vendor: "Acme", product: "Widget" }] } },
  };

  it("lists each changed field with its parents", () => {
    const current = structuredClone(original);
    current.containers.cna.affected[0]!.product = "Gadget";

    expect([...changedPaths(current, original)].sort()).toEqual([
      "containers", "containers.cna", "containers.cna.affected",
      "containers.cna.affected.0", "containers.cna.affected.0.product",
    ]);
  });

  it("counts added and removed fields and items, not key order or undefined keys", () => {
    const current = {
      containers: { cna: { affected: [{ product: "Widget", vendor: "Acme" }, { vendor: "New" }], title: "XSS", extra: undefined } },
      cveMetadata: { state: "PUBLISHED" },
    };

    expect([...changedPaths(current, original)].sort()).toEqual([
      "containers", "containers.cna", "containers.cna.affected", "containers.cna.affected.1",
      "containers.cna.affected.1.vendor", "cveMetadata", "cveMetadata.cveId",
    ]);
    expect(changedPaths(structuredClone(original), original).size).toBe(0);
  });

  describe("lists", () => {
    const references = { refs: ["a", "b", "c", "d", "e"].map((url) => ({ url })) };
    const paths = (refs: { url: string }[]) => [...changedPaths({ refs }, references)].sort();

    it("marks only the list when an item is removed, inserted or moved", () => {
      expect(paths(references.refs.filter((ref) => ref.url !== "b"))).toEqual(["refs"]);
      expect(paths([{ url: "a" }, { url: "new" }, ...references.refs.slice(1)])).toEqual(["refs", "refs.1", "refs.1.url"]);
      expect(paths([...references.refs].reverse())).toEqual(["refs"]);
      expect(paths(references.refs.map((ref) => ({ ...ref })))).toEqual([]);
    });

    it("still marks an edited item's field", () => {
      const edited = references.refs.map((ref) => ({ ...ref }));
      edited[3]!.url = "D";

      expect(paths(edited)).toEqual(["refs", "refs.3", "refs.3.url"]);
    });
  });
});

describe("diffPaths", () => {
  it("lists new cards as added, not edited ones", () => {
    const original = { items: [{ name: "a", tags: ["x"] }] };
    const current = { items: [{ name: "b", tags: ["x"] }, { name: "c", tags: [] }] };

    expect([...diffPaths(current, original).added].sort()).toEqual(["items.1", "items.1.tags"]);
  });
});

describe("countChanges", () => {
  it("counts the changed fields inside a card, not their parents", () => {
    const original = { card: { a: 1, nested: { b: 2, c: 3 } }, other: 1 };
    const current = { card: { a: 9, nested: { b: 8, c: 3 } }, other: 2 };

    expect(countChanges(changedPaths(current, original), "card")).toBe(2);
  });
});
