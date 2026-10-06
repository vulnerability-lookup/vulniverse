<script setup lang="ts">
import {
  computed,
  onMounted,
  provide,
  ref,
  toRef,
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
  useEditorController,
} from "./core/controller";

import {
  normalizeError,
} from "./core/errors";

import {
  editorRepositoryKey,
  editorSaveKey,
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

import EditorNotifications from
  "./components/EditorNotifications.vue";

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

const repositoryRef =
  toRef(props, "repository");

provide(
  editorStateKey,
  state,
);

provide(
  editorRepositoryKey,
  repositoryRef,
);

const controller =
  useEditorController({
    state,

    repository:
      repositoryRef,

    mode:
      toRef(props, "mode"),

    recordId:
      toRef(props, "recordId"),

    profile:
      toRef(props, "profile"),

    onReady() {
      emit("ready");
    },

    onLoaded(identifier) {
      emit(
        "loaded",
        identifier,
      );
    },

    onDeleted(identifier) {
      emit(
        "deleted",
        identifier,
      );
    },

    onError(error) {
      emit(
        "error",
        error,
      );
    },

    onDirtyChange(dirty) {
      emit(
        "dirtyChange",
        dirty,
      );
    },
  });

provide(
  editorSaveKey,
  (options) =>
    controller.save(
      undefined,
      options,
    ),
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
];

const BUILTIN_SECTION_COMPONENTS:
  Record<string, Component> = {
    json: JsonSection,
    editor: SchemaFormSection,
    preview: PreviewSection,
  };

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
    editor: controller.isRejected.value
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

async function handleDelete(): Promise<void> {
  const identifier = state.identifier.value;

  if (
    !identifier ||
    !controller.canDelete.value
  ) {
    return;
  }

  const confirmed = window.confirm(
    `Delete ${identifier}? This cannot be undone.`,
  );

  if (!confirmed) {
    return;
  }

  await controller.remove();
}

const rejectDialogRef =
  ref<
    InstanceType<typeof RejectDialog> | null
  >(null);

function handleRejectClick(): void {
  rejectDialogRef.value?.open();
}

onMounted(controller.load);
</script>

<template>
  <div class="vulniverse-editor">
    <EditorHeader
      :identifier="state.identifier.value"
      :profile="state.profile.value"
      :is-draft="state.isDraft.value"
      :is-rejected="controller.isRejected.value"
      :dirty="state.dirty.value"
      :loading="state.loading.value || state.saving.value"
      :modules="visibleModules"
      :can-delete="controller.canDelete.value"
      @reload="controller.load"
      @validate="controller.validate"
      @save="controller.save()"
      @publish="controller.save(false)"
      @unpublish="controller.save(true)"
      @reject="handleRejectClick"
      @delete="handleDelete"
      @run-module="handleRunModule"
    />

    <RejectDialog
      ref="rejectDialogRef"
      @submit="controller.reject"
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
      @retry="controller.load"
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
        <component
          :is="currentSection"
          v-bind="sectionProps"
        />
      </main>

      <EditorNotifications />
    </div>

    <div
      v-else
      class="editor-status text-center text-secondary p-5"
    >
      No vulnerability record is loaded.
    </div>
  </div>
</template>
