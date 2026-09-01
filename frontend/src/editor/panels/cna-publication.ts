import {
  computed,
  ref,
} from "vue";

import {
  useEditorRepository,
} from "../use-editor-repository";

import {
  RepositoryError,
} from "@/repositories/RepositoryError";

import type {
  CnaPublication,
  EditorModuleContext,
  EditorRepository,
  PublicationTarget,
} from "../contracts";

/*
 * Backs both VulnerabilityLookupPanel.vue and CVEProgramPanel.vue — "vl"
 * and "cve-program" are the same CVE Services API-shaped protocol at a
 * different host-supplied EditorRepository target, so one composable
 * serves both. Goes through EditorRepository (not a direct fetch), the
 * same way TemplatesSection.vue does — that's what makes this portable
 * to a host whose repository implements these methods against its own
 * backend, and gracefully "not supported here" for one that doesn't.
 */
export function useCnaPublication(
  target: PublicationTarget,
  context: EditorModuleContext,
) {
  const repository = useEditorRepository();

  const supported = computed(() => Boolean(repository.value?.getCnaPublication));

  const publication = ref<CnaPublication | null>(null);
  const loading = ref(false);
  const error = ref<string | null>(null);
  const notConfigured = ref(false);

  function applyError(err: unknown, fallback: string): void {
    notConfigured.value = err instanceof RepositoryError && err.status === 409;

    if (
      err instanceof RepositoryError &&
      err.details &&
      typeof err.details === "object" &&
      "publication" in err.details
    ) {
      publication.value = (err.details as { publication: CnaPublication }).publication;
    }

    error.value = notConfigured.value
      ? null
      : err instanceof Error ? err.message : fallback;
  }

  async function refresh(): Promise<void> {
    if (!context.identifier || !repository.value?.getCnaPublication) {
      return;
    }

    loading.value = true;
    error.value = null;
    notConfigured.value = false;

    try {
      publication.value = await repository.value.getCnaPublication(target, context.identifier);
    } catch (err) {
      applyError(err, "Could not load publication status.");
    } finally {
      loading.value = false;
    }
  }

  async function runAction(
    action: (repo: EditorRepository, identifier: string) => Promise<CnaPublication>,
  ): Promise<void> {
    if (!context.identifier || !repository.value) {
      return;
    }

    loading.value = true;
    error.value = null;

    try {
      publication.value = await action(repository.value, context.identifier);
    } catch (err) {
      applyError(err, "The action failed.");
    } finally {
      loading.value = false;
    }
  }

  return {
    supported,
    publication,
    loading,
    error,
    notConfigured,
    refresh,
    reserve: (year: number) => runAction((repo, id) => repo.reserveCveId!(target, id, year)),
    publish: () => runAction((repo, id) => repo.publishCna!(target, id)),
    reject: (reason: string) => runAction((repo, id) => repo.rejectCna!(target, id, reason)),
    abort: () => runAction((repo, id) => repo.abortCna!(target, id)),
  };
}
