import {
  recordStatsPanel,
} from "./record-stats";

import type {
  EditorPanel,
} from "../contracts";

/*
 * One file per panel (mirrors editor/modules/index.ts). Hosts opt in
 * by passing some subset of this list (or their own panels entirely)
 * to VulniverseEditor's `panels` prop.
 */
export const BUILTIN_PANELS: EditorPanel[] = [
  recordStatsPanel,
];

export { recordStatsPanel };
