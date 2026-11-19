import {
  changedPaths,
} from "../../core/changes";

import type {
  CveRecord,
} from "../../contracts";

/*
 * How the local record differs from the one published upstream: every
 * field. So a just-published record differs too where upstream fills in
 * its own values: cveMetadata (built by upstream), and providerMetadata
 * (dateUpdated, and orgId/shortName when filled in from the credentials
 * on sending).
 */

export interface UpstreamDifference {
  /** Dot path in the record, e.g. "containers.cna.title". */
  path: string;
  local: unknown;
  published: unknown;
}

function valueAt(value: unknown, path: string): unknown {
  return path.split(".").reduce<unknown>(
    (current, key) => (typeof current === "object" && current !== null
      ? (current as Record<string, unknown>)[key]
      : undefined),
    value,
  );
}

export function upstreamDifferences(local: CveRecord, published: CveRecord): UpstreamDifference[] {
  const paths = [...changedPaths(local, published)];

  // changedPaths also marks every parent of a change; list the changes only.
  return paths
    .filter((path) => !paths.some((other) => other.startsWith(`${path}.`)))
    .sort()
    .map((path) => ({
      path,
      local: valueAt(local, path),
      published: valueAt(published, path),
    }));
}

/**
 * Sets `path` in `record` to `value`, creating objects and lists on the
 * way; `undefined` removes it (from a list: the item). For taking over
 * one upstream value.
 */
export function setAtPath(record: Record<string, unknown>, path: string, value: unknown): void {
  const keys = path.split(".");
  const last = keys.pop()!;
  let parent: Record<string, unknown> | unknown[] = record;

  keys.forEach((key, index) => {
    const container = parent as Record<string, unknown>;
    if (typeof container[key] !== "object" || container[key] === null) {
      // The next key decides: a number means a list.
      container[key] = /^\d+$/.test(keys[index + 1] ?? last) ? [] : {};
    }
    parent = container[key] as Record<string, unknown>;
  });

  if (value !== undefined) {
    // A JSON copy: the value may hold Vue proxies, which structuredClone can't copy.
    (parent as Record<string, unknown>)[last] = JSON.parse(JSON.stringify(value));
  } else if (Array.isArray(parent)) {
    parent.splice(Number(last), 1);
  } else {
    delete (parent as Record<string, unknown>)[last];
  }
}
