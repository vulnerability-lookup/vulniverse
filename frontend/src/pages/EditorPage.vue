<script setup lang="ts">
import {
  computed,
  onMounted,
  ref,
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
  BUILTIN_MODULES,
} from "@/editor/modules";

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

const enabledModules = ref(BUILTIN_MODULES);
const enabledPanels = ref(BUILTIN_PANELS);

onMounted(async () => {
  try {
    const capabilities = await repository.getCapabilities();

    enabledModules.value = filterEnabled(BUILTIN_MODULES, capabilities.modules);
    enabledPanels.value = filterEnabled(BUILTIN_PANELS, capabilities.panels);
  } catch (error) {
    console.warn(
      "Could not load app capabilities, showing all built-in panels/modules:",
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

  router.push("/");
}
</script>

<template>
  <div class="editor-page">
    <VulniverseEditor
      :repository="repository"
      mode="edit"
      :record-id="recordId"
      :modules="enabledModules"
      :panels="enabledPanels"
      @loaded="handleLoaded"
      @error="handleError"
      @deleted="handleDeleted"
    />
  </div>
</template>

<style scoped>
/*
 * VulniverseEditor.ce.vue's own styles fill 100% of whatever height
 * they're given (see editor.scss's :host rule) but never assume a
 * height themselves, since the same component is also the embeddable
 * <vulniverse-editor> — an embedding host's page decides that, not
 * the component. This wrapper is what actually opts the standalone
 * app's own page into filling the viewport.
 */
.editor-page {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  min-height: 100dvh;
}

.editor-page :deep(.vulniverse-editor) {
  flex: 1 1 auto;
  min-height: 0;
  min-width: 0;
}
</style>
