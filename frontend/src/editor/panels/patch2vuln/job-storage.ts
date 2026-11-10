/*
 * Where the panel remembers its patch2vuln job, so it survives
 * switching panels.
 *
 * Saved records use sessionStorage, keyed by the record id. Unsaved
 * records have no id: keying them all as "unsaved" made every new
 * record in a tab pick up the same job, so they keep their job with
 * their own editor instead (one editor per new record). An unsaved
 * record doesn't survive a reload anyway.
 */

const unsavedJobs = new WeakMap<object, string>();

function storageKey(
  identifier: string,
): string {
  return `patch2vuln:${identifier}`;
}


export function rememberJob(
  editor: object,
  identifier: string | null,
  jobId: string,
): void {
  if (identifier) {
    sessionStorage.setItem(storageKey(identifier), jobId);
  } else {
    unsavedJobs.set(editor, jobId);
  }
}


export function recallJob(
  editor: object,
  identifier: string | null,
): string | null {
  if (!identifier) {
    return unsavedJobs.get(editor) ?? null;
  }

  // First recall since the record was saved: its job moves to the id.
  const unsavedJobId = unsavedJobs.get(editor);

  if (unsavedJobId) {
    sessionStorage.setItem(storageKey(identifier), unsavedJobId);
    unsavedJobs.delete(editor);
  }

  return sessionStorage.getItem(storageKey(identifier));
}
