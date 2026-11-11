import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import type { ControlElement, JsonSchema } from "@jsonforms/core";
import { describe, expect, it } from "vitest";

import authoringSchema from "@/generated/schemas/csaf-2.1/authoring.schema.json";

import { isReferenceControl } from "..";
import { childCategory, definedGroups, definedProducts, nextProductId, referenceKind } from "../products";

// Tests run from frontend/.
const example = JSON.parse(readFileSync(
  resolve("../backend/tests/fixtures/csaf/bsi-2022-0001.json"),
  "utf-8",
)) as Record<string, unknown>;

const root = authoringSchema as unknown as JsonSchema;

/** The generated schema at a dot path, following properties and items. */
function at(path: string): JsonSchema {
  return path.split(".").reduce<JsonSchema>((schema, part) => (
    part === "[]" ? schema.items as JsonSchema : schema.properties![part]!
  ), root);
}

function testsAsReference(path: string, scopeProperty: string): boolean {
  const control: ControlElement = { type: "Control", scope: `#/properties/${scopeProperty}` };

  return isReferenceControl(control, at(path), { rootSchema: root, config: {} }) === true;
}

describe("defined products", () => {
  it("collects products from branches, full product names and product paths", () => {
    const document = {
      product_tree: {
        branches: [{ category: "vendor", name: "V", branches: [{ category: "product_name", name: "P", product: { name: "V P", product_id: "A" } }] }],
        full_product_names: [{ name: "B product", product_id: "B" }, { name: "dup", product_id: "A" }],
        product_paths: [{ full_product_name: { name: "C on B", product_id: "C" } }],
        product_groups: [{ group_id: "G", product_ids: ["A", "B"] }],
      },
    };

    expect(definedProducts(document)).toEqual([
      { id: "A", name: "V P" },
      { id: "B", name: "B product" },
      { id: "C", name: "C on B" },
    ]);
    expect(definedGroups(document)).toEqual([{ id: "G", name: "A, B" }]);
  });

  it("numbers new products after the highest CSAFPID", () => {
    expect(definedProducts(example)).toHaveLength(6);
    expect(nextProductId(example)).toBe("CSAFPID-0007");
    expect(nextProductId({})).toBe("CSAFPID-0001");
  });

  it("suggests the usual category below a branch", () => {
    expect(childCategory(undefined)).toBe("vendor");
    expect(childCategory("vendor")).toBe("product_name");
    expect(childCategory("product_name")).toBe("product_version");
  });
});

describe("reference controls", () => {
  it("finds every kind of reference in the generated schema", () => {
    expect(referenceKind(at("vulnerabilities.[].product_status.known_affected"))).toEqual({ group: false, list: true });
    expect(referenceKind(at("vulnerabilities.[].remediations.[].group_ids"))).toEqual({ group: true, list: true });
    expect(referenceKind(at("product_tree.product_groups.[].product_ids"))).toEqual({ group: false, list: true });
    expect(referenceKind(at("product_tree.product_paths.[].beginning_product_reference"))).toEqual({ group: false, list: false });
    expect(referenceKind(at("product_tree.product_paths.[].subpaths.[].next_product_reference"))).toEqual({ group: false, list: false });
  });

  it("gives references a picker but leaves the defining fields as text", () => {
    expect(testsAsReference("vulnerabilities.[].product_status.known_affected", "known_affected")).toBe(true);
    expect(testsAsReference("product_tree.product_paths.[].beginning_product_reference", "beginning_product_reference")).toBe(true);
    expect(testsAsReference("product_tree.full_product_names.[].product_id", "product_id")).toBe(false);
    expect(testsAsReference("product_tree.product_groups.[].group_id", "group_id")).toBe(false);
    expect(testsAsReference("document.title", "title")).toBe(false);
  });
});
