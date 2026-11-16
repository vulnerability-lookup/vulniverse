<script setup lang="ts">
import {
  computed,
  ref,
  toRaw,
  watch,
} from "vue";

import {
  revealTarget,
} from "../core/reveal";

import {
  JsonForms,
} from "@jsonforms/vue";

import {
  vanillaRenderers,
} from "@jsonforms/vue-vanilla";

import {
  editorAjv,
} from "../core/ajv";

import {
  DEFAULT_PROFILE_ID,
  getEditorProfile,
} from "../profiles";

import {
  useEditorContext,
} from "../core/context";

import type {
  EditorDocument,
} from "../contracts";

const editor = useEditorContext();

const activeProfile = computed(() => {
  return getEditorProfile(
    editor.profile.value ?? DEFAULT_PROFILE_ID,
  );
});

const schema = computed(() => activeProfile.value.schema);
const uiSchema = computed(() => activeProfile.value.uiSchema);

/*
 * Object.freeze opts this array out of Vue's reactivity proxying
 * entirely (reactive() skips non-extensible objects) — without it,
 * every renderer registry entry's component reference would get
 * wrapped, which is exactly the "Vue made a component reactive"
 * warning class markRaw() exists to avoid elsewhere (see
 * profiles/*.ts's previewComponent/editorComponent).
 */
const renderers = computed(() => Object.freeze([
  ...activeProfile.value.renderers,
  ...vanillaRenderers,
]));

const formData = computed(() => {
  /*
   * JsonForms mutates and deep-inspects this object internally
   * (default-value filling, ajv validation). Handing it the Vue
   * reactive Proxy that editor.record.value returns causes every
   * internal read/write to round-trip through Vue's reactivity
   * tracking, which feeds back into onChange and recurses forever.
   * toRaw() gives it the plain underlying object instead.
   */
  return editor.record.value
    ? toRaw(editor.record.value)
    : {};
});

// Reveal requests (record tree, validation errors): the tab and cards
// open themselves (CategorizationRenderer, useCollapsibleItems); once
// the field is drawn, or after a few frames the closest drawn parent,
// it is scrolled to, focused and briefly highlighted.
const root = ref<HTMLElement | null>(null);
const REVEAL_MAX_FRAMES = 20;

async function reveal(path: string): Promise<void> {
  const target = await findTarget(path);

  if (!target) {
    return;
  }

  // The field itself: centred and focused. Only a parent (a renderer that
  // draws its fields itself): its top shown, nothing focused.
  const exact = target.dataset.path === path;

  target.scrollIntoView({ block: exact ? "center" : "start", behavior: "smooth" });

  if (exact) {
    target.querySelector<HTMLElement>("input, select, textarea")?.focus({ preventScroll: true });
  }
  target.classList.remove("editor-revealed");
  void target.offsetWidth; // restart the highlight animation
  target.classList.add("editor-revealed");
}

// The field, or its closest marked parent, once tabs and cards have opened.
async function findTarget(path: string): Promise<HTMLElement | null> {
  let target: HTMLElement | null = null;

  for (let frame = 0; frame < REVEAL_MAX_FRAMES; frame++) {
    await new Promise((done) => requestAnimationFrame(done));
    target = root.value ? revealTarget(root.value, path) : null;

    if (target?.dataset.path === path) {
      break;
    }
  }

  return target;
}

watch(
  () => editor.reveal.value,
  (request) => {
    if (request) {
      void reveal(request.path).finally(() => editor.finishReveal(request.id));
    }
  },
  { immediate: true },
);

function handleChange(event: {
  data: EditorDocument;
  errors?: unknown[];
}): void {
  editor.record.value = event.data;
}
</script>

<template>
  <div ref="root">
    <JsonForms
      :data="formData"
      :schema="schema"
      :uischema="uiSchema"
      :renderers="renderers"
      :ajv="editorAjv"
      validation-mode="ValidateAndShow"
      @change="handleChange"
    />
  </div>
</template>
