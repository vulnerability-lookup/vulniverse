<script setup lang="ts">
import {
  computed,
  ref,
} from "vue";

import {
  DispatchRenderer,
  rendererProps,
  useJsonFormsArrayControl,
  useJsonFormsControl,
} from "@jsonforms/vue";

import {
  composePaths,
} from "@jsonforms/core";

import type {
  ControlElement,
} from "@jsonforms/core";

import {
  useCollapsibleItems,
} from "./use-collapsible-items";

import CvssCalculatorDialog from "./CvssCalculatorDialog.vue";

const props = defineProps({
  ...rendererProps<ControlElement>(),
});

const {
  control,
  addItem,
  removeItems,
} = useJsonFormsArrayControl(props);

// TODO: every other array renderer (AffectedRenderer, ReferencesRenderer)
// types this same JSONForms data as Record<string, unknown> — this one and
// AdpRenderer.vue are the only stragglers still on `any`. Fixing it
// properly means modeling real types for the metric entries' nested
// other.content/[format].vectorString shape, not just swapping the cast.
const items = computed(() => {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any -- see TODO above
  return (control.value.data ?? []) as Array<Record<string, any>>;
});

const { isExpanded, toggle } = useCollapsibleItems(
  computed(() => items.value.length),
);

/*
 * Switching CVSS format means replacing which key exists on the
 * metric object (e.g. cvssV3_1 -> cvssV4_0) — addItem/removeItems/
 * moveUp/moveDown (from useJsonFormsArrayControl) can't set an
 * arbitrary nested path, so handleChange (from useJsonFormsControl
 * on the same props) is used for that specific operation.
 */
const { handleChange } = useJsonFormsControl(props);

interface FormatOption {
  key: string;
  label: string;
  version: string | null;
  hasSeverity: boolean;
}

const FORMATS: FormatOption[] = [
  { key: "cvssV4_0", label: "CVSS 4.0", version: "4.0", hasSeverity: true },
  { key: "cvssV3_1", label: "CVSS 3.1", version: "3.1", hasSeverity: true },
  { key: "cvssV3_0", label: "CVSS 3.0", version: "3.0", hasSeverity: true },
  { key: "cvssV2_0", label: "CVSS 2.0", version: "2.0", hasSeverity: false },
  { key: "other", label: "Other", version: null, hasSeverity: false },
];

const FORMAT_KEYS = FORMATS.map((format) => format.key);

const otherContentText = ref<Record<number, string>>({});

function itemPath(
  index: number,
): string {
  return composePaths(
    control.value.path,
    `${index}`,
  );
}

function formatOf(
  index: number,
): FormatOption | null {
  const item = items.value[index];

  if (!item) {
    return null;
  }

  const key = FORMAT_KEYS.find((candidate) => candidate in item);

  return FORMATS.find((format) => format.key === key) ?? null;
}

function controlFor(
  formatKey: string,
  field: string,
): ControlElement {
  return {
    type: "Control",
    scope: `#/properties/${formatKey}/properties/${field}`,
  };
}

function selectFormat(
  index: number,
  formatKey: string,
): void {
  const format = FORMATS.find((candidate) => candidate.key === formatKey);

  if (!format) {
    return;
  }

  const path = itemPath(index);

  for (const key of FORMAT_KEYS) {
    handleChange(
      composePaths(path, key),
      undefined,
    );
  }

  if (format.key === "other") {
    handleChange(
      composePaths(path, "other"),
      { type: "text", content: "" },
    );

    return;
  }

  handleChange(
    composePaths(path, format.key),
    {
      version: format.version,
      vectorString: "",
      baseScore: 0,
      ...(format.hasSeverity
        ? { baseSeverity: "NONE" }
        : {}),
    },
  );
}

function otherContent(
  index: number,
): string {
  if (otherContentText.value[index] !== undefined) {
    return otherContentText.value[index];
  }

  const value = items.value[index]?.other?.content;

  return typeof value === "string"
    ? value
    : JSON.stringify(value ?? "", null, 2);
}

function updateOtherContent(
  index: number,
  value: string,
): void {
  otherContentText.value[index] = value;

  handleChange(
    composePaths(itemPath(index), "other.content"),
    value,
  );
}

function addMetric(): void {
  addItem(
    control.value.path,
    {
      cvssV3_1: {
        version: "3.1",
        vectorString: "",
        baseScore: 0,
        baseSeverity: "NONE",
      },
    },
  )?.();
}

const calculatorRef = ref<InstanceType<typeof CvssCalculatorDialog> | null>(null);
const calculatorIndex = ref<number | null>(null);

function openCalculator(
  index: number,
): void {
  const format = formatOf(index);

  if (!format?.version) {
    return;
  }

  calculatorIndex.value = index;

  calculatorRef.value?.open(
    format.version as "2.0" | "3.0" | "3.1" | "4.0",
    items.value[index]?.[format.key]?.vectorString || undefined,
  );
}

function applyCalculatorResult(
  result: {
    vectorString: string;
    baseScore?: number;
    baseSeverity?: string;
  },
): void {
  const index = calculatorIndex.value;
  const format = index === null ? null : formatOf(index);

  if (index === null || !format) {
    return;
  }

  const path = itemPath(index);

  handleChange(
    composePaths(path, `${format.key}.vectorString`),
    result.vectorString,
  );

  if (result.baseScore !== undefined) {
    handleChange(
      composePaths(path, `${format.key}.baseScore`),
      result.baseScore,
    );
  }

  if (result.baseSeverity !== undefined && format.hasSeverity) {
    handleChange(
      composePaths(path, `${format.key}.baseSeverity`),
      result.baseSeverity,
    );
  }
}
</script>

<template>
  <fieldset
    v-if="control.visible"
    class="mb-3"
  >
    <legend class="d-flex align-items-center justify-content-between h5">
      {{ control.label }}

      <button
        type="button"
        class="btn btn-primary btn-sm"
        :disabled="!control.enabled"
        @click="addMetric"
      >
        + Add metric
      </button>
    </legend>

    <p
      v-if="items.length === 0"
      class="text-secondary"
    >
      No metrics yet.
    </p>

    <div
      v-for="(item, index) in items"
      :key="`${control.path}-${index}`"
      class="card mb-3"
    >
      <div class="card-header d-flex justify-content-between align-items-center">
        <span class="fw-semibold">
          {{ formatOf(index)?.label ?? `Metric ${index + 1}` }}
        </span>

        <div class="d-flex gap-1">
          <button
            type="button"
            class="btn btn-outline-secondary btn-sm"
            @click="toggle(index)"
          >
            {{ isExpanded(index) ? "▾" : "▸" }}
          </button>

          <button
            type="button"
            class="btn btn-outline-danger btn-sm"
            :disabled="!control.enabled"
            @click="removeItems?.(control.path, [index])?.()"
          >
            Remove
          </button>
        </div>
      </div>

      <div
        v-if="isExpanded(index)"
        class="card-body"
      >
        <div class="mb-3">
          <label class="form-label">Format</label>

          <select
            class="form-select"
            :value="formatOf(index)?.key"
            :disabled="!control.enabled"
            @change="
              selectFormat(
                index,
                ($event.target as HTMLSelectElement).value,
              )
            "
          >
            <option
              v-for="format in FORMATS"
              :key="format.key"
              :value="format.key"
            >
              {{ format.label }}
            </option>
          </select>
        </div>

        <template v-if="formatOf(index) && formatOf(index)?.key !== 'other'">
          <div class="row g-3">
            <div class="col-12">
              <dispatch-renderer
                :schema="control.schema"
                :uischema="controlFor(formatOf(index)!.key, 'vectorString')"
                :path="itemPath(index)"
                :enabled="control.enabled"
                :renderers="control.renderers"
                :cells="control.cells"
              />

              <button
                type="button"
                class="btn btn-outline-primary btn-sm mt-1"
                :disabled="!control.enabled"
                @click="openCalculator(index)"
              >
                Calculate
              </button>
            </div>

            <div class="col-md-6">
              <dispatch-renderer
                :schema="control.schema"
                :uischema="controlFor(formatOf(index)!.key, 'baseScore')"
                :path="itemPath(index)"
                :enabled="control.enabled"
                :renderers="control.renderers"
                :cells="control.cells"
              />
            </div>

            <div
              v-if="formatOf(index)?.hasSeverity"
              class="col-md-6"
            >
              <dispatch-renderer
                :schema="control.schema"
                :uischema="controlFor(formatOf(index)!.key, 'baseSeverity')"
                :path="itemPath(index)"
                :enabled="control.enabled"
                :renderers="control.renderers"
                :cells="control.cells"
              />
            </div>
          </div>
        </template>

        <template v-else-if="formatOf(index)?.key === 'other'">
          <div class="mb-3">
            <label class="form-label">Type</label>

            <dispatch-renderer
              :schema="control.schema"
              :uischema="controlFor('other', 'type')"
              :path="itemPath(index)"
              :enabled="control.enabled"
              :renderers="control.renderers"
              :cells="control.cells"
            />
          </div>

          <div>
            <label class="form-label">Content</label>

            <textarea
              class="form-control"
              rows="6"
              :value="otherContent(index)"
              :disabled="!control.enabled"
              @input="
                updateOtherContent(
                  index,
                  ($event.target as HTMLTextAreaElement).value,
                )
              "
            />
          </div>
        </template>
      </div>
    </div>

    <CvssCalculatorDialog
      ref="calculatorRef"
      @apply="applyCalculatorResult"
    />
  </fieldset>
</template>
