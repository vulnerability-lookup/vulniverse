import {
  computed,
  watch,
} from "vue";

import type {
  Ref,
} from "vue";

import {
  RecordValidationError,
} from "../contracts";

import type {
  EditorRepository,
} from "../contracts";

import type {
  EditorState,
} from "../use-editor-state";

import {
  normalizeError,
} from "./errors";

import { createEmptyRecord, rejectRecord } from "./record";

interface EditorControllerOptions {
  state: EditorState;

  repository: Readonly<Ref<EditorRepository | undefined>>;
  mode: Readonly<Ref<"create" | "edit">>;
  recordId: Readonly<Ref<string | undefined>>;
  profile: Readonly<Ref<string>>;

  onReady(): void;
  onLoaded(identifier: string): void;
  onDeleted(identifier: string): void;
  onError(error: Error): void;
  onDirtyChange(dirty: boolean): void;
}

export function useEditorController(
  options: EditorControllerOptions,
) {
  const {
    state,
    repository,
    mode,
    recordId,
    profile,
  } = options;

  const isRejected = computed(
    () =>
      state.record.value
        ?.cveMetadata
        ?.state === "REJECTED",
  );

  const canDelete = computed(
    () => Boolean(repository.value?.deleteRecord),
  );

  async function load(): Promise<void> {
    if (mode.value === "create") {
      state.clear();

      state.replaceRecord(
        createEmptyRecord(profile.value),
      );

      options.onReady();
      return;
    }

    if (!recordId.value) {
      const error = new Error(
        "Edit mode requires a record identifier.",
      );

      state.loadError.value = error;
      options.onError(error);

      return;
    }

    if (!repository.value) {
      const error = new Error(
        "No repository has been configured.",
      );

      state.loadError.value = error;
      options.onError(error);

      return;
    }

    state.loading.value = true;
    state.loadError.value = null;

    try {
      const loaded =
        await repository.value.loadRecord(
          recordId.value,
        );

      state.replaceRecord(loaded);

      options.onLoaded(
        loaded.identifier,
      );

      options.onReady();
    } catch (error) {
      const normalized = normalizeError(
        error,
        "Unable to load vulnerability record.",
      );

      state.loadError.value = normalized;
      options.onError(normalized);
    } finally {
      state.loading.value = false;
    }
  }

  async function validate(): Promise<void> {
    if (
      !repository.value ||
      !state.record.value
    ) {
      return;
    }

    state.saving.value = true;
    state.saveError.value = null;
    state.validationSucceeded.value = false;

    try {
      const result =
        await repository.value.validateRecord(
          state.record.value,
          state.profile.value ??
            "cve-5.2.0",
        );

      state.validationErrors.value =
        result.errors;

      state.validationSucceeded.value =
        result.errors.length === 0;
    } catch (error) {
      const normalized = normalizeError(
        error,
        "Unable to validate the record.",
      );

      state.saveError.value = normalized;
      options.onError(normalized);
    } finally {
      state.saving.value = false;
    }
  }

  async function save(
    isDraft = state.isDraft.value,
    saveOptions: {
      silent?: boolean;
    } = {},
  ): Promise<string | null> {
    if (
      !repository.value ||
      !state.record.value
    ) {
      return null;
    }

    state.saving.value = true;
    state.saveError.value = null;

    const currentProfile =
      state.profile.value ??
      "cve-5.2.0";

    try {
      const saved =
        state.identifier.value
          ? await repository.value.updateRecord(
              state.identifier.value,
              state.record.value,
              currentProfile,
              isDraft,
            )
          : await repository.value.createRecord(
              state.record.value,
              currentProfile,
              isDraft,
            );

      state.replaceRecord(saved);
      state.validationErrors.value = [];

      if (!saveOptions.silent) {
        options.onLoaded(
          saved.identifier,
        );
      }

      return saved.identifier;
    } catch (error) {
      if (
        error instanceof
        RecordValidationError
      ) {
        state.validationErrors.value =
          error.errors;

        return null;
      }

      const normalized = normalizeError(
        error,
        "Unable to save the record.",
      );

      state.saveError.value = normalized;
      options.onError(normalized);

      return null;
    } finally {
      state.saving.value = false;
    }
  }

  async function remove(): Promise<void> {
    const currentRepository =
      repository.value;

    const identifier =
      state.identifier.value;

    if (
      !currentRepository?.deleteRecord ||
      !identifier
    ) {
      return;
    }

    state.saving.value = true;
    state.saveError.value = null;

    try {
      await currentRepository.deleteRecord(
        identifier,
      );

      state.clear();

      options.onDeleted(identifier);
    } catch (error) {
      const normalized = normalizeError(
        error,
        "Unable to delete the record.",
      );

      state.saveError.value = normalized;
      options.onError(normalized);
    } finally {
      state.saving.value = false;
    }
  }

  async function reject(
    reason: string,
  ): Promise<void> {
    if (!state.record.value) {
      return;
    }

    state.record.value = rejectRecord(
      state.record.value,
      reason,
    );

    await save(false);
  }

  watch(
    recordId,
    async (
      current,
      previous,
    ) => {
      if (current !== previous) {
        await load();
      }
    },
  );

  watch(
    state.dirty,
    (dirty) => {
      if (dirty) {
        state.validationSucceeded.value = false;
      }

      options.onDirtyChange(dirty);
    },
  );

  return {
    isRejected,
    canDelete,

    load,
    validate,
    save,
    remove,
    reject,
  };
}
