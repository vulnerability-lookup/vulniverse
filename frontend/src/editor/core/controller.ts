import {
  computed,
  toRaw,
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
  LifecycleTransition,
} from "../contracts";

import type {
  EditorState,
} from "./state";

import {
  normalizeError,
} from "./errors";

import { createEmptyRecord } from "./record";

import type {
  CveRecord,
} from "../contracts";

import {
  getGcveVulnId,
} from "../gcve";

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
      // Saved instead of the editor's document; it only replaces the
      // editor's one if the save succeeds (see runTransition).
      document?: EditorDocument;
    } = {},
  ): Promise<string | null> {
    const document = saveOptions.document ?? state.record.value;

    if (
      !repository.value ||
      !document
    ) {
      return null;
    }

    state.saving.value = true;
    state.saveError.value = null;

    const wasDraft = state.isDraft.value;

    const currentProfile =
      state.profile.value ??
      DEFAULT_PROFILE_ID;

    /*
     * cveMetadata.vulnId is a derived mirror of x_gcve[].vulnId (the
     * real GCVE-BCP-05 schema field), kept in sync here as a backstop
     * regardless of how x_gcve got edited — the GCVE ID panel, the
     * CNA publication reservation flow, or a direct edit via Advanced
     * JSON/the GCVE extension renderer. It's never the other way
     * around: nothing should write cveMetadata.vulnId without x_gcve
     * already agreeing, so there's nothing to do when x_gcve has no
     * vulnId yet.
     */
    const gcveVulnId = getGcveVulnId(
      document as CveRecord,
    );

    if (gcveVulnId) {
      const record =
        document as CveRecord;

      record.cveMetadata ??= {};
      record.cveMetadata.vulnId = gcveVulnId;
    }

    try {
      const saved =
        state.identifier.value
          ? await repository.value.updateRecord(
              state.identifier.value,
              document,
              currentProfile,
              isDraft,
            )
          : await repository.value.createRecord(
              document,
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

  /**
   * A lifecycle step: save a copy of the document changed by the
   * transition's apply() (if any), with its target draft state. The
   * editor's document stays untouched until the save succeeds.
   */
  async function runTransition(
    transition: LifecycleTransition,
    input?: unknown,
  ): Promise<void> {
    if (!state.record.value) {
      return;
    }

    const document = transition.apply?.(
      structuredClone(toRaw(state.record.value)),
      input,
      new Date().toISOString(),
    );

    await save(transition.targetIsDraft, {
      document,
      notice: transition.notice,
    });
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
    runTransition,
  };
}
