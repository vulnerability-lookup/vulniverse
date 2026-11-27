<script setup lang="ts">
import {
  onMounted,
  ref,
} from "vue";

import {
  useRouter,
} from "vue-router";

import {
  HttpRepository,
} from "@/repositories/HttpRepository";

import type {
  Patch2VulnBatchSummary,
} from "@/repositories/HttpRepository";

import {
  DEFAULT_PROFILE_ID,
  SUPPORTED_PROFILES,
} from "@/editor/profiles";

const router = useRouter();
const repository = new HttpRepository("/api/v1");

const batches = ref<Patch2VulnBatchSummary[]>([]);
const loading = ref(true);
const loadError = ref<string | null>(null);

const name = ref("");
const profile = ref(DEFAULT_PROFILE_ID);
const commitUrls = ref("");
const submitting = ref(false);
const submitError = ref<string | null>(null);

function formatDate(value: string): string {
  const date = new Date(value);

  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

async function loadBatches(): Promise<void> {
  loading.value = true;
  loadError.value = null;

  try {
    batches.value = await repository.listPatch2VulnBatches();
  } catch (error) {
    loadError.value = error instanceof Error ? error.message : "Unable to load the batches.";
  } finally {
    loading.value = false;
  }
}

async function submit(): Promise<void> {
  submitting.value = true;
  submitError.value = null;

  try {
    const batch = await repository.createPatch2VulnBatch(
      name.value.trim(),
      profile.value,
      commitUrls.value.split("\n").map((line) => line.trim()).filter(Boolean),
    );

    await router.push(`/patch2vuln/${batch.id}`);
  } catch (error) {
    submitError.value = error instanceof Error ? error.message : "Unable to submit the batch.";
  } finally {
    submitting.value = false;
  }
}

onMounted(loadBatches);
</script>

<template>
  <main class="container py-5">
    <h1>Patch2Vuln batches</h1>
    <p class="text-secondary">
      Analyse several fix commits at once, then review each generated
      record in the editor. Nothing becomes a record until you save it.
    </p>

    <form
      class="card my-4"
      @submit.prevent="submit"
    >
      <div class="card-body">
        <h2 class="h5 card-title">New batch</h2>

        <div class="row g-3">
          <div class="col-md-8">
            <label
              for="batch-name"
              class="form-label"
            >Name</label>
            <input
              id="batch-name"
              v-model="name"
              class="form-control"
              maxlength="128"
              required
            >
          </div>

          <div class="col-md-4">
            <label
              for="batch-profile"
              class="form-label"
            >Record format</label>
            <select
              id="batch-profile"
              v-model="profile"
              class="form-select"
            >
              <option
                v-for="option in SUPPORTED_PROFILES"
                :key="option.id"
                :value="option.id"
              >
                {{ option.label }}
              </option>
            </select>
          </div>

          <div class="col-12">
            <label
              for="batch-urls"
              class="form-label"
            >GitHub commit URLs</label>
            <textarea
              id="batch-urls"
              v-model="commitUrls"
              class="form-control font-monospace"
              rows="6"
              required
              aria-describedby="batch-urls-help"
              placeholder="https://github.com/owner/repo/commit/…"
            />
            <div
              id="batch-urls-help"
              class="form-text"
            >
              One per line, up to 50. Each commit is analysed separately.
            </div>
          </div>
        </div>

        <div
          v-if="submitError"
          class="alert alert-danger mt-3 mb-0"
          role="alert"
        >
          {{ submitError }}
        </div>

        <button
          type="submit"
          class="btn btn-primary mt-3"
          :disabled="submitting"
        >
          {{ submitting ? "Submitting…" : "Analyse" }}
        </button>
      </div>
    </form>

    <h2 class="h5">Batches</h2>

    <div
      v-if="loading"
      class="text-secondary"
    >
      Loading batches…
    </div>

    <div
      v-else-if="loadError"
      class="alert alert-danger"
      role="alert"
    >
      {{ loadError }}
      <button
        type="button"
        class="btn btn-outline-danger btn-sm ms-2"
        @click="loadBatches"
      >
        Retry
      </button>
    </div>

    <p
      v-else-if="batches.length === 0"
      class="text-secondary"
    >
      No batches yet.
    </p>

    <div
      v-else
      class="list-group"
    >
      <RouterLink
        v-for="batch in batches"
        :key="batch.id"
        :to="`/patch2vuln/${batch.id}`"
        class="list-group-item list-group-item-action"
      >
        <div class="d-flex justify-content-between flex-wrap gap-2">
          <span class="fw-semibold">{{ batch.name }}</span>
          <span class="text-secondary small">
            {{ batch.reviewed }} of {{ batch.total }} reviewed
            <template v-if="batch.open"> · {{ batch.open }} still analysing</template>
          </span>
        </div>
        <div class="text-secondary small">
          {{ batch.profile }} · {{ formatDate(batch.createdAt) }}
          <template v-if="batch.createdBy"> · {{ batch.createdBy }}</template>
        </div>
      </RouterLink>
    </div>
  </main>
</template>
