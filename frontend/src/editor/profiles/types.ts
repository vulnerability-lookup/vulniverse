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
} from "../contracts";


export interface EditorFieldPath {
  path: string;
  title: string | null;
  type: string;
}


export interface ProfileRejection {
  isRejected(
    document: EditorDocument,
  ): boolean;

  reject(
    document: EditorDocument,
    reason: string,
    rejectedAt?: string,
  ): EditorDocument;

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

  features?: EditorProfileFeatures;
}
