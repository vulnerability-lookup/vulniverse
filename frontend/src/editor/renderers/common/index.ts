import {
  and,
  isBooleanControl,
  isObjectControl,
  isStringControl,
  or,
  rankWith,
  schemaMatches,
  schemaTypeIs,
  uiTypeIs,
} from "@jsonforms/core";

import type {
  ControlElement,
  JsonFormsRendererRegistryEntry,
  UISchemaElement,
} from "@jsonforms/core";

import {
  MultiStringControlRenderer,
} from "@jsonforms/vue-vanilla";

import ArrayCardRenderer from
  "./ArrayCardRenderer.vue";

import BooleanSelectRenderer from
  "./BooleanSelectRenderer.vue";

import FreeFormObjectRenderer from
  "./FreeFormObjectRenderer.vue";

import GridLayoutRenderer from
  "./GridLayoutRenderer.vue";


const LONG_TEXT_MIN_LENGTH = 4096;


// An object the schema says nothing about: no fields, no
// composition, so a generated form would have nothing to show.
const isFreeFormObjectControl = and(
  isObjectControl,

  schemaMatches(
    (schema) => (
      schema.properties === undefined
      && schema.patternProperties === undefined
      && schema.additionalProperties !== false
      && schema.oneOf === undefined
      && schema.anyOf === undefined
      && schema.allOf === undefined
      && schema.$ref === undefined
    ),
  ),
);


const isLongTextControl = and(
  isStringControl,

  (
    uischema: UISchemaElement,
  ) => (
    uischema as ControlElement
  ).scope !== "#",

  schemaMatches(
    (schema) => (
      typeof schema.maxLength
        === "number"
      && schema.maxLength
        >= LONG_TEXT_MIN_LENGTH
    ),
  ),
);


export const COMMON_RENDERERS:
  JsonFormsRendererRegistryEntry[] = [
    {
      renderer:
        GridLayoutRenderer,

      // Above vanilla's LayoutRenderer (1) and GroupRenderer (2).
      tester:
        rankWith(
          3,
          or(
            uiTypeIs("VerticalLayout"),
            uiTypeIs("Group"),
            uiTypeIs("Category"),
          ),
        ),
    },

    {
      renderer:
        BooleanSelectRenderer,

      tester:
        rankWith(
          2,
          isBooleanControl,
        ),
    },

    {
      renderer:
        MultiStringControlRenderer,

      tester:
        rankWith(
          3,
          isLongTextControl,
        ),
    },

    {
      renderer:
        FreeFormObjectRenderer,

      tester:
        rankWith(
          5,
          isFreeFormObjectControl,
        ),
    },

    {
      renderer:
        ArrayCardRenderer,

      tester:
        rankWith(
          5,
          schemaTypeIs("array"),
        ),
    },
  ];


export {
  ArrayCardRenderer,
  BooleanSelectRenderer,
  FreeFormObjectRenderer,
  GridLayoutRenderer,
};
