import {
  recordStatsPanel,
} from "./record-stats";

import {
  vulnerabilityLookupPanel,
} from "./vulnerability-lookup";

import {
  cveProgramPanel,
} from "./cve-program";

import type {
  EditorPanel,
} from "../contracts";

/*
 * One file per panel (mirrors editor/modules/index.ts). Hosts opt in
 * by passing some subset of this list (or their own panels entirely)
 * to VulniverseEditor's `panels` prop.
 *
 * gcveIdentifierPanel is deliberately NOT in this list — it's useful
 * only to hosts with their own GCVE-only storage constraint (see its
 * own file), so it's exported individually below instead of being
 * on by default for every host.
 */
export const BUILTIN_PANELS: EditorPanel[] = [
  recordStatsPanel,
  vulnerabilityLookupPanel,
  cveProgramPanel,
];

export { recordStatsPanel };
export { vulnerabilityLookupPanel };
export { cveProgramPanel };
export { gcveIdentifierPanel } from "./gcve-identifier";
