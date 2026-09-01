import type {
  EditorPanel,
} from "../contracts";

import TemplatesSection from "../sections/TemplatesSection.vue";

/**
 * Formerly a built-in section (always present, every host), now an
 * opt-in panel like the others — a host that wants Templates has to
 * add it to its own `panels` array. See config/vulniverse.toml.sample
 * for how the standalone app toggles it.
 */
export const templatesPanel: EditorPanel = {
  id: "templates",
  label: "Templates",
  component: TemplatesSection,
};
