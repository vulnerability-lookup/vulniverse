<script setup lang="ts">
import {
  computed,
  onMounted,
  provide,
  ref,
  watch,
} from "vue";

import type {
  Component,
} from "vue";

import type {
  EditorRepository,
} from "./contracts";

import {
  RecordValidationError,
} from "./contracts";

import {
  editorStateKey,
} from "./editor-context";

import {
  useEditorState,
} from "./use-editor-state";

import EditorError from
  "./components/EditorError.vue";

import EditorHeader from
  "./components/EditorHeader.vue";

import EditorNavigation from
  "./components/EditorNavigation.vue";

import JsonSection from
  "./sections/JsonSection.vue";

import PreviewSection from
  "./sections/PreviewSection.vue";

import SchemaFormSection from
  "./sections/SchemaFormSection.vue";

const props = withDefaults(
  defineProps<{
    repository?: EditorRepository;
    mode?: "create" | "edit";
    recordId?: string;
    profile?: string;
  }>(),
  {
    mode: "create",
    profile: "cve-5.2.0",
  },
);

const emit = defineEmits<{
  ready: [];
  loaded: [
    identifier: string,
  ];
  error: [
    error: Error,
  ];
  dirtyChange: [
    dirty: boolean,
  ];
}>();

const state = useEditorState();

provide(
  editorStateKey,
  state,
);

const activeSection = ref("editor");

const navigationItems = [
  {
    id: "editor",
    label: "Editor",
  },
  {
    id: "preview",
    label: "Preview",
  },
  {
    id: "json",
    label: "Advanced JSON",
  },
];

const sectionComponents:
  Record<string, Component> = {
    json: JsonSection,
    editor: SchemaFormSection,
    preview: PreviewSection,
  };

const currentSection = computed(() => {
  return (
    sectionComponents[activeSection.value] ??
    SchemaFormSection
  );
});

/*
 * Warnings (e.g. an unrecognized GCVE relationship type) never
 * block saving — only entries with severity "error" (the default,
 * for validators that predate the concept) do. Splitting them keeps
 * a warning-only result from reading as "you can't save this."
 */
const blockingErrors = computed(() => {
  return state.validationErrors.value.filter(
    (error) => (error.severity ?? "error") === "error",
  );
});

const validationWarnings = computed(() => {
  return state.validationErrors.value.filter(
    (error) => error.severity === "warning",
  );
});

function normalizeError(
  error: unknown,
  fallbackMessage: string,
): Error {
  return error instanceof Error
    ? error
    : new Error(fallbackMessage);
}

async function loadRecord(): Promise<void> {
  if (props.mode !== "edit") {
    state.clear();

    // dataVersion is the CVE Record Format version — GCVE is an
    // extension bolted onto that same format, not a different one,
    // so it stays "5.2.0" regardless of props.profile.
    state.replaceRecord({
      identifier: "",
      profile: props.profile,
      isDraft: true,
      record: {
        dataType: "CVE_RECORD",
        dataVersion: "5.2.0",
        cveMetadata: {},
        containers: {
          cna: {
            descriptions: [],
            affected: [],
            references: [],
          },
        },
        ...(props.profile.startsWith("gcve-")
          ? { x_gcve: [] }
          : {}),
      },
    });

    emit("ready");
    return;
  }

  if (!props.recordId) {
    const error = new Error(
      "Edit mode requires a record identifier.",
    );

    state.loadError.value = error;
    emit("error", error);
    return;
  }

  if (!props.repository) {
    const error = new Error(
      "No repository has been configured.",
    );

    state.loadError.value = error;
    emit("error", error);
    return;
  }

  state.loading.value = true;
  state.loadError.value = null;

  try {
    const loaded =
      await props.repository.loadRecord(
        props.recordId,
      );

    state.replaceRecord(loaded);

    emit(
      "loaded",
      loaded.identifier,
    );

    emit("ready");
  } catch (error) {
    const normalized = normalizeError(
      error,
      "Unable to load vulnerability record.",
    );

    state.loadError.value = normalized;
    emit("error", normalized);
  } finally {
    state.loading.value = false;
  }
}

async function handleValidate(): Promise<void> {
  if (!props.repository || !state.record.value) {
    return;
  }

  state.saving.value = true;
  state.saveError.value = null;

  try {
    const result =
      await props.repository.validateRecord(
        state.record.value,
        state.profile.value ?? "cve-5.2.0",
      );

    state.validationErrors.value = result.errors;
  } catch (error) {
    const normalized = normalizeError(
      error,
      "Unable to validate the record.",
    );

    state.saveError.value = normalized;
    emit("error", normalized);
  } finally {
    state.saving.value = false;
  }
}

async function handleSave(): Promise<void> {
  if (!props.repository || !state.record.value) {
    return;
  }

  state.saving.value = true;
  state.saveError.value = null;

  const profile = state.profile.value ?? "cve-5.2.0";

  try {
    const saved = state.identifier.value
      ? await props.repository.updateRecord(
          state.identifier.value,
          state.record.value,
          profile,
          state.isDraft.value,
        )
      : await props.repository.createRecord(
          state.record.value,
          profile,
          state.isDraft.value,
        );

    state.replaceRecord(saved);
    state.validationErrors.value = [];

    emit("loaded", saved.identifier);
  } catch (error) {
    if (error instanceof RecordValidationError) {
      state.validationErrors.value = error.errors;
      return;
    }

    const normalized = normalizeError(
      error,
      "Unable to save the record.",
    );

    state.saveError.value = normalized;
    emit("error", normalized);
  } finally {
    state.saving.value = false;
  }
}

watch(
  () => props.recordId,
  async (
    current,
    previous,
  ) => {
    if (current !== previous) {
      await loadRecord();
    }
  },
);

watch(
  state.dirty,
  (dirty) => {
    emit(
      "dirtyChange",
      dirty,
    );
  },
);

onMounted(loadRecord);
</script>

<template>
  <div class="vulniverse-editor">
    <EditorHeader
      :identifier="state.identifier.value"
      :profile="state.profile.value"
      :is-draft="state.isDraft.value"
      :dirty="state.dirty.value"
      :loading="state.loading.value || state.saving.value"
      @reload="loadRecord"
      @validate="handleValidate"
      @save="handleSave"
    />

    <div
      v-if="state.saveError.value"
      class="alert alert-danger m-3"
      role="alert"
    >
      {{ state.saveError.value.message }}
    </div>

    <div
      v-if="blockingErrors.length"
      class="alert alert-warning m-3"
      role="alert"
    >
      <p class="mb-2">
        The record has
        {{ blockingErrors.length }}
        validation
        {{
          blockingErrors.length === 1
            ? "error"
            : "errors"
        }}.
      </p>

      <ul class="mb-0">
        <li
          v-for="(error, index) in blockingErrors"
          :key="index"
        >
          <code>{{ error.path.join(".") || "record" }}</code>
          — {{ error.message }}
        </li>
      </ul>
    </div>

    <div
      v-if="validationWarnings.length"
      class="alert alert-info m-3"
      role="alert"
    >
      <p class="mb-2">
        {{ validationWarnings.length }}
        validation
        {{
          validationWarnings.length === 1
            ? "warning"
            : "warnings"
        }}
        (won't block saving).
      </p>

      <ul class="mb-0">
        <li
          v-for="(warning, index) in validationWarnings"
          :key="index"
        >
          <code>{{ warning.path.join(".") || "record" }}</code>
          — {{ warning.message }}
        </li>
      </ul>
    </div>

    <div
      v-if="state.loading.value"
      class="editor-status text-center text-secondary p-5"
    >
      Loading vulnerability record…
    </div>

    <EditorError
      v-else-if="state.loadError.value"
      :error="state.loadError.value"
      @retry="loadRecord"
    />

    <div
      v-else-if="state.record.value"
      class="editor-layout"
    >
      <EditorNavigation
        v-model="activeSection"
        :items="navigationItems"
      />

      <main class="editor-content">
        <component
          :is="currentSection"
        />
      </main>
    </div>

    <div
      v-else
      class="editor-status text-center text-secondary p-5"
    >
      No vulnerability record is loaded.
    </div>
  </div>
</template>
