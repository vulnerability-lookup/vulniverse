import type {
  Component,
} from "vue";

import type {
  JsonFormsRendererRegistryEntry,
  JsonSchema,
  UISchemaElement,
} from "@jsonforms/core";

import type {
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

  features?: EditorProfileFeatures;
}
