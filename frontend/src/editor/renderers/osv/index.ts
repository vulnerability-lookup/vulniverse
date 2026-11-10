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

import SeverityRenderer from
  "./SeverityRenderer.vue";

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

    {
      renderer:
        SeverityRenderer,

      // OSV severity lists: {type: CVSS_V3 | …, score}. Nothing in CVE matches.
      tester:
        rankWith(
          6,
          and(
            schemaTypeIs("array"),
            schemaMatches((schema) => {
              const properties = (schema.items as JsonSchema | undefined)?.properties;

              return Boolean(
                properties?.score
                && properties.type?.enum?.includes("CVSS_V3"),
              );
            }),
          ),
        ),
    },
  ];
