import {
  markRaw,
} from "vue";

import type {
  EditorPanel,
} from "../../contracts";

import CompareVulnerabilitiesPanel from
  "./CompareVulnerabilitiesPanel.vue";


export const compareVulnerabilitiesPanel:
  EditorPanel = {
    id: "compare-vulnerabilities",
    label: "Compare vulnerabilities",

    component:
      markRaw(
        CompareVulnerabilitiesPanel,
      ),

    isVisible(context) {
      return context.profile === "csaf-2.1";
    },
  };
