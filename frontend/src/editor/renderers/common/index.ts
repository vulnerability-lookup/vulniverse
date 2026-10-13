import {
  and,
  isBooleanControl,
  isStringControl,
  rankWith,
  schemaMatches,
  schemaTypeIs,
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


const LONG_TEXT_MIN_LENGTH = 4096;


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
};
