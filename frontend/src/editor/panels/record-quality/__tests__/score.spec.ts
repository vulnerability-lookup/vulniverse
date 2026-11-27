import { describe, expect, it } from "vitest";

import type { EditorDocument } from "../../../contracts";
import { scoreRecordQuality } from "../score";
import references from "./reference-scores.json";

interface PythonScore {
  score: number;
  grade: string;
  methodologyVersion: number;
  pillars: { name: string; label: string; score: number; maximum: number }[];
  checks: { name: string; pillar: string; weight: number; rule: string; credit: number; points: number }[];
}

// Results of the Python scorer this one was ported from (and VL's
// methodology v1): the port must give the same for every case.
describe.each(references as { name: string; record: object; expected: PythonScore }[])(
  "scoreRecordQuality: $name",
  ({ record, expected }) => {
    const actual = scoreRecordQuality(record as EditorDocument);

    it("gives the same score and grade", () => {
      expect([actual.score, actual.grade, actual.methodologyVersion])
        .toEqual([expected.score, expected.grade, expected.methodologyVersion]);
    });

    it("gives the same pillars", () => {
      expect(actual.pillars).toEqual(expected.pillars.map((pillar) => ({
        id: pillar.name, label: pillar.label, points: pillar.score, maximum: pillar.maximum,
      })));
    });

    it("gives the same checks", () => {
      expect(actual.checks.map(({ label: _label, ...check }) => check)).toEqual(
        expected.checks.map(({ name, ...check }) => ({ id: name, ...check })),
      );
    });
  },
);
