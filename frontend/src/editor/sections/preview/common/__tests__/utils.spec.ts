import { describe, expect, it } from "vitest";

import { safeUrl } from "../utils";

describe("safeUrl", () => {
  it("keeps http(s) links", () => {
    expect(safeUrl("https://example.com/a")).toBe("https://example.com/a");
    expect(safeUrl("HTTP://example.com")).toBe("HTTP://example.com");
  });

  it("drops script, data and non-string values", () => {
    expect(safeUrl("javascript:alert(1)")).toBeUndefined();
    expect(safeUrl(" javascript:alert(1)")).toBeUndefined();
    expect(safeUrl("data:text/html,<script>alert(1)</script>")).toBeUndefined();
    expect(safeUrl(42)).toBeUndefined();
  });
});
