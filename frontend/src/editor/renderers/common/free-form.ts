/*
 * FreeFormObjectRenderer edits only an object's undeclared keys as JSON.
 * Keys the schema declares (e.g. OSV's database_specific.x_gcve, which
 * has its own GCVE editor) are left out of the box and kept as they are.
 */

type JsonObject = Record<string, unknown>;


/** The undeclared keys of `data`, or undefined when there are none. */
export function undeclaredEntries(
  data: unknown,
  declared: readonly string[],
): JsonObject | undefined {
  if (typeof data !== "object" || data === null || Array.isArray(data)) {
    return undefined;
  }

  const entries = Object.entries(data).filter(([key]) => !declared.includes(key));

  return entries.length ? Object.fromEntries(entries) : undefined;
}


/**
 * `data`'s declared keys combined with the edited undeclared ones, or
 * undefined when nothing is left (so an emptied box unsets the field).
 */
export function withUndeclaredEntries(
  data: unknown,
  declared: readonly string[],
  edited: JsonObject | undefined,
): JsonObject | undefined {
  const kept = typeof data === "object" && data !== null && !Array.isArray(data)
    ? Object.fromEntries(
        Object.entries(data).filter(([key]) => declared.includes(key)),
      )
    : {};

  const merged = { ...kept, ...edited };

  return Object.keys(merged).length ? merged : undefined;
}
