<script setup lang="ts">
import {
  computed,
  onMounted,
  reactive,
  ref,
  watch,
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

import {
  MAX_COMMITS_PER_VULNERABILITY,
  MAX_VULNERABILITIES,
  parseBatchInput,
  sharedRepository,
} from "./batch-input";

import type {
  BatchLine,
} from "./batch-input";

const router = useRouter();
const repository = new HttpRepository("/api/v1");

const batches = ref<Patch2VulnBatchSummary[]>([]);
const loading = ref(true);
const loadError = ref<string | null>(null);

const name = ref("");
const profile = ref(DEFAULT_PROFILE_ID);
const commitUrls = ref("");

// The Patch2Vuln panel's optional fields; Patch2Vuln applies them to
// every vulnerability of the batch.
const context = reactive({
  vendor: "",
  product: "",
  affectedVersion: "",
  fixedVersion: "",
  versionType: "",
  packageUrl: "",
  osvEcosystem: "",
  prompt: "",
});
const isOsv = computed(() => profile.value.startsWith("osv-"));
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

// What will be analysed, as the user types.
const lines = computed(() => parseBatchInput(commitUrls.value));
const commitCount = computed(() => lines.value.reduce((sum, line) => sum + line.commits.length, 0));
const tooMany = computed(() => lines.value.length > MAX_VULNERABILITIES);
const canSubmit = computed(() =>
  lines.value.length > 0 && !tooMany.value && lines.value.every((line) => !line.error));

// Vendor and product follow the commits while they all come from one
// repository, as in the panel, until the user types their own; with
// several repositories they'd be wrong for some, so they're cleared.
const filled = reactive({ vendor: "", product: "" });
const autofilled = computed(() => (
  (context.vendor !== "" && context.vendor === filled.vendor)
  || (context.product !== "" && context.product === filled.product)
));

watch(lines, (current) => {
  const shared = sharedRepository(current);

  if (context.vendor === filled.vendor) {
    context.vendor = filled.vendor = shared?.owner ?? "";
  }
  if (context.product === filled.product) {
    context.product = filled.product = shared?.repo ?? "";
  }
});

function plural(count: number, one: string, many: string): string {
  return `${count} ${count === 1 ? one : many}`;
}

// The line's repositories once each, then its commits.
function repositories(line: BatchLine): string {
  return [...new Set(line.commits.map((commit) => commit.repository))].join(", ");
}

async function submit(): Promise<void> {
  submitting.value = true;
  submitError.value = null;

  try {
    const batch = await repository.createPatch2VulnBatch(
      name.value.trim(),
      profile.value,
      lines.value.map((line) => line.commits.map((commit) => commit.url)),
      { ...context, osvEcosystem: isOsv.value ? context.osvEcosystem : "" },
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
              wrap="off"
              required
              aria-describedby="batch-urls-help batch-urls-preview"
              placeholder="https://github.com/owner/repo/commit/…"
            />
            <div
              id="batch-urls-help"
              class="form-text"
            >
              One line per vulnerability, up to {{ MAX_VULNERABILITIES }} lines.
              Several commits fixing the same vulnerability go on one line,
              separated by spaces (up to {{ MAX_COMMITS_PER_VULNERABILITY }});
              they're analysed together.
            </div>

            <div
              v-if="lines.length"
              id="batch-urls-preview"
              class="mt-2"
              aria-live="polite"
            >
              <div class="small fw-semibold">
                {{ plural(lines.length, "vulnerability", "vulnerabilities") }},
                {{ plural(commitCount, "commit", "commits") }}
                <span
                  v-if="tooMany"
                  class="text-danger"
                >· at most {{ MAX_VULNERABILITIES }} per batch</span>
              </div>

              <ol class="batch-preview small mb-0">
                <li
                  v-for="(line, index) in lines"
                  :key="index"
                >
                  <span
                    v-if="line.error"
                    class="text-danger"
                  >⚠ {{ line.error }}</span>
                  <template v-else>
                    <span>{{ repositories(line) }}</span>
                    <span class="font-monospace text-secondary ms-2">
                      {{ line.commits.map((commit) => commit.sha.slice(0, 7)).join(" · ") }}
                    </span>
                    <span
                      v-if="line.commits.length > 1"
                      class="badge text-bg-secondary ms-2"
                    >{{ line.commits.length }} commits, analysed together</span>
                  </template>
                </li>
              </ol>
            </div>
          </div>

          <details class="col-12">
            <summary class="fw-semibold">
              Additional context <span class="text-secondary fw-normal">(optional)</span>
              <span
                v-if="autofilled"
                class="text-secondary fw-normal ms-1"
              >· vendor and product filled in</span>
            </summary>

            <p class="form-text mt-1">
              The same values go with every vulnerability of the batch, as
              in the Patch2Vuln panel. Leave fields empty that differ
              between them, such as vendor and product for commits from
              different projects.
            </p>

            <div class="row g-3">
              <div class="col-md-6">
                <label
                  for="batch-vendor"
                  class="form-label"
                >Vendor</label>
                <input
                  id="batch-vendor"
                  v-model="context.vendor"
                  class="form-control"
                  maxlength="200"
                  :aria-describedby="autofilled ? 'batch-autofilled' : undefined"
                >
              </div>

              <div class="col-md-6">
                <label
                  for="batch-product"
                  class="form-label"
                >Product</label>
                <input
                  id="batch-product"
                  v-model="context.product"
                  class="form-control"
                  maxlength="200"
                  :aria-describedby="autofilled ? 'batch-autofilled' : undefined"
                >
              </div>

              <div
                v-if="autofilled"
                id="batch-autofilled"
                class="col-12 form-text mt-1"
              >
                Filled in from the commit URLs, which all come from one
                repository. Change them if the real names differ.
              </div>

              <div class="col-md-6">
                <label
                  for="batch-affected-version"
                  class="form-label"
                >Affected version</label>
                <input
                  id="batch-affected-version"
                  v-model="context.affectedVersion"
                  class="form-control"
                  maxlength="200"
                >
              </div>

              <div class="col-md-6">
                <label
                  for="batch-fixed-version"
                  class="form-label"
                >Fixed version</label>
                <input
                  id="batch-fixed-version"
                  v-model="context.fixedVersion"
                  class="form-control"
                  maxlength="200"
                >
              </div>

              <div class="col-md-6">
                <label
                  for="batch-package-url"
                  class="form-label"
                >Package URL</label>
                <input
                  id="batch-package-url"
                  v-model="context.packageUrl"
                  class="form-control"
                  maxlength="200"
                  placeholder="e.g. pkg:pypi/widget"
                >
              </div>

              <div class="col-md-6">
                <label
                  for="batch-version-type"
                  class="form-label"
                >Version type</label>
                <select
                  id="batch-version-type"
                  v-model="context.versionType"
                  class="form-select"
                >
                  <option value="">Automatic</option>
                  <option value="semver">SemVer</option>
                  <option value="custom">Custom</option>
                </select>
              </div>

              <div
                v-if="isOsv"
                class="col-md-6"
              >
                <label
                  for="batch-osv-ecosystem"
                  class="form-label"
                >OSV ecosystem</label>
                <input
                  id="batch-osv-ecosystem"
                  v-model="context.osvEcosystem"
                  class="form-control"
                  maxlength="200"
                  placeholder="e.g. PyPI, npm, Go, Debian"
                >
              </div>

              <div class="col-12">
                <label
                  for="batch-prompt"
                  class="form-label"
                >Additional instructions</label>
                <textarea
                  id="batch-prompt"
                  v-model="context.prompt"
                  class="form-control"
                  rows="3"
                  maxlength="16000"
                  placeholder="e.g. Focus on the authentication impact."
                  aria-describedby="batch-prompt-help"
                />
                <div
                  id="batch-prompt-help"
                  class="form-text"
                >
                  Added to the model's instructions for every analysis.
                </div>
              </div>
            </div>
          </details>
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
          :disabled="submitting || !canSubmit"
        >
          {{ submitting ? "Submitting…" : lines.length
            ? `Analyse ${plural(lines.length, "vulnerability", "vulnerabilities")}`
            : "Analyse" }}
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

<style scoped>
/* A long batch scrolls inside the form instead of stretching the page. */
.batch-preview {
  max-height: 16rem;
  overflow-y: auto;
  padding-left: 2rem;
}
</style>
