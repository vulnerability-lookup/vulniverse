<script setup lang="ts">
import {
  computed,
} from "vue";

import type {
  EditorContext,
} from "../../contracts";

import {
  scoreRecordQuality,
} from "./score";

const props = defineProps<{
  context: EditorContext;
}>();

// Scored in the browser, so it follows every edit; context.record is the
// editor's live reactive record, read in full by the scorer.
const score = computed(() => scoreRecordQuality(props.context.record));

const GRADE_VARIANT: Record<string, string> = {
  A: "success",
  B: "success",
  C: "warning",
  D: "warning",
  E: "danger",
};

const gradeVariant = computed(() => GRADE_VARIANT[score.value.grade] ?? "secondary");

function ratioVariant(
  points: number,
  maximum: number,
): string {
  if (maximum <= 0) {
    return "secondary";
  }

  const ratio = points / maximum;

  if (ratio >= 0.75) {
    return "success";
  }

  if (ratio >= 0.5) {
    return "warning";
  }

  return "danger";
}

function creditLabel(
  credit: number,
): string {
  if (credit >= 1) {
    return "Full credit";
  }

  if (credit > 0) {
    return "Partial credit";
  }

  return "No credit";
}

function creditVariant(
  credit: number,
): string {
  if (credit >= 1) {
    return "success";
  }

  if (credit > 0) {
    return "warning";
  }

  return "secondary";
}

const pillarGroups = computed(() => score.value.pillars.map((pillar) => ({
  pillar,
  checks: score.value.checks.filter((check) => check.pillar === pillar.id),
})));
</script>

<template>
  <div class="p-3">
    <div class="d-flex align-items-center gap-2 mb-3">
      <span
        class="badge fs-6"
        :class="`text-bg-${gradeVariant}`"
      >
        {{ score.grade }}
      </span>

      <span class="fw-semibold">
        {{ score.score }} / 100
      </span>
    </div>

    <div
      v-for="group in pillarGroups"
      :key="group.pillar.id"
      class="mb-3"
    >
      <div class="d-flex justify-content-between align-items-baseline mb-1">
        <span class="fw-semibold small">{{ group.pillar.label }}</span>

        <span class="text-secondary small">
          {{ group.pillar.points }} / {{ group.pillar.maximum }}
        </span>
      </div>

      <div
        class="progress mb-2"
        style="height: 6px"
      >
        <div
          class="progress-bar"
          :class="`bg-${ratioVariant(group.pillar.points, group.pillar.maximum)}`"
          :style="{ width: `${(group.pillar.points / group.pillar.maximum) * 100}%` }"
        />
      </div>

      <ul class="list-unstyled small mb-0">
        <li
          v-for="check in group.checks"
          :key="check.id"
          class="d-flex justify-content-between align-items-start gap-2 py-1 border-bottom"
          :title="check.rule"
        >
          <span>{{ check.label }}</span>

          <span class="d-flex align-items-center gap-2 text-nowrap">
            <span
              class="badge"
              :class="`text-bg-${creditVariant(check.credit)}`"
            >
              {{ creditLabel(check.credit) }}
            </span>

            <span class="text-secondary">
              {{ check.points }} / {{ check.weight }}
            </span>
          </span>
        </li>
      </ul>
    </div>

    <p class="text-secondary small mb-0">
      Scoring methodology v{{ score.methodologyVersion }} — mirrors
      Vulnerability-Lookup's assigner scorecard.
    </p>
  </div>
</template>
