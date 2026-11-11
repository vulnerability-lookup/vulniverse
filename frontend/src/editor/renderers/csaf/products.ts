import type {
  JsonSchema,
} from "@jsonforms/core";


/*
 * CSAF documents name products once, in the product tree, and refer to
 * them everywhere else by product ID (product status, remediations,
 * metrics, threats, …) or by product group ID. The generator marks the
 * schemas of those IDs (editor.markDefinitions in schemas/manifest.json).
 */
export const DEFINITION_MARKER = "x-vulniverse-definition";

export type Definition =
  | "branches_t"
  | "product_id_t"
  | "products_t"
  | "product_group_id_t"
  | "product_groups_t";

export interface Named {
  id: string;
  name: string;
}

type JsonObject = Record<string, unknown>;


export function definitionOf(
  schema: JsonSchema | undefined,
): Definition | undefined {
  return (schema as JsonObject | undefined)?.[DEFINITION_MARKER] as Definition | undefined;
}


/**
 * What a product/group reference control holds, or undefined for any
 * other schema. A list is products_t/product_groups_t, or an array of
 * single IDs declared inline (product_groups[].product_ids).
 */
export function referenceKind(
  schema: JsonSchema | undefined,
): { group: boolean; list: boolean } | undefined {
  const own = definitionOf(schema);
  const items = schema?.type === "array" && !Array.isArray(schema.items)
    ? definitionOf(schema.items)
    : undefined;

  switch (own ?? items) {
    case "products_t":
    case "product_id_t":
      return { group: false, list: schema?.type === "array" };
    case "product_groups_t":
    case "product_group_id_t":
      return { group: true, list: schema?.type === "array" };
    default:
      return undefined;
  }
}


function asObject(
  value: unknown,
): JsonObject {
  return typeof value === "object" && value !== null && !Array.isArray(value)
    ? value as JsonObject
    : {};
}


function asArray(
  value: unknown,
): unknown[] {
  return Array.isArray(value) ? value : [];
}


/** A full_product_name_t as {id, name}, or nothing without an ID. */
function named(
  product: unknown,
): Named[] {
  const { product_id: id, name } = asObject(product);

  return typeof id === "string" && id
    ? [{ id, name: typeof name === "string" ? name : "" }]
    : [];
}


function branchProducts(
  branches: unknown,
): Named[] {
  return asArray(branches).flatMap((branch) => {
    const { product, branches: children } = asObject(branch);

    return [...named(product), ...branchProducts(children)];
  });
}


/**
 * Every product the document defines: the product tree's branches,
 * full_product_names and product_paths, in that order. The first
 * definition of an ID wins.
 */
export function definedProducts(
  document: unknown,
): Named[] {
  const tree = asObject(asObject(document).product_tree);

  const all = [
    ...branchProducts(tree.branches),
    ...asArray(tree.full_product_names).flatMap(named),
    ...asArray(tree.product_paths).flatMap((path) => named(asObject(path).full_product_name)),
  ];

  return all.filter((product, index) => all.findIndex((other) => other.id === product.id) === index);
}


/** The product groups, named by their summary or their products. */
export function definedGroups(
  document: unknown,
): Named[] {
  const tree = asObject(asObject(document).product_tree);

  return asArray(tree.product_groups).flatMap((group) => {
    const { group_id: id, summary, product_ids: ids } = asObject(group);

    if (typeof id !== "string" || !id) {
      return [];
    }

    return [{ id, name: typeof summary === "string" ? summary : asArray(ids).join(", ") }];
  });
}


/**
 * A product ID not used yet, following the CSAFPID-0001 numbering the
 * CSAF examples use.
 */
export function nextProductId(
  document: unknown,
): string {
  const numbers = definedProducts(document)
    .map((product) => /^CSAFPID-(\d+)$/.exec(product.id)?.[1])
    .filter((value) => value !== undefined)
    .map(Number);

  const next = Math.max(0, ...numbers) + 1;

  return `CSAFPID-${String(next).padStart(4, "0")}`;
}


/** The usual category of a branch below one of `parent`. */
export function childCategory(
  parent: string | undefined,
): string {
  if (parent === undefined) return "vendor";
  if (parent === "vendor" || parent === "product_family") return "product_name";

  return "product_version";
}
