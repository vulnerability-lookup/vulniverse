import {
  rankWith,
  schemaMatches,
  uiTypeIs,
  and,
} from "@jsonforms/core";

import type {
  JsonFormsRendererRegistryEntry,
} from "@jsonforms/core";

import CvssRenderer from
  "./CvssRenderer.vue";

import {
  cvssVersions,
} from "./cvss";


export const CSAF_RENDERERS:
  JsonFormsRendererRegistryEntry[] = [
    {
      renderer:
        CvssRenderer,

      // FIRST CVSS objects (metrics content.cvss_v2/v3/v4). Above the
      // composite-object JSON box (5) that cvss_v3/v4 would get otherwise.
      tester:
        rankWith(
          7,
          and(
            uiTypeIs("Control"),
            schemaMatches((schema) => cvssVersions(schema).length > 0),
          ),
        ),
    },
  ];
