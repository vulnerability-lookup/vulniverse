import type {
  EditorPanel,
} from "../../contracts";

import RecordStatsPanel from "./RecordStatsPanel.vue";

export const recordStatsPanel: EditorPanel = {
  id: "stats",
  label: "Stats",
  component: RecordStatsPanel,
};
