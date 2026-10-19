import {
  and,
  isStringControl,
  rankWith,
  schemaMatches,
  schemaTypeIs,
} from "@jsonforms/core";

import type {
  JsonFormsRendererRegistryEntry,
} from "@jsonforms/core";

import AdpRenderer from
  "./AdpRenderer.vue";

import AffectedRenderer from
  "./AffectedRenderer.vue";

import ReferencesRenderer from
  "./ReferencesRenderer.vue";

import SourceRenderer from
  "./SourceRenderer.vue";

import TagsRenderer from
  "./TagsRenderer.vue";

import {
  CpeApplicabilityRenderer,
} from "./cpe-applicability";

import {
  MetricsRenderer,
} from "./metrics";

import {
  ReferenceIdRenderer,
  referenceKindForPattern,
} from "./reference-id";

import {
  CpeNameRenderer,
  isCpeNamePattern,
} from "../../cpe";

import {
  rendererOptionIs,
} from "../testers";


const isReferenceIdControl = and(
  isStringControl,

  schemaMatches(
    (schema) => (
      referenceKindForPattern(
        schema.pattern,
      ) !== null
    ),
  ),
);


const isCpeNameControl = and(
  isStringControl,

  schemaMatches(
    (schema) => isCpeNamePattern(schema.pattern),
  ),
);


/*
 * CVE tag arrays use an item schema containing a oneOf with:
 *
 * - a fixed enum of known values, and
 * - an x_-prefixed extension value.
 *
 * Top-level occurrences normally select TagsRenderer explicitly
 * through the generated UI schema. This tester also catches nested
 * occurrences reached through ArrayCardRenderer.
 */
const isCveTagsControl = and(
  schemaTypeIs("array"),

  schemaMatches(
    (schema) => {
      const items =
        schema.items;

      if (
        !items
        || typeof items
        !== "object"
        || Array.isArray(items)
      ) {
        return false;
      }

      const branches = (
        items as {
          oneOf?: unknown[];
        }
      ).oneOf;

      if (
        !Array.isArray(
          branches,
        )
      ) {
        return false;
      }

      const hasKnownValues =
        branches.some(
          (branch) => (
            typeof branch
            === "object"
            && branch !== null
            && Array.isArray(
              (
                branch as {
                  enum?: unknown;
                }
              ).enum,
            )
          ),
        );

      const hasExtensionValue =
        branches.some(
          (branch) => {
            if (
              typeof branch
              !== "object"
              || branch === null
            ) {
              return false;
            }

            const pattern = (
              branch as {
                pattern?: unknown;
              }
            ).pattern;

            return (
              typeof pattern
              === "string"
              && pattern.startsWith(
                "^x_",
              )
            );
          },
        );

      return (
        hasKnownValues
        && hasExtensionValue
      );
    },
  ),
);


export const CVE_RENDERERS:
  JsonFormsRendererRegistryEntry[] = [
    {
      renderer:
        AffectedRenderer,

      tester:
        rendererOptionIs(
          "vulniverse-affected",
        ),
    },

    {
      renderer:
        CpeApplicabilityRenderer,

      tester:
        rendererOptionIs(
          "vulniverse-cpe-applicability",
        ),
    },

    {
      renderer:
        MetricsRenderer,

      tester:
        rendererOptionIs(
          "vulniverse-metrics",
        ),
    },

    {
      renderer:
        ReferencesRenderer,

      tester:
        rendererOptionIs(
          "vulniverse-references",
        ),
    },

    {
      renderer:
        AdpRenderer,

      tester:
        rendererOptionIs(
          "vulniverse-adp",
        ),
    },

    {
      renderer:
        SourceRenderer,

      tester:
        rendererOptionIs(
          "vulniverse-source",
        ),
    },

    {
      renderer:
        TagsRenderer,

      tester:
        rendererOptionIs(
          "vulniverse-tags",
        ),
    },

    /*
     * Nested CVE tags have no explicit generated UI-schema override.
     * Rank 6 beats the common ArrayCardRenderer at rank 5.
     */
    {
      renderer:
        TagsRenderer,

      tester:
        rankWith(
          6,
          isCveTagsControl,
        ),
    },

    {
      renderer:
        ReferenceIdRenderer,

      tester:
        rankWith(
          4,
          isReferenceIdControl,
        ),
    },

    {
      renderer:
        CpeNameRenderer,

      tester:
        rankWith(
          4,
          isCpeNameControl,
        ),
    },
  ];
