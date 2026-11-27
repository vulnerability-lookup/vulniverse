import { describe, expect, it } from "vitest";

import {
  addAttackTechniques,
  attackTechniqueIds,
  cvssSeverity,
  englishDescription,
} from "../apply";

function record(cna: Record<string, unknown>, cveMetadata: Record<string, unknown> = {}) {
  return { cveMetadata, containers: { cna } };
}

describe("englishDescription", () => {
  it("picks the English description, also en-US", () => {
    const value = record({
      descriptions: [
        { lang: "fr", value: "Injection SQL" },
        { lang: "en-US", value: " SQL injection " },
      ],
    });

    expect(englishDescription(value)).toBe("SQL injection");
  });

  it("is empty without one", () => {
    expect(englishDescription(record({ descriptions: [{ lang: "de", value: "x" }] }))).toBe("");
    expect(englishDescription({ id: "OSV-1" })).toBe("");
  });
});

describe("cvssSeverity", () => {
  it("prefers CVSS 4.0 over 3.1", () => {
    const value = record({
      metrics: [
        { cvssV3_1: { baseSeverity: "MEDIUM" } },
        { cvssV4_0: { baseSeverity: "HIGH" } },
      ],
    });

    expect(cvssSeverity(value)).toBe("HIGH");
  });

  it("is null without CVSS", () => {
    expect(cvssSeverity(record({ metrics: [{ other: {} }] }))).toBeNull();
  });
});

describe("addAttackTechniques", () => {
  it("creates the ATT&CK mapping, also without a record ID", () => {
    const value = record({});

    expect(addAttackTechniques(value, [
      { id: "T1190", name: "Exploit Public-Facing Application" },
      { id: "T1059", name: " " },
    ])).toBe(2);
    expect(value.containers.cna.taxonomyMappings).toEqual([
      {
        taxonomyName: "ATT&CK",
        taxonomyRelations: [
          {
            taxonomyId: "T1190",
            relationshipName: "maps to",
            relationshipValue: "Exploit Public-Facing Application",
          },
          // No name: the ID stands in, as the value can't be empty.
          { taxonomyId: "T1059", relationshipName: "maps to", relationshipValue: "T1059" },
        ],
      },
    ]);
  });

  it("adds to an existing mapping and skips techniques already there", () => {
    const value = record({
      taxonomyMappings: [
        { taxonomyName: "CWE", taxonomyRelations: [] },
        {
          taxonomyName: "ATT&CK",
          taxonomyVersion: "16.1",
          taxonomyRelations: [
            { taxonomyId: "T1190", relationshipName: "uses", relationshipValue: "CVE-2026-0001" },
          ],
        },
      ],
    });

    expect(addAttackTechniques(value, [
      { id: "T1190", name: "Exploit Public-Facing Application" },
      { id: "T1059", name: "Command and Scripting Interpreter" },
      { id: "T1059", name: "Command and Scripting Interpreter" },
    ])).toBe(1);
    expect([...attackTechniqueIds(value)]).toEqual(["T1190", "T1059"]);
    expect(value.containers.cna.taxonomyMappings).toHaveLength(2);
  });

  it("adds nothing to a rejected record", () => {
    const rejected = record({}, { cveId: "CVE-2026-0001", state: "REJECTED" });

    expect(addAttackTechniques(rejected, [{ id: "T1190", name: "x" }])).toBe(0);
    expect(rejected.containers.cna).toEqual({});
  });
});
