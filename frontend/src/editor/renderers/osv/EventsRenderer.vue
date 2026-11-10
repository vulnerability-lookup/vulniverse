<script setup lang="ts">
import {
  computed,
} from "vue";

import type {
  ControlElement,
  JsonSchema,
} from "@jsonforms/core";

import {
  rendererProps,
  useJsonFormsControl,
} from "@jsonforms/vue";

import {
  singleKeyChoices,
} from "./testers";

const props = defineProps({
  ...rendererProps<ControlElement>(),
});

/*
 * OSV range events are objects with exactly one key, where the key is
 * the event kind and the value the version: [{"introduced": "0"},
 * {"fixed": "1.2.3"}]. The schema expresses that as items.oneOf, which
 * the generated form renders as empty cards. Edit them as rows of
 * kind + version instead.
 */
const {
  control,
  handleChange,
} = useJsonFormsControl(props);

type Event = Record<string, string>;

const kinds = computed(() => {
  return singleKeyChoices(control.value.schema.items as JsonSchema | undefined);
});

const events = computed(() => {
  return (Array.isArray(control.value.data) ? control.value.data : []) as Event[];
});

function kindOf(
  event: Event,
): string {
  return Object.keys(event)[0] ?? kinds.value[0] ?? "";
}

function write(
  next: Event[],
): void {
  // Unset rather than leave [], which breaks minItems on an optional field.
  handleChange(control.value.path, next.length ? next : undefined);
}

function update(
  index: number,
  kind: string,
  version: string,
): void {
  write(events.value.map((event, i) => (i === index ? { [kind]: version } : event)));
}

function add(): void {
  // OSV needs an "introduced" event; offer it first, then "fixed".
  const hasIntroduced = events.value.some((event) => "introduced" in event);
  const kind = !hasIntroduced && kinds.value.includes("introduced")
    ? "introduced"
    : kinds.value.find((candidate) => candidate !== "introduced") ?? kinds.value[0] ?? "";

  write([...events.value, { [kind]: "" }]);
}

function remove(
  index: number,
): void {
  write(events.value.filter((_, i) => i !== index));
}

function label(
  kind: string,
): string {
  return kind.replace(/_/g, " ");
}
</script>

<template>
  <fieldset
    v-if="control.visible"
    class="mb-3"
  >
    <legend class="d-flex align-items-center justify-content-between h6">
      Events

      <button
        type="button"
        class="btn btn-outline-primary btn-sm"
        :disabled="!control.enabled"
        @click="add"
      >
        + Add event
      </button>
    </legend>

    <p class="text-secondary small mb-2">
      {{ control.label }}
    </p>

    <p
      v-if="events.length === 0"
      class="text-secondary small"
    >
      No events
    </p>

    <div
      v-for="(event, index) in events"
      :key="`${control.path}-${index}`"
      class="d-flex gap-2 mb-2"
    >
      <select
        class="form-select w-auto"
        :aria-label="`Event ${index + 1} kind`"
        :value="kindOf(event)"
        :disabled="!control.enabled"
        @change="update(index, ($event.target as HTMLSelectElement).value, event[kindOf(event)] ?? '')"
      >
        <option
          v-for="kind in kinds"
          :key="kind"
          :value="kind"
        >
          {{ label(kind) }}
        </option>
      </select>

      <input
        type="text"
        class="form-control"
        :aria-label="`Event ${index + 1} version`"
        :value="event[kindOf(event)] ?? ''"
        :disabled="!control.enabled"
        placeholder="Version or commit, e.g. 0 or 1.2.3"
        @input="update(index, kindOf(event), ($event.target as HTMLInputElement).value)"
      >

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
      v-if="control.errors"
      class="text-danger small"
    >
      {{ control.errors }}
    </div>
  </fieldset>
</template>
