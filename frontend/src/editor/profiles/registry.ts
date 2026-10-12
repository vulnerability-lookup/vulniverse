import {
  cve52Profile,
} from "./cve-5.2.0";

import {
  gcveBcp05Profile,
} from "./gcve-bcp-05-1.7";

import type {
  EditorProfileDefinition,
} from "./types";


export const DEFAULT_PROFILE_ID =
  "gcve-bcp-05-1.7";


export const EDITOR_PROFILES:
  EditorProfileDefinition[] = [
  cve52Profile,
  gcveBcp05Profile,
];


const PROFILE_MAP =
  new Map(
    EDITOR_PROFILES.map(
      (profile) => [
        profile.id,
        profile,
      ],
    ),
  );


export function getEditorProfile(
  profileId: string,
): EditorProfileDefinition {
  const profile =
    PROFILE_MAP.get(profileId);

  if (!profile) {
    throw new Error(
      `Unsupported editor profile: ${profileId}`,
    );
  }

  return profile;
}
