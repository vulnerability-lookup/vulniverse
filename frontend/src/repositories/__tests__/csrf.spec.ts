import { afterEach, describe, expect, it, vi } from "vitest";

import { clearCsrfToken, getCsrfToken } from "../csrf";

afterEach(() => {
  vi.unstubAllGlobals();
  clearCsrfToken();
});

describe("getCsrfToken", () => {
  it("names the HTTP error instead of a JSON parse error, and retries next time", async () => {
    const html = new Response("<html>Bad Gateway</html>", {
      status: 502, statusText: "Bad Gateway", headers: { "Content-Type": "text/html" },
    });
    const json = new Response(JSON.stringify({ csrfToken: "t" }), {
      headers: { "Content-Type": "application/json" },
    });
    vi.stubGlobal("fetch", vi.fn<typeof fetch>()
      .mockResolvedValueOnce(html)
      .mockResolvedValueOnce(json));

    await expect(getCsrfToken()).rejects.toThrow("502 Bad Gateway");
    await expect(getCsrfToken()).resolves.toBe("t");
  });

  it("rejects an HTML page sent with status 200", async () => {
    vi.stubGlobal("fetch", vi.fn<typeof fetch>().mockResolvedValue(
      new Response("<!doctype html>", { headers: { "Content-Type": "text/html" } }),
    ));

    await expect(getCsrfToken()).rejects.toThrow("is the backend running?");
  });
});
