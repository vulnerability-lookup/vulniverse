import type {
  EditorPanel,
} from "../../contracts";

import TemplatesPanel from "./TemplatesPanel.vue";

export const templatesPanel: EditorPanel = {
  id: "templates",
  label: "Templates",
  component: TemplatesPanel,
};
