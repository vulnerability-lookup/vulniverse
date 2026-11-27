import { describe, expect, it } from "vitest";

import { githubCommit, repositoryOfCommitUrl } from "../commit-url";

const commit = (sha: string, repo = "acme/widget") => `https://github.com/${repo}/commit/${sha}`;

describe("repositoryOfCommitUrl", () => {
  it.each([
    ["https://github.com/apache/httpd/commit/abc123", "apache", "httpd"],
    [" https://gitlab.com/gnutls/gnutls/-/commit/abc123 ", "gnutls", "gnutls"],
    ["https://codeberg.org/forgejo/forgejo/commit/abc123", "forgejo", "forgejo"],
  ])("reads %s", (url, owner, repo) => {
    expect(repositoryOfCommitUrl(url)).toEqual({ owner, repo });
  });

  it.each([
    "https://github.com/apache/httpd",
    "https://gitlab.com/group/subgroup/repo/-/commit/abc123",
    "not a url",
  ])("ignores %s", (url) => {
    expect(repositoryOfCommitUrl(url)).toBeNull();
  });
});

describe("githubCommit", () => {
  it.each([
    commit("abcdef1"),
    `${commit("abcdef1")}.patch`,
    `${commit("abcdef1")}/`,
  ])("accepts %s", (url) => {
    expect(githubCommit(url)).toEqual({ url, repository: "acme/widget", sha: "abcdef1" });
  });

  // The backend refuses these too (normalize_commit_url).
  it.each([
    "http://github.com/acme/widget/commit/abcdef1",
    "https://gitlab.com/acme/widget/-/commit/abcdef1",
    "https://github.com:8443/acme/widget/commit/abcdef1",
    "https://user@github.com/acme/widget/commit/abcdef1",
    `${commit("abcdef1")}?diff=split`,
    `${commit("abcdef1")}#L1`,
    commit("abc12"),
    "https://github.com/acme/widget/pull/12",
    "not a url",
  ])("refuses %s", (url) => {
    expect(githubCommit(url)).toBeNull();
  });
});
