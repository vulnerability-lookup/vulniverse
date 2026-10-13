<script setup lang="ts">
import {
  computed,
  ref,
} from "vue";

import {
  rendererProps,
  useJsonFormsControl,
} from "@jsonforms/vue";

import type {
  ControlElement,
} from "@jsonforms/core";

const props = defineProps({
  ...rendererProps<ControlElement>(),
});

const {
  control,
  handleChange,
} = useJsonFormsControl(props);

/*
 * The CVE schema leaves "source" entirely open-ended — {type:
 * object, minProperties: 1}, no declared properties at all — since
 * real usage varies (a simple {discovery: "..."} or a longer CNA-
 * chain of attribution data). There's no schema-declared enum for
 * "discovery" either; these are just commonly observed real-world
 * values, offered as non-exclusive presets.
 */
const DISCOVERY_PRESETS = [
  "UNKNOWN",
  "INTERNAL",
  "EXTERNAL",
  "USER",
  "HACKERONE",
];

function currentData(): Record<string, unknown> {
  return {
    ...(control.value.data as Record<string, unknown> | undefined),
  };
}

const discoveryValue = computed(() => {
  const value = currentData().discovery;

  return typeof value === "string" ? value : "";
});

const otherEntries = computed(() => {
  return Object.entries(currentData()).filter(
    ([key]) => key !== "discovery",
  );
});

function entryDisplayValue(
  value: unknown,
): string {
  return typeof value === "string"
    ? value
    : JSON.stringify(value);
}

/*
 * "source" is optional but must have at least one property when
 * present (minProperties: 1) — same "optional but non-empty if
 * present" shape as the array fields elsewhere in this codebase, so
 * clearing the last field clears the whole property rather than
 * leaving an invalid empty object behind.
 */
function commit(
  data: Record<string, unknown>,
): void {
  handleChange(
    control.value.path,
    Object.keys(data).length > 0 ? data : undefined,
  );
}

function setDiscovery(
  value: string,
): void {
  const data = currentData();

  if (value) {
    data.discovery = value;
  } else {
    delete data.discovery;
  }

  commit(data);
}

function setEntryValue(
  key: string,
  value: string,
): void {
  const data = currentData();

  data[key] = value;

  commit(data);
}

function removeEntry(
  key: string,
): void {
  const data = currentData();

  delete data[key];

  commit(data);
}

const newKey = ref("");
const newValue = ref("");

function addEntry(): void {
  const key = newKey.value.trim();

  if (!key) {
    return;
  }

  const data = currentData();

  data[key] = newValue.value;

  commit(data);

  newKey.value = "";
  newValue.value = "";
}
</script>

<template>
  <fieldset
    v-if="control.visible"
    class="mb-3"
  >
    <legend class="h5">
      {{ control.label }}
    </legend>

    <div class="mb-3">
      <label class="form-label">Discovery</label>

      <input
        list="source-discovery-presets"
        type="text"
        class="form-control"
        :value="discoveryValue"
        :disabled="!control.enabled"
        @change="
          setDiscovery(
            ($event.target as HTMLInputElement).value,
          )
        "
      >

      <datalist id="source-discovery-presets">
        <option
          v-for="preset in DISCOVERY_PRESETS"
          :key="preset"
          :value="preset"
        />
      </datalist>
    </div>

    <label class="form-label">Additional fields</label>

    <p
      v-if="otherEntries.length === 0"
      class="text-secondary small"
    >
      No additional fields.
    </p>

    <div
      v-for="[key, value] in otherEntries"
      :key="key"
      class="row g-2 mb-2 align-items-end"
    >
      <div class="col-md-3">
        <label class="form-label small">{{ key }}</label>
      </div>

      <div class="col-md-7">
        <input
          type="text"
          class="form-control form-control-sm"
          :value="entryDisplayValue(value)"
          :disabled="!control.enabled"
          @change="
            setEntryValue(
              key,
              ($event.target as HTMLInputElement).value,
            )
          "
        >
      </div>

      <div class="col-md-2">
        <button
          type="button"
          class="btn btn-outline-danger btn-sm"
          :disabled="!control.enabled"
          @click="removeEntry(key)"
        >
          Remove
        </button>
      </div>
    </div>

    <div class="d-flex gap-2 mt-2">
      <input
        v-model="newKey"
        type="text"
        class="form-control form-control-sm"
        placeholder="Field name (e.g. advisory)"
        :disabled="!control.enabled"
      >

      <input
        v-model="newValue"
        type="text"
        class="form-control form-control-sm"
        placeholder="Value"
        :disabled="!control.enabled"
      >

      <button
        type="button"
        class="btn btn-outline-secondary btn-sm"
        :disabled="!control.enabled"
        @click="addEntry"
      >
        + Add field
      </button>
    </div>
  </fieldset>
</template>
