<script setup lang="ts">
import {
  computed,
  onMounted,
  ref,
  shallowRef,
  watch,
} from "vue";

import type {
  CveRecord,
  EditorContext,
  PublicationTarget,
} from "../../contracts";

import {
  useCnaPublication,
} from "./use-cna-publication";

import {
  setAtPath,
} from "../../core/changes";

import {
  upstreamDifferences,
} from "./upstream-diff";

import type {
  UpstreamDifference,
} from "./upstream-diff";

import {
  getGcveVulnId,
  recordHasGcveId,
  setGcveVulnId,
} from "../../gcve";

import {
  useEditorContext,
  useEditorSave,
} from "../../core/context";

/*
 * Shared by VulnerabilityLookupPanel.vue and CVEProgramPanel.vue — "vl" and
 * "cve-program" are the same CVE Services API-shaped protocol at a
 * different EditorRepository-resolved target, so one panel body serves
 * both; only `target`/`label` differ between the two call sites.
 *
 * The panel shows what fits the record's state (STATES below): not
 * linked yet (reserve a new ID, or link an existing one), reserved,
 * published, rejected, or an attempt that didn't complete.
 */
const props = defineProps<{
  target: PublicationTarget;
  label: string;
  context: EditorContext;
}>();

const {
  supported,
  pullSupported,
  unlinkSupported,
  upstreamSupported,
  fetchUpstream,
  pull,
  publication,
  loading,
  error,
  notConfigured,
  refresh,
  reserve,
  publish,
  reject,
  abort,
  unlink,
} = useCnaPublication(props.target, props.context);

/*
 * The live record ref — not props.context.record. A reserve on a
 * never-saved record auto-saves first (see use-cna-publication.ts's
 * ensureIdentifier()), and that save points state.record.value at a
 * brand-new object; props.context may not have caught up with that
 * swap by the time applyReservedId() runs.
 */
const editor = useEditorContext();
const requestSave = useEditorSave();

onMounted(async () => {
  if (supported.value && props.context.identifier) {
    await refresh();
    await compareWithUpstream();
  }
});

const status = computed(() => publication.value?.status ?? "LOCAL_ONLY");
const linkedId = computed(() => publication.value?.cveId ?? null);

/** "GCVE ID" for Vulnerability-Lookup, "CVE ID" for the CVE Program. */
const idKind = computed(() => props.target === "vl" ? "GCVE ID" : "CVE ID");

interface StateText {
  title: string;
  detail?: string;
  tone: "secondary" | "primary" | "success" | "danger" | "warning";
}

const STATES: Record<string, (id: string, label: string) => StateText> = {
  LOCAL_ONLY: (_id, label) => ({ title: `Not on ${label} yet`, tone: "secondary" }),
  RESERVATION_PENDING: () => ({
    title: "Reserving didn't complete",
    detail: "Try again, or link the ID if it was reserved after all.",
    tone: "warning",
  }),
  RESERVED: () => ({ title: "Reserved, not published yet", tone: "primary" }),
  PUBLICATION_PENDING: () => ({
    title: "Publishing didn't complete",
    detail: "Try again; Check shows what arrived.",
    tone: "warning",
  }),
  PUBLISHED: (_id, label) => ({ title: `Published on ${label}`, tone: "success" }),
  REJECTION_PENDING: () => ({
    title: "Rejecting didn't complete",
    detail: "Try again; Check shows what arrived.",
    tone: "warning",
  }),
  REJECTED: (_id, label) => ({ title: `Rejected on ${label}`, tone: "danger" }),
  ABORTED: () => ({
    title: "No longer tracked",
    detail: "Start over to reserve or link an ID again.",
    tone: "secondary",
  }),
};

const stateText = computed(() =>
  (STATES[status.value] ?? STATES.LOCAL_ONLY!)(linkedId.value ?? "", props.label));

const isLinked = computed(() => Boolean(linkedId.value) && status.value !== "ABORTED");

/*
 * "vl" reserves a GCVE identifier — a record that already has one
 * (e.g. assembled elsewhere, or after Stop tracking) must not reserve a
 * second one; it can be linked instead. Doesn't apply to "cve-program":
 * a record can hold both a GCVE ID and a CVE ID.
 */
const alreadyHasGcveId = computed(() =>
  props.target === "vl" && recordHasGcveId(editor.record.value ?? {}));

/*
 * Whether the reserved ID made it onto the record — false when the
 * follow-up apply+save after a reserve was interrupted. The backend
 * already has it RESERVED, so the panel offers to finish the job.
 */
const reservedIdApplied = computed(() => {
  const reservedId = linkedId.value;
  const record = editor.record.value as CveRecord | null;

  return !reservedId || (record !== null && recordId(record, reservedId) === reservedId);
});

const canReserve = computed(() =>
  ["LOCAL_ONLY", "RESERVATION_PENDING"].includes(status.value) && !alreadyHasGcveId.value);

const canReject = computed(() =>
  ["RESERVED", "PUBLISHED", "REJECTION_PENDING"].includes(status.value));

/** The main action's label once linked, by state. */
const publishLabel = computed(() => ({
  RESERVED: `Publish to ${props.label}`,
  PUBLICATION_PENDING: "Try publishing again",
  PUBLISHED: "Publish update",
  REJECTED: "Publish again",
}[status.value] ?? null));

function formatDate(value: string | null | undefined): string | null {
  if (!value) {
    return null;
  }

  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
}

/*
 * The ID's way through upstream: Reserved → Published → Rejected. A step
 * is done (with its date), the one the last attempt failed at, skipped
 * (rejected without being published), or still ahead.
 */
interface TimelineStep {
  label: string;
  state: "done" | "failed" | "skipped" | "ahead";
  date: string | null;
}

const timeline = computed<TimelineStep[]>(() => {
  const entry = publication.value;
  const now = status.value;
  const rejected = now === "REJECTED";

  const step = (
    label: string,
    date: string | null | undefined,
    done: boolean,
    failedAt: string,
  ): TimelineStep => ({
    label,
    date: formatDate(date),
    state: now === failedAt ? "failed" : done ? "done" : "ahead",
  });

  const published = step("Published", entry?.publishedAt, Boolean(entry?.publishedAt), "PUBLICATION_PENDING");

  return [
    step("Reserved", entry?.reservedAt, Boolean(entry?.cveId), "RESERVATION_PENDING"),
    rejected && !entry?.publishedAt ? { ...published, state: "skipped" } : published,
    step("Rejected", entry?.rejectedAt, rejected, "REJECTION_PENDING"),
  ];
});

// After the first publication: when the last update went out.
const lastUpdate = computed(() => {
  const entry = publication.value;
  return status.value === "PUBLISHED" && entry?.lastSentAt && entry.lastSentAt !== entry.publishedAt
    ? formatDate(entry.lastSentAt)
    : null;
});

/*
 * Where an ID like `id` lives on the record: a GCVE ID from "vl" in
 * x_gcve[].vulnId, any other ID in cveMetadata.cveId (also where the
 * backend looks before publishing).
 */
function isGcveForThisTarget(id: string): boolean {
  return props.target === "vl" && id.toUpperCase().startsWith("GCVE-");
}

function recordId(record: CveRecord, id: string): string | undefined {
  return isGcveForThisTarget(id) ? getGcveVulnId(record) : record.cveMetadata?.cveId;
}

function applyId(record: CveRecord, id: string): void {
  if (isGcveForThisTarget(id)) {
    setGcveVulnId(record, id);
  } else {
    record.cveMetadata ??= {};
    record.cveMetadata.cveId = id;
  }
}

/** Puts the linked ID onto the record; whether there was one. */
function applyReservedId(): boolean {
  if (!linkedId.value || !editor.record.value) {
    return false;
  }

  applyId(editor.record.value as CveRecord, linkedId.value);

  return true;
}

async function handleReserve(): Promise<void> {
  // Guards against a double-click starting a second reserve sequence.
  if (loading.value) {
    return;
  }

  loading.value = true;

  try {
    // Resuming an interrupted attempt: the backend already reserved an
    // ID, it just never made it onto the record.
    if (status.value !== "RESERVED") {
      await reserve(new Date().getFullYear());
    }

    // A real (non-silent) save: persists the ID, and for a record just
    // auto-saved for the first time, lets the host page update its URL.
    if (applyReservedId()) {
      await requestSave();
    }
  } finally {
    loading.value = false;
  }
}

/*
 * Linking an existing upstream ID: the backend links it and takes over
 * its state; its content (once published) lands here as unsaved
 * changes, marked like any edit, for the user to review and save.
 */
const pullId = ref("");
const notice = ref<string | null>(null);

// A record that already carries an ID of this kind (and isn't linked)
// offers it for linking.
watch(
  () => [editor.record.value, isLinked.value] as const,
  ([record, linked]) => {
    if (linked || pullId.value || !record) {
      return;
    }

    const own = props.target === "vl"
      ? getGcveVulnId(record as CveRecord)
      : (record as CveRecord).cveMetadata?.cveId;

    if (own) {
      pullId.value = own;
    }
  },
  { immediate: true },
);

async function handlePull(): Promise<void> {
  const id = pullId.value.trim();

  if (!id || !editor.record.value) {
    return;
  }

  notice.value = null;
  const upstream = await pull(id);

  if (upstream === undefined || !linkedId.value || !editor.record.value) {
    return;
  }

  const linked = linkedId.value;
  const record = plainCopy(editor.record.value) as CveRecord;

  if (upstream?.containers?.cna && window.confirm(
    `Replace this record's content with ${linked} as published on ${props.label}?`
    + " You can review the changes before saving.",
  )) {
    record.containers ??= {};
    record.containers.cna = plainCopy(upstream.containers.cna);
    const state = upstream.cveMetadata?.state;
    if (state === "PUBLISHED" || state === "REJECTED") {
      record.cveMetadata ??= {};
      record.cveMetadata.state = state;
    }
  }

  applyId(record, linked);
  editor.record.value = record;
  pullId.value = "";
  notice.value = `Linked to ${linked}. Review the changes and save.`;
}

// "Review the changes and save" is done once the record is saved.
watch(
  () => editor.dirty.value,
  (dirty) => {
    if (!dirty) {
      notice.value = null;
    }
  },
);

/** Asks upstream for the linked ID's state; the content stays as it is. */
/*
 * The published record, read when the panel opens, after publishing and
 * on Check; the comparison follows local edits live from it.
 */
const published = shallowRef<CveRecord | null>(null);
const compareError = ref<string | null>(null);
const showDifferences = ref(false);

async function compareWithUpstream(): Promise<void> {
  published.value = null;
  compareError.value = null;

  if (!upstreamSupported.value || status.value !== "PUBLISHED") {
    return;
  }

  const result = await fetchUpstream();

  if (typeof result === "string") {
    compareError.value = result;
  } else {
    published.value = result;
  }
}

const differences = computed(() =>
  published.value && editor.record.value && status.value === "PUBLISHED"
    ? upstreamDifferences(editor.record.value as CveRecord, published.value)
    : null);

/** A value as text: in full for the tooltip, shortened for the table. */
function full(value: unknown): string {
  return typeof value === "string" ? value : JSON.stringify(value);
}

function shown(value: unknown): string {
  const text = full(value);
  return text.length > 80 ? `${text.slice(0, 79)}…` : text;
}

// For buttons: "Use VL's", "Use CVE's".
const shortLabel = computed(() => props.target === "vl" ? "VL" : "CVE");

// Records are plain JSON, but after form edits they hold nested Vue
// proxies, which structuredClone (even after toRaw) can't copy.
function plainCopy<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

/*
 * Taking over upstream's version: it lands in the editor as unsaved
 * changes (marked like any edit), so nothing changes until Save.
 */
function useUpstreamValue(difference: UpstreamDifference): void {
  if (!editor.record.value) {
    return;
  }

  const record = plainCopy(editor.record.value) as Record<string, unknown>;
  setAtPath(record, difference.path, difference.published);
  editor.record.value = record as CveRecord;
}

function useUpstreamRecord(): void {
  if (!published.value || !window.confirm(
    `Replace the whole record with the version published on ${props.label}?`
    + " Your other unsaved changes are replaced too; nothing is saved until you click Save.",
  )) {
    return;
  }

  editor.record.value = plainCopy(published.value);
  notice.value = `Took over the version from ${props.label}. Review the changes and save.`;
}

async function handlePublish(): Promise<void> {
  await publish();
  await compareWithUpstream();
}

async function handleCheck(): Promise<void> {
  if (!linkedId.value) {
    return;
  }

  notice.value = null;

  if (await pull(linkedId.value) !== undefined) {
    notice.value = `${props.label}: ${stateText.value.title.toLowerCase()}.`;
  }

  await compareWithUpstream();
}

async function handleStopTracking(): Promise<void> {
  const what = linkedId.value ?? "this record";

  if (!window.confirm(
    `Stop tracking ${what}? It stays on ${props.label}; Vulniverse only`
    + " forgets the link, and this record can reserve or link an ID again.",
  )) {
    return;
  }

  notice.value = null;
  await (unlinkSupported.value ? unlink() : abort());
}

const showRejectForm = ref(false);
const rejectReason = ref("");

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
      <!-- Where the record stands -->
      <div class="mb-3">
        <div class="d-flex flex-wrap align-items-center gap-2">
          <span
            class="cna-dot"
            :class="`bg-${stateText.tone}`"
            aria-hidden="true"
          />
          <strong>{{ stateText.title }}</strong>
          <code
            v-if="isLinked"
            class="small"
          >{{ linkedId }}</code>
        </div>
        <ol
          v-if="isLinked"
          class="cna-timeline mt-3 mb-2"
          :aria-label="`${linkedId} on ${label}`"
        >
          <li
            v-for="step in timeline"
            :key="step.label"
            :class="`cna-timeline-${step.state}`"
          >
            <span class="cna-timeline-mark" />
            <span class="cna-timeline-label">{{ step.label }}</span>
            <span class="cna-timeline-date">
              {{ step.state === "failed" ? "didn't complete" : step.state === "skipped" ? "skipped" : step.date }}
            </span>
          </li>
        </ol>
        <div
          v-if="lastUpdate"
          class="small text-secondary"
        >
          Last update sent {{ lastUpdate }}
        </div>
        <div
          v-if="differences"
          class="mt-3"
        >
          <p
            v-if="!differences.length"
            class="small text-success mb-0"
          >
            Matches the published version on {{ label }}.
          </p>
          <template v-else>
            <div class="d-flex flex-wrap align-items-center gap-2">
              <span class="small fw-semibold text-warning-emphasis">
                Differs from the published version:
                {{ differences.length }} {{ differences.length === 1 ? "field" : "fields" }}
              </span>
              <button
                type="button"
                class="btn btn-outline-secondary btn-sm"
                :aria-expanded="showDifferences"
                aria-controls="cna-differences"
                @click="showDifferences = !showDifferences"
              >
                {{ showDifferences ? "Hide" : "Show" }} differences
              </button>
              <button
                v-if="showDifferences"
                type="button"
                class="btn btn-outline-secondary btn-sm ms-auto"
                @click="useUpstreamRecord()"
              >
                Use all from {{ shortLabel }}
              </button>
            </div>
            <div
              v-if="showDifferences"
              id="cna-differences"
              class="table-responsive mt-2"
            >
              <table class="table table-sm small align-middle mb-0">
                <thead>
                  <tr>
                    <th scope="col">
                      Field
                    </th>
                    <th scope="col">
                      This record
                    </th>
                    <th scope="col">
                      {{ label }}
                    </th>
                    <th scope="col">
                      <span class="visually-hidden">Actions</span>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="difference in differences"
                    :key="difference.path"
                  >
                    <td>
                      <code class="cna-diff-path">{{ difference.path }}</code>
                    </td>
                    <td :title="difference.local === undefined ? 'Not set' : full(difference.local)">
                      <span
                        v-if="difference.local === undefined"
                        class="text-secondary"
                      >—</span>
                      <template v-else>
                        {{ shown(difference.local) }}
                      </template>
                    </td>
                    <td :title="difference.published === undefined ? 'Not set' : full(difference.published)">
                      <span
                        v-if="difference.published === undefined"
                        class="text-secondary"
                      >—</span>
                      <template v-else>
                        {{ shown(difference.published) }}
                      </template>
                    </td>
                    <td class="text-end text-nowrap">
                      <button
                        type="button"
                        class="btn btn-outline-secondary btn-sm"
                        :aria-label="`Show ${difference.path} in the editor`"
                        @click="editor.revealPath(difference.path)"
                      >
                        Show
                      </button>
                      <button
                        type="button"
                        class="btn btn-outline-primary btn-sm ms-1"
                        :aria-label="`Use ${shortLabel}'s value for ${difference.path}`"
                        @click="useUpstreamValue(difference)"
                      >
                        Use {{ shortLabel }}'s
                      </button>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </template>
        </div>
        <div
          v-else-if="compareError"
          class="small text-secondary mt-2"
        >
          Couldn't compare with {{ label }}: {{ compareError }}
        </div>
        <div
          v-if="stateText.detail"
          class="small text-secondary mt-1"
        >
          {{ stateText.detail }}
        </div>
      </div>

      <div
        v-if="error"
        class="alert alert-danger small"
        role="alert"
      >
        {{ error }}
      </div>

      <div
        v-else-if="publication?.lastError && status.endsWith('_PENDING')"
        class="alert alert-warning small"
      >
        {{ publication.lastError }}
      </div>

      <div
        v-if="notice"
        class="alert alert-info small"
        role="status"
      >
        {{ notice }}
      </div>

      <!-- Not linked: a new ID, or one that exists already -->
      <div
        v-if="['LOCAL_ONLY', 'RESERVATION_PENDING'].includes(status)"
        class="row g-3"
      >
        <div class="col-md-6">
          <div class="small fw-semibold mb-1">
            New vulnerability?
          </div>
          <button
            type="button"
            class="btn btn-primary btn-sm"
            :disabled="!canReserve || loading"
            @click="handleReserve()"
          >
            {{ status === "RESERVATION_PENDING" ? "Try reserving again" : `Reserve a ${idKind}` }}
          </button>
          <div
            v-if="alreadyHasGcveId"
            class="form-text"
          >
            This record already has a GCVE ID; link it instead.
          </div>
        </div>

        <form
          v-if="pullSupported"
          class="col-md-6"
          @submit.prevent="handlePull"
        >
          <label
            for="cna-pull-id"
            class="small fw-semibold mb-1 d-block"
          >Already has an ID on {{ label }}?</label>
          <div class="input-group input-group-sm">
            <input
              id="cna-pull-id"
              v-model="pullId"
              class="form-control"
              :placeholder="target === 'vl' ? 'GCVE-…' : 'CVE-…'"
              required
            >
            <button
              type="submit"
              class="btn btn-outline-primary"
              :disabled="loading"
            >
              Link
            </button>
          </div>
          <div class="form-text">
            Takes over its status, and its content once published.
          </div>
        </form>

        <p
          v-if="!context.identifier"
          class="col-12 small text-secondary mb-0"
        >
          Either saves this record first.
        </p>
      </div>

      <!-- Linked -->
      <template v-else-if="isLinked">
        <div
          v-if="status === 'RESERVED' && !reservedIdApplied"
          class="alert alert-warning small d-flex flex-wrap align-items-center gap-2"
        >
          {{ linkedId }} isn't in the record yet.
          <button
            type="button"
            class="btn btn-warning btn-sm"
            :disabled="loading"
            @click="handleReserve()"
          >
            Add it and save
          </button>
        </div>

        <div class="d-flex flex-wrap align-items-center gap-2">
          <button
            v-if="publishLabel"
            type="button"
            class="btn btn-primary btn-sm"
            :disabled="loading"
            @click="handlePublish()"
          >
            {{ publishLabel }}
          </button>

          <button
            v-if="canReject"
            type="button"
            class="btn btn-outline-danger btn-sm"
            :disabled="loading"
            :aria-expanded="showRejectForm"
            @click="showRejectForm = !showRejectForm"
          >
            {{ status === "REJECTION_PENDING" ? "Try rejecting again…" : "Reject…" }}
          </button>

          <span class="ms-auto d-flex gap-1">
            <button
              v-if="pullSupported"
              type="button"
              class="btn btn-link btn-sm text-decoration-none"
              :disabled="loading"
              :title="`Ask ${label} for this ID's current status`"
              @click="handleCheck()"
            >
              Check with {{ target === "vl" ? "VL" : label }}
            </button>
            <button
              type="button"
              class="btn btn-link btn-sm text-secondary text-decoration-none"
              :disabled="loading"
              @click="handleStopTracking()"
            >
              Stop tracking
            </button>
          </span>
        </div>

        <div
          v-if="showRejectForm"
          class="mt-3"
        >
          <label
            for="cna-reject-reason"
            class="form-label small"
          >
            Why is {{ linkedId }} rejected? (sent to {{ label }})
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
            Reject {{ linkedId }}
          </button>
        </div>
      </template>

      <!-- Stopped tracking the old way (ABORTED): start over -->
      <button
        v-else-if="status === 'ABORTED' && unlinkSupported"
        type="button"
        class="btn btn-outline-primary btn-sm"
        :disabled="loading"
        @click="unlink()"
      >
        Start over
      </button>
    </template>
  </div>
</template>
