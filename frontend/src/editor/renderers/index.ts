import type {
  JsonFormsRendererRegistryEntry,
} from "@jsonforms/core";

import {
  COMMON_RENDERERS,
} from "./common";

import {
  CSAF_RENDERERS,
} from "./csaf";

import {
  CVE_RENDERERS,
} from "./cve";

import {
  GCVE_RENDERERS,
} from "./gcve";

import {
  OSV_RENDERERS,
} from "./osv";


export {
  COMMON_RENDERERS,
  CSAF_RENDERERS,
  CVE_RENDERERS,
  GCVE_RENDERERS,
  OSV_RENDERERS,
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
    ...OSV_RENDERERS,
    ...CSAF_RENDERERS,
  ];
