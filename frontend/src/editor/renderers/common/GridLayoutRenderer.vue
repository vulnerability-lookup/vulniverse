<script setup lang="ts">
import {
  computed,
  inject,
} from "vue";

import {
  Resolve,
  isControl,
} from "@jsonforms/core";

import type {
  JsonFormsSubStates,
  JsonSchema,
  Layout,
} from "@jsonforms/core";

import {
  DispatchRenderer,
  rendererProps,
  useJsonFormsLayout,
} from "@jsonforms/vue";

import {
  useVanillaLayout,
} from "@jsonforms/vue-vanilla";

import {
  fieldWidth,
} from "./field-width";

const props = defineProps({
  ...rendererProps<Layout>(),
});

/*
 * Replaces vanilla's vertical LayoutRenderer and GroupRenderer: the
 * same children, laid out on a grid so short fields (IDs, enums,
 * dates) share a row instead of each stretching across the page.
 * Each child's width comes from its own schema (see field-width.ts),
 * which works for build-time layouts and the ones JSON Forms
 * generates at runtime for nested objects alike.
 */
const {
  layout,
  styles,
} = useVanillaLayout(useJsonFormsLayout(props));

const jsonforms = inject<JsonFormsSubStates>("jsonforms");

const widths = computed(() => {
  const rootSchema = jsonforms?.core?.schema ?? layout.value.schema;

  return layout.value.uischema.elements.map((element) => {
    if (!isControl(element)) {
      return "full";
    }

    const schema = Resolve.schema(
      layout.value.schema,
      element.scope,
      rootSchema as JsonSchema,
    );

    return fieldWidth(schema, element.options);
  });
});

const isGroup = computed(() => layout.value.uischema.type === "Group");

const label = computed(() => {
  return (layout.value.uischema as Layout & { label?: string }).label;
});
</script>

<template>
  <component
    :is="isGroup ? 'fieldset' : 'div'"
    v-if="layout.visible"
    :class="isGroup ? styles.group.root : styles.verticalLayout.root"
  >
    <legend
      v-if="isGroup && label"
      :class="styles.group.label"
    >
      {{ label }}
    </legend>

    <div class="editor-field-grid">
      <div
        v-for="(element, index) in layout.uischema.elements"
        :key="`${layout.path}-${index}`"
        :class="`editor-field-${widths[index]}`"
      >
        <DispatchRenderer
          :schema="layout.schema"
          :uischema="element"
          :path="layout.path"
          :enabled="layout.enabled"
          :renderers="layout.renderers"
          :cells="layout.cells"
        />
      </div>
    </div>
  </component>
</template>
