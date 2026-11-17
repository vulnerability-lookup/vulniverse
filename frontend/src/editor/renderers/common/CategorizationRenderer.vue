<script setup lang="ts">
import {
  inject,
  ref,
  watch,
} from "vue";

import {
  composePaths,
  isControl,
  toDataPath,
} from "@jsonforms/core";

import type {
  Layout,
  UISchemaElement,
} from "@jsonforms/core";

import {
  DispatchRenderer,
  rendererProps,
  useJsonFormsCategorization,
} from "@jsonforms/vue";

import {
  useVanillaLayout,
} from "@jsonforms/vue-vanilla";

import {
  editorStateKey,
} from "../../core/context/keys";

import {
  isWithin,
} from "../../core/reveal";

const props = defineProps({
  ...rendererProps<Layout>(),
});

/*
 * Vanilla's tabs (same markup and classes, so editor.scss styles them),
 * plus: a reveal request (record tree, validation error) selects the tab
 * holding that field.
 */
const {
  layout,
  categories,
  styles,
} = useVanillaLayout(useJsonFormsCategorization(props));

const selected = ref(0);

function controlPaths(element: UISchemaElement): string[] {
  if (isControl(element)) {
    return [composePaths(layout.value.path, toDataPath(element.scope))];
  }

  return ((element as Layout).elements ?? []).flatMap(controlPaths);
}

/** The tab with the closest control containing `path` (or below it). */
function tabFor(path: string): number | null {
  let best: number | null = null;
  let bestScore = -1;

  categories.forEach((category, index) => {
    if (!category.value.visible) {
      return;
    }

    for (const controlPath of controlPaths(category.value.uischema)) {
      const score = isWithin(path, controlPath)
        ? controlPath.length + 1
        : isWithin(controlPath, path) ? 0 : -1;

      if (score > bestScore) {
        bestScore = score;
        best = index;
      }
    }
  });

  return best;
}

const state = inject(editorStateKey, null);

// A tab with a field that differs from the last save (core/changes.ts
// lists parents too, so a change deep inside a card counts).
function tabChanged(index: number): boolean {
  const changed = state?.changedPaths.value;

  return Boolean(changed?.size)
    && controlPaths(categories[index]!.value.uischema).some((path) => changed!.has(path));
}

watch(
  () => state?.reveal.value,
  (request) => {
    const tab = request ? tabFor(request.path) : null;

    if (tab !== null) {
      selected.value = tab;
    }
  },
  { immediate: true },
);
</script>

<template>
  <div :class="styles.categorization.root">
    <div :class="styles.categorization.category">
      <template
        v-for="(category, index) in categories"
        :key="`category-${index}`"
      >
        <div v-if="category.value.visible">
          <button
            type="button"
            :class="[selected === index ? styles.categorization.selected : '']"
            :disabled="!category.value.enabled"
            @click="selected = index"
          >
            <label>{{ category.value.label }}</label>
            <span
              v-if="tabChanged(index)"
              class="editor-changed-dot"
              title="Changed since the last save"
            ><span class="visually-hidden">(changed)</span></span>
          </button>
        </div>
      </template>
    </div>

    <div :class="styles.categorization.panel">
      <DispatchRenderer
        v-if="categories[selected]"
        :schema="layout.schema"
        :uischema="categories[selected]!.value.uischema"
        :path="layout.path"
        :enabled="layout.enabled"
        :renderers="layout.renderers"
        :cells="layout.cells"
      />
    </div>
  </div>
</template>
