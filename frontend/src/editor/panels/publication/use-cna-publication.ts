import {
  computed,
  ref,
} from "vue";

import {
  useEditorContext,
  useEditorRepository,
  useEditorSave,
} from "../../core/context";

import {
  EditorRepositoryError,
} from "../../core/errors";

import {
  RecordValidationError,
} from "../../contracts";

import type {
  CnaPublication,
  CveRecord,
  EditorContext,
  EditorRepository,
  PublicationTarget,
} from "../../contracts";

/*
 * Backs both VulnerabilityLookupPanel.vue and CVEProgramPanel.vue — "vl"
 * and "cve-program" are the same CVE Services API-shaped protocol at a
 * different host-supplied EditorRepository target, so one composable
 * serves both. Goes through EditorRepository (not a direct fetch), the
 * same way TemplatesPanel.vue does — that's what makes this portable
 * to a host whose repository implements these methods against its own
 * backend, and gracefully "not supported here" for one that doesn't.
 */
export function useCnaPublication(
  target: PublicationTarget,
  context: EditorContext,
) {
  const repository = useEditorRepository();
  const requestSave = useEditorSave();
  const editor = useEditorContext();

  const supported = computed(() => Boolean(repository.value?.getCnaPublication));
  const pullSupported = computed(() => Boolean(repository.value?.pullCna));
  const unlinkSupported = computed(() => Boolean(repository.value?.unlinkCna));
  const upstreamSupported = computed(() => Boolean(repository.value?.getUpstreamCna));

  /** The record upstream has, or why it couldn't be read. */
  async function fetchUpstream(): Promise<CveRecord | string> {
    if (!context.identifier || !repository.value?.getUpstreamCna) {
      return "not supported here";
    }

    try {
      return await repository.value.getUpstreamCna(target, context.identifier);
    } catch (err) {
      return err instanceof Error ? err.message : "the request failed";
    }
  }

  const publication = ref<CnaPublication | null>(null);
  const loading = ref(false);
  const error = ref<string | null>(null);
  const notConfigured = ref(false);

  function applyError(err: unknown, fallback: string): void {
    // Publishing refused an invalid record: mark its fields, as a save does.
    if (err instanceof RecordValidationError) {
      editor.validationErrors.value = err.errors;
      notConfigured.value = false;
      error.value = "Fix the marked fields before publishing.";
      return;
    }

    // 409 means "no credentials" here, except for a record someone else
    // saved in the meantime (api/records.py's CHANGED_MEANWHILE).
    notConfigured.value = err instanceof EditorRepositoryError
      && err.status === 409
      && (err.details as { code?: string } | undefined)?.code !== "CHANGED_MEANWHILE";

    let hasUpstreamDetail = false;

    if (
      err instanceof EditorRepositoryError &&
      err.details &&
      typeof err.details === "object" &&
      "publication" in err.details
    ) {
      publication.value = (err.details as { publication: CnaPublication }).publication;
      hasUpstreamDetail = Boolean(publication.value?.lastError);
    }

    // publication.lastError (rendered below, in the template) carries
    // the actual upstream failure — the request URL/status/body — so
    // it's strictly more useful than this generic message whenever
    // it's available; showing both just buries the real detail under
    // "The upstream request failed." every time.
    error.value = notConfigured.value || hasUpstreamDetail
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

  /*
   * A brand-new, never-saved record has no identifier at all yet (see
   * use-editor-state.ts) — silently save it first (as whatever draft
   * state it's already in) so an action like "Reserve a CVE ID" can
   * still be the very first thing a user does, rather than requiring
   * a manual Save first. A no-op once the record already has an
   * identifier. A save failure is already surfaced via the editor's
   * own saveError/@error path, so this just bails out rather than
   * reporting it a second time.
   */
  async function ensureIdentifier(): Promise<string | null> {
    // A brand-new record's identifier starts as "" (see
    // VulniverseEditor.ce.vue's loadRecord()), not null — ?? only
    // catches null/undefined, so it would return "" as-is here and
    // skip the save entirely. || treats both the same, matching the
    // !context.identifier check the template already uses.
    //
    // silent: true — this save is only to obtain SOME identifier so
    // the action below (reserve/publish/...) has something to act
    // on; it isn't "the user is done" yet. A non-silent save here
    // would make the host page navigate to the record's own URL
    // immediately (see editorSaveKey), tearing this component down
    // before the action — and CnaPublicationPanel.vue's own
    // follow-up save applying the result — ever gets to run.
    return context.identifier || await requestSave({ silent: true });
  }

  /*
   * Publishing sends the stored record, so unsaved edits are saved first
   * (silently, like ensureIdentifier()): what goes out is what the user
   * sees. A failed save stops here; the editor already shows why.
   */
  async function savedIdentifier(): Promise<string | null> {
    return context.identifier && !editor.dirty.value
      ? context.identifier
      : await requestSave({ silent: true });
  }

  async function runAction(
    action: (repo: EditorRepository, identifier: string) => Promise<CnaPublication>,
    identify: () => Promise<string | null> = ensureIdentifier,
  ): Promise<void> {
    if (!repository.value) {
      return;
    }

    loading.value = true;
    error.value = null;

    try {
      const identifier = await identify();

      if (!identifier) {
        return;
      }

      publication.value = await action(repository.value, identifier);
    } catch (err) {
      applyError(err, "The action failed.");
    } finally {
      loading.value = false;
    }
  }

  /**
   * Links the record to an upstream ID and takes over its state (saving
   * a never-saved record first). The upstream record, null while only
   * reserved; undefined if it failed (the error is shown).
   */
  async function pull(cveId: string): Promise<CveRecord | null | undefined> {
    if (!repository.value?.pullCna) {
      return undefined;
    }

    loading.value = true;
    error.value = null;

    try {
      const identifier = await ensureIdentifier();

      if (!identifier) {
        return undefined;
      }

      const result = await repository.value.pullCna(target, identifier, cveId);
      publication.value = result.publication;
      return result.record;
    } catch (err) {
      applyError(err, "Pulling from upstream failed.");
      return undefined;
    } finally {
      loading.value = false;
    }
  }

  return {
    supported,
    pullSupported,
    unlinkSupported,
    upstreamSupported,
    fetchUpstream,
    pull,
    publication,
    loading,
    error,
    notConfigured,
    refresh,
    reserve: (year: number) => runAction((repo, id) => repo.reserveCveId!(target, id, year)),
    publish: () => runAction((repo, id) => repo.publishCna!(target, id), savedIdentifier),
    reject: (reason: string) => runAction((repo, id) => repo.rejectCna!(target, id, reason)),
    abort: () => runAction((repo, id) => repo.abortCna!(target, id)),
    unlink: () => runAction((repo, id) => repo.unlinkCna!(target, id)),
  };
}
