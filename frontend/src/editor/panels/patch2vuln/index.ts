import { markRaw } from "vue";

import type {
  EditorPanel,
} from "../../contracts";

import Patch2VulnPanel from "./Patch2VulnPanel.vue";


export const patch2vulnPanel: EditorPanel = {
  id: "patch2vuln",
  label: "Patch2Vuln",

  component: markRaw(Patch2VulnPanel),

  isVisible(context) {
    return context.profile === "cve-5.2.0";
  },
};
