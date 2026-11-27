<script setup lang="ts">
import {
  computed,
  onBeforeUnmount,
  onMounted,
  ref,
  shallowRef,
  watch,
} from "vue";

import type {
  CveRecord,
  EditorContext,
  EditorDocument,
  Patch2VulnJob,
} from "../../contracts";

import {
  stopBackgroundWatch,
  watchInBackground,
} from "./background-watch";

import {
  useEditorContext,
  useEditorRepository,
} from "../../core/context";

import {
  applyCveFields as copyCveFields,
  applyOsvFields as copyOsvFields,
  CVE_FIELDS,
  OSV_FIELDS,
} from "./apply";

import {
  recallJob,
  rememberJob,
} from "./job-storage";

import {
  githubCommit,
  MAX_PATCH_INPUTS,
  repositoryOfCommitUrl,
} from "./commit-url";


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

// Checked as typed, with the backends' rules, instead of after submitting.
const urlLines = computed(() => commitUrls.value.split("\n").map((url) => url.trim()));
const inputProblem = computed(() => {
  const invalid = urlLines.value.flatMap((url, index) => url && !githubCommit(url) ? [index + 1] : []);
  const inputs = urlLines.value.filter(Boolean).length + files.value.length;

  if (invalid.length === 1) return `Line ${invalid[0]} is not a GitHub commit URL.`;
  if (invalid.length > 1) return `Lines ${invalid.join(", ")} are not GitHub commit URLs.`;
  if (inputs > MAX_PATCH_INPUTS) return `${inputs} patches; at most ${MAX_PATCH_INPUTS} per analysis.`;

  return null;
});
const files = ref<File[]>([]);

const vendor = ref("");
const product = ref("");

// Vendor and product follow the first commit URL's owner and repository,
// unless the user typed their own.
const filledVendor = ref("");
const filledProduct = ref("");
// The hint under the fields, while either still holds the URL's value.
const autofilled = computed(() => (
  (vendor.value !== "" && vendor.value === filledVendor.value)
  || (product.value !== "" && product.value === filledProduct.value)
));

watch(commitUrls, (text) => {
  const found = repositoryOfCommitUrl(text.split("\n")[0] ?? "");
  if (!found) {
    return;
  }
  if (vendor.value === filledVendor.value) {
    vendor.value = filledVendor.value = found.owner;
  }
  if (product.value === filledProduct.value) {
    product.value = filledProduct.value = found.repo;
  }
});
const affectedVersion = ref("");
const fixedVersion = ref("");
const versionType = ref("");
// Added to the model's instructions, e.g. what to focus on.
const prompt = ref("");
const packageUrl = ref("");

// OSV records apply patch2vuln's OSV output instead of its CVE record.
const isOsv = computed(() => props.context.profile.startsWith("osv-"));

function firstEcosystem(record: EditorDocument): string {
  const affected = (record as { affected?: { package?: { ecosystem?: unknown } }[] }).affected;
  const ecosystem = affected?.[0]?.package?.ecosystem;

  return typeof ecosystem === "string" && ecosystem !== "Unknown" ? ecosystem : "";
}

// Optional: it only fills in the generated package ecosystem, so it can
// just as well be set afterwards under Affected packages.
const osvEcosystem = ref(isOsv.value ? firstEcosystem(props.context.record) : "");


// Job state
const job = shallowRef<Patch2VulnJob | null>(null);
const submitting = ref(false);
const error = ref<string | null>(null);
// The editor's toast stack, shared with Save and Apply JSON.
const editor = useEditorContext();

let pollTimer: ReturnType<typeof setTimeout> | undefined;

// After the live stream's maximum lifetime, check now and then without
// holding a server connection open in between.
const SLOW_POLL_MS = 30_000;

// When the job's status can't be retrieved (patch2vuln or the network is
// down), the panel can't tell whether the job still runs: it shows the
// status as unknown and keeps checking. After this long it also says the
// job may have been lost.
const LONG_OUTAGE_MS = 10 * 60_000;

// Set while status checks fail; null once one succeeds again.
const statusError = ref<{ message: string; since: number } | null>(null);
const longOutage = ref(false);

// The live stream reports an outage once, not per failed check, so the
// 10-minute note needs its own timer.
let longOutageTimer: ReturnType<typeof setTimeout> | undefined;

function statusReceived(): void {
  clearTimeout(longOutageTimer);
  longOutageTimer = undefined;
  statusError.value = null;
  longOutage.value = false;
}

// The status can't be retrieved; keeps the time the outage began.
function statusUnavailable(
  message: string,
): void {
  const since = statusError.value?.since ?? Date.now();

  statusError.value = { message, since };
  longOutage.value = Date.now() - since >= LONG_OUTAGE_MS;

  if (!longOutage.value && longOutageTimer === undefined) {
    longOutageTimer = setTimeout(() => {
      longOutage.value = true;
    }, since + LONG_OUTAGE_MS - Date.now());
  }
}
let mounted = false;
let unsubscribeJobEvents: (() => void) | null = null;


// Set once Cancel was pressed on a running job, until it stops.
const cancelRequested = ref(false);

const canCancel = computed(
  () =>
    Boolean(repository.value?.cancelPatch2VulnJob) &&
    (job.value?.status === "queued" || job.value?.status === "running"),
);


const generatedRecord = computed(
  () => job.value?.status !== "completed"
    ? undefined
    : isOsv.value
      ? job.value.result?.osv ?? undefined
      : job.value.result?.record,
);


const isRunning = computed(
  () =>
    submitting.value ||
    job.value?.status === "queued" ||
    job.value?.status === "running",
);


const fields = computed<readonly { id: string; label: string }[]>(
  () => isOsv.value ? OSV_FIELDS : CVE_FIELDS,
);

const selectedFields = ref<string[]>(
  fields.value.map((field) => field.id),
);

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
    statusReceived();

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

      if (event.unreachable) {
        statusUnavailable(event.error ?? "Could not reach the Patch2Vuln service");
      } else {
        statusReceived();
      }

      if (
        event.status === "completed" ||
        event.status === "failed" ||
        event.status === "canceled"
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

      // job uses shallowRef(), so replace the object. A null status
      // (expired before patch2vuln answered) keeps the last known one.
      if (event.status) {
        job.value = {
          ...job.value,
          status: event.status,
          workerAvailable: event.workerAvailable,
        };
      }

      if (event.expired) {
        // Closing it stops the browser from reconnecting.
        stopWatchingJob();
        pollTimer = setTimeout(() => void pollJob(SLOW_POLL_MS), SLOW_POLL_MS);
      }
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
async function pollJob(
  intervalMs = 2000,
): Promise<void> {
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
    error.value = null;
    statusReceived();

    if (
      result.status === "queued" ||
      result.status === "running"
    ) {
      pollTimer = setTimeout(
        () => void pollJob(intervalMs),
        intervalMs,
      );
    }
  } catch (err) {
    if (!mounted || job.value?.jobId !== jobId) {
      return;
    }

    if ((err as { status?: number }).status === 404) {
      // The job is gone (expired after 24 h, or deleted): nothing to wait for.
      error.value = "This analysis is no longer available. Start a new one.";
      job.value = { jobId, status: "failed" };
      statusReceived();
      return;
    }

    // Shown in the status line rather than as a separate error.
    statusUnavailable(
      err instanceof Error
        ? err.message
        : "Could not retrieve analysis status",
    );

    // Likely a passing outage: keep checking instead of going silent.
    pollTimer = setTimeout(
      () => void pollJob(intervalMs),
      intervalMs,
    );
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
  job.value = null;
  cancelRequested.value = false;
  statusReceived();

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
          packageUrl: packageUrl.value,
          osvEcosystem: isOsv.value ? osvEcosystem.value : "",
          fixedVersion: fixedVersion.value,
          versionType: versionType.value,
          prompt: prompt.value.trim(),
        },
      });

    // Persist the job so it survives switching panels.
    rememberJob(editor, props.context.identifier, result.jobId);

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


// Cancel the current job. patch2vuln cancels a queued job at once and
// asks a running one to stop; the job's status then reports "canceled".
async function cancel(): Promise<void> {
  const jobId = job.value?.jobId;

  if (!jobId || !repository.value?.cancelPatch2VulnJob) {
    return;
  }

  cancelRequested.value = true;
  error.value = null;

  try {
    const result = await repository.value.cancelPatch2VulnJob(jobId);

    if (!mounted || job.value?.jobId !== jobId) {
      return;
    }

    if (result.status === "completed") {
      // Finished just before the cancel arrived: show its result.
      stopWatchingJob();
      void refreshJob(jobId);
    } else if (result.status !== "queued" && result.status !== "running") {
      stopWatchingJob();
      job.value = { jobId, status: result.status };
    }
    // Still running: keep watching until it reports "canceled".
  } catch (err) {
    cancelRequested.value = false;

    if (mounted) {
      error.value = err instanceof Error
        ? err.message
        : "Could not cancel the analysis.";
    }
  }
}


// Copies the selected CNA fields; null when nothing may be applied.
function applyCveFields(): number | null {
  const generated = generatedRecord.value as CveRecord | undefined;

  if (!generated?.containers?.cna) {
    error.value = "No generated CNA container available.";
    return null;
  }

  const current = props.context.record as CveRecord;

  if (current.cveMetadata?.state === "REJECTED") {
    error.value = "Cannot modify a rejected record.";
    return null;
  }

  return copyCveFields(current, generated, selectedFields.value);
}


// Copies the selected top-level fields of patch2vuln's OSV record.
function applyOsvFields(): number | null {
  const generated = generatedRecord.value as Record<string, unknown> | undefined;

  if (!generated) {
    error.value = "No generated OSV record available.";
    return null;
  }

  return copyOsvFields(
    props.context.record as Record<string, unknown>,
    generated,
    selectedFields.value,
  );
}


// Apply selected generated fields to the live editor record.
function applyResult(): void {
  const count = isOsv.value ? applyOsvFields() : applyCveFields();

  if (count === null) {
    return;
  }

  if (count === 0) {
    error.value = "None of the selected fields are in the generated record.";
    return;
  }

  error.value = null;
  editor.notice.value =
    `Applied ${count} ${count === 1 ? "field" : "fields"} from patch2vuln. Save to keep the changes.`;
}


// Resume polling when reopening the panel.
onMounted(() => {
  mounted = true;
  // The panel watches its job itself again.
  stopBackgroundWatch(editor);

  const savedJobId = recallJob(editor, props.context.identifier);

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
  clearTimeout(longOutageTimer);
  //stopPolling();
  stopWatchingJob();

  // Still running: keep an eye on it, so the editor can say when it's done
  // while another panel or section is open.
  const running = job.value?.status === "queued" || job.value?.status === "running";
  const getJob = repository.value?.getPatch2VulnJob?.bind(repository.value);

  if (running && job.value && getJob) {
    watchInBackground(editor, job.value.jobId, getJob);
  }
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
          :class="{ 'is-invalid': inputProblem }"
          rows="3"
          placeholder="https://github.com/owner/repo/commit/..."
          aria-describedby="patch2vuln-commits-help patch2vuln-input-problem"
          :aria-invalid="inputProblem !== null"
          :disabled="isRunning"
        />

        <div
          v-if="inputProblem"
          id="patch2vuln-input-problem"
          class="invalid-feedback"
        >
          ⚠ {{ inputProblem }}
        </div>

        <div
          id="patch2vuln-commits-help"
          class="form-text"
        >
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

      <div class="row mb-3">
        <div class="col-md-6">
          <label class="form-label">Vendor</label>

          <input
            v-model="vendor"
            class="form-control"
            :disabled="isRunning"
            :aria-describedby="autofilled ? 'patch2vuln-autofilled' : undefined"
          >
        </div>

        <div class="col-md-6">
          <label class="form-label">Product</label>

          <input
            v-model="product"
            class="form-control"
            :disabled="isRunning"
            :aria-describedby="autofilled ? 'patch2vuln-autofilled' : undefined"
          >
        </div>

        <div
          v-if="autofilled"
          id="patch2vuln-autofilled"
          class="col-12 form-text"
        >
          Filled in from the commit URL. Change them if the real names
          differ.
        </div>
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
        <label
          class="form-label"
          for="patch2vuln-package-url"
        >
          Package URL
        </label>

        <input
          id="patch2vuln-package-url"
          v-model="packageUrl"
          class="form-control"
          placeholder="e.g. pkg:pypi/widget"
          aria-describedby="patch2vuln-package-url-help"
          :disabled="isRunning"
        >

        <div
          id="patch2vuln-package-url-help"
          class="form-text"
        >
          Given to the analysis, so it can improve the result. Leave out the version.
        </div>
      </div>

      <div
        v-if="isOsv"
        class="mb-3"
      >
        <label
          class="form-label"
          for="patch2vuln-osv-ecosystem"
        >
          OSV ecosystem
        </label>

        <input
          id="patch2vuln-osv-ecosystem"
          v-model="osvEcosystem"
          class="form-control"
          placeholder="e.g. PyPI, npm, Go, Debian"
          aria-describedby="patch2vuln-osv-ecosystem-help"
          :disabled="isRunning"
        >

        <div
          id="patch2vuln-osv-ecosystem-help"
          class="form-text"
        >
          Optional. It doesn't change the analysis; if left empty, set it
          afterwards under Affected packages.
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

      <div class="mb-3">
        <label
          for="patch2vuln-prompt"
          class="form-label"
        >
          Additional instructions <span class="text-secondary">(optional)</span>
        </label>

        <textarea
          id="patch2vuln-prompt"
          v-model="prompt"
          class="form-control"
          rows="3"
          maxlength="16000"
          placeholder="e.g. The session cookie is attacker-controlled. Focus on the authentication impact."
          aria-describedby="patch2vuln-prompt-help"
          :disabled="isRunning"
        />

        <div
          id="patch2vuln-prompt-help"
          class="form-text"
        >
          Added to the model's instructions: context the patch doesn't show,
          or what to focus on. The generated record still needs review.
        </div>
      </div>

      <button
        type="button"
        class="btn btn-primary"
        :disabled="
          isRunning ||
          inputProblem !== null ||
          (!commitUrls.trim() && files.length === 0)
        "
        @click="submit"
      >
        {{ isRunning ? "Analyzing..." : "Analyze patches" }}
      </button>

      <button
        v-if="canCancel"
        type="button"
        class="btn btn-outline-danger ms-2"
        :disabled="cancelRequested || statusError !== null"
        :title="statusError ? 'patch2vuln can\'t be reached right now' : undefined"
        @click="cancel"
      >
        {{ cancelRequested ? "Cancelling..." : "Cancel analysis" }}
      </button>

      <div
        v-if="error"
        class="alert alert-danger mt-3"
      >
        {{ error }}
      </div>

      <div
        v-if="job"
        class="mt-4"
      >
        <hr>

        <h5>Analysis</h5>

        <p v-if="statusError && isRunning">
          Status:
          <strong>unknown</strong>
          <span class="text-secondary">
            — {{ statusError.message }} (last known: {{ job.status }}). Retrying…
          </span>
        </p>

        <p v-else>
          Status:
          <strong>{{ job.status }}</strong>
        </p>

        <div
          v-if="isRunning && statusError && longOutage"
          class="alert alert-warning"
          role="status"
        >
          The analysis status couldn't be retrieved for 10 minutes. The
          analysis may have been lost, for example if the patch2vuln server
          restarted. You can keep waiting or start a new one.
        </div>

        <div
          v-if="isRunning && !statusError"
          class="spinner-border spinner-border-sm"
          role="status"
        />

        <div
          v-if="isRunning && job.workerAvailable === false"
          class="alert alert-warning mt-3"
          role="status"
        >
          No analysis worker is running on the patch2vuln server, so this
          job is waiting. It starts once a worker is back; you can also
          cancel it.
        </div>

        <div
          v-if="job.status === 'canceled'"
          class="alert alert-secondary"
        >
          Analysis canceled.
        </div>

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
            v-for="field in fields"
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
