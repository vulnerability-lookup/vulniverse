<script setup lang="ts">
import {
  computed,
  onMounted,
  ref,
} from "vue";

import type {
  EditorModuleContext,
  PublicationTarget,
} from "../contracts";

import {
  useCnaPublication,
} from "./cna-publication";

/*
 * Shared by VulnerabilityLookupPanel.vue and CVEProgramPanel.vue — "vl" and
 * "cve-program" are the same CVE Services API-shaped protocol at a
 * different EditorRepository-resolved target, so one panel body serves
 * both; only `target`/`label` differ between the two call sites.
 */
const props = defineProps<{
  target: PublicationTarget;
  label: string;
  context: EditorModuleContext;
}>();

const {
  supported,
  publication,
  loading,
  error,
  notConfigured,
  refresh,
  reserve,
  publish,
  reject,
  abort,
} = useCnaPublication(props.target, props.context);

const showRejectForm = ref(false);
const rejectReason = ref("");

onMounted(async () => {
  if (supported.value && props.context.identifier) {
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

/*
 * "vl" reserves a GCVE identifier (vulnId), not an official CVE ID —
 * VL's own reservation response even leaves cve_id blank for these
 * (see services/cna_publication.py's reserve_cve_id). "cve-program" is
 * the real CVE Services API, where the reserved value genuinely is a
 * cveId. Same `publication.cveId` field either way; only which
 * cveMetadata property it belongs in differs by target.
 */
const targetIdField = computed(() =>
  props.target === "vl" ? "vulnId" : "cveId");

const canUseReservedId = computed(() =>
  Boolean(publication.value?.cveId) &&
  props.context.record.cveMetadata?.[targetIdField.value] !== publication.value?.cveId);

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

function useReservedId(): void {
  if (!publication.value?.cveId) {
    return;
  }

  /* eslint-disable vue/no-mutating-props */
  props.context.record.cveMetadata ??= {};
  props.context.record.cveMetadata[targetIdField.value] = publication.value.cveId;
  /* eslint-enable vue/no-mutating-props */
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
      v-if="!supported"
      class="text-secondary"
    >
      This host doesn't support publishing to {{ label }}.
    </p>

    <p
      v-else-if="!context.identifier"
      class="text-secondary"
    >
      Save this record before publishing it to {{ label }}.
    </p>

    <p
      v-else-if="notConfigured"
      class="text-secondary"
    >
      {{ label }} isn't configured on this deployment.
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
        v-if="canUseReservedId"
        type="button"
        class="btn btn-link btn-sm px-0"
        @click="useReservedId"
      >
        Use {{ publication?.cveId }} as cveMetadata.{{ targetIdField }}
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
