import {
  ref,
} from "vue";

import type {
  EditorModuleContext,
} from "../contracts";

/*
 * "vl" and "cve-program" are the same CVE Services API-shaped protocol at a
 * different backend-configured base_url/credentials (see
 * services/cna_publication.py) — this one composable backs both panels.
 */
export type PublicationTarget = "vl" | "cve-program";

export interface CnaPublicationRecord {
  id: number;
  recordIdentifier: string;
  target: PublicationTarget;
  status: string;
  cveId: string | null;
  reservedAt: string | null;
  publishedAt: string | null;
  rejectedAt: string | null;
  lastError: string | null;
  createdAt: string;
  updatedAt: string;
}

export class PublishApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly publication?: CnaPublicationRecord,
  ) {
    super(message);
  }
}

async function apiFetch<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const headers = new Headers(init.headers);

  headers.set("Accept", "application/json");

  if (init.body !== undefined) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`/api/v1${path}`, {
    ...init,
    headers,
    credentials: "same-origin",
  });

  const body = await response.json().catch(() => null);

  if (!response.ok) {
    throw new PublishApiError(
      body?.message ?? `${response.status} ${response.statusText}`,
      response.status,
      body?.publication,
    );
  }

  return body as T;
}

export async function fetchPublishTargets(): Promise<
  Record<string, { configured: boolean }>
> {
  return apiFetch("/publish/targets");
}

export function useCnaPublication(
  target: PublicationTarget,
  context: EditorModuleContext,
) {
  const publication = ref<CnaPublicationRecord | null>(null);
  const loading = ref(false);
  const error = ref<string | null>(null);

  async function refresh(): Promise<void> {
    if (!context.identifier) {
      return;
    }

    loading.value = true;
    error.value = null;

    try {
      publication.value = await apiFetch<CnaPublicationRecord>(
        `/publish/${target}/${encodeURIComponent(context.identifier)}`,
      );
    } catch (err) {
      error.value = err instanceof Error ? err.message : "Could not load publication status.";
    } finally {
      loading.value = false;
    }
  }

  async function runAction(
    action: string,
    body?: unknown,
  ): Promise<void> {
    if (!context.identifier) {
      return;
    }

    loading.value = true;
    error.value = null;

    try {
      publication.value = await apiFetch<CnaPublicationRecord>(
        `/publish/${target}/${encodeURIComponent(context.identifier)}/${action}`,
        {
          method: "POST",
          body: body !== undefined ? JSON.stringify(body) : undefined,
        },
      );
    } catch (err) {
      if (err instanceof PublishApiError && err.publication) {
        publication.value = err.publication;
      }

      error.value = err instanceof Error ? err.message : "The action failed.";
    } finally {
      loading.value = false;
    }
  }

  return {
    publication,
    loading,
    error,
    refresh,
    reserve: (year: number) => runAction("reserve", { year }),
    publish: () => runAction("publish"),
    reject: (reason: string) => runAction("reject", { reason }),
    abort: () => runAction("abort"),
  };
}
