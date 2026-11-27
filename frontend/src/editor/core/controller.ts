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
  EditorDocument,
  EditorRepository,
} from "../contracts";

import type {
  EditorState,
} from "./state";

import {
  normalizeError,
} from "./errors";

import { createEmptyRecord, withGenerator } from "./record";

import {
  DEFAULT_PROFILE_ID,
  getEditorProfile,
} from "../profiles";

interface EditorControllerOptions {
  state: EditorState;

  repository: Readonly<Ref<EditorRepository | undefined>>;
  mode: Readonly<Ref<"create" | "edit">>;
  recordId: Readonly<Ref<string | undefined>>;
  profile: Readonly<Ref<string>>;
  // A new record's starting content, instead of an empty one.
  initialRecord?: Readonly<Ref<EditorDocument | undefined>>;

  onReady(): void;
  onLoaded(identifier: string): void;
  onDeleted(identifier: string): void;
  onError(error: Error): void;
  onDirtyChange(dirty: boolean): void;
}

function saveNotice(
  wasDraft: boolean,
  isDraft: boolean,
): string {
  if (wasDraft && !isDraft) return "Record published.";
  if (!wasDraft && isDraft) return "Record reverted to draft.";

  return isDraft ? "Draft saved." : "Record saved.";
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

  const activeProfile = computed(
    () =>
      getEditorProfile(
        state.profile.value ??
          profile.value ??
          DEFAULT_PROFILE_ID,
      ),
  );

  const isRejected = computed(() => {
    if (!state.record.value) {
      return false;
    }

    return (
      activeProfile.value.rejection?.isRejected(
        state.record.value,
      ) ?? false
    );
  });

  const canReject = computed(() => {
    return Boolean(
      state.record.value
        && activeProfile.value.rejection
        && !isRejected.value,
    );
  });

  const canDelete = computed(
    () => Boolean(repository.value?.deleteRecord),
  );

  async function load(): Promise<void> {
    const identifier = mode.value === "create"
      ? state.identifier.value
      : recordId.value;

    if (mode.value === "create" && !identifier) {
      state.clear();

      const empty = createEmptyRecord(profile.value);
      const initial = options.initialRecord?.value;

      state.replaceRecord(
        initial ? { ...empty, record: initial } : empty,
      );

      options.onReady();
      return;
    }

    if (!identifier) {
      const error = new Error(
        "Edit mode requires a record identifier.",
      );

      state.loadError.value = error;
      options.onError(error);

      return;
    }

    // Hosts that bind properties after inserting the element (frameworks)
    // set the repository a moment later: wait for it (see the watch below).
    if (!repository.value) {
      return;
    }

    state.loading.value = true;
    state.loadError.value = null;

    try {
      const loaded =
        await repository.value.loadRecord(
          identifier,
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
            DEFAULT_PROFILE_ID,
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
      notice?: string;
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

    const wasDraft = state.isDraft.value;

    const currentProfile =
      state.profile.value ??
      DEFAULT_PROFILE_ID;

    const record =
      !state.identifier.value || state.dirty.value
        ? withGenerator(state.record.value)
        : state.record.value;

    try {
      const saved =
        state.identifier.value
          ? await repository.value.updateRecord(
              state.identifier.value,
              record,
              currentProfile,
              isDraft,
            )
          : await repository.value.createRecord(
              record,
              currentProfile,
              isDraft,
            );

      state.replaceRecord(saved);
      state.validationErrors.value = [];

      if (!saveOptions.silent) {
        state.notice.value = saveOptions.notice ?? saveNotice(wasDraft, saved.isDraft);

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

    const rejection = activeProfile.value.rejection;

    if (!rejection) {
      throw new Error(
        `Profile ${activeProfile.value.id} does not support rejection.`,
      );
    }

    state.record.value = rejection.reject(
      state.record.value,
      reason,
    );

    await save(false, { notice: "Record rejected." });
  }

  // The first repository loads the record a missing one held up (not in
  // create mode, whose empty record never waited and may be edited already).
  watch(
    repository,
    async (current, previous) => {
      if (current && !previous && !state.record.value) {
        await load();
      }
    },
  );

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

  if (options.initialRecord) {
    watch(
      options.initialRecord,
      async () => {
        if (mode.value === "create") {
          state.clear();
          await load();
        }
      },
    );
  }

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
    canReject,
    canDelete,

    load,
    validate,
    save,
    remove,
    reject,
  };
}
