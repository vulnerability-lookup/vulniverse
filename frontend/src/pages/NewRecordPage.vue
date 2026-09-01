<script setup lang="ts">
import {
  onMounted,
  ref,
} from "vue";

import {
  useRouter,
} from "vue-router";

import VulniverseEditor from
  "@/editor/VulniverseEditor.ce.vue";

import {
  HttpRepository,
} from "@/repositories/HttpRepository";

import {
  SUPPORTED_PROFILES,
} from "@/editor/profiles";

import {
  BUILTIN_MODULES,
} from "@/editor/modules";

import {
  BUILTIN_PANELS,
} from "@/editor/panels";

import {
  filterEnabled,
} from "@/editor/enabled-extensions";

const router = useRouter();

const repository = new HttpRepository("/api/v1");

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

const selectedProfile = ref<string | null>(null);

function selectProfile(
  profileId: string,
): void {
  selectedProfile.value = profileId;
}

function handleLoaded(
  identifier: string,
): void {
  router.push({
    name: "editor",
    params: { recordId: identifier },
  });
}

function handleError(
  error: Error,
): void {
  console.error(
    "Editor error:",
    error,
  );
}
</script>

<template>
  <div
    v-if="!selectedProfile"
    class="container py-5"
  >
    <h1 class="h3 mb-4">Create a new vulnerability record</h1>

    <div class="row g-3">
      <div
        v-for="profile in SUPPORTED_PROFILES"
        :key="profile.id"
        class="col-md-6"
      >
        <div class="card h-100">
          <div class="card-body d-flex flex-column">
            <h2 class="h5 card-title">{{ profile.label }}</h2>

            <p class="card-text text-secondary flex-grow-1">
              {{ profile.description }}
            </p>

            <button
              type="button"
              class="btn btn-primary"
              @click="selectProfile(profile.id)"
            >
              Create as {{ profile.label }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>

  <div
    v-else
    class="editor-page"
  >
    <VulniverseEditor
      :repository="repository"
      mode="create"
      :profile="selectedProfile"
      :modules="enabledModules"
      :panels="enabledPanels"
      @loaded="handleLoaded"
      @error="handleError"
    />
  </div>
</template>

<style scoped>
/*
 * See EditorPage.vue for why this wrapper exists — it's what opts
 * the standalone app's page into filling the viewport height, which
 * VulniverseEditor.ce.vue itself deliberately doesn't assume.
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
