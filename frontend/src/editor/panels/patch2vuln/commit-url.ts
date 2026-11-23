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
