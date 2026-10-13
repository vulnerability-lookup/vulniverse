<script setup lang="ts">
/*
 * For a plain free-form tags array with no oneOf/enum (e.g.
 * GCVE-BCP-05-X-01's ai_annotations[].tags) — unlike TagsRenderer.vue,
 * which is built specifically around the CVE schema's own tags shape
 * (a fixed enum of known values, plus a SEPARATE "x_"-prefixed
 * pattern for custom ones). BCP-05-X-01's own spec text has no fixed
 * enum and no required prefix at all: it names three MISP taxonomies
 * ("AI Bias Terminology", "AI Computer Assisted", "AI Safety
 * Benchmark") as SHOULD-prefer suggestions, and separately says a
 * free-form tag SHOULD (not must) use an "ai:custom-*" namespace —
 * reusing TagsRenderer as-is would hide any tag not starting with
 * "x_" (a convention this format doesn't use at all) and would
 * force-prepend "x_" onto anything typed, corrupting real values
 * like "ai-computer-assisted:llm-generated".
 */
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

// The exact example tags from BCP-05-X-01's own spec text — shown as
// suggestions via a <datalist>, not a restriction: any value is
// still accepted, matching the spec's "SHOULD prefer" (not "MUST
// use") wording.
const TAG_PRESETS = [
  "ai-computer-assisted:llm-generated",
  "ai-computer-assisted:classification",
  "ai-bias:potential-hallucination",
];

// A <datalist> id must be unique in the document — more than one
// tags control (e.g. multiple ai_annotations[] entries) can be on
// the page at once.
let instanceCount = 0;

const datalistId = `gcve-tags-presets-${instanceCount++}`;

const tags = computed(() => {
  return (control.value.data ?? []) as string[];
});

function setTags(
  next: string[],
): void {
  handleChange(
    control.value.path,
    next.length > 0 ? next : undefined,
  );
}

function removeTag(
  tag: string,
): void {
  setTags(
    tags.value.filter((value) => value !== tag),
  );
}

const tagInput = ref("");

function addTag(): void {
  const value = tagInput.value.trim();

  if (!value || tags.value.includes(value)) {
    tagInput.value = "";
    return;
  }

  setTags([...tags.value, value]);
  tagInput.value = "";
}
</script>

<template>
  <div
    v-if="control.visible"
    class="mb-3"
  >
    <label class="form-label">{{ control.label }}</label>

    <div
      v-if="tags.length > 0"
      class="d-flex flex-wrap gap-2 mb-2"
    >
      <span
        v-for="tag in tags"
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
        v-model="tagInput"
        type="text"
        :list="datalistId"
        class="form-control form-control-sm"
        placeholder="e.g. ai-computer-assisted:llm-generated"
        :disabled="!control.enabled"
        @keydown.enter.prevent="addTag"
      >

      <datalist :id="datalistId">
        <option
          v-for="preset in TAG_PRESETS"
          :key="preset"
          :value="preset"
        />
      </datalist>

      <button
        type="button"
        class="btn btn-outline-secondary btn-sm"
        :disabled="!control.enabled"
        @click="addTag"
      >
        Add
      </button>
    </div>

    <p class="form-text small text-secondary mb-0">
      Prefer an existing taxonomy (ai-computer-assisted:, ai-bias:,
      ai-safety-benchmark:) when applicable; free-form tags should use
      an ai:custom-* namespace.
    </p>
  </div>
</template>
