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
 * Every CVE "tags" field (containers.cna.tags, containers.adp[].tags,
 * references[].tags, and any of those reached via ArrayCardRenderer
 * recursively flattening a nested structure, e.g.
 * problemTypes[].descriptions[].references[].tags) shares the same
 * schema shape — a oneOf of a free "x_"-prefixed extension string
 * and a small fixed enum — but the enum's actual values differ per
 * field (e.g. ADP only allows "disputed", CNA allows three).
 * uischema.options.knownTags (set per top-level field in
 * schemas/editor/cve.layout.json, or AdpRenderer's field-options
 * map) is an explicit override; the fallback derives the same list
 * straight from this control's own schema, which is what makes
 * nested occurrences — which have no such per-path config at all —
 * work correctly too.
 */
const knownTags = computed(() => {
  const options = control.value.uischema.options as
    | { knownTags?: string[] }
    | undefined;

  if (options?.knownTags) {
    return options.knownTags;
  }

  const itemsSchema = control.value.schema?.items as
    | { oneOf?: unknown[] }
    | undefined;

  const branches = itemsSchema?.oneOf ?? [];

  for (const branch of branches) {
    const enumValues = (branch as { enum?: unknown[] } | undefined)?.enum;

    if (Array.isArray(enumValues)) {
      return enumValues.filter(
        (value): value is string => typeof value === "string",
      );
    }
  }

  return [];
});

const tags = computed(() => {
  return (control.value.data ?? []) as string[];
});

const customTags = computed(() => {
  return tags.value.filter((tag) => tag.startsWith("x_"));
});

function setTags(
  next: string[],
): void {
  handleChange(
    control.value.path,
    next.length > 0 ? next : undefined,
  );
}

function toggleTag(
  tag: string,
): void {
  setTags(
    tags.value.includes(tag)
      ? tags.value.filter((value) => value !== tag)
      : [...tags.value, tag],
  );
}

function removeTag(
  tag: string,
): void {
  setTags(
    tags.value.filter((value) => value !== tag),
  );
}

const customTagInput = ref("");

function addCustomTag(): void {
  const value = customTagInput.value.trim();

  if (!value) {
    return;
  }

  const tag = value.startsWith("x_")
    ? value
    : `x_${value}`;

  setTags([...tags.value, tag]);

  customTagInput.value = "";
}
</script>

<template>
  <div
    v-if="control.visible"
    class="mb-3"
  >
    <label class="form-label">{{ control.label }}</label>

    <div class="d-flex flex-wrap gap-2 mb-2">
      <button
        v-for="tag in knownTags"
        :key="tag"
        type="button"
        class="btn btn-sm"
        :class="
          tags.includes(tag)
            ? 'btn-primary'
            : 'btn-outline-secondary'
        "
        :disabled="!control.enabled"
        @click="toggleTag(tag)"
      >
        {{ tag }}
      </button>
    </div>

    <div
      v-if="customTags.length > 0"
      class="d-flex flex-wrap gap-2 mb-2"
    >
      <span
        v-for="tag in customTags"
        :key="tag"
        class="badge text-bg-secondary d-flex align-items-center gap-1"
      >
        {{ tag }}

        <button
          type="button"
          class="btn-close btn-close-white"
          style="font-size: 0.55rem"
          :disabled="!control.enabled"
          @click="removeTag(tag)"
        />
      </span>
    </div>

    <div class="d-flex gap-2">
      <input
        v-model="customTagInput"
        type="text"
        class="form-control form-control-sm"
        placeholder="Custom tag (x_...)"
        :disabled="!control.enabled"
        @keydown.enter.prevent="addCustomTag"
      >

      <button
        type="button"
        class="btn btn-outline-secondary btn-sm"
        :disabled="!control.enabled"
        @click="addCustomTag"
      >
        Add
      </button>
    </div>
  </div>
</template>
