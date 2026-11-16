import type {
  JsonSchema,
} from "@jsonforms/core";

/*
 * The record as a tree for the Tree section: one node per field that is
 * present, labelled with the schema's title, array items with a short
 * summary of what they are. Each node's path is the data path the editor
 * reveals (core/reveal.ts).
 */

export interface TreeNode {
  path: string;
  label: string;
  // A leaf's value, or what an array item is ("Example Widget").
  summary: string;
  kind: "object" | "array" | "value";
  // The schema requires this field in its parent.
  required: boolean;
  children: TreeNode[];
}

// Item fields that tell what an item is, in order of preference.
const SUMMARY_KEYS = [
  "title", "name", "summary", "value", "product", "vendor", "url", "cve",
  "id", "vulnId", "cweId", "description", "text", "type", "category", "lang",
];

const MAX_SUMMARY = 80;


function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}


/** "assignerShortName" -> "Assigner short name", for fields without title. */
export function humanize(key: string): string {
  const words = key.replace(/([a-z0-9])([A-Z])/g, "$1 $2").replace(/_/g, " ").toLowerCase();

  return words.charAt(0).toUpperCase() + words.slice(1);
}


function short(value: string): string {
  const line = value.replace(/\s+/g, " ").trim();

  return line.length > MAX_SUMMARY ? `${line.slice(0, MAX_SUMMARY)}…` : line;
}


function summaryOf(value: unknown): string {
  if (typeof value === "string") {
    return short(value);
  }

  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }

  if (isObject(value)) {
    if (typeof value.vendor === "string" && typeof value.product === "string") {
      return short(`${value.vendor} ${value.product}`);
    }

    for (const key of SUMMARY_KEYS) {
      if (typeof value[key] === "string" && value[key]) {
        return short(value[key] as string);
      }
    }
  }

  return "";
}


function childSchema(schema: JsonSchema | undefined, key: string | number): JsonSchema | undefined {
  if (!schema) {
    return undefined;
  }

  if (typeof key === "number") {
    return Array.isArray(schema.items) ? undefined : schema.items;
  }

  return schema.properties?.[key];
}


/** Child nodes of `value` (an object or array) at `path`. */
export function recordTree(
  value: unknown,
  schema: JsonSchema | undefined,
  path = "",
): TreeNode[] {
  const entries: [string | number, unknown][] = Array.isArray(value)
    ? value.map((item, index) => [index, item])
    : isObject(value) ? Object.entries(value) : [];

  return entries.map(([key, child]) => {
    const nodePath = path ? `${path}.${key}` : String(key);
    const nodeSchema = childSchema(schema, key);
    const label = typeof key === "number"
      ? `#${key + 1}`
      : nodeSchema?.title ?? humanize(key);

    return {
      path: nodePath,
      label,
      summary: Array.isArray(child) ? `${child.length} ${child.length === 1 ? "item" : "items"}` : summaryOf(child),
      kind: Array.isArray(child) ? "array" : isObject(child) ? "object" : "value",
      required: typeof key === "string" && (schema?.required ?? []).includes(key),
      children: recordTree(child, nodeSchema, nodePath),
    };
  });
}


export interface PlacedNode {
  node: TreeNode;
  x: number;
  y: number;
  open: boolean;
  // Open nodes put their label left of the circle, so it doesn't sit on
  // the links to their children; all others put it right.
  labelLeft: boolean;
}

export interface TreeLayout {
  nodes: PlacedNode[];
  links: { from: PlacedNode; to: PlacedNode }[];
  width: number;
  height: number;
}

export const ROW_HEIGHT = 34;
const COLUMN_GAP = 56;
const PAD = 16;
// Characters shown of a label or value before "…".
export const MAX_TEXT = 40;

/*
 * A left-to-right tidy tree of `root` with only the `open` paths
 * expanded: every visible leaf takes the next row, a parent sits midway
 * between its first and last child, and each depth is a column wide
 * enough for the labels on both sides of it.
 */
export function layoutTree(
  root: TreeNode,
  open: ReadonlySet<string>,
  // shortcut: an average glyph width, not measured text; labels in very wide fonts may touch the next column.
  charWidth = 7,
): TreeLayout {
  const nodes: PlacedNode[] = [];
  const links: TreeLayout["links"] = [];
  const depths: number[] = [];
  let nextRow = 0;

  function place(node: TreeNode, depth: number): PlacedNode {
    const isOpen = node.children.length > 0 && open.has(node.path);
    const children = isOpen ? node.children.map((child) => place(child, depth + 1)) : [];
    const row = children.length
      ? (children[0]!.y + children[children.length - 1]!.y) / 2
      : nextRow++;
    const placed = { node, x: 0, y: row, open: isOpen, labelLeft: isOpen };

    nodes.push(placed);
    depths.push(depth);
    children.forEach((child) => links.push({ from: placed, to: child }));

    return placed;
  }

  place(root, 0);

  const columns = Math.max(...depths) + 1;
  const left = Array.from({ length: columns }, () => 0);
  const right = Array.from({ length: columns }, () => 0);

  nodes.forEach((placed, index) => {
    // Open nodes show no summary: their children say it.
    const summary = placed.open ? 0 : placed.node.summary.length;
    const text = Math.min(MAX_TEXT, Math.max(placed.node.label.length + 2, summary));
    const side = placed.labelLeft ? left : right;
    side[depths[index]!] = Math.max(side[depths[index]!]!, text * charWidth);
  });

  const columnX = [PAD + left[0]!];
  for (let depth = 1; depth < columns; depth++) {
    columnX.push(columnX[depth - 1]! + right[depth - 1]! + left[depth]! + COLUMN_GAP);
  }

  nodes.forEach((placed, index) => {
    placed.x = columnX[depths[index]!]!;
    placed.y = PAD + placed.y * ROW_HEIGHT + ROW_HEIGHT / 2;
  });

  return {
    nodes,
    links,
    width: columnX[columns - 1]! + right[columns - 1]! + 2 * PAD,
    height: nextRow * ROW_HEIGHT + 2 * PAD,
  };
}


/** Nodes under `root` (itself excluded) whose label or summary contains `query`, in reading order. */
export function searchTree(root: TreeNode, query: string): TreeNode[] {
  const needle = query.trim().toLowerCase();
  const found: TreeNode[] = [];

  function visit(node: TreeNode): void {
    for (const child of node.children) {
      if (`${child.label}\n${child.summary}`.toLowerCase().includes(needle)) found.push(child);
      visit(child);
    }
  }

  if (needle) visit(root);

  return found;
}


/** The paths of the nodes above `path`, the root ("") included. */
export function ancestorPaths(path: string): string[] {
  const parts = path.split(".");

  return parts.map((_, index) => parts.slice(0, index).join("."));
}
