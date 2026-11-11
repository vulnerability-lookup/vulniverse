import {
  and,
  isBooleanControl,
  isDateTimeControl,
  isObjectControl,
  isStringControl,
  optionIs,
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

import DateTimeRenderer from
  "./DateTimeRenderer.vue";

import FreeFormObjectRenderer from
  "./FreeFormObjectRenderer.vue";

import GridLayoutRenderer from
  "./GridLayoutRenderer.vue";

import WrappingTextRenderer from
  "./WrappingTextRenderer.vue";


const LONG_TEXT_MIN_LENGTH = 4096;


// An object (or a choice of objects) built with allOf/oneOf/anyOf, reached
// through the generated form: CSAF's cvss_v3 (CVSS 3.0 or 3.1) and cvss_v4.
// JSON Forms generates a control for such an object that points back at the
// object itself and renders it without end, so it is edited as JSON. Array
// items and the custom renderers lay out their own fields and never get here.
const isCompositeObjectControl = and(
  uiTypeIs("Control"),

  schemaMatches((schema) => {
    const branches = schema.oneOf ?? schema.anyOf ?? [];

    return Boolean(schema.oneOf || schema.anyOf || schema.allOf)
      && (
        schema.type === "object"
        || (
          schema.type === undefined
          && branches.length > 0
          && branches.every((branch) => branch.type === "object")
        )
      );
  }),
);


// An object the schema says nothing about: no fields, no
// composition, so a generated form would have nothing to show. The
// layout option freeForm opts in an object that declares a few keys
// edited elsewhere (see FreeFormObjectRenderer.vue).
const isFreeFormObjectControl = and(
  isObjectControl,

  or(
    optionIs("freeForm", true),
    optionIs("json", true),

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
        DateTimeRenderer,

      // Above vanilla's DateTimeControlRenderer (2).
      tester:
        rankWith(
          3,
          isDateTimeControl,
        ),
    },

    {
      renderer:
        WrappingTextRenderer,

      // Opt-in per field via controlOptions.<path>.wrap.
      tester:
        rankWith(
          4,
          and(
            isStringControl,
            optionIs("wrap", true),
          ),
        ),
    },

    {
      renderer:
        FreeFormObjectRenderer,

      tester:
        rankWith(
          5,
          or(
            isFreeFormObjectControl,
            isCompositeObjectControl,
          ),
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
  DateTimeRenderer,
  FreeFormObjectRenderer,
  GridLayoutRenderer,
  WrappingTextRenderer,
};
