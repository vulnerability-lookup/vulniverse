export type AnyRecord =
  Record<string, unknown>;


export interface PreviewSource {
  key: string;
  label: string;
  badge: string;
  data: AnyRecord;
}


export interface PreviewDate {
  label: string;
  value: string;
}
