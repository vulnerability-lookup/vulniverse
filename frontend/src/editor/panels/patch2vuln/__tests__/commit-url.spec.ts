import { describe, expect, it } from "vitest";

import { repositoryOfCommitUrl } from "../commit-url";

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
