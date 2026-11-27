/*
 * The public types of the <vulniverse-editor> package, bundled into one
 * self-contained vulniverse-editor.d.ts by `npm run build:types`
 * (scripts/build-types.mjs). It mirrors element.ts's exports, but
 * declares the panels and actions instead of importing them, so the
 * type bundler never has to read .vue files. Keep the two in sync.
 */

import type {
  EditorAction,
  EditorDocument,
  EditorPanel,
  EditorRepository,
} from "./editor/contracts";

import type {
  ThemePreference,
} from "./editor/core/theme";

export type {
  AttackTechniquePrediction,
  EditorAction,
  EditorContext,
  EditorDocument,
  EditorPanel,
  EditorRepository,
  LifecycleTransition,
  LoadedRecord,
  SeverityPrediction,
  ValidationError,
  ValidationResult,
} from "./editor/contracts";

export type {
  ThemePreference,
} from "./editor/core/theme";

export {
  RecordValidationError,
} from "./editor/contracts";

export {
  EditorRepositoryError,
} from "./editor/core/errors";

/** The editor's version, e.g. "1.0.0". */
export declare const version: string;

/** Download the record as JSON, an HTML page or a PDF. */
export declare const downloadAction: EditorAction;
/** A short guided tour of the editor. */
export declare const tutorialAction: EditorAction;

/** Saved field values; needs the repository's template methods. */
export declare const templatesPanel: EditorPanel;
/** A completeness score, computed in the browser; needs no repository method. */
export declare const recordQualityPanel: EditorPanel;
/** Drafts fields from a patch; needs the Patch2Vuln methods. */
export declare const patch2vulnPanel: EditorPanel;
/** ML-Gateway severity and ATT&CK suggestions; needs the classify methods. */
export declare const mlGatewayPanel: EditorPanel;
/** Reserve and publish with Vulnerability-Lookup; needs the CNA methods. */
export declare const vulnerabilityLookupPanel: EditorPanel;
/** Publish to the CVE Program; needs the CNA methods. */
export declare const cveProgramPanel: EditorPanel;

/*
 * The editor's own copy of Vue's runtime, for writing panels without a
 * build step. Typed loosely: install `vue` and use its types if you
 * write panels in TypeScript.
 */
/* eslint-disable @typescript-eslint/no-explicit-any */
export declare const defineComponent: (...args: any[]) => any;
export declare const h: (...args: any[]) => any;
export declare const onMounted: (...args: any[]) => any;
export declare const ref: (...args: any[]) => any;
export declare const watch: (...args: any[]) => any;
/* eslint-enable @typescript-eslint/no-explicit-any */

/** The `<vulniverse-editor>` element. */
export interface VulniverseEditorElement extends HTMLElement {
  /** Loads and saves records. Required. */
  repository?: EditorRepository;
  /** `"create"` (the default) or `"edit"`; also the `mode` attribute. */
  mode?: "create" | "edit";
  /** The record to edit; also the `record-id` attribute. */
  recordId?: string;
  /** The profile of a new record, e.g. `"gcve-bcp-05-1.7"` (the default). */
  profile?: string;
  /**
   * Create mode: the new record's content instead of an empty record,
   * e.g. a generated draft. It is copied, and only saved when the user
   * saves. Assigning another object starts a new record.
   */
  initialRecord?: EditorDocument;
  panels?: EditorPanel[];
  actions?: EditorAction[];
  /** `"auto"` (the default) follows the page, else `"light"` or `"dark"`. */
  theme?: ThemePreference;
}

declare global {
  interface HTMLElementTagNameMap {
    "vulniverse-editor": VulniverseEditorElement;
  }
}
