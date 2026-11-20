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
