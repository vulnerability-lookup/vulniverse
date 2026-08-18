<script setup lang="ts">
import {
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

const router = useRouter();

const repository = new HttpRepository("/api/v1");

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

  <VulniverseEditor
    v-else
    :repository="repository"
    mode="create"
    :profile="selectedProfile"
    @loaded="handleLoaded"
    @error="handleError"
  />
</template>
