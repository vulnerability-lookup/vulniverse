<script setup lang="ts">
import {
  computed,
  onMounted,
  ref,
} from "vue";

import type {
  EditorModuleContext,
  GcveExtension,
  PublicationTarget,
} from "../contracts";

import {
  useCnaPublication,
} from "./cna-publication";

import {
  recordHasGcveId,
} from "../gcve";

import {
  useEditorContext,
  useEditorSave,
} from "../core/context";

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

/*
 * The live record ref — not props.context.record. A reserve on a
 * never-saved record auto-saves first (see cna-publication.ts's
 * ensureIdentifier()), and that save calls state.replaceRecord(),
 * which points state.record.value at a BRAND NEW object
 * (structuredClone(loaded.record)), not a mutation of the existing
 * one. props.context is a snapshot computed in VulniverseEditor.ce.vue
 * that isn't guaranteed to have propagated that swap down to this
 * component's props by the time applyReservedId() runs — mutating it
 * risked writing the reserved id onto the old, already-discarded
 * record object while the rest of the editor had already moved on to
 * the new one.
 */
const editor = useEditorContext();
const requestSave = useEditorSave();

const showRejectForm = ref(false);
const rejectReason = ref("");

onMounted(async () => {
  if (supported.value && props.context.identifier) {
    await refresh();
  }
});

const status = computed(() => publication.value?.status ?? "LOCAL_ONLY");

/*
 * "vl" reserves a GCVE identifier — a record that already has one
 * (e.g. assembled elsewhere and pasted/loaded in with its identifier
 * already set) must not be allowed to reserve a second one, even
 * though this target's own publication.status may still read
 * LOCAL_ONLY/RESERVATION_PENDING (no reservation has happened through
 * *this* panel yet). Doesn't apply to "cve-program", which reserves
 * an official CVE ID — a record can legitimately hold both a GCVE ID
 * and a CVE ID.
 */
const alreadyHasGcveId = computed(() =>
  props.target === "vl" && recordHasGcveId(editor.record.value ?? {}));

/*
 * Whether the last-reserved id has actually made it onto the record
 * yet — false right after a reserve() succeeds but the follow-up
 * apply+save (see handleReserve()) hasn't completed, e.g. because a
 * network error, validation failure, or the tab closing interrupted
 * it. When that happens, the *backend* already considers this
 * identifier RESERVED (reserving again would be rejected — a
 * publication can't transition to RESERVED twice), but the record
 * itself never got the id — a stuck state with no way out unless
 * Reserve can still be clicked to finish the job.
 */
const reservedIdApplied = computed(() => {
  const reservedId = publication.value?.cveId;

  return !reservedId
    || editor.record.value?.cveMetadata?.[targetIdField.value] === reservedId;
});

const canReserve = computed(() => {
  if (status.value === "RESERVED") {
    return !reservedIdApplied.value;
  }

  return ["LOCAL_ONLY", "RESERVATION_PENDING"].includes(status.value)
    && !alreadyHasGcveId.value;
});

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

/*
 * Applies whatever CVE/GCVE ID the last reserve() call obtained onto
 * the record — cveMetadata.{{targetIdField}}, plus (for "vl" only)
 * a matching containers.cna.x_gcve entry — automatically, right after
 * reserving. Previously a separate "Use <id> as ..." button the user
 * had to click; folded into reserve itself since there's no reason
 * to reserve an ID and NOT want it applied to the record. Returns
 * whether it actually changed anything, so handleReserve() below only
 * saves again when there's something new to persist.
 */
function applyReservedId(): boolean {
  if (!publication.value?.cveId || !editor.record.value) {
    return false;
  }

  const reservedId = publication.value.cveId;
  const record = editor.record.value;

  record.cveMetadata ??= {};
  record.cveMetadata[targetIdField.value] = reservedId;

  // "vl" reserves a real GCVE identifier (see targetIdField above) —
  // record it in the GCVE-BCP-05 extension too, not only in the
  // non-standard cveMetadata.vulnId convenience field, so the record
  // is actually GCVE-conformant. "cve-program" reserves an official
  // CVE ID, which isn't a valid x_gcve[].vulnId shape at all (its
  // pattern requires "GCVE-..."), so this only applies to "vl".
  if (props.target === "vl") {
    record.containers ??= {};
    record.containers.cna ??= {};
    record.containers.cna.x_gcve ??= [];

    const entries = record.containers.cna.x_gcve as GcveExtension[];
    const alreadyPresent = entries.some((entry) => entry.vulnId === reservedId);

    if (!alreadyPresent) {
      entries.push({ vulnId: reservedId, recordType: "advisory" });
    }
  }

  return true;
}

async function handleReserve(): Promise<void> {
  // Guards against a double-click (or any other overlapping call)
  // starting a second reserve sequence while one is already in
  // flight.
  if (loading.value) {
    return;
  }

  loading.value = true;

  try {
    // Resuming an interrupted attempt (see reservedIdApplied above):
    // the backend already reserved an id for this identifier, it
    // just never made it onto the record. Reserving again would be
    // rejected — a publication can't transition to RESERVED twice —
    // so just finish applying and saving instead.
    if (status.value !== "RESERVED") {
      await reserve(new Date().getFullYear());
    }

    // A real, non-silent save — persists the applied id to the
    // backend right away (rather than leaving it as an uncommitted
    // local change) and, for a record that was just auto-saved for
    // the first time by ensureIdentifier() above, is what correctly
    // triggers the host page's URL update now that the record
    // actually has its final content.
    if (applyReservedId()) {
      await requestSave();
    }
  } finally {
    loading.value = false;
  }
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

      <p
        v-if="!context.identifier"
        class="text-secondary small mb-2"
      >
        Reserving will save this record first.
      </p>

      <p
        v-if="alreadyHasGcveId && ['LOCAL_ONLY', 'RESERVATION_PENDING'].includes(status)"
        class="text-secondary small mb-2"
      >
        This record already has a GCVE identifier — reserving a new one is disabled.
      </p>

      <div class="d-flex flex-wrap gap-2 mb-3">
        <button
          type="button"
          class="btn btn-primary btn-sm"
          :disabled="!canReserve || loading"
          @click="handleReserve()"
        >
          Reserve a CVE ID
        </button>

        <template v-if="context.identifier">
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
        </template>
      </div>

      <div
        v-if="context.identifier && showRejectForm"
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
