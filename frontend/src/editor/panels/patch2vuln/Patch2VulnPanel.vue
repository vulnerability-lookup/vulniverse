<script setup lang="ts">
import {
  computed,
  onBeforeUnmount,
  onMounted,
  ref,
  shallowRef,
} from "vue";

import type {
  CveRecord,
  EditorContext,
  Patch2VulnJob,
  GcveExtension,
} from "../../contracts";

import {
  useEditorRepository,
} from "../../core/context";


const props = defineProps<{
  context: EditorContext;
}>();

const repository = useEditorRepository();

const supported = computed(() =>
  Boolean(
    repository.value?.submitPatch2VulnJob &&
    repository.value?.getPatch2VulnJob,
  ),
);


// Input state
const commitUrls = ref("");
const files = ref<File[]>([]);

const vendor = ref("");
const product = ref("");
const affectedVersion = ref("");
const fixedVersion = ref("");
const versionType = ref("");


// Job state
const job = shallowRef<Patch2VulnJob | null>(null);
const submitting = ref(false);
const error = ref<string | null>(null);
const message = ref<string | null>(null);

let pollTimer: ReturnType<typeof setTimeout> | undefined;
let mounted = false;
let unsubscribeJobEvents: (() => void) | null = null;


// Persist the current job when switching panels.
const storageKey = computed(
  () => `patch2vuln:${props.context.identifier ?? "unsaved"}`,
);


const generatedRecord = computed(
  () => job.value?.status === "completed"
    ? job.value.result?.record
    : undefined,
);


const isRunning = computed(
  () =>
    submitting.value ||
    job.value?.status === "queued" ||
    job.value?.status === "running",
);


// Supported CNA fields for selective merging.
const FIELDS = [
  { id: "title", label: "Title" },
  { id: "descriptions", label: "Descriptions" },
  { id: "affected", label: "Affected products" },
  { id: "problemTypes", label: "CWE classifications" },
  { id: "metrics", label: "CVSS metrics" },
  { id: "solutions", label: "Solutions" },
  { id: "references", label: "References" },
  { id: "impacts", label: "Impacts / CAPEC" },
  { id: "credits", label: "Credits" },
  { id: "cpeApplicability", label: "CPE applicability" },
  { id: "x_gcve", label: "GCVE metadata / AI provenance" },
] as const;

const PROTECTED_FIELDS = new Set([
  "providerMetadata",
  "datePublic",
  "dateUpdated",
  "dateAssigned",
  "rejectedReasons",
  "replacedBy",
]);

const selectedFields = ref<string[]>(
  FIELDS.map((field) => field.id),
);

// handle gcve extensions
function mergeGeneratedGcve(
  current: CveRecord,
  generated: CveRecord,
): boolean {
  const sourceEntries = generated.containers?.cna?.x_gcve;

  if (!Array.isArray(sourceEntries) || sourceEntries.length === 0) {
    return false;
  }

  current.containers ??= {};
  current.containers.cna ??= {};

  const cna = current.containers.cna;

  // Always use containers.cna.x_gcve, regardless of profile.
  const entries: GcveExtension[] = Array.isArray(cna.x_gcve)
    ? cna.x_gcve as GcveExtension[]
    : [];

  // Prefer the existing assigned GCVE identifier.
  const assignedId = [
    current.cveMetadata?.vulnId,
    entries[0]?.vulnId,
    current.x_gcve?.[0]?.vulnId,
  ].find(
    (id) =>
      typeof id === "string" &&
      /^GCVE-\d+-\d{4}-\d+$/.test(id),
  );

  for (const source of sourceEntries as GcveExtension[]) {
    const incoming = JSON.parse(
      JSON.stringify(source),
    ) as GcveExtension;

    if (assignedId) {
      incoming.vulnId = assignedId;
    }

    // Find an existing entry of the same record type.
    const existing = entries.find(
      (entry) =>
        entry.vulnId === incoming.vulnId &&
        entry.recordType === incoming.recordType,
    );

    if (!existing) {
      // No existing entry: include the complete generated entry.
      entries.push(incoming);
      continue;
    }

    // Preserve existing GCVE metadata and unrelated extensions.
    const oldExtensions =
      existing.extensions &&
      typeof existing.extensions === "object" &&
      !Array.isArray(existing.extensions)
        ? existing.extensions as Record<string, unknown>
        : {};

    const newExtensions =
      incoming.extensions &&
      typeof incoming.extensions === "object" &&
      !Array.isArray(incoming.extensions)
        ? incoming.extensions as Record<string, unknown>
        : {};

    existing.extensions = {
      ...oldExtensions,
      ...newExtensions,
    };
  }

  cna.x_gcve = entries;

  return true;
}

// Handle uploaded files.
function onFileChange(event: Event): void {
  const input = event.target as HTMLInputElement;

  files.value = Array.from(input.files ?? []);
}


// Stop polling without canceling the background job.
function stopPolling(): void {
  if (pollTimer !== undefined) {
    clearTimeout(pollTimer);
    pollTimer = undefined;
  }
}

// function for SSE
function stopWatchingJob(): void {
  unsubscribeJobEvents?.();
  unsubscribeJobEvents = null;

  stopPolling();
}

async function refreshJob(jobId: string): Promise<void> {
  if (!repository.value?.getPatch2VulnJob) {
    return;
  }

  try {
    const result =
      await repository.value.getPatch2VulnJob(jobId);

    if (!mounted || job.value?.jobId !== jobId) {
      return;
    }

    job.value = result;
    error.value = null;

    // Normally this won't happen because the worker
    // publishes only after persisting the result.
    // Reconnect if the job isn't terminal yet.
    if (
      result.status === "queued" ||
      result.status === "running"
    ) {
      startWatchingJob(jobId);
    }

  } catch (err) {
    if (!mounted || job.value?.jobId !== jobId) {
      return;
    }

    error.value = err instanceof Error
      ? err.message
      : "Could not retrieve the job result.";
  }
}

function startWatchingJob(jobId: string): void {
  stopWatchingJob();

  const repo = repository.value;

  if (!repo) {
    return;
  }

  // Compatibility with embedding hosts without SSE.
  if (!repo.subscribeJobEvents) {
    void pollJob();
    return;
  }

  unsubscribeJobEvents = repo.subscribeJobEvents(
    jobId,

    (event) => {
      if (
        !mounted ||
        job.value?.jobId !== jobId ||
        event.jobId !== jobId
      ) {
        return;
      }

      error.value = null;

      if (
        event.status === "completed" ||
        event.status === "failed"
      ) {
        // Update status immediately.
        job.value = {
          jobId,
          status: event.status,
        };

        // Close the stream.
        stopWatchingJob();

        // Fetch the actual result once.
        void refreshJob(jobId);

        return;
      }

      // job uses shallowRef(), so replace the object.
      job.value = {
        ...job.value,
        status: event.status,
      };
    },

    () => {
      if (!mounted || job.value?.jobId !== jobId) {
        return;
      }

      error.value =
        "Live updates disconnected. Reconnecting...";
    },
  );
}


// Retrieve the current job status.
async function pollJob(): Promise<void> {
  if (
    !job.value?.jobId ||
    !repository.value?.getPatch2VulnJob
  ) {
    return;
  }

  const jobId = job.value.jobId;

  try {
    const result =
      await repository.value.getPatch2VulnJob(jobId);

    if (!mounted || job.value?.jobId !== jobId) {
      return;
    }

    job.value = result;

    if (
      result.status === "queued" ||
      result.status === "running"
    ) {
      pollTimer = setTimeout(
        () => void pollJob(),
        2000,
      );
    }
  } catch (err) {
    if (mounted) {
      error.value = err instanceof Error
        ? err.message
        : "Could not retrieve analysis status.";
    }
  }
}


// Submit a new analysis job.
async function submit(): Promise<void> {
  if (!repository.value?.submitPatch2VulnJob) {
    return;
  }

  //stopPolling();
  stopWatchingJob();

  submitting.value = true;
  error.value = null;
  message.value = null;
  job.value = null;

  const urls = commitUrls.value
    .split("\n")
    .map((url) => url.trim())
    .filter(Boolean);

  try {
    const result =
      await repository.value.submitPatch2VulnJob({
        commitUrls: urls,
        files: files.value,

        context: {
          vendor: vendor.value,
          product: product.value,
          affectedVersion: affectedVersion.value,
          fixedVersion: fixedVersion.value,
          versionType: versionType.value,
        },
      });

    sessionStorage.setItem(
      storageKey.value,
      result.jobId,
    );

    if (mounted) {
      job.value = result;
      //void pollJob();
      startWatchingJob(result.jobId);
    }
  } catch (err) {
    if (mounted) {
      error.value = err instanceof Error
        ? err.message
        : "Could not submit patch analysis.";
    }
  } finally {
    submitting.value = false;
  }
}


// Apply selected generated fields to the live editor record.
function applyResult(): void {
  const generated = generatedRecord.value;

  if (!generated?.containers?.cna) {
    error.value = "No generated CNA container available.";
    return;
  }

  const current = props.context.record as CveRecord;

  if (current.cveMetadata?.state === "REJECTED") {
    error.value = "Cannot modify a rejected record.";
    return;
  }

  current.containers ??= {};
  current.containers.cna ??= {};

  const source = generated.containers.cna;
  const target = current.containers.cna;

  let count = 0;

  for (const field of selectedFields.value) {
    // Handle GCVE metadata independently.
    if (field === "x_gcve") {
      if (mergeGeneratedGcve(current, generated)) {
        count++;
      }

      continue;
    }

    // Do not overwrite provider or lifecycle metadata.
    if (PROTECTED_FIELDS.has(field)) {
      continue;
    }

    if (!Object.prototype.hasOwnProperty.call(source, field)) {
      continue;
    }

    const value = source[field];

    if (value === undefined) {
      continue;
    }

    // Works with Vue proxies and creates missing fields.
    target[field] = JSON.parse(JSON.stringify(value));

    count++;
  }

  message.value = `Applied ${count} field(s) to the editor.`;
  error.value = null;
}


// Resume polling when reopening the panel.
onMounted(() => {
  mounted = true;

  const savedJobId = sessionStorage.getItem(
    storageKey.value,
  );

  if (savedJobId) {
    job.value = {
      jobId: savedJobId,
      status: "queued",
    };

    // void pollJob();
    startWatchingJob(savedJobId);
  }
});

onBeforeUnmount(() => {
  mounted = false;
  //stopPolling();
  stopWatchingJob();
});
</script>

<template>
  <section class="p-3">
    <h4>Patch2Vuln</h4>

    <p class="text-secondary">
      Analyze security patches and generate vulnerability information.
      Generated data must be reviewed before publication.
    </p>

    <div
      v-if="!supported"
      class="alert alert-warning"
    >
      Patch2Vuln is not supported by this host.
    </div>

    <template v-else>
      <div class="mb-3">
        <label class="form-label">
          GitHub commit URLs
        </label>

        <textarea
          v-model="commitUrls"
          class="form-control"
          rows="3"
          placeholder="https://github.com/owner/repo/commit/..."
          :disabled="isRunning"
        />

        <div class="form-text">
          One URL per line. Multiple commits must relate
          to the same vulnerability.
        </div>
      </div>

      <div class="mb-3">
        <label class="form-label">
          Patch files
        </label>

        <input
          type="file"
          class="form-control"
          accept=".patch,.diff"
          multiple
          :disabled="isRunning"
          @change="onFileChange"
        >
      </div>

      <hr>

      <h6>Additional context (optional)</h6>

      <div class="mb-3">
        <label class="form-label">Vendor</label>

        <input
          v-model="vendor"
          class="form-control"
          :disabled="isRunning"
        >
      </div>

      <div class="mb-3">
        <label class="form-label">Product</label>

        <input
          v-model="product"
          class="form-control"
          :disabled="isRunning"
        >
      </div>

      <div class="row mb-3">
        <div class="col-md-6">
          <label class="form-label">
            Affected version
          </label>

          <input
            v-model="affectedVersion"
            class="form-control"
            :disabled="isRunning"
          >
        </div>

        <div class="col-md-6">
          <label class="form-label">
            Fixed version
          </label>

          <input
            v-model="fixedVersion"
            class="form-control"
            :disabled="isRunning"
          >
        </div>
      </div>

      <div class="mb-3">
        <label class="form-label">
          Version type
        </label>

        <select
          v-model="versionType"
          class="form-select"
          :disabled="isRunning"
        >
          <option value="">Automatic</option>
          <option value="semver">SemVer</option>
          <option value="custom">Custom</option>
        </select>
      </div>

      <button
        type="button"
        class="btn btn-primary"
        :disabled="
          isRunning ||
          (!commitUrls.trim() && files.length === 0)
        "
        @click="submit"
      >
        {{ isRunning ? "Analyzing..." : "Analyze patches" }}
      </button>

      <div
        v-if="error"
        class="alert alert-danger mt-3"
      >
        {{ error }}
      </div>

      <div
        v-if="message"
        class="alert alert-success mt-3"
      >
        {{ message }}
      </div>

      <div
        v-if="job"
        class="mt-4"
      >
        <hr>

        <h5>Analysis</h5>

        <p>
          Status:
          <strong>{{ job.status }}</strong>
        </p>

        <div
          v-if="isRunning"
          class="spinner-border spinner-border-sm"
          role="status"
        />

        <div
          v-if="job.status === 'failed'"
          class="alert alert-danger"
        >
          {{ job.error ?? "Analysis failed." }}
        </div>

        <template v-if="generatedRecord">
          <div class="alert alert-success">
            Analysis completed successfully.
          </div>

          <h6>Apply generated information</h6>

          <div
            v-for="field in FIELDS"
            :key="field.id"
            class="form-check"
          >
            <input
              :id="`patch-field-${field.id}`"
              v-model="selectedFields"
              class="form-check-input"
              type="checkbox"
              :value="field.id"
            >

            <label
              class="form-check-label"
              :for="`patch-field-${field.id}`"
            >
              {{ field.label }}
            </label>
          </div>

          <p class="text-secondary small mt-3">
            Selected fields will replace their current values.
            Record identifiers and publication metadata are preserved.
          </p>

          <button
            type="button"
            class="btn btn-success mt-2"
            :disabled="selectedFields.length === 0"
            @click="applyResult"
          >
            Apply selected fields
          </button>

          <details class="mt-4">
            <summary>
              View generated record
            </summary>

            <pre class="border rounded p-3 mt-2">{{
              JSON.stringify(generatedRecord, null, 2)
            }}</pre>
          </details>

          <details
            v-if="job.result?.analysis"
            class="mt-3"
          >
            <summary>
              View analysis details
            </summary>

            <pre class="border rounded p-3 mt-2">{{
              JSON.stringify(job.result.analysis, null, 2)
            }}</pre>
          </details>
        </template>
      </div>
    </template>
  </section>
</template>
