import type { JSONContent } from '@tiptap/react';
import type {
  ContentPatch,
  FormatPatch,
  FigureContentBlock,
  MathContentBlock,
  ReportContentBlock,
  ReportMetadata,
  ReportPatch,
  SourceRecord,
  UniFoliReportSectionId,
} from '../types/reportDocument';

export type MaybePromise<T> = T | Promise<T>;

export interface EditorAdapter {
  getDocumentJSON(): MaybePromise<JSONContent | Record<string, unknown>>;
  getDocumentHTML(): MaybePromise<string>;
  getDocumentMarkdown(): MaybePromise<string>;
  applyContentPatch(patch: ContentPatch): MaybePromise<void>;
  applyFormatPatch(patch: FormatPatch): MaybePromise<void>;
  applyReportPatch(patch: ReportPatch): MaybePromise<void>;
  updateCoverMetadata(metadata: ReportMetadata): MaybePromise<void>;
  updateReferences(sources: SourceRecord[]): MaybePromise<void>;
  insertMathBlock(block: MathContentBlock): MaybePromise<void>;
  insertFigureBlock(block: FigureContentBlock): MaybePromise<void>;
  appendToSection(sectionId: UniFoliReportSectionId, blocks: ReportContentBlock[]): MaybePromise<void>;
  replaceSection(sectionId: UniFoliReportSectionId, blocks: ReportContentBlock[]): MaybePromise<void>;
  focusSection(sectionId: UniFoliReportSectionId): MaybePromise<void>;
}
