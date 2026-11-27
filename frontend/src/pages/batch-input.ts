/*
 * Reads the Patch2Vuln batch form: one line per vulnerability, its
 * commits separated by spaces or commas. The preview shows what will be
 * analysed and what the backend would refuse.
 */

import {
  githubCommit,
  MAX_PATCH_INPUTS,
} from "@/editor/panels/patch2vuln/commit-url";

import type {
  Commit,
} from "@/editor/panels/patch2vuln/commit-url";

export const MAX_VULNERABILITIES = 50;
// One Patch2Vuln analysis takes as many commits as the panel's.
export const MAX_COMMITS_PER_VULNERABILITY = MAX_PATCH_INPUTS;

export interface BatchLine {
  commits: Commit[];
  /** What's wrong with the line; null when it can be submitted. */
  error: string | null;
}

export function parseBatchInput(text: string): BatchLine[] {
  const lines = new Map<string, BatchLine>();

  for (const raw of text.split("\n")) {
    const tokens = raw.split(/[\s,]+/).filter(Boolean);

    if (tokens.length === 0) continue;

    const commits = new Map<string, Commit>();
    const invalid: string[] = [];

    for (const token of tokens) {
      const commit = githubCommit(token);

      if (commit) {
        // The same commit twice is analysed once (as the backend does).
        commits.set(`${commit.repository}@${commit.sha}`, commit);
      } else {
        invalid.push(token);
      }
    }

    const key = [...commits.keys()].join(" ");
    let error: string | null = null;

    if (invalid.length > 0) {
      error = `Not a GitHub commit URL: ${invalid.join(", ")}`;
    } else if (commits.size > MAX_COMMITS_PER_VULNERABILITY) {
      error = `${commits.size} commits; at most ${MAX_COMMITS_PER_VULNERABILITY} per vulnerability`;
    }

    // An identical line is the same vulnerability; invalid ones all show.
    lines.set(error ? `invalid ${lines.size}` : key, { commits: [...commits.values()], error });
  }

  return [...lines.values()];
}
