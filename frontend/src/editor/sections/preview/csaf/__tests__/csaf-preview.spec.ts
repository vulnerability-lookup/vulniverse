import { describe, expect, it } from "vitest";

import { label, scores } from "../csaf-preview";

describe("scores", () => {
  it("lists CVSS (newest first), EPSS, qualitative severity and SSVC", () => {
    expect(scores({
      cvss_v3: { version: "3.1", baseScore: 6.1, baseSeverity: "MEDIUM", vectorString: "CVSS:3.1/AV:L" },
      cvss_v4: { version: "4.0", baseScore: 9.3, baseSeverity: "CRITICAL", vectorString: "CVSS:4.0/AV:N" },
      epss: { probability: "0.0009", percentile: "0.38" },
      qualitative_severity_rating: "high",
      ssvc_v2: { timestamp: "2024-01-01T00:00:00Z", selections: [{ key: "E", values: [{ key: "A" }] }] },
    })).toEqual([
      { kind: "CVSS 4.0", value: "9.3 CRITICAL", detail: "CVSS:4.0/AV:N" },
      { kind: "CVSS 3.1", value: "6.1 MEDIUM", detail: "CVSS:3.1/AV:L" },
      { kind: "EPSS", value: "probability 0.0009", detail: "percentile 0.38" },
      { kind: "Severity", value: "high", detail: "" },
      { kind: "SSVC", value: "E: A", detail: "2024-01-01T00:00:00Z" },
    ]);
  });

  it("tolerates incomplete drafts", () => {
    expect(scores({ cvss_v3: {} })).toEqual([]);
    expect(scores({ cvss_v2: { baseScore: 7.5 } })).toEqual([{ kind: "CVSS 2.0", value: "7.5", detail: "" }]);
  });
});

describe("label", () => {
  it("humanizes CSAF enum values", () => {
    expect(label("known_not_affected")).toBe("Known not affected");
  });
});
