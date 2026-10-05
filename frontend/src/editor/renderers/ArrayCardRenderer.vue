<script setup lang="ts">
import {
  computed,
} from "vue";

import {
  DispatchRenderer,
  rendererProps,
  useJsonFormsArrayControl,
  useJsonFormsControl,
} from "@jsonforms/vue";

import {
  composePaths,
  createDefaultValue,
  getFirstPrimitiveProp,
} from "@jsonforms/core";

import type {
  ControlElement,
  JsonSchema,
  UISchemaElement,
} from "@jsonforms/core";

import {
  useCollapsibleItems,
} from "./use-collapsible-items";

const props = defineProps({
  ...rendererProps<ControlElement>(),
});

const {
  control,
  addItem,
  removeItems,
} = useJsonFormsArrayControl(props);

/*
 * removeItems only ever splices the array. For a property that's
 * required on its parent, disabling delete at schema.minItems
 * (below) is correct — there's no valid fallback. But for an
 * optional property (control.required, already computed by
 * JSONForms itself), splicing down below minItems leaves a
 * permanently invalid AND — in the vanilla renderer — permanently
 * undeletable state. handleChange lets us clear the whole property
 * instead, which is what "optional, but non-empty if present"
 * actually means once you want zero entries.
 */
const { handleChange } = useJsonFormsControl(props);

const items = computed(() => {
  return (control.value.data ?? []) as unknown[];
});

const isObjectItems = computed(() => {
  return control.value.schema?.type === "object";
});

const atMinItems = computed(() => {
  const minItems = control.value.arraySchema?.minItems ?? 0;

  return items.value.length <= minItems;
});

/*
 * How many levels of "a card nested inside another card" deep this
 * instance is — read from whatever the parent (another
 * ArrayCardRenderer instance, or GcveExtensionRenderer.vue's own
 * hand-built uischema) put in uischema.options.depth, defaulting to
 * 0 for a top-level array with no such ancestor. Used purely for a
 * subtle background tint (see cardBackgroundClass below) so deeply
 * nested structures (e.g. a GCVE extension's ai_annotations[]
 * entries, each with their own models[]) are easier to tell apart
 * at a glance than card borders + indentation alone — not used for
 * anything else, so a control that never sets this just behaves
 * exactly as before.
 */
const depth = computed(() => {
  const options = control.value.uischema?.options as { depth?: number } | undefined;

  return options?.depth ?? 0;
});

/*
 * Bootstrap's own theme-aware "subtle" background utilities —
 * correct in both light and dark mode with no custom colors to
 * maintain. Deliberately colored (not a plain gray body-tint):
 * measured live, bg-body-secondary's rgb(233,236,239) sits barely
 * 10 units from the card border's own rgb(222,226,230) — all in
 * the same neutral gray, so the border all but disappeared into
 * the fill. Shifting hue (blue for depth 1, cyan for depth 2)
 * against that same neutral-gray border reads far more clearly
 * than any two shades of gray can, without the two depths being
 * mistakable for each other. Depth 0 (a plain, non-nested list)
 * stays untinted; nesting cycles rather than growing unboundedly
 * for arbitrarily deep structures.
 */
const BACKGROUND_TINT_CLASSES = ["", "bg-body-secondary", "bg-body-tertiary"];

const cardBackgroundClass = computed(() => {
  return BACKGROUND_TINT_CLASSES[depth.value % BACKGROUND_TINT_CLASSES.length];
});

/*
 * A property shaped like {type: "array", items: {oneOf: [...]}} is
 * how every "tags" field in the CVE schema is defined (a free
 * "x_"-prefixed extension string, or one of a small fixed enum) —
 * confirmed to be exactly 3 occurrences in the whole schema
 * (reference.tags, cnaPublishedContainer.tags, adpContainer.tags),
 * all the same concept. Flattening it as a plain Control would fall
 * through to JSONForms' generic oneOf picker (confusing "oneOf-0"/
 * "oneOf-1" labels); routing it to TagsRenderer instead works no
 * matter how deeply this property is nested — e.g.
 * problemTypes[].descriptions[].references[].tags, reached only by
 * this renderer flattening itself recursively — since TagsRenderer
 * derives its known values straight from this same schema shape
 * rather than needing a per-path config entry.
 */
function isTagsShaped(
  propertySchema: JsonSchema | undefined,
): boolean {
  const schema = propertySchema as Record<string, unknown> | undefined;

  if (!schema || schema.type !== "array") {
    return false;
  }

  const items = schema.items;

  return (
    !!items
    && typeof items === "object"
    && Array.isArray((items as Record<string, unknown>).oneOf)
  );
}

/*
 * @jsonforms/core's Generate.uiSchema — what findUISchema falls
 * back to for an array item with no explicit uischema — is what
 * crashed on "affected" (13 properties) and, confirmed by testing,
 * crashes the same way on anything else with enough properties
 * (containers.adp's 19). AffectedRenderer avoided it by hand-
 * building a flat list of Controls instead of asking JSONForms to
 * auto-generate one; this does the same thing generically for any
 * object-item array, so no array can hit that path again — the
 * fields themselves still go through the normal String/Enum/Array
 * renderers, unchanged. For a primitive item (string/number/
 * boolean array, e.g. cpes/modules/platforms) there are no
 * properties to flatten — scope "#" dispatches straight at the
 * item value itself.
 */

/*
 * isLongTextControl (renderers/index.ts) deliberately excludes a
 * bare item control (scope "#") from its own maxLength-based
 * detection — a primitive-item array's item schema can coincidally
 * have a large maxLength despite holding short enumerable values,
 * not prose (confirmed live: the official CVE schema's own
 * containers.cna.affected[].modules has maxLength 4096 too, purely
 * as a generic ceiling — reusing that same threshold here would
 * wrongly turn "Modules" into a growing textarea as well). A
 * genuinely prose-shaped primitive item (e.g. a GCVE extension's
 * free-text "assumptions" entries) still deserves one, so this opts
 * in via an explicit, unambiguous marker instead — "format":
 * "long-text" on the item schema, not derived from any length
 * constraint — set only on hand-authored schemas Vulniverse
 * controls (see schemas/extensions/gcve/bcp-05-x-02), never on a
 * vendored/official one. Vanilla's own MultiStringControlRenderer
 * (rank 2, @jsonforms/vue-vanilla) matches on options.multi alone,
 * with no scope exclusion, and renders with the same "text-area"
 * CSS class as the schema-detected (non-array) case.
 */
const isLongTextItems = computed(() => {
  const itemSchema = control.value.schema as JsonSchema | undefined;

  return itemSchema?.format === "long-text";
});

const childUiSchema = computed((): UISchemaElement => {
  if (!isObjectItems.value) {
    return {
      type: "Control",
      scope: "#",
      ...(isLongTextItems.value
        ? { options: { multi: true } }
        : {}),
    } as ControlElement;
  }

  const properties = control.value.schema?.properties ?? {};

  return {
    type: "VerticalLayout",
    elements: Object.keys(properties).map((key) => ({
      type: "Control",
      scope: `#/properties/${key}`,
      options: {
        // Propagated so a nested array reached through this
        // property (dispatching to another ArrayCardRenderer
        // instance) knows it's one level deeper than this one —
        // see the depth computed above.
        depth: depth.value + 1,
        ...(isTagsShaped(properties[key])
          ? { renderer: "vulniverse-tags" }
          : {}),
      },
    })),
  };
});

const { isExpanded, toggle } = useCollapsibleItems(
  computed(() => items.value.length),
);

function labelFor(
  index: number,
): string {
  const item = items.value[index];

  // A long-text item's own textarea, right below the header, already
  // shows its full value — using that same text as the heading too
  // just duplicates it. "Item N" gives a clean, short label instead,
  // exactly like the object-item fallback further down.
  if (
    typeof item === "string"
    && item.length > 0
    && !isLongTextItems.value
  ) {
    return item;
  }

  if (typeof item === "number" || typeof item === "boolean") {
    return String(item);
  }

  const labelProperty = isObjectItems.value
    ? getFirstPrimitiveProp(control.value.schema)
    : undefined;

  const value = labelProperty && item && typeof item === "object"
    ? (item as Record<string, unknown>)[labelProperty]
    : undefined;

  return typeof value === "string" && value.length > 0
    ? value
    : `Item ${index + 1}`;
}

function itemPath(
  index: number,
): string {
  return composePaths(
    control.value.path,
    `${index}`,
  );
}

function addEntry(): void {
  addItem(
    control.value.path,
    createDefaultValue(
      control.value.schema,
      control.value.rootSchema,
    ),
  )?.();
}

function deleteEntry(
  index: number,
): void {
  if (atMinItems.value) {
    if (control.value.required) {
      return;
    }

    handleChange(
      control.value.path,
      undefined,
    );

    return;
  }

  removeItems?.(control.value.path, [index])?.();
}
</script>

<template>
  <fieldset
    v-if="control.visible"
    class="mb-3"
  >
    <legend class="d-flex align-items-center justify-content-between h6">
      {{ control.label }}

      <button
        type="button"
        class="btn btn-outline-primary btn-sm"
        :disabled="!control.enabled"
        @click="addEntry"
      >
        + Add
      </button>
    </legend>

    <p
      v-if="items.length === 0"
      class="text-secondary small"
    >
      No data
    </p>

    <div
      v-for="(item, index) in items"
      :key="`${control.path}-${index}`"
      class="card mb-2"
      :class="cardBackgroundClass"
    >
      <div class="card-header d-flex justify-content-between align-items-center py-2">
        <span class="fw-semibold small">
          {{ labelFor(index) }}
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
            :disabled="!control.enabled || (control.required && atMinItems)"
            @click="deleteEntry(index)"
          >
            Remove
          </button>
        </div>
      </div>

      <div
        v-if="isExpanded(index)"
        class="card-body"
      >
        <dispatch-renderer
          :schema="control.schema"
          :uischema="childUiSchema"
          :path="itemPath(index)"
          :enabled="control.enabled"
          :renderers="control.renderers"
          :cells="control.cells"
        />
      </div>
    </div>
  </fieldset>
</template>
