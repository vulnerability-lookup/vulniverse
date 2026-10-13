<script setup lang="ts">
import {
  computed,
  ref,
} from "vue";

import {
  CVSS2_METRICS,
  CVSS3_METRICS,
  CVSS4_ENVIRONMENTAL_METRICS,
  CVSS4_METRICS,
  CVSS4_SUPPLEMENTAL_METRICS,
  CVSS4_THREAT_METRICS,
  buildVectorString,
  calculateCvss2BaseScore,
  calculateCvss3BaseScore,
  calculateCvss4BaseScore,
  defaultSelection,
  parseVectorString,
  severityFor3x,
} from "./cvss-calculator";

import type {
  MetricSelection,
} from "./cvss-calculator";

const emit = defineEmits<{
  apply: [
    result: {
      vectorString: string;
      baseScore?: number;
      baseSeverity?: string;
    },
  ];
}>();

const dialog = ref<HTMLDialogElement | null>(null);
const version = ref<"2.0" | "3.0" | "3.1" | "4.0">("3.1");
const selection = ref<MetricSelection>({});
const showAdvanced = ref(false);

const metrics = computed(() => {
  if (version.value === "2.0") return CVSS2_METRICS;
  if (version.value === "4.0") return CVSS4_METRICS;

  return CVSS3_METRICS;
});

// CVSS 4.0's optional Threat/Environmental/Supplemental groups.
// Threat and Environmental affect the score; Supplemental never
// does (it's purely informational). Every option defaults to "Not
// Defined" so leaving them alone doesn't change anything. Not
// offered for 2.0/3.x (those versions' temporal/environmental groups
// are out of scope, matching the base-metrics-only design used
// throughout this calculator).
const advancedMetrics = computed(() => {
  return version.value === "4.0"
    ? [...CVSS4_THREAT_METRICS, ...CVSS4_ENVIRONMENTAL_METRICS, ...CVSS4_SUPPLEMENTAL_METRICS]
    : [];
});

const allMetrics = computed(() => [...metrics.value, ...advancedMetrics.value]);

const vectorPrefix = computed(() => {
  return version.value === "2.0" ? undefined : `CVSS:${version.value}`;
});

const vectorString = computed(() => {
  return buildVectorString(
    allMetrics.value,
    selection.value,
    vectorPrefix.value,
  );
});

const baseScore = computed(() => {
  if (version.value === "2.0") {
    return calculateCvss2BaseScore(selection.value);
  }

  if (version.value === "3.0" || version.value === "3.1") {
    return calculateCvss3BaseScore(
      selection.value,
      version.value,
    );
  }

  return calculateCvss4BaseScore(selection.value);
});

const baseSeverity = computed(() => {
  return baseScore.value === null
    ? null
    : severityFor3x(baseScore.value);
});

function open(
  openVersion: "2.0" | "3.0" | "3.1" | "4.0",
  currentVectorString?: string,
): void {
  version.value = openVersion;
  showAdvanced.value = false;

  selection.value = currentVectorString
    ? parseVectorString(allMetrics.value, currentVectorString)
    : defaultSelection(allMetrics.value);

  dialog.value?.showModal();
}

function close(): void {
  dialog.value?.close();
}

function handleApply(): void {
  emit("apply", {
    vectorString: vectorString.value,
    ...(baseScore.value !== null
      ? {
        baseScore: baseScore.value,
        baseSeverity: baseSeverity.value!,
      }
      : {}),
  });

  close();
}

defineExpose({
  open,
});
</script>

<template>
  <dialog
    ref="dialog"
    class="editor-dialog cvss-calculator-dialog"
  >
    <div class="editor-dialog-header">
      <h2 class="h6 mb-0">
        CVSS {{ version }} calculator
      </h2>

      <button
        type="button"
        class="btn-close"
        aria-label="Close"
        @click="close"
      />
    </div>

    <div class="editor-dialog-body">
      <div class="card mb-3">
        <div class="card-header">
          Base metrics
        </div>

        <div class="card-body">
          <div class="row g-3">
            <div
              v-for="def in metrics"
              :key="def.key"
              class="col-md-6"
            >
              <label class="form-label">{{ def.label }}</label>

              <select
                v-model="selection[def.key]"
                class="form-select"
              >
                <option
                  v-for="option in def.options"
                  :key="option.key"
                  :value="option.key"
                >
                  {{ option.label }}
                </option>
              </select>
            </div>
          </div>
        </div>
      </div>

      <button
        v-if="version === '4.0'"
        type="button"
        class="btn btn-link btn-sm ps-0 mb-3"
        @click="showAdvanced = !showAdvanced"
      >
        {{ showAdvanced ? "▾" : "▸" }} Threat &amp; environmental metrics (optional)
      </button>

      <template v-if="version === '4.0' && showAdvanced">
        <div class="card mb-3">
          <div class="card-header d-flex justify-content-between align-items-center">
            Threat

            <span class="text-secondary small fw-normal">affects score</span>
          </div>

          <div class="card-body">
            <div class="row g-3">
              <div
                v-for="def in CVSS4_THREAT_METRICS"
                :key="def.key"
                class="col-md-6"
              >
                <label class="form-label">{{ def.label }}</label>

                <select
                  v-model="selection[def.key]"
                  class="form-select"
                >
                  <option
                    v-for="option in def.options"
                    :key="option.key"
                    :value="option.key"
                  >
                    {{ option.label }}
                  </option>
                </select>
              </div>
            </div>
          </div>
        </div>

        <div class="card mb-3">
          <div class="card-header d-flex justify-content-between align-items-center">
            Environmental

            <span class="text-secondary small fw-normal">affects score</span>
          </div>

          <div class="card-body">
            <div class="row g-3">
              <div
                v-for="def in CVSS4_ENVIRONMENTAL_METRICS"
                :key="def.key"
                class="col-md-6"
              >
                <label class="form-label">{{ def.label }}</label>

                <select
                  v-model="selection[def.key]"
                  class="form-select"
                >
                  <option
                    v-for="option in def.options"
                    :key="option.key"
                    :value="option.key"
                  >
                    {{ option.label }}
                  </option>
                </select>
              </div>
            </div>
          </div>
        </div>

        <div class="card mb-3">
          <div class="card-header d-flex justify-content-between align-items-center">
            Supplemental

            <span class="text-secondary small fw-normal">informational only</span>
          </div>

          <div class="card-body">
            <div class="row g-3">
              <div
                v-for="def in CVSS4_SUPPLEMENTAL_METRICS"
                :key="def.key"
                class="col-md-6"
              >
                <label class="form-label">{{ def.label }}</label>

                <select
                  v-model="selection[def.key]"
                  class="form-select"
                >
                  <option
                    v-for="option in def.options"
                    :key="option.key"
                    :value="option.key"
                  >
                    {{ option.label }}
                  </option>
                </select>
              </div>
            </div>
          </div>
        </div>
      </template>

      <div class="mt-3 p-2 border rounded">
        <div class="small text-secondary">
          Vector string
        </div>

        <code>{{ vectorString }}</code>

        <div
          v-if="baseScore !== null"
          class="mt-2"
        >
          <span class="fw-semibold">
            {{ baseScore.toFixed(1) }}
          </span>

          <span class="text-secondary">
            ({{ baseSeverity }})
          </span>
        </div>
      </div>

      <div class="d-flex justify-content-end gap-2 mt-3">
        <button
          type="button"
          class="btn btn-outline-secondary"
          @click="close"
        >
          Cancel
        </button>

        <button
          type="button"
          class="btn btn-primary"
          @click="handleApply"
        >
          Apply
        </button>
      </div>
    </div>
  </dialog>
</template>
