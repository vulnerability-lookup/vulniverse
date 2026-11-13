import {
  markRaw,
} from "vue";

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
  CSAF_RENDERERS,
} from "../renderers";

import type {
  LifecycleTransition,
} from "../contracts";

import CsafReleaseDialog from
  "./CsafReleaseDialog.vue";

import { CsafPreviewSection } from
  "../sections/preview/csaf";

import {
  isReleased,
  releaseCsaf,
} from "./csaf-release";

import type {
  ReleaseInput,
} from "./csaf-release";

import type {
  EditorProfileDefinition,
} from "./types";


// CSAF 2.1 fixes the value: a document must name exactly this schema.
const CSAF_SCHEMA_URL =
  "https://docs.oasis-open.org/csaf/csaf/v2.1/schema/csaf.json";


/*
 * CSAF's own steps replace Publish/Revert: a document is shared in
 * Vulniverse as a draft or by releasing a version (csaf-release.ts).
 * "Make private" only changes who can see it in Vulniverse. It comes
 * right after the Share steps, so the visibility toggle keeps its place
 * in the header and the release step always follows it.
 */
const CSAF_TRANSITIONS: LifecycleTransition[] = [
  {
    id: "csaf-share-draft",
    label: "Share draft",
    targetIsDraft: false,
    tone: "success",
    notice: "Draft shared.",
    isVisible: (context) => context.isDraft && !isReleased(context.record),
  },
  {
    id: "csaf-share",
    label: "Share",
    targetIsDraft: false,
    tone: "success",
    notice: "Advisory shared.",
    isVisible: (context) => context.isDraft && isReleased(context.record),
  },
  {
    id: "csaf-make-private",
    label: "Make private",
    targetIsDraft: true,
    tone: "warning",
    notice: "Advisory made private.",
    isVisible: (context) => !context.isDraft,
  },
  {
    id: "csaf-release",
    label: "Release…",
    targetIsDraft: false,
    tone: "success",
    notice: "Advisory released.",
    isVisible: (context) => !isReleased(context.record),
    dialog: markRaw(CsafReleaseDialog),
    apply: (record, input, now) => releaseCsaf(record, input as ReleaseInput, now),
  },
  {
    id: "csaf-update",
    label: "Update…",
    targetIsDraft: false,
    tone: "success",
    notice: "New version released.",
    isVisible: (context) => isReleased(context.record),
    dialog: markRaw(CsafReleaseDialog),
    apply: (record, input, now) => releaseCsaf(record, input as ReleaseInput, now),
  },
];


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
    ...CSAF_RENDERERS,
  ],

  previewComponent:
    markRaw(CsafPreviewSection),

  lifecycleTransitions: CSAF_TRANSITIONS,

  replacesDefaultTransitions: true,

  // A released version must not change (spec 3.1.19, rule 2); Save is
  // still allowed, e.g. for a typo, after this warning.
  saveWarning: (context) => (
    !context.isDraft && isReleased(context.record)
      ? "This advisory is released. The CSAF rules say a released version "
        + "must not change: changes go into a new version with Update…."
      : null
  ),
};
