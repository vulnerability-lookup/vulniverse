<script setup lang="ts">
import {
  computed,
  onMounted,
  shallowRef,
} from "vue";

import {
  useRoute,
  useRouter,
} from "vue-router";

import VulniverseEditor from
  "@/editor/VulniverseEditor.ce.vue";

import {
  HttpRepository,
} from "@/repositories/HttpRepository";

import {
  BUILTIN_ACTIONS,
  createConvertAction,
} from "@/editor/actions";

import {
  BUILTIN_PANELS,
} from "@/editor/panels";

import {
  filterEnabled,
} from "@/editor/enabled-extensions";

const route = useRoute();
const router = useRouter();

const repository =
  new HttpRepository("/api/v1");

// Whether the open record has unsaved changes (from the editor).
const unsaved = { changes: false };

function handleDirtyChange(value: boolean): void {
  unsaved.changes = value;
}

// Opens the converted record in this tab, so unsaved changes to the
// source record would be lost: ask first.
const PAGE_ACTIONS = [
  ...BUILTIN_ACTIONS,
  createConvertAction(
    repository,
    (identifier) => router.push(`/editor/${encodeURIComponent(identifier)}`),
    () => !unsaved.changes || window.confirm(
      "This record has unsaved changes. They are used for the conversion, "
      + "but not saved here, and are lost when the new record opens. Continue?",
    ),
  ),
];

const enabledActions = shallowRef(PAGE_ACTIONS);
const enabledPanels = shallowRef(BUILTIN_PANELS);

onMounted(async () => {
  try {
    const capabilities = await repository.getCapabilities();

    enabledActions.value = filterEnabled(PAGE_ACTIONS, capabilities.actions);
    enabledPanels.value = filterEnabled(BUILTIN_PANELS, capabilities.panels);
    repository.setFeatures(capabilities.features);
  } catch (error) {
    console.warn(
      "Could not load app capabilities, showing all built-in panels/actions:",
      error,
    );
  }
});

const recordId = computed(() => {
  const parameter =
    route.params.recordId;

  if (Array.isArray(parameter)) {
    return parameter[0] ?? "";
  }

  return parameter ?? "";
});

function handleLoaded(
  identifier: string,
): void {
  console.info(
    "Opened vulnerability record:",
    identifier,
  );
}

function handleError(
  error: Error,
): void {
  console.error(
    "Editor error:",
    error,
  );
}

function handleDeleted(
  identifier: string,
): void {
  console.info(
    "Deleted vulnerability record:",
    identifier,
  );

  router.push("/records");
}
</script>

<template>
  <div class="editor-page">
    <div class="editor-card card shadow-sm">
      <VulniverseEditor
        :repository="repository"
        mode="edit"
        :record-id="recordId"
        :actions="enabledActions"
        :panels="enabledPanels"
        @loaded="handleLoaded"
        @dirty-change="handleDirtyChange"
        @error="handleError"
        @deleted="handleDeleted"
      />
    </div>
  </div>
</template>

<style scoped>
/*
 * VulniverseEditor.ce.vue's own styles fill 100% of whatever height
 * they're given (see editor.scss's :host rule) but never assume a
 * height themselves, since the same component is also the embeddable
 * <vulniverse-editor> — an embedding host's page decides that, not
 * the component. This wrapper is what actually opts the standalone
 * app's own page into filling the viewport (#app is a flex column in
 * main.scss, so flex: 1 1 auto here fills whatever's left below
 * AppHeader rather than re-claiming the full viewport height itself).
 */
.editor-page {
  display: flex;
  flex-direction: column;
  flex: 1 1 auto;
  min-height: 0;
  padding: 1.5rem;
}

/*
 * The editor sits in its own card, similar to how Vulnerability-Lookup
 * frames embedded widgets — overflow: hidden keeps the editor's own
 * (rectangular) header/sidebar backgrounds clipped to the card's
 * rounded corners.
 */
.editor-card {
  flex: 1 1 auto;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}

.editor-card :deep(.vulniverse-editor) {
  flex: 1 1 auto;
  min-height: 0;
  min-width: 0;
}
</style>
