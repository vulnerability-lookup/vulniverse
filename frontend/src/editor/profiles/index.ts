import {
  EDITOR_PROFILES,
} from "./registry";


export {
  DEFAULT_PROFILE_ID,
  EDITOR_PROFILES,
  getEditorProfile,
} from "./registry";


export type {
  EditorFieldPath,
  EditorProfileDefinition,
  EditorProfileFeatures,
  ProfileRejection,
} from "./types";


export const SUPPORTED_PROFILES =
  EDITOR_PROFILES.map(
    ({
      id,
      label,
      description,
    }) => ({
      id,
      label,
      description,
    }),
  );
