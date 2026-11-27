import type {
  EditorDocument,
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

const GENERATOR = { engine: `Vulniverse v${__VULNIVERSE_VERSION__}` };

// Names the editor in CVE/GCVE records (containers.cna.x_generator, the
// convention Vulnogram started). OSV records have no CNA container and
// are returned as they are.
export function withGenerator(
  record: EditorDocument,
): EditorDocument {
  const containers = record.containers as Record<string, unknown> | undefined;
  const cna = containers?.cna;

  if (!cna || typeof cna !== "object" || Array.isArray(cna)) {
    return record;
  }

  return {
    ...record,
    containers: {
      ...containers,
      cna: { ...cna, x_generator: GENERATOR },
    },
  };
}
