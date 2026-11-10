import type {
  EditorPanel,
} from "../../contracts";

import RecordStatsPanel from "./RecordStatsPanel.vue";

export const recordStatsPanel: EditorPanel = {
  id: "stats",
  label: "Stats",
  component: RecordStatsPanel,
  // The panel reads containers.cna, which only CVE-shaped records have.
  isVisible(context) {
    return ["cve-5.2.0", "gcve-bcp-05-1.7"].includes(context.profile);
  },
};
