/**
 * The owner and repository of a commit URL on GitHub, Codeberg/Gitea or
 * GitLab (without subgroups), e.g. https://github.com/owner/repo/commit/…
 */
export function repositoryOfCommitUrl(
  url: string,
): { owner: string; repo: string } | null {
  const [, owner, repo] = /^https?:\/\/[^/]+\/([^/]+)\/([^/]+?)(?:\.git)?\/(?:-\/)?commits?\//.exec(url.trim()) ?? [];

  return owner && repo ? { owner, repo } : null;
}

// Commit URLs and uploaded patches per analysis: the limit of the
// Vulniverse and Vulnerability-Lookup backends.
export const MAX_PATCH_INPUTS = 5;

export interface Commit {
  url: string;
  repository: string;
  sha: string;
}

const GITHUB_COMMIT_PATH = /^\/([a-zA-Z0-9_.-]+)\/([a-zA-Z0-9_.-]+)\/commit\/([0-9a-fA-F]{7,64})(?:\.patch)?\/?$/;

/**
 * A GitHub commit URL as the backends accept it for analysis (Vulniverse's
 * and Vulnerability-Lookup's normalize_commit_url), or null.
 */
export function githubCommit(value: string): Commit | null {
  let url: URL;

  try {
    url = new URL(value);
  } catch {
    return null;
  }

  const match = GITHUB_COMMIT_PATH.exec(url.pathname);

  if (
    url.protocol !== "https:" || url.hostname !== "github.com" || url.port
    || url.username || url.password || url.search || url.hash || !match
  ) {
    return null;
  }

  const [, owner = "", repo = "", sha = ""] = match;

  return { url: value, repository: `${owner}/${repo}`, sha };
}
