<script setup lang="ts">
import {
  computed,
  ref,
} from "vue";

import type {
  AttackTechniquePrediction,
  EditorContext,
  SeverityPrediction,
} from "../../contracts";

import {
  useEditorContext,
  useEditorRepository,
} from "../../core/context";

import {
  normalizeError,
} from "../../core/errors";

import {
  addAttackTechniques,
  attackTechniqueIds,
  cvssSeverity,
  englishDescription,
  isRejected,
} from "./apply";

import {
  recallResult,
  rememberResult,
} from "./result-cache";

const TOP_K = 10;

const props = defineProps<{
  context: EditorContext;
}>();

const repository = useEditorRepository();
const editor = useEditorContext();

const supported = computed(() => Boolean(
  repository.value?.classifySeverity &&
  repository.value?.classifyAttackTechniques,
));

const description = computed(() => englishDescription(props.context.record));
const rejected = computed(() => isRejected(props.context.record));
const recordSeverity = computed(() => cvssSeverity(props.context.record));
const inRecord = computed(() => attackTechniqueIds(props.context.record));

const loading = ref(false);
const error = ref<string | null>(null);
const notice = ref<string | null>(null);
const severity = ref<SeverityPrediction | null>(null);
const techniques = ref<AttackTechniquePrediction[]>([]);
const attackModel = ref<string | null>(null);
const selected = ref<Set<string>>(new Set());
// The description the shown results were computed from.
const classifiedDescription = ref<string | null>(null);

// Back from another panel: show the last result again.
const previous = recallResult(editor, props.context.identifier);

if (previous) {
  severity.value = previous.severity;
  techniques.value = previous.techniques;
  attackModel.value = previous.attackModel;
  selected.value = previous.selected;
  classifiedDescription.value = previous.description;
}

function remember(): void {
  if (!severity.value || classifiedDescription.value === null) {
    return;
  }

  rememberResult(editor, {
    identifier: props.context.identifier,
    description: classifiedDescription.value,
    severity: severity.value,
    techniques: techniques.value,
    attackModel: attackModel.value,
    selected: selected.value,
  });
}

const outdated = computed(() => (
  classifiedDescription.value !== null &&
  classifiedDescription.value !== description.value
));

const disagrees = computed(() => (
  severity.value !== null &&
  recordSeverity.value !== null &&
  severity.value.severity.toLowerCase() !== recordSeverity.value.toLowerCase()
));

const toAdd = computed(() => (
  techniques.value.filter((technique) => (
    selected.value.has(technique.id) && !inRecord.value.has(technique.id)
  ))
));

async function classify(): Promise<void> {
  const repo = repository.value;

  if (!repo?.classifySeverity || !repo.classifyAttackTechniques || !description.value) {
    return;
  }

  const text = description.value;

  loading.value = true;
  error.value = null;
  notice.value = null;

  try {
    const [severityResult, attackResult] = await Promise.all([
      repo.classifySeverity(text),
      repo.classifyAttackTechniques(text, TOP_K),
    ]);

    severity.value = severityResult;
    techniques.value = attackResult.techniques;
    attackModel.value = attackResult.model ?? null;
    selected.value = new Set(
      attackResult.techniques
        .filter((technique) => technique.predicted)
        .map((technique) => technique.id),
    );
    classifiedDescription.value = text;
    remember();
  } catch (caught) {
    error.value = normalizeError(caught, "The ML gateway request failed.").message;
  } finally {
    loading.value = false;
  }
}

function toggle(technique: string): void {
  const next = new Set(selected.value);

  if (!next.delete(technique)) {
    next.add(technique);
  }

  selected.value = next;
  notice.value = null;
  remember();
}

function addSelected(): void {
  const count = addAttackTechniques(props.context.record, toAdd.value);

  notice.value = count === 1
    ? "Added 1 technique to the record's ATT&CK mapping."
    : `Added ${count} techniques to the record's ATT&CK mapping.`;
}

// T1059.001 → techniques/T1059/001/
function techniqueUrl(technique: string): string {
  return `https://attack.mitre.org/techniques/${technique.replace(".", "/")}/`;
}

// The CVSS calculator's colours (editor.scss), for the model's label
// ("High") and the record's ("HIGH") alike.
function severityClass(label: string): string {
  const level = label.toLowerCase();

  return ["low", "medium", "high", "critical"].includes(level)
    ? `cvss-severity is-${level}`
    : "text-bg-secondary";
}

function percent(value: number): string {
  return `${Math.round(value * 100)} %`;
}
</script>

<template>
  <div class="p-3">
    <p class="text-secondary small">
      Suggestions from machine-learning models, based on the record's
      English description. Check them before using them.
    </p>

    <div
      v-if="!supported"
      class="alert alert-secondary small"
      role="status"
    >
      ML suggestions aren't available here.
    </div>

    <div
      v-else-if="rejected"
      class="alert alert-secondary small"
      role="status"
    >
      Rejected records have no description to classify.
    </div>

    <div
      v-else-if="!description"
      class="alert alert-secondary small"
      role="status"
    >
      Add an English description to get suggestions.
    </div>

    <template v-else>
      <button
        type="button"
        class="btn btn-primary btn-sm mb-3"
        :disabled="loading"
        @click="classify"
      >
        <span
          v-if="loading"
          class="spinner-border spinner-border-sm me-1"
          aria-hidden="true"
        />
        {{ classifiedDescription === null ? "Classify" : "Classify again" }}
      </button>

      <div
        v-if="outdated"
        class="alert alert-warning small"
        role="status"
      >
        The description changed since these suggestions were made.
      </div>
    </template>

    <div
      v-if="error"
      class="alert alert-danger small"
      role="alert"
    >
      {{ error }}
    </div>

    <section
      v-if="severity"
      class="card mb-3"
      aria-labelledby="ml-severity-title"
    >
      <div class="card-header d-flex justify-content-between align-items-baseline gap-2">
        <h3
          id="ml-severity-title"
          class="h6 mb-0"
        >
          Severity
        </h3>
        <span class="text-secondary small">hint only, not added to the record</span>
      </div>

      <div class="card-body">
        <div class="d-flex align-items-center flex-wrap gap-2 mb-2">
          <span class="text-secondary small">Model</span>
          <span
            class="badge fs-6"
            :class="severityClass(severity.severity)"
          >{{ severity.severity }}</span>
          <span class="text-secondary small">{{ percent(severity.confidence) }} confidence</span>
        </div>

        <div
          v-if="recordSeverity"
          class="d-flex align-items-center flex-wrap gap-2"
        >
          <span class="text-secondary small">Record's CVSS</span>
          <span
            class="badge"
            :class="severityClass(recordSeverity)"
          >{{ recordSeverity }}</span>
          <span
            class="small"
            :class="disagrees ? 'text-warning-emphasis' : 'text-success-emphasis'"
          >{{ disagrees ? "differs from the model" : "matches the model" }}</span>
        </div>

        <p
          v-else
          class="text-secondary small mb-0"
        >
          The record has no CVSS severity to compare with.
        </p>
      </div>

      <div
        v-if="severity.model"
        class="card-footer text-secondary small"
      >
        {{ severity.model }}
      </div>
    </section>

    <section
      v-if="classifiedDescription !== null"
      class="card"
      aria-labelledby="ml-attack-title"
    >
      <div class="card-header d-flex justify-content-between align-items-baseline gap-2">
        <h3
          id="ml-attack-title"
          class="h6 mb-0"
        >
          MITRE ATT&amp;CK techniques
        </h3>
        <span class="text-secondary small">score per technique</span>
      </div>

      <p
        v-if="techniques.length === 0"
        class="card-body text-secondary small mb-0"
      >
        No techniques suggested.
      </p>

      <ul
        v-else
        class="list-group list-group-flush small"
      >
        <li
          v-for="technique in techniques"
          :key="technique.id"
          class="list-group-item d-flex align-items-center gap-2"
        >
          <input
            :id="`ml-technique-${technique.id}`"
            class="form-check-input mt-0 flex-shrink-0"
            type="checkbox"
            :checked="inRecord.has(technique.id) || selected.has(technique.id)"
            :disabled="inRecord.has(technique.id)"
            @change="toggle(technique.id)"
          >

          <label
            class="flex-grow-1"
            :for="`ml-technique-${technique.id}`"
          >
            <a
              :href="techniqueUrl(technique.id)"
              target="_blank"
              rel="noopener noreferrer"
              class="font-monospace"
            >{{ technique.id }}</a>
            {{ technique.name }}
            <span
              v-if="inRecord.has(technique.id)"
              class="badge text-bg-secondary ms-1"
            >in record</span>
          </label>

          <div
            class="progress flex-shrink-0"
            style="width: 4rem; height: 6px"
            role="presentation"
          >
            <div
              class="progress-bar"
              :class="technique.predicted ? 'bg-primary' : 'bg-secondary'"
              :style="{ width: `${technique.score * 100}%` }"
            />
          </div>

          <span class="text-secondary text-nowrap text-end" style="width: 3rem">{{ percent(technique.score) }}</span>
        </li>
      </ul>

      <div class="card-footer d-flex align-items-center flex-wrap gap-2">
        <button
          type="button"
          class="btn btn-primary btn-sm"
          :disabled="toAdd.length === 0"
          @click="addSelected"
        >
          Add {{ toAdd.length || "" }} to record
        </button>

        <span
          v-if="notice"
          class="text-success small"
          role="status"
        >{{ notice }}</span>

        <span
          v-else-if="techniques.length > 0 && toAdd.length === 0"
          class="text-secondary small"
        >Tick a technique that isn't in the record yet to add it.</span>

        <span
          v-if="attackModel"
          class="text-secondary small ms-auto"
        >{{ attackModel }}</span>
      </div>
    </section>
  </div>
</template>
