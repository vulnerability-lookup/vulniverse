import type {
  JsonSchema,
  UISchemaElement,
} from "@jsonforms/core";

import authoringSchema from
  "@/generated/schemas/csaf-2.1/authoring.schema.json";

import uiSchema from
  "@/generated/schemas/csaf-2.1/ui.schema.json";

import fieldPaths from
  "@/generated/schemas/csaf-2.1/field-paths.json";

import {
  COMMON_RENDERERS,
} from "../renderers";

import type {
  EditorProfileDefinition,
} from "./types";


// CSAF 2.1 fixes the value: a document must name exactly this schema.
const CSAF_SCHEMA_URL =
  "https://docs.oasis-open.org/csaf/csaf/v2.1/schema/csaf.json";


export const csaf21Profile:
  EditorProfileDefinition = {
  id: "csaf-2.1",

  label: "CSAF",

  description:
    "A CSAF 2.1 advisory (Committee Specification 01, release candidate).",

  schema:
    // The inferred JSON type is too narrow to cast directly.
    authoringSchema as unknown as JsonSchema,

  uiSchema:
    uiSchema as UISchemaElement,

  fieldPaths,

  createEmptyDocument() {
    // Whole seconds in UTC, as the date-time fields store them.
    const now = new Date().toISOString().replace(/\.\d{3}Z$/, "Z");

    return {
      $schema: CSAF_SCHEMA_URL,
      document: {
        category: "csaf_base",
        csaf_version: "2.1",
        distribution: {
          tlp: { label: "CLEAR" },
        },
        publisher: {
          category: "vendor",
          name: "",
          namespace: "",
        },
        title: "",
        tracking: {
          id: "",
          // A draft's version must be 0 or 0.y.z.
          status: "draft",
          version: "0.1.0",
          initial_release_date: now,
          current_release_date: now,
          revision_history: [
            {
              date: now,
              number: "0.1.0",
              summary: "Initial draft.",
            },
          ],
        },
      },
    };
  },

  renderers: [
    ...COMMON_RENDERERS,
  ],
};
