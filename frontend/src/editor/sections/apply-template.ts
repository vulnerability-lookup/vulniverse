import type {
  TemplateField,
} from "../contracts";

/*
 * A template's paths are plain dot-separated strings (with optional
 * bracket-array syntax, e.g. "affected[0].vendor", accepted purely
 * as a friendlier alternative to "affected.0.vendor" — both mean
 * the same thing).
 */
function splitPath(
  path: string,
): string[] {
  return path
    .replace(/\[(\d+)\]/g, ".$1")
    .split(".")
    .map((segment) => segment.trim())
    .filter((segment) => segment.length > 0);
}

/**
 * Writes a single value into a (possibly deeply nested, possibly
 * not-yet-existing) path on the given object, creating intermediate
 * objects/arrays as needed. Existing intermediate values are left
 * untouched — only the leaf named by the path is overwritten — so
 * applying a template never clobbers sibling fields it doesn't
 * mention.
 */
export function setPath(
  target: Record<string, unknown>,
  path: string,
  value: unknown,
): void {
  const segments = splitPath(path);

  if (segments.length === 0) {
    return;
  }

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  let current: any = target;

  for (let i = 0; i < segments.length - 1; i++) {
    const key = segments[i]!;
    const nextIsIndex = /^\d+$/.test(segments[i + 1]!);

    if (
      current[key] === undefined
      || current[key] === null
      || typeof current[key] !== "object"
    ) {
      current[key] = nextIsIndex ? [] : {};
    }

    current = current[key];
  }

  current[segments[segments.length - 1]!] = value;
}

/**
 * Attempts to parse a template field's raw text input as JSON (so
 * "42", "true", or '["a","b"]' become the number/boolean/array they
 * look like), falling back to the literal string when that fails —
 * the common ergonomic trick that lets both `Acme` and `"Acme"` work
 * as a plain string.
 */
export function parseFieldValue(
  raw: string,
): unknown {
  try {
    return JSON.parse(raw);
  } catch {
    return raw;
  }
}

/**
 * The inverse of parseFieldValue, for populating an edit form's text
 * inputs from a template's already-typed values: a plain string
 * round-trips as itself (not re-quoted), everything else round-trips
 * through JSON so parseFieldValue can recover it unchanged later.
 */
export function stringifyFieldValue(
  value: unknown,
): string {
  return typeof value === "string" ? value : JSON.stringify(value);
}

export function applyTemplateFields(
  record: Record<string, unknown>,
  fields: TemplateField[],
): void {
  for (const field of fields) {
    setPath(record, field.path, field.value);
  }
}
