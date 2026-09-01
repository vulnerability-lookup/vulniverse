<script setup lang="ts">
import {
  computed,
  onMounted,
  ref,
} from "vue";

import type {
  EditorModuleContext,
} from "../contracts";

import {
  fetchPublishTargets,
  useCnaPublication,
  type PublicationTarget,
} from "./cna-publication";

/*
 * Shared by VulnerabilityLookupPanel.vue and CVEProgramPanel.vue — "vl" and
 * "cve-program" are the same CVE Services API-shaped protocol at a
 * different configured target, so one panel body serves both; only
 * `target`/`label` differ between the two call sites.
 */
const props = defineProps<{
  target: PublicationTarget;
  label: string;
  context: EditorModuleContext;
}>();

const {
  publication,
  loading,
  error,
  refresh,
  reserve,
  publish,
  reject,
  abort,
} = useCnaPublication(props.target, props.context);

const targetConfigured = ref<boolean | null>(null);
const showRejectForm = ref(false);
const rejectReason = ref("");

onMounted(async () => {
  const targets = await fetchPublishTargets().catch(() => null);

  targetConfigured.value = targets ? Boolean(targets[props.target]?.configured) : null;

  if (targetConfigured.value && props.context.identifier) {
    await refresh();
  }
});

const status = computed(() => publication.value?.status ?? "LOCAL_ONLY");

const canReserve = computed(() =>
  ["LOCAL_ONLY", "RESERVATION_PENDING"].includes(status.value));

const canPublish = computed(() =>
  ["RESERVED", "PUBLICATION_PENDING", "PUBLISHED", "REJECTED"].includes(status.value));

const canReject = computed(() =>
  ["RESERVED", "PUBLISHED", "REJECTION_PENDING"].includes(status.value));

const canAbort = computed(() => status.value !== "ABORTED");

const canUseCveId = computed(() =>
  Boolean(publication.value?.cveId) &&
  props.context.record.cveMetadata?.cveId !== publication.value?.cveId);

const STATUS_BADGE: Record<string, string> = {
  LOCAL_ONLY: "secondary",
  RESERVATION_PENDING: "info",
  RESERVED: "primary",
  PUBLICATION_PENDING: "info",
  PUBLISHED: "success",
  REJECTED: "danger",
  REJECTION_PENDING: "warning",
  ABORTED: "dark",
};

const badgeClass = computed(() => STATUS_BADGE[status.value] ?? "secondary");

function useCveId(): void {
  if (!publication.value?.cveId) {
    return;
  }

  props.context.record.cveMetadata ??= {};
  props.context.record.cveMetadata.cveId = publication.value.cveId;
}

async function submitReject(): Promise<void> {
  if (!rejectReason.value.trim()) {
    return;
  }

  await reject(rejectReason.value.trim());

  showRejectForm.value = false;
  rejectReason.value = "";
}
</script>

<template>
  <div class="p-3">
    <p
      v-if="!context.identifier"
      class="text-secondary"
    >
      Save this record before publishing it to {{ label }}.
    </p>

    <p
      v-else-if="targetConfigured === false"
      class="text-secondary"
    >
      {{ label }} isn't configured on this deployment. An operator needs to
      set <code>[integrations.{{ target }}]</code> in
      <code>config/vulniverse.toml</code>.
    </p>

    <template v-else>
      <div class="d-flex align-items-center gap-2 mb-3">
        <span
          class="badge"
          :class="`text-bg-${badgeClass}`"
        >
          {{ status }}
        </span>

        <span
          v-if="publication?.cveId"
          class="text-secondary small"
        >
          {{ publication.cveId }}
        </span>
      </div>

      <div
        v-if="error"
        class="alert alert-danger small"
      >
        {{ error }}
      </div>

      <div
        v-else-if="publication?.lastError"
        class="alert alert-warning small"
      >
        {{ publication.lastError }}
      </div>

      <div class="d-flex flex-wrap gap-2 mb-3">
        <button
          type="button"
          class="btn btn-primary btn-sm"
          :disabled="!canReserve || loading"
          @click="reserve(new Date().getFullYear())"
        >
          Reserve a CVE ID
        </button>

        <button
          type="button"
          class="btn btn-primary btn-sm"
          :disabled="!canPublish || loading"
          @click="publish()"
        >
          {{ status === "PUBLISHED" ? "Republish" : "Publish" }}
        </button>

        <button
          type="button"
          class="btn btn-outline-danger btn-sm"
          :disabled="!canReject || loading"
          @click="showRejectForm = !showRejectForm"
        >
          Reject
        </button>

        <button
          type="button"
          class="btn btn-outline-secondary btn-sm"
          :disabled="!canAbort || loading"
          @click="abort()"
        >
          Abort
        </button>

        <button
          type="button"
          class="btn btn-outline-secondary btn-sm"
          :disabled="loading"
          @click="refresh()"
        >
          Refresh
        </button>
      </div>

      <div
        v-if="showRejectForm"
        class="mb-3"
      >
        <label
          for="cna-reject-reason"
          class="form-label small"
        >
          Rejection reason
        </label>

        <textarea
          id="cna-reject-reason"
          v-model="rejectReason"
          class="form-control form-control-sm mb-2"
          rows="2"
        />

        <button
          type="button"
          class="btn btn-danger btn-sm"
          :disabled="!rejectReason.trim() || loading"
          @click="submitReject"
        >
          Confirm reject
        </button>
      </div>

      <button
        v-if="canUseCveId"
        type="button"
        class="btn btn-link btn-sm px-0"
        @click="useCveId"
      >
        Use {{ publication?.cveId }} as cveMetadata.cveId
      </button>

      <dl
        v-if="publication"
        class="row small mt-3 mb-0"
      >
        <dt class="col-4">Reserved</dt>
        <dd class="col-8">{{ publication.reservedAt ?? "—" }}</dd>

        <dt class="col-4">Published</dt>
        <dd class="col-8">{{ publication.publishedAt ?? "—" }}</dd>

        <dt class="col-4">Rejected</dt>
        <dd class="col-8">{{ publication.rejectedAt ?? "—" }}</dd>
      </dl>
    </template>
  </div>
</template>
