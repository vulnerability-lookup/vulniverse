/*
 * A line-by-line comparison of two texts (the saved and the edited
 * record as formatted JSON), for the JSON section's "Changes" view.
 * An edited line shows as the old one removed and the new one added.
 */

export interface DiffLine {
  kind: "same" | "added" | "removed";
  text: string;
  /** Line number in the old text (not for an added line). */
  oldNumber?: number;
  /** Line number in the new text (not for a removed line). */
  newNumber?: number;
}

// shortcut: above this many cells (lines × lines in the changed middle),
// the middle shows as all removed, then all added; a Myers diff would
// handle huge rewrites in less memory.
const MAX_TABLE_CELLS = 4_000_000;

export function diffLines(before: string[], after: string[]): DiffLine[] {
  // Lines equal at the start and end are skipped before the table, so
  // a small edit in a big record only compares a few lines.
  let start = 0;
  while (start < before.length && start < after.length && before[start] === after[start]) start += 1;

  let end = 0;
  while (
    end < before.length - start && end < after.length - start
    && before[before.length - 1 - end] === after[after.length - 1 - end]
  ) end += 1;

  const a = before.slice(start, before.length - end);
  const b = after.slice(start, after.length - end);
  const lines: DiffLine[] = [];
  let oldNumber = 1;
  let newNumber = 1;

  const same = (text: string) => lines.push({ kind: "same", text, oldNumber: oldNumber++, newNumber: newNumber++ });
  const removed = (text: string) => lines.push({ kind: "removed", text, oldNumber: oldNumber++ });
  const added = (text: string) => lines.push({ kind: "added", text, newNumber: newNumber++ });

  before.slice(0, start).forEach(same);

  if ((a.length + 1) * (b.length + 1) > MAX_TABLE_CELLS) {
    a.forEach(removed);
    b.forEach(added);
  } else {
    // common[i][j]: longest common run of lines in a[i..] and b[j..].
    const width = b.length + 1;
    const common = new Uint32Array((a.length + 1) * width);

    for (let i = a.length - 1; i >= 0; i -= 1) {
      for (let j = b.length - 1; j >= 0; j -= 1) {
        common[i * width + j] = a[i] === b[j]
          ? common[(i + 1) * width + j + 1]! + 1
          : Math.max(common[(i + 1) * width + j]!, common[i * width + j + 1]!);
      }
    }

    let i = 0;
    let j = 0;
    while (i < a.length || j < b.length) {
      if (i < a.length && j < b.length && a[i] === b[j]) {
        same(a[i]!);
        i += 1;
        j += 1;
      } else if (j >= b.length || (i < a.length && common[(i + 1) * width + j]! >= common[i * width + j + 1]!)) {
        // Removed lines first, so an edited line reads old, then new.
        removed(a[i]!);
        i += 1;
      } else {
        added(b[j]!);
        j += 1;
      }
    }
  }

  before.slice(before.length - end).forEach(same);

  return lines;
}

export type DiffRow =
  | { type: "line"; line: DiffLine }
  | { type: "gap"; lines: DiffLine[] };

/**
 * The comparison with long runs of unchanged lines folded into gaps,
 * keeping `context` lines around each change.
 */
export function foldUnchanged(lines: DiffLine[], context = 3): DiffRow[] {
  const near = lines.map(() => false);

  lines.forEach((line, index) => {
    if (line.kind === "same") return;
    for (let other = Math.max(0, index - context); other <= Math.min(lines.length - 1, index + context); other += 1) {
      near[other] = true;
    }
  });

  const rows: DiffRow[] = [];
  let run: DiffLine[] = [];

  const flush = () => {
    // A gap of one line hides nothing worth a button.
    if (run.length > 1) rows.push({ type: "gap", lines: run });
    else run.forEach((line) => rows.push({ type: "line", line }));
    run = [];
  };

  lines.forEach((line, index) => {
    if (near[index]) {
      flush();
      rows.push({ type: "line", line });
    } else {
      run.push(line);
    }
  });
  flush();

  return rows;
}
