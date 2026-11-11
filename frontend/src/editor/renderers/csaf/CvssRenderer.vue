<script setup lang="ts">
import {
  computed,
  ref,
} from "vue";

import type {
  ControlElement,
} from "@jsonforms/core";

import {
  rendererProps,
  useJsonFormsControl,
} from "@jsonforms/vue";

import CvssCalculatorDialog from
  "../common/cvss/CvssCalculatorDialog.vue";

import type {
  CalculatorVersion,
} from "../common/cvss/score";

import {
  cvssObject,
  cvssVersions,
  extraFields,
  prefixVersion,
  versionOf,
} from "./cvss";

import type {
  CvssObject,
} from "./cvss";

const props = defineProps({
  ...rendererProps<ControlElement>(),
});

/*
 * One CSAF metric score (content.cvss_v2 / cvss_v3 / cvss_v4, FIRST's
 * schemas): the vector is edited, by hand or with the shared calculator,
 * and the base score and severity are computed from it.
 */
const {
  control,
  handleChange,
} = useJsonFormsControl(props);

const versions = computed(() => cvssVersions(control.value.schema));

const data = computed(() => {
  const value = control.value.data as unknown;

  return typeof value === "object" && value !== null && !Array.isArray(value)
    ? value as CvssObject
    : undefined;
});

const version = computed(() => versionOf(data.value, versions.value));

const vector = computed(() => {
  return typeof data.value?.vectorString === "string" ? data.value.vectorString : "";
});

const extras = computed(() => extraFields(data.value));

function write(
  nextVersion: CalculatorVersion,
  vectorString: string,
): void {
  handleChange(control.value.path, cvssObject(nextVersion, vectorString, data.value));
}

// Typed or pasted: a "CVSS:3.0/" prefix picks the version, an emptied
// field unsets the score.
function input(
  value: string,
): void {
  const vectorString = value.trim();

  if (!vectorString) {
    remove();
    return;
  }

  write(prefixVersion(vectorString, versions.value) ?? version.value, vectorString);
}

function selectVersion(
  nextVersion: CalculatorVersion,
): void {
  // Keep the metrics, switch the prefix (3.0 and 3.1 share them).
  write(nextVersion, vector.value.replace(/^CVSS:\d\.\d\//, `CVSS:${nextVersion}/`));
}

function remove(): void {
  handleChange(control.value.path, undefined);
}

const calculator = ref<InstanceType<typeof CvssCalculatorDialog> | null>(null);

function openCalculator(): void {
  calculator.value?.open(version.value, vector.value || undefined);
}

function applyCalculator(
  result: { vectorString: string },
): void {
  write(version.value, result.vectorString);
}
</script>

<template>
  <fieldset
    v-if="control.visible"
    class="mb-3"
  >
    <legend class="h6">
      {{ control.label }}
    </legend>

    <div class="d-flex flex-wrap flex-md-nowrap gap-2">
      <select
        v-if="data && versions.length > 1"
        class="form-select w-auto"
        :aria-label="`${control.label} version`"
        :value="version"
        :disabled="!control.enabled"
        @change="selectVersion(($event.target as HTMLSelectElement).value as CalculatorVersion)"
      >
        <option
          v-for="option in versions"
          :key="option"
          :value="option"
        >
          CVSS {{ option }}
        </option>
      </select>

      <input
        type="text"
        class="form-control"
        :aria-label="`${control.label} vector`"
        :value="vector"
        :disabled="!control.enabled"
        :placeholder="`Paste a vector, e.g. ${version === '2.0' ? 'AV:N/AC:L/Au:N/…' : `CVSS:${version}/AV:N/…`}, or use the calculator`"
        @input="input(($event.target as HTMLInputElement).value)"
      >

      <button
        type="button"
        class="btn btn-outline-secondary btn-sm text-nowrap"
        :disabled="!control.enabled"
        @click="openCalculator"
      >
        Calculator
      </button>

      <button
        v-if="data"
        type="button"
        class="btn btn-outline-danger btn-sm"
        :disabled="!control.enabled"
        @click="remove"
      >
        Remove
      </button>
    </div>

    <template v-if="data">
      <div class="small text-secondary mt-1">
        CVSS {{ version }} base score
        <strong>{{ typeof data.baseScore === "number" ? data.baseScore.toFixed(1) : "–" }}</strong>
        <template v-if="data.baseSeverity">
          ({{ data.baseSeverity }})
        </template>
        · computed from the vector
        <template v-if="extras.length">
          · also stores {{ extras.length }} per-metric fields, removed when the vector changes
        </template>
      </div>
    </template>

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
