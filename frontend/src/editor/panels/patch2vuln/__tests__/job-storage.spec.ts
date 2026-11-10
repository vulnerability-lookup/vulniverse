import { beforeEach, describe, expect, it } from "vitest";

import { recallJob, rememberJob } from "../job-storage";

describe("patch2vuln job storage", () => {
  beforeEach(() => sessionStorage.clear());

  it("keeps each unsaved record's job with its own editor", () => {
    const first = {};
    const second = {};

    rememberJob(first, null, "job-a");

    expect(recallJob(first, null)).toBe("job-a");
    // A different new record must not pick up the first one's job.
    expect(recallJob(second, null)).toBeNull();
    expect(sessionStorage.length).toBe(0);
  });

  it("moves an unsaved record's job to its id once saved", () => {
    const editor = {};

    rememberJob(editor, null, "job-a");

    expect(recallJob(editor, "42")).toBe("job-a");
    expect(sessionStorage.getItem("patch2vuln:42")).toBe("job-a");
    expect(recallJob(editor, null)).toBeNull();
  });

  it("stores saved records' jobs by id", () => {
    rememberJob({}, "7", "job-b");

    expect(recallJob({}, "7")).toBe("job-b");
  });
});
