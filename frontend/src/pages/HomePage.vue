<script setup lang="ts">
import {
  onMounted,
  ref,
} from "vue";

import {
  HttpRepository,
} from "@/repositories/HttpRepository";

import type {
  RecordSummary,
} from "@/repositories/HttpRepository";

import {
  SUPPORTED_PROFILES,
} from "@/editor/profiles";

const repository = new HttpRepository("/api/v1");

function kindLabelFor(
  profileId: string,
): string {
  return (
    SUPPORTED_PROFILES.find((profile) => profile.id === profileId)?.label
    ?? profileId
  );
}

const records = ref<RecordSummary[]>([]);
const loading = ref(true);
const loadError = ref<Error | null>(null);

function formatDate(
  value: string,
): string {
  const date = new Date(value);

  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleString(undefined, {
      dateStyle: "medium",
      timeStyle: "short",
    });
}

async function loadRecords(): Promise<void> {
  loading.value = true;
  loadError.value = null;

  try {
    records.value = await repository.listRecords();
  } catch (error) {
    loadError.value = error instanceof Error
      ? error
      : new Error("Unable to load records.");
  } finally {
    loading.value = false;
  }
}

onMounted(loadRecords);
</script>

<template>
  <main class="container py-5">
    <h1>Vulniverse</h1>

    <p>
      <RouterLink
        to="/editor/new"
        class="btn btn-primary"
      >
        Create new record
      </RouterLink>
    </p>

    <h2 class="h4 mt-5">Records</h2>

    <div
      v-if="loading"
      class="text-secondary"
    >
      Loading records…
    </div>

    <div
      v-else-if="loadError"
      class="alert alert-danger"
      role="alert"
    >
      {{ loadError.message }}

      <button
        type="button"
        class="btn btn-outline-danger btn-sm ms-2"
        @click="loadRecords"
      >
        Retry
      </button>
    </div>

    <p
      v-else-if="records.length === 0"
      class="text-secondary"
    >
      No records yet.
    </p>

    <div
      v-else
      class="list-group"
    >
      <RouterLink
        v-for="record in records"
        :key="record.identifier"
        :to="`/editor/${record.identifier}`"
        class="list-group-item list-group-item-action d-flex
               justify-content-between align-items-center"
      >
        <span>
          <span class="fw-semibold">{{ record.identifier }}</span>

          <span class="badge text-bg-primary ms-2">
            {{ kindLabelFor(record.profile) }}
          </span>

          <span class="badge text-bg-secondary ms-1">
            {{ record.profile }}
          </span>

          <span
            v-if="record.isDraft"
            class="badge text-bg-warning ms-1"
          >
            Draft
          </span>
        </span>

        <span class="text-secondary small">
          {{ formatDate(record.updatedAt) }}
        </span>
      </RouterLink>
    </div>
  </main>
</template>
