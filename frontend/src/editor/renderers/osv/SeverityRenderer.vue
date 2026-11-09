<script setup lang="ts">
import {
  computed,
  ref,
} from "vue";

import type {
  ControlElement,
  JsonSchema,
} from "@jsonforms/core";

import {
  rendererProps,
  useJsonFormsControl,
} from "@jsonforms/vue";

import CvssCalculatorDialog from
  "../common/cvss/CvssCalculatorDialog.vue";

import {
  calculatorVersion,
  scoreHint,
} from "./cvss";

const props = defineProps({
  ...rendererProps<ControlElement>(),
});

/*
 * OSV severity entries: {type: CVSS_V2|CVSS_V3|CVSS_V4|Ubuntu,
 * score: <vector or text>, source?}. Rows of type + score + source,
 * with the shared CVSS calculator filling `score` for CVSS types.
 */
const {
  control,
  handleChange,
} = useJsonFormsControl(props);

type Entry = Record<string, string>;

function enumOf(
  key: string,
): string[] {
  const items = control.value.schema.items as JsonSchema | undefined;
  const values = items?.properties?.[key]?.enum;

  return Array.isArray(values) ? values.map(String) : [];
}

const types = computed(() => enumOf("type"));
const sources = computed(() => enumOf("source"));

const entries = computed(() => {
  return (Array.isArray(control.value.data) ? control.value.data : []) as Entry[];
});

const hints = computed(() => {
  return entries.value.map((entry) => scoreHint(entry.type, entry.score));
});

function write(
  next: Entry[],
): void {
  // Unset rather than leave [], same as the events renderer.
  handleChange(control.value.path, next.length ? next : undefined);
}

function update(
  index: number,
  key: string,
  value: string,
): void {
  write(entries.value.map((entry, i) => {
    if (i !== index) {
      return entry;
    }

    const next = { ...entry, [key]: value };

    // Source is optional; "" would fail the enum.
    if (key === "source" && value === "") {
      delete next.source;
    }

    return next;
  }));
}

function add(): void {
  write([...entries.value, { type: types.value.includes("CVSS_V3") ? "CVSS_V3" : types.value[0] ?? "", score: "" }]);
}

function remove(
  index: number,
): void {
  write(entries.value.filter((_, i) => i !== index));
}

const calculator = ref<InstanceType<typeof CvssCalculatorDialog> | null>(null);
const calculatorIndex = ref<number | null>(null);

function openCalculator(
  index: number,
): void {
  const entry = entries.value[index];
  const version = calculatorVersion(entry?.type, entry?.score);

  if (!entry || !version) {
    return;
  }

  calculatorIndex.value = index;
  calculator.value?.open(version, entry.score || undefined);
}

function applyCalculator(
  result: { vectorString: string },
): void {
  if (calculatorIndex.value !== null) {
    update(calculatorIndex.value, "score", result.vectorString);
  }
}
</script>

<template>
  <fieldset
    v-if="control.visible"
    class="mb-3"
  >
    <legend class="d-flex align-items-center justify-content-between h6">
      {{ control.label }}

      <button
        type="button"
        class="btn btn-outline-primary btn-sm"
        :disabled="!control.enabled"
        @click="add"
      >
        + Add severity
      </button>
    </legend>

    <p
      v-if="entries.length === 0"
      class="text-secondary small"
    >
      No data
    </p>

    <div
      v-for="(entry, index) in entries"
      :key="`${control.path}-${index}`"
      class="mb-2"
    >
      <div class="d-flex flex-wrap flex-md-nowrap gap-2">
        <select
          class="form-select w-auto"
          :aria-label="`Severity ${index + 1} type`"
          :value="entry.type ?? ''"
          :disabled="!control.enabled"
          @change="update(index, 'type', ($event.target as HTMLSelectElement).value)"
        >
          <option
            v-for="type in types"
            :key="type"
            :value="type"
          >
            {{ type }}
          </option>
        </select>

        <input
          type="text"
          class="form-control"
          :aria-label="`Severity ${index + 1} score`"
          :value="entry.score ?? ''"
          :disabled="!control.enabled"
          :placeholder="calculatorVersion(entry.type, entry.score) ? 'CVSS vector, e.g. CVSS:3.1/AV:N/…' : 'Score'"
          @input="update(index, 'score', ($event.target as HTMLInputElement).value)"
        >

        <button
          v-if="calculatorVersion(entry.type, entry.score)"
          type="button"
          class="btn btn-outline-secondary btn-sm text-nowrap"
          :disabled="!control.enabled"
          @click="openCalculator(index)"
        >
          Calculator
        </button>

        <select
          v-if="sources.length"
          class="form-select w-auto"
          :aria-label="`Severity ${index + 1} source`"
          :value="entry.source ?? ''"
          :disabled="!control.enabled"
          @change="update(index, 'source', ($event.target as HTMLSelectElement).value)"
        >
          <option value="">
            No source
          </option>

          <option
            v-for="source in sources"
            :key="source"
            :value="source"
          >
            {{ source }}
          </option>
        </select>

        <button
          type="button"
          class="btn btn-outline-danger btn-sm"
          :disabled="!control.enabled"
          @click="remove(index)"
        >
          Remove
        </button>
      </div>

      <div
        v-if="hints[index]"
        class="small text-secondary mt-1"
      >
        Base score
        <strong>{{ hints[index].score.toFixed(1) }}</strong>
        <template v-if="hints[index].severity">
          ({{ hints[index].severity }})
        </template>
        · not stored, OSV keeps only the vector
      </div>
    </div>

    <div
      v-if="control.errors"
      class="text-danger small"
    >
      {{ control.errors }}
    </div>

    <CvssCalculatorDialog
      ref="calculator"
      @apply="applyCalculator"
    />
  </fieldset>
</template>
