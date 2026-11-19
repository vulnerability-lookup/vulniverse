import { afterEach, describe, expect, it, vi } from "vitest";

import { HttpRepository } from "../HttpRepository";

/** A fetch stub answering each call with the next body, recording requests. */
function stubFetch(...bodies: object[]) {
  const calls: { url: string; body: Record<string, unknown> | null }[] = [];

  vi.stubGlobal("fetch", vi.fn(async (url: string, init: RequestInit = {}) => {
    calls.push({ url, body: typeof init.body === "string" ? JSON.parse(init.body) : null });

    // The CSRF token request comes first for a mutating call.
    const body = url.endsWith("/auth/csrf-token") ? { csrfToken: "t" } : bodies.shift();

    return new Response(JSON.stringify(body), { status: 200 });
  }));

  return calls;
}

const response = (version: number) => ({
  id: 7, identifier: "CVE-2026-0001", profile: "cve-5.2.0", record: {}, isDraft: true, version,
});

afterEach(() => vi.unstubAllGlobals());

describe("HttpRepository record versions", () => {
  it("sends the version it loaded, then the one each save returned", async () => {
    const calls = stubFetch(response(3), response(4), response(5));
    const repository = new HttpRepository("/api/v1");

    await repository.loadRecord("7");
    await repository.updateRecord("7", {}, "cve-5.2.0", true);
    await repository.updateRecord("7", {}, "cve-5.2.0", true);

    const saves = calls.filter((call) => call.url === "/api/v1/records/7" && call.body);
    expect(saves.map((call) => call.body?.version)).toEqual([3, 4]);
  });

  it("sends no version for a record it never loaded", async () => {
    const calls = stubFetch(response(1));

    await new HttpRepository("/api/v1").updateRecord("7", {}, "cve-5.2.0", true);

    expect(calls.find((call) => call.body)?.body).not.toHaveProperty("version");
  });

  it("publishes naming the version it last saved", async () => {
    const calls = stubFetch(response(3), response(4), { status: "PUBLISHED" });
    const repository = new HttpRepository("/api/v1");

    await repository.loadRecord("7");
    await repository.updateRecord("7", {}, "cve-5.2.0", true);
    await repository.publishCna("vl", "7");

    const publish = calls.find((call) => call.url.endsWith("/publish/vl/7/publish"));
    expect(publish?.body).toEqual({ version: 4 });
  });
});
