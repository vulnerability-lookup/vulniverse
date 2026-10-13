import type {
  LoadedRecord,
} from "../contracts";

import {
  getEditorProfile,
} from "../profiles";

export function createEmptyRecord(
  profileId: string,
): LoadedRecord {
  const profile = getEditorProfile(profileId);

  return {
    identifier: "",
    profile: profile.id,
    isDraft: true,
    record: profile.createEmptyDocument(),
  };
}
