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


/** The profiles the standalone app offers for new records: not the ones
 * whose identifiers only a host can issue (see `standalone`). */
export const STANDALONE_PROFILES =
  SUPPORTED_PROFILES.filter(
    ({ id }) =>
      EDITOR_PROFILES.find(
        (profile) => profile.id === id,
      )?.standalone !== false,
  );
