import type {
  AttackTechniquePrediction,
  SeverityPrediction,
} from "../../contracts";

/*
 * The panel's last result, kept per editor so it survives switching
 * panels (the panel is rebuilt each time it opens). Memory only: a
 * reload starts fresh, and classifying again takes about a second.
 * Keyed by the editor rather than the record id so unsaved records in
 * one tab don't share a result, like Patch2Vuln's job-storage.ts.
 */
export interface MlResult {
  // null for an unsaved record.
  identifier: string | null;
  description: string;
  severity: SeverityPrediction;
  techniques: AttackTechniquePrediction[];
  attackModel: string | null;
  selected: Set<string>;
}

const results = new WeakMap<object, MlResult>();

export function rememberResult(editor: object, result: MlResult): void {
  results.set(editor, result);
}

export function recallResult(
  editor: object,
  identifier: string | null,
): MlResult | null {
  const result = results.get(editor);

  // A result from before the record's first save still belongs to it;
  // one for another record (an editor reused for it) doesn't.
  if (!result || (result.identifier !== null && result.identifier !== identifier)) {
    return null;
  }

  return result;
}
