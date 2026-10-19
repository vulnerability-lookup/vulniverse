import {
  markRaw,
} from "vue";

import type {
  EditorPanel,
} from "../../contracts";

import RecordQualityPanel from
  "./RecordQualityPanel.vue";


export const recordQualityPanel:
  EditorPanel = {
    id: "record-quality",
    label: "Record quality",

    component:
      markRaw(
        RecordQualityPanel,
      ),

    isVisible(context) {
      return [
        "cve-5.2.0",
        "gcve-bcp-05-1.7",
      ].includes(
        context.profile,
      );
    },
  };
