<script setup lang="ts">
import {
  computed,
  onBeforeUnmount,
  onMounted,
  ref,
} from "vue";

import {
  useRoute,
  useRouter,
} from "vue-router";

import {
  HttpRepository,
} from "@/repositories/HttpRepository";

import type {
  CandidateStatus,
  Patch2VulnBatch,
  Patch2VulnCandidate,
} from "@/repositories/HttpRepository";

const REFRESH_SECONDS = 5;

const STATUS_LABELS: Record<CandidateStatus, string> = {
  queued: "Queued",
  running: "Analysing",
  completed: "Ready",
  failed: "Failed",
  canceled: "Canceled",
  expired: "Expired",
};

const route = useRoute();
const router = useRouter();
const repository = new HttpRepository("/api/v1");

const batchId = Number(route.params.batchId);
const batch = ref<Patch2VulnBatch | null>(null);
const loadError = ref<string | null>(null);
const actionError = ref<string | null>(null);
let timer: ReturnType<typeof setTimeout> | undefined;
let active = true;

const isOpen = computed(() => (batch.value?.open ?? 0) > 0);

function commitLabel(url: string): string {
  // owner/repo@abcdef1
  const match = /github\.com\/([^/]+\/[^/]+)\/commit\/([0-9a-f]{7})/i.exec(url);

  return match ? `${match[1]}@${match[2]}` : url;
}

function reviewState(candidate: Patch2VulnCandidate): string | null {
  if (candidate.recordId !== null) return "Record created";
  if (candidate.dismissed) return "Dismissed";

  return null;
}

async function load(): Promise<void> {
  clearTimeout(timer);

  try {
    batch.value = await repository.getPatch2VulnBatch(batchId);
    loadError.value = null;
  } catch (error) {
    loadError.value = error instanceof Error ? error.message : "Unable to load the batch.";
  }

  // Patch2Vuln doesn't notify; ask again while analyses are running.
  if (active && isOpen.value) {
    timer = setTimeout(() => void load(), REFRESH_SECONDS * 1000);
  }
}

async function setDismissed(candidate: Patch2VulnCandidate, dismissed: boolean): Promise<void> {
  actionError.value = null;

  try {
    Object.assign(candidate, await repository.setPatch2VulnCandidateDismissed(candidate.id, dismissed));
  } catch (error) {
    actionError.value = error instanceof Error ? error.message : "Unable to change the candidate.";
  }
}

async function deleteBatch(): Promise<void> {
  if (!batch.value || !window.confirm(
    `Delete the batch "${batch.value.name}"? Running analyses are canceled.`
    + " Records already created stay.",
  )) {
    return;
  }

  actionError.value = null;

  try {
    await repository.deletePatch2VulnBatch(batchId);
    await router.push("/patch2vuln");
  } catch (error) {
    actionError.value = error instanceof Error ? error.message : "Unable to delete the batch.";
  }
}

onMounted(load);

onBeforeUnmount(() => {
  active = false;
  clearTimeout(timer);
});
</script>

<template>
  <main class="container py-5">
    <RouterLink
      to="/patch2vuln"
      class="small"
    >
      ← All batches
    </RouterLink>

    <div
      v-if="loadError && !batch"
      class="alert alert-danger mt-3"
      role="alert"
    >
      {{ loadError }}
    </div>

    <p
      v-else-if="!batch"
      class="text-secondary mt-3"
    >
      Loading…
    </p>

    <template v-else>
      <div class="d-flex justify-content-between align-items-start flex-wrap gap-3 mt-2">
        <div>
          <h1 class="mb-0">{{ batch.name }}</h1>
          <p class="text-secondary mb-0">
            {{ batch.total }} commits · {{ batch.completed }} analysed ·
            {{ batch.reviewed }} reviewed
            <template v-if="isOpen"> · {{ batch.open }} still analysing</template>
          </p>
        </div>

        <button
          type="button"
          class="btn btn-outline-danger"
          @click="deleteBatch"
        >
          Delete batch
        </button>
      </div>

      <div
        v-if="batch.refreshError || loadError"
        class="alert alert-warning mt-3"
        role="status"
      >
        {{ batch.refreshError ?? loadError }}. The statuses below may be out of date.
      </div>

      <div
        v-if="actionError"
        class="alert alert-danger mt-3"
        role="alert"
      >
        {{ actionError }}
      </div>

      <div class="table-responsive mt-4">
        <table class="table align-middle">
          <thead>
            <tr>
              <th scope="col">Commit</th>
              <th scope="col">Generated title</th>
              <th scope="col">Status</th>
              <th scope="col">
                <span class="visually-hidden">Actions</span>
              </th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="candidate in batch.candidates"
              :key="candidate.id"
              :class="{ 'text-secondary': candidate.dismissed }"
            >
              <td>
                <a
                  :href="candidate.commitUrl.replace(/\.patch$/, '')"
                  target="_blank"
                  rel="noopener"
                  class="font-monospace small"
                >{{ commitLabel(candidate.commitUrl) }}</a>
              </td>
              <td>{{ candidate.title ?? "—" }}</td>
              <td>
                {{ reviewState(candidate) ?? STATUS_LABELS[candidate.status] }}
              </td>
              <td class="text-end text-nowrap">
                <RouterLink
                  v-if="candidate.recordId !== null"
                  :to="`/editor/${candidate.recordId}`"
                  class="btn btn-sm btn-outline-primary"
                >
                  Open record
                </RouterLink>

                <template v-else-if="candidate.dismissed">
                  <button
                    type="button"
                    class="btn btn-sm btn-outline-secondary"
                    @click="setDismissed(candidate, false)"
                  >
                    Restore
                  </button>
                </template>

                <template v-else-if="candidate.status === 'completed'">
                  <RouterLink
                    :to="{ path: '/editor/new', query: { candidate: candidate.id } }"
                    class="btn btn-sm btn-primary"
                  >
                    Review
                  </RouterLink>
                  <button
                    type="button"
                    class="btn btn-sm btn-outline-secondary ms-2"
                    @click="setDismissed(candidate, true)"
                  >
                    Dismiss
                  </button>
                </template>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>
  </main>
</template>
