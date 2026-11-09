import {
  and,
  rankWith,
  schemaMatches,
  schemaTypeIs,
} from "@jsonforms/core";

import type {
  JsonFormsRendererRegistryEntry,
  JsonSchema,
} from "@jsonforms/core";

import EventsRenderer from
  "./EventsRenderer.vue";

import {
  singleKeyChoices,
} from "./testers";


export const OSV_RENDERERS:
  JsonFormsRendererRegistryEntry[] = [
    {
      renderer:
        EventsRenderer,

      // Above ArrayCardRenderer (5), which would show empty cards.
      tester:
        rankWith(
          6,
          and(
            schemaTypeIs("array"),
            schemaMatches(
              (schema) => singleKeyChoices(schema.items as JsonSchema).length > 0,
            ),
          ),
        ),
    },
  ];
