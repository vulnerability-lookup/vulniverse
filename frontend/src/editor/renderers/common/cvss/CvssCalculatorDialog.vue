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
  unknownVectorParts,
} from "./cvss-calculator";

import type {
  MetricDefinition,
  MetricOption,
  MetricSelection,
} from "./cvss-calculator";

import {
  SPEC_URLS,
  metricHelp,
} from "./cvss-help";

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
// Metrics from the opened vector that have no dropdown here; re-added on apply.
const keptParts = ref<string[]>([]);

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
  return [
    buildVectorString(
      allMetrics.value,
      selection.value,
      vectorPrefix.value,
    ),
    ...keptParts.value,
  ].join("/");
});

function scoreOf(chosen: MetricSelection): number {
  if (version.value === "2.0") {
    return calculateCvss2BaseScore(chosen);
  }

  if (version.value === "3.0" || version.value === "3.1") {
    return calculateCvss3BaseScore(
      chosen,
      version.value,
    );
  }

  return calculateCvss4BaseScore(chosen);
}

const baseScore = computed(() => scoreOf(selection.value));

const baseSeverity = computed(() => {
  return baseScore.value === null
    ? null
    : severityFor3x(baseScore.value);
});

interface MetricGroup {
  title: string;
  note?: string;
  metrics: MetricDefinition[];
  // Supplemental metrics never change the score.
  scored: boolean;
}

const groups = computed<MetricGroup[]>(() => [
  { title: "Base metrics", metrics: metrics.value, scored: true },
  ...(version.value === "4.0" && showAdvanced.value
    ? [
      { title: "Threat", note: "affects score", metrics: CVSS4_THREAT_METRICS, scored: true },
      { title: "Environmental", note: "affects score", metrics: CVSS4_ENVIRONMENTAL_METRICS, scored: true },
      { title: "Supplemental", note: "informational only", metrics: CVSS4_SUPPLEMENTAL_METRICS, scored: false },
    ]
    : []),
]);

function help(key: string) {
  return metricHelp(version.value, key);
}

// CVSS 2.0 has no official qualitative rating.
function severityLabel(score: number): string {
  return version.value === "2.0" ? "" : ` ${severityFor3x(score).charAt(0)}${severityFor3x(score).slice(1).toLowerCase()}`;
}

/** "8.4 High": the score the vector would get with this option. */
function optionScore(def: MetricDefinition, option: MetricOption): string {
  const score = scoreOf({ ...selection.value, [def.key]: option.key });

  return `${score.toFixed(1)}${severityLabel(score)}`;
}

// The option under the mouse or keyboard focus: its score shows in the
// top bar and its explanation under its metric, before it's picked.
const preview = ref<{ key: string; option: string; scored: boolean } | null>(null);

const previewScore = computed(() => {
  const current = preview.value;

  if (!current?.scored || selection.value[current.key] === current.option) return null;

  return scoreOf({ ...selection.value, [current.key]: current.option });
});

function shownOption(key: string): string {
  return preview.value?.key === key ? preview.value.option : selection.value[key] ?? "";
}

const openTips = ref<Set<string>>(new Set());

function toggleTip(key: string): void {
  if (!openTips.value.delete(key)) openTips.value.add(key);
}

function open(
  openVersion: "2.0" | "3.0" | "3.1" | "4.0",
  currentVectorString?: string,
): void {
  version.value = openVersion;
  showAdvanced.value = false;
  openTips.value = new Set();
  preview.value = null;

  selection.value = currentVectorString
    ? parseVectorString(allMetrics.value, currentVectorString)
    : defaultSelection(allMetrics.value);

  keptParts.value = currentVectorString
    ? unknownVectorParts(allMetrics.value, currentVectorString)
    : [];

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
      <div
        class="cvss-score-bar"
        aria-live="polite"
      >
        <div class="d-flex flex-wrap align-items-center gap-2">
          <span class="cvss-score">{{ baseScore === null ? "–" : baseScore.toFixed(1) }}</span>
          <span
            v-if="baseScore !== null && version !== '2.0'"
            :class="['badge', 'cvss-severity', `is-${baseSeverity?.toLowerCase()}`]"
          >
            {{ baseSeverity }}
          </span>
          <span
            v-if="previewScore !== null"
            class="text-secondary"
          >
            → {{ previewScore.toFixed(1) }}{{ severityLabel(previewScore) }} with this choice
          </span>
          <code class="cvss-vector w-100">{{ vectorString }}</code>
        </div>

        <div
          v-if="keptParts.length"
          class="small text-secondary mt-1"
        >
          Kept from the existing vector (not editable here):
          <code>{{ keptParts.join("/") }}</code>
        </div>
      </div>

      <p class="small text-secondary">
        Each choice shows the score the vector would get with it; point at
        one to preview it.
        What the metrics mean in detail:
        <a
          :href="SPEC_URLS[version]"
          target="_blank"
          rel="noopener noreferrer"
        >CVSS {{ version }} specification</a>.
      </p>

      <template
        v-for="(group, groupIndex) in groups"
        :key="group.title"
      >
        <div class="card mb-3">
          <div class="card-header d-flex justify-content-between align-items-center">
            {{ group.title }}

            <span
              v-if="group.note"
              class="text-secondary small fw-normal"
            >{{ group.note }}</span>
          </div>

          <div class="card-body">
            <div class="row g-3">
              <div
                v-for="def in group.metrics"
                :key="def.key"
                class="col-md-6"
              >
                <div class="d-flex align-items-center gap-1">
                  <span
                    :id="`cvss-metric-${def.key}`"
                    class="fw-semibold"
                  >
                    {{ def.label }}
                    <span class="text-secondary fw-normal small">({{ def.key }})</span>
                  </span>

                  <button
                    v-if="help(def.key)?.tip"
                    type="button"
                    class="btn btn-outline-secondary btn-sm rounded-circle cvss-tip-toggle"
                    :aria-expanded="openTips.has(def.key)"
                    :aria-label="`Scoring tip for ${def.label}`"
                    :title="`Scoring tip for ${def.label}`"
                    @click="toggleTip(def.key)"
                  >
                    ?
                  </button>
                </div>

                <div
                  v-if="help(def.key)"
                  class="form-text mt-0 mb-1"
                >
                  {{ help(def.key)!.question }}
                </div>

                <div
                  class="cvss-options"
                  role="radiogroup"
                  :aria-labelledby="`cvss-metric-${def.key}`"
                  @mouseleave="preview = null"
                >
                  <button
                    v-for="option in def.options"
                    :key="option.key"
                    type="button"
                    role="radio"
                    :aria-checked="selection[def.key] === option.key"
                    :data-option="option.key"
                    :class="['btn', 'btn-sm', selection[def.key] === option.key ? 'btn-primary' : 'btn-outline-secondary']"
                    @click="selection[def.key] = option.key"
                    @mouseenter="preview = { key: def.key, option: option.key, scored: group.scored }"
                    @focus="preview = { key: def.key, option: option.key, scored: group.scored }"
                    @blur="preview = null"
                  >
                    {{ option.label }}
                    <span
                      v-if="group.scored"
                      class="cvss-option-score"
                    >{{ optionScore(def, option) }}</span>
                  </button>
                </div>

                <div
                  v-if="help(def.key)?.values[shownOption(def.key)]"
                  :class="['form-text', { 'cvss-previewed': shownOption(def.key) !== selection[def.key] }]"
                >
                  {{ help(def.key)!.values[shownOption(def.key)] }}
                </div>

                <div
                  v-if="openTips.has(def.key)"
                  class="alert alert-info small py-1 px-2 mt-1 mb-0"
                >
                  {{ help(def.key)?.tip }}
                </div>
              </div>
            </div>
          </div>
        </div>

        <button
          v-if="groupIndex === 0 && version === '4.0'"
          type="button"
          class="btn btn-link btn-sm ps-0 mb-3"
          @click="showAdvanced = !showAdvanced"
        >
          {{ showAdvanced ? "▾" : "▸" }} Threat, environmental &amp; supplemental metrics (optional)
        </button>
      </template>

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
