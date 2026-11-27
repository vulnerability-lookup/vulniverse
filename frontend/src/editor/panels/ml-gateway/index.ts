import {
  ICONS,
} from "../../icons";

import { markRaw } from "vue";

import type {
  EditorPanel,
} from "../../contracts";

import MlGatewayPanel from "./MlGatewayPanel.vue";


export const mlGatewayPanel: EditorPanel = {
  id: "ml-gateway",
  label: "ML suggestions",
  icon: ICONS.sparkle,

  component: markRaw(MlGatewayPanel),

  isVisible(context) {
    // Only CVE-format records have taxonomyMappings for the techniques.
    return [
      "cve-5.2.0",
      "gcve-bcp-05-1.7",
    ].includes(context.profile);
  },
};
