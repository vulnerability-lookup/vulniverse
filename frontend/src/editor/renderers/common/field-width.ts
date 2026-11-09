import type {
  JsonSchema,
} from "@jsonforms/core";


export type FieldWidth = "short" | "medium" | "full";

const WIDTHS: readonly string[] = ["short", "medium", "full"];

const SHORT_FORMATS = new Set(["date", "date-time", "time"]);

// CVE marks UUIDs with a regex rather than format: "uuid".
const UUID_PATTERN = /\{8\}-.*\{12\}/;

const SCALAR_TYPES = new Set(["boolean", "number", "integer", "null"]);


/**
 * How much room a control needs in the form grid, read from its
 * schema: IDs, enums, dates and numbers are "short", plain strings
 * "medium", and anything structured, long or custom-rendered "full".
 * A layout file can force it with controlOptions.<path>.width.
 */
export function fieldWidth(
  schema: JsonSchema | undefined,
  options: Record<string, unknown> = {},
): FieldWidth {
  if (typeof options.width === "string" && WIDTHS.includes(options.width)) {
    return options.width as FieldWidth;
  }

  // Custom renderers and multi-line text bring their own layout.
  if (!schema || options.renderer || options.multi) {
    return "full";
  }

  if (schema.oneOf || schema.anyOf || schema.allOf) {
    return "full";
  }

  if (schema.enum || schema.const !== undefined) {
    return "short";
  }

  const types = Array.isArray(schema.type)
    ? schema.type
    : schema.type ? [schema.type] : [];

  if (types.length === 0 || types.some((type) => type === "object" || type === "array")) {
    return "full";
  }

  if (types.every((type) => SCALAR_TYPES.has(type))) {
    return "short";
  }

  if (typeof schema.maxLength === "number" && schema.maxLength >= 4096) {
    return "full";
  }

  // 36 characters never fit a single column.
  if (schema.format === "uuid" || UUID_PATTERN.test(schema.pattern ?? "")) {
    return "medium";
  }

  if (
    (schema.format && SHORT_FORMATS.has(schema.format))
    || schema.pattern
    || (typeof schema.maxLength === "number" && schema.maxLength <= 64)
  ) {
    return "short";
  }

  return "medium";
}
