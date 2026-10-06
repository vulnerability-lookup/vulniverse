import {
  computed,
  ref,
} from "vue";

import type {
  LoadedRecord,
  ValidationError,
  VulnerabilityRecord,
} from "../contracts";

export function useEditorState() {
  const record =
    ref<VulnerabilityRecord | null>(null);

  const originalRecord =
    ref<VulnerabilityRecord | null>(null);

  const identifier =
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

  function replaceRecord(
    loaded: LoadedRecord,
  ): void {
    record.value =
      structuredClone(loaded.record);

    originalRecord.value =
      structuredClone(loaded.record);

    identifier.value = loaded.identifier;
    profile.value = loaded.profile;
    isDraft.value = loaded.isDraft;

    loadError.value = null;
  }

  function clear(): void {
    record.value = null;
    originalRecord.value = null;
    identifier.value = null;
    profile.value = null;
    isDraft.value = false;
    loadError.value = null;
    saveError.value = null;
    validationErrors.value = [];
    validationSucceeded.value = false;
  }

  return {
    record,
    originalRecord,
    identifier,
    profile,
    isDraft,
    loading,
    loadError,
    saving,
    saveError,
    validationErrors,
    validationSucceeded,
    dirty,
    replaceRecord,
    clear,
  };
}

export type EditorState =
  ReturnType<typeof useEditorState>;
