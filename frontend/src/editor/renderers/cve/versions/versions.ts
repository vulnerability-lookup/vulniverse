/*
 * One entry of an affected product's "versions" (CVE 5.x): a single
 * version, or a range from `version` up to `lessThan` (excluded) or
 * `lessThanOrEqual` (included), which then needs a `versionType` to say
 * how versions compare. `changes` are status changes within a range.
 */

export interface VersionEntry {
  version?: string;
  status?: string;
  versionType?: string;
  lessThan?: string;
  lessThanOrEqual?: string;
  changes?: { at?: string; status?: string }[];
  [key: string]: unknown;
}

export type UpperBound = "lessThan" | "lessThanOrEqual";

export function isRange(entry: VersionEntry): boolean {
  return "lessThan" in entry || "lessThanOrEqual" in entry;
}

export function upperBoundKey(entry: VersionEntry): UpperBound {
  return "lessThanOrEqual" in entry && !("lessThan" in entry) ? "lessThanOrEqual" : "lessThan";
}

/** The entry without keys set to undefined (an emptied field is gone). */
function cleaned(entry: VersionEntry): VersionEntry {
  return Object.fromEntries(Object.entries(entry).filter(([, value]) => value !== undefined)) as VersionEntry;
}

/** `entry` with `changes` applied; "" removes an optional field. */
export function withFields(entry: VersionEntry, changes: Partial<VersionEntry>): VersionEntry {
  const next: VersionEntry = { ...entry, ...changes };

  for (const key of ["versionType", "lessThan", "lessThanOrEqual"] as const) {
    if (key in changes && changes[key] === "") {
      // A range keeps its (empty) bound, so it stays a range.
      next[key] = key === upperBoundKey(entry) && isRange(entry) ? "" : undefined;
    }
  }

  return cleaned(next);
}

/** Switches between a single version and a range, keeping what fits. */
export function withKind(entry: VersionEntry, range: boolean): VersionEntry {
  if (range === isRange(entry)) return entry;

  return range
    ? cleaned({ ...entry, lessThan: "" })
    : cleaned({ ...entry, lessThan: undefined, lessThanOrEqual: undefined, changes: undefined });
}

/** Moves the upper bound's value to `key` (below / up to and including). */
export function withUpperBound(entry: VersionEntry, key: UpperBound): VersionEntry {
  const value = entry[upperBoundKey(entry)] ?? "";

  return cleaned({ ...entry, lessThan: undefined, lessThanOrEqual: undefined, [key]: value });
}

/** "affected · 2.0 ≤ v < 2.4.1 (semver)", for the card header. */
export function summary(entry: VersionEntry): string {
  const status = entry.status || "no status";

  if (!isRange(entry)) {
    return `${status} · ${entry.version || "?"}`;
  }

  const key = upperBoundKey(entry);
  const bound = `${key === "lessThan" ? "<" : "≤"} ${entry[key] || "?"}`;
  const type = entry.versionType ? ` (${entry.versionType})` : "";
  const changes = entry.changes?.length
    ? ` · ${entry.changes.length} status ${entry.changes.length === 1 ? "change" : "changes"}`
    : "";

  return `${status} · ${entry.version || "?"} ≤ v ${bound}${type}${changes}`;
}
