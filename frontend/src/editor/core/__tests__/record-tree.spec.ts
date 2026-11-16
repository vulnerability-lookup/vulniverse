import { describe, expect, it } from "vitest";

import { ancestorPaths, humanize, layoutTree, recordTree, searchTree } from "../record-tree";
import { isWithin, itemIndex } from "../reveal";

const schema = {
  properties: {
    containers: { properties: { cna: { required: ["title"], properties: {
      title: { title: "Title" },
      affected: { title: "Affected products", items: { properties: { vendor: { title: "Vendor" } } } },
    } } } },
  },
};

describe("recordTree", () => {
  it("builds nodes with schema titles, item summaries and data paths", () => {
    const tree = recordTree({
      containers: { cna: {
        title: "Stored XSS",
        affected: [{ vendor: "Example", product: "Widget", versions: [] }],
      } },
    }, schema);

    const cna = tree[0]!.children[0]!;
    const [title, affected] = cna.children;

    expect(title).toMatchObject({ path: "containers.cna.title", label: "Title", summary: "Stored XSS", kind: "value", required: true, children: [] });
    expect(affected).toMatchObject({ path: "containers.cna.affected", label: "Affected products", summary: "1 item", kind: "array", required: false });
    expect(affected!.children[0]).toMatchObject({ path: "containers.cna.affected.0", label: "#1", summary: "Example Widget" });
    expect(affected!.children[0]!.children.map((node) => [node.label, node.summary])).toEqual([
      ["Vendor", "Example"], ["Product", "Widget"], ["Versions", "0 items"],
    ]);
  });

  it("humanizes keys without a schema title", () => {
    expect(humanize("assignerShortName")).toBe("Assigner short name");
    expect(humanize("x_gcve")).toBe("X gcve");
  });
});

describe("layoutTree", () => {
  const leaf = (path: string) => ({ path, label: path, summary: "", kind: "value" as const, required: false, children: [] });
  const root = { ...leaf(""), kind: "object" as const, children: [
    { ...leaf("a"), kind: "object" as const, children: [leaf("a.x"), leaf("a.y"), leaf("a.z")] },
    leaf("b"),
  ] };
  const at = (layout: ReturnType<typeof layoutTree>, path: string) => layout.nodes.find((n) => n.node.path === path)!;

  it("gives each visible leaf a row and centres parents on their children", () => {
    const layout = layoutTree(root, new Set(["", "a"]));
    const [x, y, z, a, b, top] = ["a.x", "a.y", "a.z", "a", "b", ""].map((path) => at(layout, path));

    expect(layout.nodes).toHaveLength(6);
    expect(layout.links).toHaveLength(5);
    expect([x!.y < y!.y, y!.y < z!.y, z!.y < b!.y]).toEqual([true, true, true]);
    expect(a!.y).toBe(y!.y);
    expect(top!.y).toBe((a!.y + b!.y) / 2);
    expect(x!.x).toBeGreaterThan(a!.x);
    expect([a!.labelLeft, b!.labelLeft]).toEqual([true, false]);
  });

  it("finds nodes by label or value, below the root", () => {
    const named = { ...root, children: [{ ...root.children[0]!, summary: "Widget" }, leaf("b")] };

    expect(searchTree(named, " a.Y ").map((n) => n.path)).toEqual(["a.y"]);
    expect(searchTree(named, "widget").map((n) => n.path)).toEqual(["a"]);
    expect(searchTree(named, "")).toEqual([]);
    expect(ancestorPaths("a.b.c")).toEqual(["", "a", "a.b"]);
  });

  it("hides the children of closed nodes", () => {
    const layout = layoutTree(root, new Set([""]));

    expect(layout.nodes.map((n) => n.node.path).sort()).toEqual(["", "a", "b"]);
    expect(at(layout, "a").open).toBe(false);
  });
});

describe("reveal paths", () => {
  it("tells what lies within a path and which item", () => {
    expect(isWithin("containers.cna.affected.2.vendor", "containers.cna.affected")).toBe(true);
    expect(isWithin("containers.cna.affectedX", "containers.cna.affected")).toBe(false);
    expect(itemIndex("containers.cna.affected.2.vendor", "containers.cna.affected")).toBe(2);
    expect(itemIndex("containers.cna.affected", "containers.cna.affected")).toBeNull();
  });
});
