<script setup lang="ts">
import {
  computed,
  onMounted,
  provide,
  ref,
  toRef,
  watch,
} from "vue";

import type {
  Component,
} from "vue";

import type {
  EditorModule,
  EditorModuleContext,
  EditorPanel,
  EditorRepository,
} from "./contracts";

import {
  RecordValidationError,
} from "./contracts";

import {
  editorRepositoryKey,
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

import RejectDialog from
  "./components/RejectDialog.vue";

import JsonSection from
  "./sections/JsonSection.vue";

import PreviewSection from
  "./sections/PreviewSection.vue";

import RejectedRecordSection from
  "./sections/RejectedRecordSection.vue";

import SchemaFormSection from
  "./sections/SchemaFormSection.vue";

import TemplatesSection from
  "./sections/TemplatesSection.vue";

const props = withDefaults(
  defineProps<{
    repository?: EditorRepository;
    mode?: "create" | "edit";
    recordId?: string;
    profile?: string;
    modules?: EditorModule[];
    panels?: EditorPanel[];
  }>(),
  {
    mode: "create",
    profile: "cve-5.2.0",
    modules: () => [],
    panels: () => [],
  },
);

const emit = defineEmits<{
  ready: [];
  loaded: [
    identifier: string,
  ];
  deleted: [
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

provide(
  editorRepositoryKey,
  toRef(props, "repository"),
);

const activeSection = ref("editor");

const BUILTIN_NAVIGATION_ITEMS = [
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
  {
    id: "templates",
    label: "Templates",
  },
];

const BUILTIN_SECTION_COMPONENTS:
  Record<string, Component> = {
    json: JsonSection,
    editor: SchemaFormSection,
    preview: PreviewSection,
    templates: TemplatesSection,
  };

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

const blockingErrorsDismissed = ref(false);
const validationWarningsDismissed = ref(false);

watch(state.validationErrors, () => {
  blockingErrorsDismissed.value = false;
  validationWarningsDismissed.value = false;
});

const validationSucceeded = ref(false);

const isRejected = computed(() => {
  return state.record.value?.cveMetadata?.state === "REJECTED";
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
  validationSucceeded.value = false;

  try {
    const result =
      await props.repository.validateRecord(
        state.record.value,
        state.profile.value ?? "cve-5.2.0",
      );

    state.validationErrors.value = result.errors;
    validationSucceeded.value = result.errors.length === 0;
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

async function handleSave(
  isDraft: boolean = state.isDraft.value,
): Promise<void> {
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
          isDraft,
        )
      : await props.repository.createRecord(
          state.record.value,
          profile,
          isDraft,
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

async function handleDelete(): Promise<void> {
  if (!props.repository || !state.identifier.value) {
    return;
  }

  if (
    !window.confirm(
      `Delete ${state.identifier.value}? This cannot be undone.`,
    )
  ) {
    return;
  }

  const identifier = state.identifier.value;

  state.saving.value = true;
  state.saveError.value = null;

  try {
    await props.repository.deleteRecord(identifier);

    state.clear();
    emit("deleted", identifier);
  } catch (error) {
    const normalized = normalizeError(
      error,
      "Unable to delete the record.",
    );

    state.saveError.value = normalized;
    emit("error", normalized);
  } finally {
    state.saving.value = false;
  }
}

const rejectDialogRef = ref<InstanceType<typeof RejectDialog> | null>(null);

function handleRejectClick(): void {
  rejectDialogRef.value?.open();
}

/*
 * A rejected CNA container is a different, minimal shape from a
 * normal one (schemas/upstream/cve/5.2.0's cnaRejectedContainer:
 * additionalProperties false, only providerMetadata/rejectedReasons/
 * replacedBy) — so this replaces containers.cna outright rather than
 * just flipping cveMetadata.state, which alone wouldn't produce a
 * schema-valid record. Saved through the same repository.updateRecord
 * used everywhere else: hosts don't need a dedicated "reject" method,
 * since a rejected record is still just a record to save.
 */
async function handleRejectConfirm(
  reason: string,
): Promise<void> {
  if (!props.repository || !state.record.value) {
    return;
  }

  const record = state.record.value;
  const now = new Date().toISOString();
  const previousProviderMetadata = record.containers?.cna?.providerMetadata;

  record.cveMetadata ??= {};
  record.cveMetadata.state = "REJECTED";
  record.cveMetadata.dateRejected = now;
  record.cveMetadata.dateUpdated = now;

  record.containers ??= {};
  record.containers.cna = {
    providerMetadata: {
      ...previousProviderMetadata,
      dateUpdated: now,
    },
    rejectedReasons: [
      {
        lang: "en",
        value: reason,
      },
    ],
  };

  await handleSave(false);
}

const moduleContext = computed<EditorModuleContext>(() => {
  return {
    identifier: state.identifier.value,
    profile: state.profile.value ?? "cve-5.2.0",
    record: state.record.value ?? {},
    isDraft: state.isDraft.value,
  };
});

const visiblePanels = computed(() => {
  return props.panels.filter(
    (panel) => panel.isVisible?.(moduleContext.value) ?? true,
  );
});

const panelNavigationItems = computed(() => {
  return visiblePanels.value.map((panel) => ({
    id: panel.id,
    label: panel.label,
  }));
});

const sectionComponents = computed<Record<string, Component>>(() => {
  return {
    ...BUILTIN_SECTION_COMPONENTS,
    editor: isRejected.value
      ? RejectedRecordSection
      : SchemaFormSection,
    ...Object.fromEntries(
      visiblePanels.value.map((panel) => [panel.id, panel.component]),
    ),
  };
});

const currentSection = computed(() => {
  return (
    sectionComponents.value[activeSection.value] ??
    SchemaFormSection
  );
});

/*
 * Panel components receive `context` as a prop; built-in sections
 * (JsonSection/SchemaFormSection/PreviewSection) don't declare it and
 * read shared state via useEditorContext() instead — binding it
 * unconditionally would leak as a stringified fallthrough attribute
 * onto their root element, so it's only passed for panel-sourced
 * sections.
 */
const sectionProps = computed(() => {
  const isPanel = visiblePanels.value.some(
    (panel) => panel.id === activeSection.value,
  );

  return isPanel ? { context: moduleContext.value } : {};
});

const visibleModules = computed(() => {
  return props.modules
    .filter((module) => module.isVisible?.(moduleContext.value) ?? true)
    .map((module) => ({
      id: module.id,
      label: module.label,
      enabled: module.isEnabled?.(moduleContext.value) ?? true,
    }));
});

async function handleRunModule(
  moduleId: string,
): Promise<void> {
  const module = props.modules.find(
    (candidate) => candidate.id === moduleId,
  );

  if (!module || !state.record.value) {
    return;
  }

  state.saving.value = true;
  state.saveError.value = null;

  try {
    await module.run(moduleContext.value);
  } catch (error) {
    const normalized = normalizeError(
      error,
      `Unable to run "${module.label}".`,
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
    if (dirty) {
      validationSucceeded.value = false;
    }

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
      :is-rejected="isRejected"
      :dirty="state.dirty.value"
      :loading="state.loading.value || state.saving.value"
      :modules="visibleModules"
      @reload="loadRecord"
      @validate="handleValidate"
      @save="handleSave()"
      @publish="handleSave(false)"
      @unpublish="handleSave(true)"
      @reject="handleRejectClick"
      @delete="handleDelete"
      @run-module="handleRunModule"
    />

    <RejectDialog
      ref="rejectDialogRef"
      @submit="handleRejectConfirm"
    />

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
        :items="BUILTIN_NAVIGATION_ITEMS"
        :panel-items="panelNavigationItems"
      />

      <main class="editor-content">
        <div
          v-if="state.saveError.value"
          class="alert alert-danger alert-dismissible mb-3"
          role="alert"
        >
          {{ state.saveError.value.message }}

          <button
            type="button"
            class="btn-close"
            aria-label="Close"
            @click="state.saveError.value = null"
          />
        </div>

        <div
          v-if="validationSucceeded"
          class="alert alert-success alert-dismissible mb-3"
          role="status"
        >
          The record is valid.

          <button
            type="button"
            class="btn-close"
            aria-label="Close"
            @click="validationSucceeded = false"
          />
        </div>

        <div
          v-if="blockingErrors.length && !blockingErrorsDismissed"
          class="alert alert-warning alert-dismissible mb-3"
          role="alert"
        >
          <button
            type="button"
            class="btn-close"
            aria-label="Close"
            @click="blockingErrorsDismissed = true"
          />

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
          v-if="validationWarnings.length && !validationWarningsDismissed"
          class="alert alert-info alert-dismissible mb-3"
          role="alert"
        >
          <button
            type="button"
            class="btn-close"
            aria-label="Close"
            @click="validationWarningsDismissed = true"
          />

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

        <component
          :is="currentSection"
          v-bind="sectionProps"
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
