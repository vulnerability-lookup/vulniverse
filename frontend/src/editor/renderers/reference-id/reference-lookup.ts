import type {
  EditorRepository,
  ReferenceListItem,
} from "../contracts";

export const CWE_ID_PATTERN = "^CWE-[1-9][0-9]*$";
export const CAPEC_ID_PATTERN = "^CAPEC-[1-9][0-9]{0,4}$";

export type ReferenceKind = "cwe" | "capec";

export function referenceKindForPattern(
  pattern: unknown,
): ReferenceKind | null {
  if (pattern === CWE_ID_PATTERN) {
    return "cwe";
  }

  if (pattern === CAPEC_ID_PATTERN) {
    return "capec";
  }

  return null;
}

const cache = new Map<ReferenceKind, Promise<ReferenceListItem[]>>();

/**
 * Session-lifetime cache so the combobox doesn't refetch the whole
 * list every time it's opened — the backend itself already caches
 * for a day, this just avoids redundant round-trips within one
 * editing session. A rejected fetch is deliberately NOT cached, so
 * a transient failure doesn't wedge the picker for the rest of the
 * session — the next attempt just retries.
 */
export function loadReferenceList(
  repository: EditorRepository,
  kind: ReferenceKind,
): Promise<ReferenceListItem[]> {
  const cached = cache.get(kind);

  if (cached) {
    return cached;
  }

  if (!repository.getReferenceList) {
    return Promise.resolve([]);
  }

  const promise = repository.getReferenceList(kind).catch((error: unknown) => {
    cache.delete(kind);

    throw error;
  });

  cache.set(kind, promise);

  return promise;
}
