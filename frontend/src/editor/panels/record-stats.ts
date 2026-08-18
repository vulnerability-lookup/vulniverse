import type {
  EditorPanel,
} from "../contracts";

import RecordStatsPanel from "./RecordStatsPanel.vue";

/**
 * A minimal panel module: adds a "Stats" nav tab rendering
 * RecordStatsPanel.vue. Template for a new one: create panels/<id>.ts
 * exporting an EditorPanel + a companion .vue component, then list it
 * in panels/index.ts.
 */
export const recordStatsPanel: EditorPanel = {
  id: "stats",
  label: "Stats",
  component: RecordStatsPanel,
};
