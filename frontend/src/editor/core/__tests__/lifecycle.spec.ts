import { ref } from "vue";
import { describe, expect, it } from "vitest";

import { RecordValidationError } from "../../contracts";
import type { EditorDocument, EditorRepository, LifecycleTransition, LoadedRecord } from "../../contracts";
import { rejectCveTransition } from "../../profiles/cve-common";
import { useEditorController } from "../controller";
import { DEFAULT_LIFECYCLE_TRANSITIONS, resolveLifecycleTransitions } from "../lifecycle";
import { useEditorState } from "../state";

const step: LifecycleTransition = {
  id: "release",
  label: "Release",
  targetIsDraft: false,
  apply: (record, input, now) => ({ ...record, released: now, note: input }),
};

const ids = (transitions: LifecycleTransition[]) => transitions.map((transition) => transition.id);

describe("resolveLifecycleTransitions", () => {
  it("adds the profile's steps to the default pair", () => {
    expect(ids(resolveLifecycleTransitions(undefined, [step]))).toEqual(["publish", "unpublish", "release"]);
  });

  it("lets a host array replace only the default pair", () => {
    // vulnerability-lookup: no drafts, but a profile's Reject remains.
    expect(ids(resolveLifecycleTransitions([], [rejectCveTransition]))).toEqual(["reject"]);
  });

  it("gives a host function the whole list", () => {
    const withoutRelease = (all: LifecycleTransition[]) => all.filter((t) => t.id !== "release");

    expect(ids(resolveLifecycleTransitions(withoutRelease, [step]))).toEqual(["publish", "unpublish"]);
  });

  it("keeps the default pair's visibility rules", () => {
    const context = { identifier: "1", profile: "cve-5.2.0", record: {}, isDraft: true };

    expect(DEFAULT_LIFECYCLE_TRANSITIONS.filter((t) => t.isVisible?.(context)).map((t) => t.id)).toEqual(["publish"]);
  });
});

describe("rejectCveTransition", () => {
  const context = (record: EditorDocument, identifier: string | null = "1") => ({
    identifier, profile: "cve-5.2.0", record, isDraft: false,
  });

  it("is offered for saved records that aren't rejected yet", () => {
    expect(rejectCveTransition.isVisible?.(context({ cveMetadata: {} }))).toBe(true);
    expect(rejectCveTransition.isVisible?.(context({ cveMetadata: {} }, null))).toBe(false);
    expect(rejectCveTransition.isVisible?.(context({ cveMetadata: { state: "REJECTED" } }))).toBe(false);
  });

  it("rejects with the dialog's reason and the step's timestamp", () => {
    const rejected = rejectCveTransition.apply!({ cveMetadata: {}, containers: { cna: {} } }, "Duplicate", "2026-11-13T10:00:00.000Z") as {
      cveMetadata: Record<string, unknown>;
    };

    expect(rejected.cveMetadata).toMatchObject({ state: "REJECTED", dateRejected: "2026-11-13T10:00:00.000Z" });
  });
});

describe("runTransition", () => {
  function setup(updateRecord: EditorRepository["updateRecord"]) {
    const state = useEditorState();
    const repository = { updateRecord } as unknown as EditorRepository;
    const controller = useEditorController({
      state,
      repository: ref(repository),
      mode: ref("edit"),
      recordId: ref("1"),
      profile: ref("cve-5.2.0"),
      onReady: () => {},
      onLoaded: () => {},
      onDeleted: () => {},
      onError: () => {},
      onDirtyChange: () => {},
    });

    state.replaceRecord({ identifier: "1", profile: "cve-5.2.0", record: { title: "draft" }, isDraft: true });

    return { state, controller };
  }

  it("saves the applied copy and shows it once saved", async () => {
    let sent: EditorDocument | undefined;
    const { state, controller } = setup(async (identifier, record, profile, isDraft): Promise<LoadedRecord> => {
      sent = record;
      return { identifier, record, profile, isDraft };
    });

    await controller.runTransition(step, "first release");

    expect(sent).toMatchObject({ title: "draft", note: "first release" });
    expect(state.record.value).toMatchObject({ note: "first release" });
    expect(state.isDraft.value).toBe(false);
  });

  it("leaves the editor's document untouched when validation rejects the save", async () => {
    const { state, controller } = setup(async () => {
      throw new RecordValidationError("invalid", [{ path: ["title"], schemaPath: [], message: "bad" }]);
    });

    await controller.runTransition(step, "first release");

    expect(state.record.value).toEqual({ title: "draft" });
    expect(state.isDraft.value).toBe(true);
    expect(state.validationErrors.value).toHaveLength(1);
  });
});
