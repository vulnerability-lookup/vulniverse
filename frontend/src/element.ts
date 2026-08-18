import { defineCustomElement } from "vue";

import VulniverseEditor from
  "./editor/VulniverseEditor.ce.vue";

import bootstrapCss from
  "./editor/styles/editor-bootstrap.scss?inline";

import editorCss from
  "./editor/styles/editor.scss?inline";

import jsonFormsCss from
  "@jsonforms/vue-vanilla/vanilla.css?inline";

const VulniverseEditorElement = defineCustomElement(
  VulniverseEditor,
  {
    styles: [
      bootstrapCss,
      jsonFormsCss,
      editorCss,
    ],
  },
);

if (!customElements.get("vulniverse-editor")) {
  customElements.define(
    "vulniverse-editor",
    VulniverseEditorElement,
  );
}

export type {
  EditorModule,
  EditorPanel,
  EditorRepository,
  VulnerabilityRecord,
} from "./editor/contracts";

export {
  gcveIdentifierPanel,
} from "./editor/panels";
