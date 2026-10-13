import {
  and,
  rankWith,
  schemaMatches,
  schemaTypeIs,
} from "@jsonforms/core";

import type {
  ControlElement,
  JsonFormsRendererRegistryEntry,
  UISchemaElement,
} from "@jsonforms/core";

import GcveExtensionRenderer from
  "./GcveExtensionRenderer.vue";

import GcveTagsRenderer from
  "./GcveTagsRenderer.vue";

import {
  rendererOptionIs,
} from "../testers";


const isGcvePlainTagsControl = and(
  schemaTypeIs("array"),

  (
    uischema: UISchemaElement,
  ) => (
    (
      uischema as ControlElement
    ).scope?.endsWith(
      "/tags",
    )
    ?? false
  ),

  schemaMatches(
    (schema) => {
      const items =
        schema.items as
          | {
            type?: string;
            enum?: unknown;
            oneOf?: unknown;
          }
          | undefined;

      return Boolean(
        items
        && items.type
          === "string"
        && !items.enum
        && !items.oneOf,
      );
    },
  ),
);


export const GCVE_RENDERERS:
  JsonFormsRendererRegistryEntry[] = [
    {
      renderer:
        GcveExtensionRenderer,

      tester:
        rendererOptionIs(
          "vulniverse-gcve-extension",
        ),
    },

    {
      renderer:
        GcveTagsRenderer,

      tester:
        rankWith(
          6,
          isGcvePlainTagsControl,
        ),
    },
  ];


export {
  GcveExtensionRenderer,
  GcveTagsRenderer,
};
