import { describe, expect, it, vi } from "vitest";
import { ref } from "vue";

import type { EditorRepository, LoadedRecord } from "../../contracts";
import { useEditorController } from "../controller";
import { useEditorState } from "../state";

const saved: LoadedRecord = {
  identifier: "42",
  record: { title: "Saved" },
  profile: "gcve-bcp-05-1.7",
  isDraft: true,
} as unknown as LoadedRecord;

function createModeEditor() {
  const state = useEditorState();
  const loadRecord = vi.fn(async () => saved);
  const controller = useEditorController({
    state,
    repository: ref({ loadRecord } as unknown as EditorRepository),
    mode: ref("create"),
    recordId: ref(undefined),
    profile: ref("gcve-bcp-05-1.7"),
    onReady: () => {},
    onLoaded: () => {},
    onDeleted: () => {},
    onError: () => {},
    onDirtyChange: () => {},
  });
  return { state, loadRecord, controller };
}

describe("reloading in create mode", () => {
  it("starts empty before the first save", async () => {
    const { state, loadRecord, controller } = createModeEditor();

    await controller.load();

    expect(loadRecord).not.toHaveBeenCalled();
    expect(state.identifier.value).toBeFalsy();
  });

  it("loads the saved record after the first save", async () => {
    const { state, loadRecord, controller } = createModeEditor();
    await controller.load();
    state.identifier.value = "42";

    await controller.load();

    expect(loadRecord).toHaveBeenCalledWith("42");
    expect(state.record.value).toEqual({ title: "Saved" });
  });
});
