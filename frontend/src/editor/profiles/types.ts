import type {
  Component,
} from "vue";

import type {
  JsonFormsRendererRegistryEntry,
  JsonSchema,
  UISchemaElement,
} from "@jsonforms/core";

import type {
  EditorContext,
  EditorDocument,
  LifecycleTransition,
} from "../contracts";


export interface EditorFieldPath {
  path: string;
  title: string | null;
  type: string;
}


/**
 * How the editor recognises and shows a rejected record. Rejecting is
 * a LifecycleTransition of the profile (see lifecycleTransitions).
 */
export interface ProfileRejection {
  isRejected(
    document: EditorDocument,
  ): boolean;

  editorComponent?: Component;
}


export interface EditorProfileFeatures {
  cnaPublication?: boolean;
}


export interface EditorProfileDefinition {
  id: string;
  label: string;
  description: string;

  schema: JsonSchema;
  uiSchema: UISchemaElement;

  fieldPaths: EditorFieldPath[];

  createEmptyDocument():
    EditorDocument;

  renderers:
    JsonFormsRendererRegistryEntry[];

  previewComponent?: Component;

  rejection?: ProfileRejection;

  /** Profile-specific lifecycle steps, e.g. Reject or a release. */
  lifecycleTransitions?: LifecycleTransition[];

  /**
   * The profile's steps replace the default Publish/Revert pair, for a
   * format whose own steps decide when a record is shared (CSAF).
   */
  replacesDefaultTransitions?: boolean;

  /**
   * A warning shown before a plain Save of changed content, or null.
   * CSAF: a released version must not change; changes go through a
   * new version.
   */
  saveWarning?(context: EditorContext): string | null;

  features?: EditorProfileFeatures;
}
