import { describe, expect, it, vi } from "vitest";
import { nextTick, ref } from "vue";

import type { EditorDocument, EditorRepository, LoadedRecord } from "../../contracts";
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
  const loadRecord = vi.fn<(identifier: string) => Promise<LoadedRecord>>(async () => saved);
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

describe("a repository set after the editor started", () => {
  // As in a framework that binds properties after inserting the element.
  function editorWithoutRepository(mode: "create" | "edit") {
    const state = useEditorState();
    const loadRecord = vi.fn<(identifier: string) => Promise<LoadedRecord>>(async () => saved);
    const onError = vi.fn<(error: Error) => void>();
    const repository = ref<EditorRepository | undefined>(undefined);
    const controller = useEditorController({
      state,
      repository,
      mode: ref(mode),
      recordId: ref(mode === "edit" ? "42" : undefined),
      profile: ref("gcve-bcp-05-1.7"),
      onReady: () => {},
      onLoaded: () => {},
      onDeleted: () => {},
      onError,
      onDirtyChange: () => {},
    });
    const arrive = () => {
      repository.value = { loadRecord } as unknown as EditorRepository;
    };
    return { state, loadRecord, onError, controller, arrive };
  }

  it("waits without an error, then loads the record", async () => {
    const { state, loadRecord, onError, controller, arrive } = editorWithoutRepository("edit");

    await controller.load();
    expect(onError).not.toHaveBeenCalled();
    expect(state.loadError.value).toBeNull();

    arrive();
    await vi.waitFor(() => expect(state.record.value).toEqual({ title: "Saved" }));
    expect(loadRecord).toHaveBeenCalledWith("42");
  });

  it("keeps a new record's edits in create mode", async () => {
    const { state, loadRecord, controller, arrive } = editorWithoutRepository("create");

    await controller.load();
    state.record.value = { ...state.record.value!, title: "Typed already" };
    arrive();
    await Promise.resolve();

    expect(loadRecord).not.toHaveBeenCalled();
    expect(state.record.value?.title).toBe("Typed already");
  });
});

describe("saving", () => {
  it("accepts a repository that returns the record it was given", async () => {
    const state = useEditorState();
    const createRecord = vi.fn<(record: object, profile: string, isDraft: boolean) => Promise<LoadedRecord>>(async (record, profile, isDraft) =>
      ({ identifier: "1", record, profile, isDraft }) as unknown as LoadedRecord);
    const onError = vi.fn<(error: Error) => void>();
    const controller = useEditorController({
      state,
      repository: ref({ createRecord } as unknown as EditorRepository),
      mode: ref("create"),
      recordId: ref(undefined),
      profile: ref("gcve-bcp-05-1.7"),
      onReady: () => {},
      onLoaded: () => {},
      onDeleted: () => {},
      onError,
      onDirtyChange: () => {},
    });
    await controller.load();
    (state.record.value as Record<string, unknown>).title = "Edited";

    await controller.save(true);

    expect(onError).not.toHaveBeenCalled();
    expect(state.identifier.value).toBe("1");
    expect(state.record.value).toMatchObject({ title: "Edited" });
  });
});

describe("create mode with an initial record", () => {
  function editorWithInitialRecord() {
    const state = useEditorState();
    const initialRecord = ref<EditorDocument | undefined>({ title: "Generated" } as unknown as EditorDocument);
    const createRecord = vi.fn<(record: object, profile: string, isDraft: boolean) => Promise<LoadedRecord>>(
      async () => saved,
    );
    const controller = useEditorController({
      state,
      repository: ref({ createRecord, loadRecord: async () => saved } as unknown as EditorRepository),
      mode: ref("create"),
      recordId: ref(undefined),
      profile: ref("gcve-bcp-05-1.7"),
      initialRecord,
      onReady: () => {},
      onLoaded: () => {},
      onDeleted: () => {},
      onError: () => {},
      onDirtyChange: () => {},
    });
    return { state, initialRecord, createRecord, controller };
  }

  it("starts from it, unchanged and without an identifier", async () => {
    const { state, initialRecord, controller } = editorWithInitialRecord();

    await controller.load();

    expect(state.record.value).toEqual({ title: "Generated" });
    expect(state.record.value).not.toBe(initialRecord.value);
    expect(state.identifier.value).toBeFalsy();
    expect(state.dirty.value).toBe(false);
  });

  it("creates the record on the first save", async () => {
    const { createRecord, controller } = editorWithInitialRecord();
    await controller.load();

    await controller.save();

    expect(createRecord).toHaveBeenCalledWith({ title: "Generated" }, "gcve-bcp-05-1.7", expect.anything());
  });

  it("starts a new record when another one is assigned, even after saving", async () => {
    const { state, initialRecord, controller } = editorWithInitialRecord();
    await controller.load();
    await controller.save();

    initialRecord.value = { title: "Next" } as unknown as EditorDocument;
    await nextTick();
    await nextTick();

    expect(state.record.value).toEqual({ title: "Next" });
    expect(state.identifier.value).toBeFalsy();
  });
});
