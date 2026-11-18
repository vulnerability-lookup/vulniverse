import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ref } from "vue";

import type { Patch2VulnJob } from "../../../contracts";
import { stopBackgroundWatch, watchInBackground } from "../background-watch";

const editor = () => ({ notice: ref<string | null>(null) });

/** A job that answers `statuses` in turn, the last one from then on. */
function jobAnswering(...statuses: Patch2VulnJob["status"][]) {
  return vi.fn<(jobId: string) => Promise<Patch2VulnJob>>(
    async (jobId) => ({ jobId, status: statuses.shift() ?? "completed" }),
  );
}

describe("patch2vuln background watch", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it("tells the editor when the job finishes", async () => {
    const state = editor();
    const getJob = jobAnswering("running", "completed");

    watchInBackground(state, "job-a", getJob);
    await vi.advanceTimersByTimeAsync(10_000);
    expect(state.notice.value).toBeNull();

    await vi.advanceTimersByTimeAsync(10_000);
    expect(state.notice.value).toMatch(/^Patch2Vuln finished/);

    await vi.advanceTimersByTimeAsync(60_000);
    expect(getJob).toHaveBeenCalledTimes(2);
  });

  it("says when it failed, and nothing when it was canceled", async () => {
    const failed = editor();
    const canceled = editor();

    watchInBackground(failed, "job-a", jobAnswering("failed"));
    watchInBackground(canceled, "job-b", jobAnswering("canceled"));
    await vi.advanceTimersByTimeAsync(10_000);

    expect(failed.notice.value).toMatch(/^Patch2Vuln failed/);
    expect(canceled.notice.value).toBeNull();
  });

  it("stops when the panel is opened again", async () => {
    const state = editor();
    const getJob = jobAnswering("completed");

    watchInBackground(state, "job-a", getJob);
    stopBackgroundWatch(state);
    await vi.advanceTimersByTimeAsync(60_000);

    expect(getJob).not.toHaveBeenCalled();
    expect(state.notice.value).toBeNull();
  });

  it("keeps checking through an outage, and gives up on a lost job", async () => {
    const state = editor();
    const getJob = vi.fn<(jobId: string) => Promise<Patch2VulnJob>>()
      .mockRejectedValueOnce(new Error("network down"))
      .mockRejectedValueOnce(Object.assign(new Error("not found"), { status: 404 }));

    watchInBackground(state, "job-a", getJob);
    await vi.advanceTimersByTimeAsync(60_000);

    expect(getJob).toHaveBeenCalledTimes(2);
    expect(state.notice.value).toBeNull();
  });
});
