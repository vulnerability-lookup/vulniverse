import { describe, expect, it } from "vitest";

import { parseBatchInput } from "../batch-input";

const commit = (sha: string, repo = "acme/widget") => `https://github.com/${repo}/commit/${sha}`;

describe("parseBatchInput", () => {
  it("reads one vulnerability per line, its commits separated by spaces or commas", () => {
    const lines = parseBatchInput(
      `${commit("aaaaaaa")}\n\n  ${commit("bbbbbbb")}, ${commit("ccccccc")} ${commit("bbbbbbb")}\n`,
    );

    expect(lines.map((line) => [line.commits.map((c) => c.sha), line.error])).toEqual([
      [["aaaaaaa"], null],
      [["bbbbbbb", "ccccccc"], null],
    ]);
  });

  it("merges a repeated line", () => {
    expect(parseBatchInput(`${commit("aaaaaaa")}\n${commit("aaaaaaa")}.patch`)).toHaveLength(1);
  });

  it("marks lines the backend would refuse", () => {
    const tooMany = ["1111111", "2222222", "3333333", "4444444", "5555555", "6666666"].map((sha) => commit(sha));
    const [invalid, crowded] = parseBatchInput(`${commit("aaaaaaa")} https://example.com/x\n${tooMany.join(" ")}`);

    expect(invalid?.error).toBe("Not a GitHub commit URL: https://example.com/x");
    expect(crowded?.error).toBe("6 commits; at most 5 per vulnerability");
  });
});
