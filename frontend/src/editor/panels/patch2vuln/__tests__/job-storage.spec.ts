import { beforeEach, describe, expect, it } from "vitest";
import { ref } from "vue";

import { recallJob, rememberJob } from "../job-storage";

/** An editor's state as far as job storage cares: the record's id. */
const editor = (identifier: string | null = null) => ({ identifier: ref(identifier) });

describe("patch2vuln job storage", () => {
  beforeEach(() => sessionStorage.clear());

  it("keeps each unsaved record's job with its own editor", () => {
    const first = editor();
    const second = editor();

    rememberJob(first, null, "job-a");

    expect(recallJob(first, null)).toBe("job-a");
    // A different new record must not pick up the first one's job.
    expect(recallJob(second, null)).toBeNull();
    expect(sessionStorage.length).toBe(0);
  });

  it("moves an unsaved record's job to its id as soon as it's saved", () => {
    const unsaved = editor();

    rememberJob(unsaved, null, "job-a");
    unsaved.identifier.value = "42";

    expect(sessionStorage.getItem("patch2vuln:42")).toBe("job-a");
    expect(recallJob(unsaved, null)).toBeNull();
  });

  it("lets a fresh editor find a job started before the record's first save", () => {
    // The standalone app opens a new editor once a new record is saved.
    const beforeSave = editor();

    rememberJob(beforeSave, null, "job-a");
    beforeSave.identifier.value = "42";

    expect(recallJob(editor("42"), "42")).toBe("job-a");
  });

  it("stores saved records' jobs by id", () => {
    rememberJob(editor("7"), "7", "job-b");

    expect(recallJob(editor("7"), "7")).toBe("job-b");
  });
});
