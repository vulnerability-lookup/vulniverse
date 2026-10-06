<script setup lang="ts">
import {
  onMounted,
  provide,
  ref,
  toRef,
} from "vue";

import type {
  EditorModule,
  EditorPanel,
  EditorRepository,
} from "./contracts";

import {
  useEditorController,
} from "./core/controller";

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

import EditorNotifications from
  "./components/EditorNotifications.vue";

import {
  BUILTIN_NAVIGATION_ITEMS,
  useEditorExtensions,
} from "./core/extensions";

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

const extensions =
  useEditorExtensions({
    state,

    activeSection,

    panels:
      toRef(props, "panels"),

    modules:
      toRef(props, "modules"),

    isRejected:
      controller.isRejected,

    onError(error) {
      emit(
        "error",
        error,
      );
    },
  });

const {
  visibleModules,
  panelNavigationItems,
  currentSection,
  sectionProps,
  runModule,
} = extensions;


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
      @run-module="runModule"
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
