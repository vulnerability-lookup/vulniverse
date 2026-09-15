<script setup lang="ts">
import {
  ref,
} from "vue";

import VulniverseEditor from
  "@/editor/VulniverseEditor.ce.vue";

import {
  SandboxRepository,
} from "@/repositories/SandboxRepository";

import {
  SUPPORTED_PROFILES,
} from "@/editor/profiles";

// One SandboxRepository instance per page load — everything it holds
// is in memory only, so there's nothing to reset between mounts
const repository = new SandboxRepository();

const selectedProfile = ref<string | null>(null);

function selectProfile(
  profileId: string,
): void {
  selectedProfile.value = profileId;
}

function handleError(
  error: Error,
): void {
  console.error(
    "Sandbox editor error:",
    error,
  );
}
</script>

<template>
  <div
    v-if="!selectedProfile"
    class="container py-5"
  >
    <h1 class="h3 mb-2">Try the editor</h1>

    <p class="text-secondary mb-4">
      Nothing you enter here is saved — this is an in-memory sandbox,
      gone as soon as you leave or refresh the page. Register an
      account to keep your work and publish real records.
    </p>

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
              Try as {{ profile.label }}
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
    <div class="alert alert-warning mb-3" role="status">
      Sandbox mode — nothing here is saved. Refreshing or leaving this
      page discards everything.
    </div>

    <div class="editor-card card shadow-sm">
      <VulniverseEditor
        :repository="repository"
        mode="create"
        :profile="selectedProfile"
        :panels="[]"
        :modules="[]"
        @error="handleError"
      />
    </div>
  </div>
</template>

<style scoped>
/* See EditorPage.vue for why this wrapper exists. */
.editor-page {
  display: flex;
  flex-direction: column;
  flex: 1 1 auto;
  min-height: 0;
  padding: 1.5rem;
}

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
