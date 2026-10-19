<script setup lang="ts">
import {
  computed,
  onBeforeUnmount,
  onMounted,
  ref,
  watch,
} from "vue";

import type {
  EditorContext,
  RecordQualityScore,
} from "../../contracts";

import {
  useEditorRepository,
} from "../../core/context";

const props = defineProps<{
  context: EditorContext;
}>();

const repository = useEditorRepository();

const supported = computed(() => Boolean(repository.value?.scoreRecordQuality));

const score = ref<RecordQualityScore | null>(null);
const loading = ref(false);
const error = ref<string | null>(null);

const DEBOUNCE_MS = 800;
let debounceTimer: ReturnType<typeof setTimeout> | undefined;

async function compute(): Promise<void> {
  if (!repository.value?.scoreRecordQuality) {
    return;
  }

  loading.value = true;
  error.value = null;

  try {
    score.value = await repository.value.scoreRecordQuality(
      props.context.record,
      props.context.profile,
    );
  } catch (err) {
    error.value = err instanceof Error
      ? err.message
      : "Could not score this record.";
  } finally {
    loading.value = false;
  }
}

function scheduleCompute(): void {
  if (debounceTimer !== undefined) {
    clearTimeout(debounceTimer);
  }

  debounceTimer = setTimeout(
    () => {
      debounceTimer = undefined;
      void compute();
    },
    DEBOUNCE_MS,
  );
}

onMounted(() => {
  if (supported.value) {
    void compute();
  }
});

onBeforeUnmount(() => {
  if (debounceTimer !== undefined) {
    clearTimeout(debounceTimer);
  }
});

/*
 * context.record is the editor's live reactive record (same object
 * threaded through on every render, see GcveIdentifierPanel.vue) —
 * every keystroke mutates it in place rather than replacing it, so
 * only a deep watch actually fires while the user is editing. A
 * full record replacement (e.g. after Save re-clones the record, or
 * loading a different one) still triggers this watch too, since the
 * top-level reference itself changes.
 */
watch(
  () => props.context.record,
  () => {
    if (supported.value) {
      scheduleCompute();
    }
  },
  { deep: true },
);

watch(
  () => props.context.profile,
  () => {
    if (supported.value) {
      scheduleCompute();
    }
  },
);

const GRADE_VARIANT: Record<string, string> = {
  A: "success",
  B: "success",
  C: "warning",
  D: "warning",
  E: "danger",
};

const gradeVariant = computed(() => GRADE_VARIANT[score.value?.grade ?? ""] ?? "secondary");

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

const pillarGroups = computed(() => {
  const current = score.value;

  if (!current) {
    return [];
  }

  return current.pillars.map((pillar) => ({
    pillar,
    checks: current.checks.filter((check) => check.pillar === pillar.id),
  }));
});
</script>

<template>
  <div class="p-3">
    <p
      v-if="!supported"
      class="text-secondary"
    >
      This host doesn't support record quality scoring.
    </p>

    <template v-else>
      <div class="d-flex align-items-center justify-content-between mb-3">
        <div class="d-flex align-items-center gap-2">
          <span
            v-if="score"
            class="badge fs-6"
            :class="`text-bg-${gradeVariant}`"
          >
            {{ score.grade }}
          </span>

          <span
            v-if="score"
            class="fw-semibold"
          >
            {{ score.score }} / 100
          </span>

          <span
            v-else-if="loading"
            class="text-secondary small"
          >
            Scoring…
          </span>
        </div>

        <button
          type="button"
          class="btn btn-outline-secondary btn-sm"
          :disabled="loading"
          @click="compute"
        >
          {{ loading ? "Scoring…" : "Recalculate" }}
        </button>
      </div>

      <div
        v-if="error"
        class="alert alert-danger small"
      >
        {{ error }}
      </div>

      <template v-if="score">
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
      </template>
    </template>
  </div>
</template>
