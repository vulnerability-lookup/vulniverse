<script setup lang="ts">
import {
  computed,
} from "vue";

import type {
  ControlElement,
} from "@jsonforms/core";

import {
  rendererProps,
  useJsonForms,
  useJsonFormsControl,
} from "@jsonforms/vue";

import {
  definedGroups,
  definedProducts,
  referenceKind,
} from "./products";

const props = defineProps({
  ...rendererProps<ControlElement>(),
});

/*
 * A reference to products or product groups defined in the product
 * tree: one ID (a select) or a list of IDs (toggle buttons). IDs the
 * tree doesn't define stay visible as warnings rather than vanish.
 */
const {
  control,
  handleChange,
} = useJsonFormsControl(props);

const jsonforms = useJsonForms();

const kind = computed(() => referenceKind(control.value.schema));
const isList = computed(() => kind.value?.list ?? false);
const isGroup = computed(() => kind.value?.group ?? false);

// shortcut: one button per defined product; a search field would scale
// better once documents list hundreds of products.
const options = computed(() => {
  const document = jsonforms.core?.data;

  return isGroup.value ? definedGroups(document) : definedProducts(document);
});

const knownIds = computed(() => new Set(options.value.map((option) => option.id)));

const selected = computed(() => {
  const data = control.value.data as unknown;

  if (isList.value) {
    return Array.isArray(data) ? data.filter((id): id is string => typeof id === "string") : [];
  }

  return typeof data === "string" && data ? [data] : [];
});

const unknown = computed(() => selected.value.filter((id) => !knownIds.value.has(id)));

const thing = computed(() => (isGroup.value ? "product group" : "product"));

function toggle(
  id: string,
): void {
  const next = selected.value.includes(id)
    ? selected.value.filter((value) => value !== id)
    : [...selected.value, id];

  // The lists need at least one entry; an empty one is unset.
  handleChange(control.value.path, next.length ? next : undefined);
}

function select(
  id: string,
): void {
  handleChange(control.value.path, id || undefined);
}
</script>

<template>
  <div
    v-if="control.visible"
    class="mb-3"
  >
    <label
      class="form-label"
      :for="isList ? undefined : control.id + '-select'"
    >
      {{ control.label }}
      <span
        v-if="control.required"
        class="text-danger"
      >*</span>
    </label>

    <p
      v-if="options.length === 0"
      class="text-secondary small mb-1"
    >
      No {{ thing }}s defined yet. Add them on the Product tree tab.
    </p>

    <div
      v-if="isList && options.length"
      class="d-flex flex-wrap gap-2"
      role="group"
      :aria-label="control.label"
    >
      <button
        v-for="option in options"
        :key="option.id"
        type="button"
        class="btn btn-sm"
        :class="selected.includes(option.id) ? 'btn-primary' : 'btn-outline-secondary'"
        :aria-pressed="selected.includes(option.id)"
        :title="option.name"
        :disabled="!control.enabled"
        @click="toggle(option.id)"
      >
        {{ option.id }}
        <span
          v-if="option.name"
          class="opacity-75"
        >· {{ option.name }}</span>
      </button>
    </div>

    <select
      v-else-if="!isList"
      :id="control.id + '-select'"
      class="form-select"
      :value="selected[0] ?? ''"
      :disabled="!control.enabled"
      @change="select(($event.target as HTMLSelectElement).value)"
    >
      <option value="">
        Choose a {{ thing }}…
      </option>

      <option
        v-for="option in options"
        :key="option.id"
        :value="option.id"
      >
        {{ option.id }}{{ option.name ? ` · ${option.name}` : "" }}
      </option>

      <option
        v-for="id in unknown"
        :key="id"
        :value="id"
      >
        {{ id }} (not defined)
      </option>
    </select>

    <div
      v-if="unknown.length"
      class="d-flex flex-wrap align-items-center gap-2 mt-2 small text-warning-emphasis"
    >
      Not defined in the product tree:

      <span
        v-for="id in unknown"
        :key="id"
        class="badge text-bg-warning d-flex align-items-center gap-1"
      >
        {{ id }}

        <button
          v-if="isList"
          type="button"
          class="btn-close"
          style="font-size: 0.55rem"
          :aria-label="`Remove ${id}`"
          :disabled="!control.enabled"
          @click="toggle(id)"
        />
      </span>
    </div>

    <div
      v-if="control.errors"
      class="text-danger small mt-1"
    >
      {{ control.errors }}
    </div>
  </div>
</template>
