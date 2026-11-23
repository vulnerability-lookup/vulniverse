import {
  computed,
  ref,
} from "vue";

import {
  diffPaths,
} from "./changes";

import type {
  EditorDocument,
  LoadedRecord,
  ValidationError,
} from "../contracts";

export function useEditorState() {
  const record =
    ref<EditorDocument | null>(null);

  const originalRecord =
    ref<EditorDocument | null>(null);

  const identifier =
    ref<string | null>(null);

  const vulnerabilityId =
    ref<string | null>(null);

  const profile =
    ref<string | null>(null);

  const isDraft = ref(false);
  const loading = ref(false);
  const loadError = ref<Error | null>(null);

  const saving = ref(false);
  const saveError = ref<Error | null>(null);
  const validationErrors = ref<ValidationError[]>([]);
  const validationSucceeded = ref(false);
  // Short success message for the toast stack, e.g. "Draft saved.".
  const notice = ref<string | null>(null);

  // A request to show a field in the Editor section (from the record
  // tree or a validation error): switch to its tab, expand the cards on
  // the way, scroll to it. Dot path, e.g. "containers.cna.affected.2.vendor";
  // `id` makes a repeated request for the same path a new one. The
  // Editor section clears it once done (finishReveal), so coming back
  // to the section later doesn't jump to the same field again.
  const reveal = ref<{ path: string; id: number } | null>(null);
  let lastRevealId = 0;

  function revealPath(path: string): void {
    reveal.value = { path, id: ++lastRevealId };
  }

  function finishReveal(id: number): void {
    // A newer request that came in meanwhile stays.
    if (reveal.value?.id === id) {
      reveal.value = null;
    }
  }

  const dirty = computed(() => {
    if (
      !record.value ||
      !originalRecord.value
    ) {
      return false;
    }

    return JSON.stringify(record.value) !==
      JSON.stringify(originalRecord.value);
  });

  // Paths that differ from the last load or save (core/changes.ts).
  const diff = computed(() => (
    record.value && originalRecord.value
      ? diffPaths(record.value, originalRecord.value)
      : { changed: new Set<string>(), added: new Set<string>(), changes: [] }
  ));
  const changedPaths = computed(() => diff.value.changed);
  // New objects and lists, e.g. an added card.
  const addedPaths = computed(() => diff.value.added);
  // What changed, one entry per change, for the list in the header.
  const changes = computed(() => diff.value.changes);

  function replaceRecord(
    loaded: LoadedRecord,
  ): void {
    // JSON copies: a repository may hand back the object it was given,
    // a Vue proxy, which structuredClone can't copy.
    record.value =
      JSON.parse(JSON.stringify(loaded.record));

    originalRecord.value =
      JSON.parse(JSON.stringify(loaded.record));

    identifier.value = loaded.identifier;
    vulnerabilityId.value = loaded.vulnerabilityId === undefined
      ? loaded.identifier
      : loaded.vulnerabilityId;
    profile.value = loaded.profile;
    isDraft.value = loaded.isDraft;

    loadError.value = null;
  }

  function clear(): void {
    record.value = null;
    originalRecord.value = null;
    identifier.value = null;
    vulnerabilityId.value = null;
    profile.value = null;
    isDraft.value = false;
    loadError.value = null;
    saveError.value = null;
    validationErrors.value = [];
    validationSucceeded.value = false;
    notice.value = null;
  }

  return {
    record,
    originalRecord,
    changedPaths,
    addedPaths,
    changes,
    identifier,
    vulnerabilityId,
    profile,
    isDraft,
    loading,
    loadError,
    saving,
    saveError,
    validationErrors,
    validationSucceeded,
    notice,
    reveal,
    revealPath,
    finishReveal,
    dirty,
    replaceRecord,
    clear,
  };
}

export type EditorState =
  ReturnType<typeof useEditorState>;
