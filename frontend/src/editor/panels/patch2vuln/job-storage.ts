import {
  watch,
} from "vue";

import type {
  Ref,
} from "vue";

/*
 * Where the panel remembers its patch2vuln job, so it survives
 * switching panels.
 *
 * Saved records use sessionStorage, keyed by the record id. Unsaved
 * records have no id: keying them all as "unsaved" made every new
 * record in a tab pick up the same job, so they keep their job with
 * their own editor instead (one editor per new record), until the
 * record's first save gives it an id. The job then moves to
 * sessionStorage right away: in the standalone app, that save takes a
 * new record to its own address, which opens a fresh editor that must
 * find the job by id. An unsaved record doesn't survive a reload anyway.
 */

/** The part of the editor state this needs: the record's id, once saved. */
interface Editor {
  identifier: Ref<string | null>;
}

const unsavedJobs = new WeakMap<Editor, string>();

function storageKey(
  identifier: string,
): string {
  return `patch2vuln:${identifier}`;
}


export function rememberJob(
  editor: Editor,
  identifier: string | null,
  jobId: string,
): void {
  if (identifier) {
    sessionStorage.setItem(storageKey(identifier), jobId);
    return;
  }

  unsavedJobs.set(editor, jobId);

  // Synchronous: the first save may replace this editor right after.
  const stop = watch(editor.identifier, (savedAs) => {
    if (!savedAs || unsavedJobs.get(editor) !== jobId) {
      return;
    }

    sessionStorage.setItem(storageKey(savedAs), jobId);
    unsavedJobs.delete(editor);
    stop();
  }, { flush: "sync" });
}


export function recallJob(
  editor: Editor,
  identifier: string | null,
): string | null {
  return identifier
    ? sessionStorage.getItem(storageKey(identifier))
    : unsavedJobs.get(editor) ?? null;
}
