import type {
  JsonFormsRendererRegistryEntry,
} from "@jsonforms/core";

import {
  COMMON_RENDERERS,
} from "./common";

import {
  CVE_RENDERERS,
} from "./cve";

import {
  GCVE_RENDERERS,
} from "./gcve";


export {
  COMMON_RENDERERS,
  CVE_RENDERERS,
  GCVE_RENDERERS,
};


/*
 * Compatibility aggregate for consumers that want the complete
 * built-in renderer set. Editor profiles compose the individual
 * renderer families directly.
 */
export const customRenderers:
  JsonFormsRendererRegistryEntry[] = [
    ...COMMON_RENDERERS,
    ...CVE_RENDERERS,
    ...GCVE_RENDERERS,
  ];
