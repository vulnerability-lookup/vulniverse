import type {
  Patch2VulnJob,
} from "../../contracts";

import type {
  EditorState,
} from "../../core/state";

/*
 * While the Patch2Vuln panel is closed (another panel or section is
 * open), its job is still checked now and then, and the editor's toast
 * says when it's done. Reopening the panel stops this: the panel then
 * watches the job itself again.
 */

const CHECK_EVERY_MS = 10_000;

const MESSAGES: Partial<Record<Patch2VulnJob["status"], string>> = {
  completed: "Patch2Vuln finished. Open the Patch2Vuln panel to review the result.",
  failed: "Patch2Vuln failed. Open the Patch2Vuln panel for details.",
};

// One watcher per editor: the stop function.
const watchers = new WeakMap<object, () => void>();

export function watchInBackground(
  editor: Pick<EditorState, "notice">,
  jobId: string,
  getJob: (jobId: string) => Promise<Patch2VulnJob>,
): void {
  stopBackgroundWatch(editor);

  let stopped = false;
  let timer: ReturnType<typeof setTimeout> | undefined;

  async function check(): Promise<void> {
    try {
      const job = await getJob(jobId);

      if (stopped) {
        return;
      }

      if (job.status !== "queued" && job.status !== "running") {
        watchers.delete(editor);
        // Canceled: someone pressed Cancel, nothing to announce.
        editor.notice.value = MESSAGES[job.status] ?? editor.notice.value;
        return;
      }
    } catch (error) {
      // Gone (404): nothing left to wait for. Other failures: an outage,
      // keep checking as the panel does.
      if ((error as { status?: number }).status === 404 || stopped) {
        watchers.delete(editor);
        return;
      }
    }

    timer = setTimeout(() => void check(), CHECK_EVERY_MS);
  }

  watchers.set(editor, () => {
    stopped = true;
    clearTimeout(timer);
  });
  timer = setTimeout(() => void check(), CHECK_EVERY_MS);
}

export function stopBackgroundWatch(editor: object): void {
  watchers.get(editor)?.();
  watchers.delete(editor);
}
