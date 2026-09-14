<script setup lang="ts">
import {
  computed,
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

const searchText = ref("");
const profileFilter = ref("all");
const statusFilter = ref<"all" | "draft" | "published">("all");

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

const usedProfiles = computed(() => {
  const ids = new Set(records.value.map((record) => record.profile));

  return Array.from(ids);
});

const stats = computed(() => {
  const total = records.value.length;
  const drafts = records.value.filter((record) => record.isDraft).length;

  return {
    total,
    drafts,
    published: total - drafts,
    byProfile: usedProfiles.value.map((profileId) => ({
      profileId,
      label: kindLabelFor(profileId),
      count: records.value.filter((record) => record.profile === profileId).length,
    })),
  };
});

const filteredRecords = computed(() => {
  const text = searchText.value.trim().toLowerCase();

  return records.value.filter((record) => {
    if (text && !record.identifier.toLowerCase().includes(text)) {
      return false;
    }

    if (profileFilter.value !== "all" && record.profile !== profileFilter.value) {
      return false;
    }

    if (statusFilter.value === "draft" && !record.isDraft) {
      return false;
    }

    if (statusFilter.value === "published" && record.isDraft) {
      return false;
    }

    return true;
  });
});
</script>

<template>
  <main class="container py-5">
    <div class="d-flex justify-content-between align-items-start flex-wrap gap-3">
      <h1>Overview</h1>

      <RouterLink
        to="/editor/new"
        class="btn btn-primary"
      >
        Create new record
      </RouterLink>
    </div>

    <div
      v-if="!loading && !loadError"
      class="row g-3 my-4"
    >
      <div class="col-6 col-md-3">
        <div class="card text-center h-100">
          <div class="card-body">
            <div class="fs-3 fw-semibold">{{ stats.total }}</div>
            <div class="text-secondary small">Total records</div>
          </div>
        </div>
      </div>

      <div class="col-6 col-md-3">
        <div class="card text-center h-100">
          <div class="card-body">
            <div class="fs-3 fw-semibold">{{ stats.published }}</div>
            <div class="text-secondary small">Published</div>
          </div>
        </div>
      </div>

      <div class="col-6 col-md-3">
        <div class="card text-center h-100">
          <div class="card-body">
            <div class="fs-3 fw-semibold">{{ stats.drafts }}</div>
            <div class="text-secondary small">Drafts</div>
          </div>
        </div>
      </div>

      <div
        v-for="entry in stats.byProfile"
        :key="entry.profileId"
        class="col-6 col-md-3"
      >
        <div class="card text-center h-100">
          <div class="card-body">
            <div class="fs-3 fw-semibold">{{ entry.count }}</div>
            <div class="text-secondary small">{{ entry.label }}</div>
          </div>
        </div>
      </div>
    </div>

    <div
      v-if="!loading && !loadError && records.length > 0"
      class="row g-2 align-items-center mb-3"
    >
      <div class="col-md-6">
        <input
          v-model="searchText"
          type="search"
          class="form-control"
          placeholder="Search by identifier…"
        >
      </div>

      <div class="col-6 col-md-3">
        <select v-model="profileFilter" class="form-select">
          <option value="all">All profiles</option>
          <option
            v-for="profileId in usedProfiles"
            :key="profileId"
            :value="profileId"
          >
            {{ kindLabelFor(profileId) }}
          </option>
        </select>
      </div>

      <div class="col-6 col-md-3">
        <select v-model="statusFilter" class="form-select">
          <option value="all">All statuses</option>
          <option value="draft">Drafts only</option>
          <option value="published">Published only</option>
        </select>
      </div>
    </div>

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

    <p
      v-else-if="filteredRecords.length === 0"
      class="text-secondary"
    >
      No records match this filter.
    </p>

    <div
      v-else
      class="row g-3"
    >
      <div
        v-for="record in filteredRecords"
        :key="record.identifier"
        class="col-md-6 col-lg-4"
      >
        <RouterLink
          :to="`/editor/${record.identifier}`"
          class="card h-100 text-decoration-none text-body"
        >
          <div class="card-body">
            <div class="d-flex justify-content-between align-items-start">
              <span class="fw-semibold">{{ record.identifier }}</span>

              <span
                v-if="record.isDraft"
                class="badge text-bg-warning"
              >
                Draft
              </span>
            </div>

            <div class="mt-2">
              <span class="badge text-bg-primary">
                {{ kindLabelFor(record.profile) }}
              </span>

              <span class="badge text-bg-secondary ms-1">
                {{ record.profile }}
              </span>
            </div>

            <div class="text-secondary small mt-3">
              <div v-if="record.createdBy">
                Created by {{ record.createdBy }}
              </div>
              <div>
                Updated {{ formatDate(record.updatedAt) }}
              </div>
            </div>
          </div>
        </RouterLink>
      </div>
    </div>
  </main>
</template>
