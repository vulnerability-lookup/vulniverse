<script setup lang="ts">
import {
  nextTick,
  onMounted,
  provide,
  ref,
  shallowRef,
  toRef,
} from "vue";

import type {
  Component,
} from "vue";

import type {
  EditorAction,
  EditorPanel,
  EditorRepository,
  LifecycleTransition,
  TransitionDialog,
} from "./contracts";

import {
  useEditorController,
} from "./core/controller";

import {
  editorRepositoryKey,
  editorSaveKey,
  editorStateKey,
} from "./core/context";

import {
  useEditorState,
} from "./core/state";

import EditorError from
  "./components/EditorError.vue";

import { displayIdentifier } from "./identifier";

import EditorHeader from
  "./components/EditorHeader.vue";

import EditorNavigation from
  "./components/EditorNavigation.vue";

import EditorNotifications from
  "./components/EditorNotifications.vue";

import {
  BUILTIN_NAVIGATION_ITEMS,
  useEditorExtensions,
} from "./core/extensions";

import {
  DEFAULT_PROFILE_ID,
} from "./profiles";

const props = withDefaults(
  defineProps<{
    repository?: EditorRepository;
    mode?: "create" | "edit";
    recordId?: string;
    profile?: string;
    actions?: EditorAction[];
    panels?: EditorPanel[];
  }>(),
  {
    mode: "create",
    profile: DEFAULT_PROFILE_ID,
    actions: () => [],
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

    actions:
      toRef(props, "actions"),

    repository:
      repositoryRef,

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
  visibleActions,
  visibleLifecycleTransitions,
  panelNavigationItems,
  currentSection,
  sectionProps,
  runAction,
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
    `Delete ${displayIdentifier(state.vulnerabilityId.value, true)}? This cannot be undone.`,
  );

  if (!confirmed) {
    return;
  }

  await controller.remove();
}

// The open transition's dialog, mounted only while it asks for input.
const transitionDialog = shallowRef<Component | null>(null);
const transitionDialogRef = ref<TransitionDialog | null>(null);

async function handleTransition(
  transition: LifecycleTransition,
): Promise<void> {
  let input: unknown;

  if (transition.dialog) {
    transitionDialog.value = transition.dialog;
    await nextTick();

    try {
      input = await transitionDialogRef.value?.open(extensions.context.value);
    } finally {
      transitionDialog.value = null;
    }

    // Cancelled: nothing changes.
    if (input === null || input === undefined) {
      return;
    }
  }

  await controller.runTransition(transition, input);
}

onMounted(controller.load);
</script>

<template>
  <div class="vulniverse-editor">
    <EditorHeader
      :identifier="state.identifier.value"
      :vulnerability-id="state.vulnerabilityId.value"
      :profile="state.profile.value"
      :is-draft="state.isDraft.value"
      :is-rejected="controller.isRejected.value"
      :dirty="state.dirty.value"
      :loading="state.loading.value || state.saving.value"
      :actions="visibleActions"
      :lifecycle-transitions="visibleLifecycleTransitions"
      :can-delete="controller.canDelete.value"
      @reload="controller.load"
      @validate="controller.validate"
      @save="controller.save()"
      @transition="handleTransition"
      @delete="handleDelete"
      @run-action="runAction"
    />

    <component
      :is="transitionDialog"
      v-if="transitionDialog"
      ref="transitionDialogRef"
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
