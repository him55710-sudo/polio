import type { TiptapEditorHandle } from '../../../components/editor/TiptapEditor';
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
import type { EditorAdapter } from './EditorAdapter';

export class TiptapEditorAdapter implements EditorAdapter {
  constructor(private readonly handle: TiptapEditorHandle) {}

  getDocumentJSON() {
    return this.handle.getJSON();
  }

  getDocumentHTML() {
    return this.handle.getHTML();
  }

  getDocumentMarkdown() {
    return this.handle.getMarkdown();
  }

  applyContentPatch(patch: ContentPatch) {
    this.handle.applyPatch(patch);
  }

  applyFormatPatch(patch: FormatPatch) {
    this.handle.applyPatch(patch);
  }

  applyReportPatch(patch: ReportPatch) {
    this.handle.applyPatch(patch);
  }

  updateCoverMetadata(metadata: ReportMetadata) {
    this.handle.updateCoverMetadata(metadata);
  }

  updateReferences(sources: SourceRecord[]) {
    this.handle.updateReferences(sources);
  }

  insertMathBlock(block: MathContentBlock) {
    this.handle.insertMathBlock(block);
  }

  insertFigureBlock(block: FigureContentBlock) {
    this.handle.insertFigureBlock(block);
  }

  appendToSection(sectionId: UniFoliReportSectionId, blocks: ReportContentBlock[]) {
    this.handle.appendToSection(sectionId, blocks);
  }

  replaceSection(sectionId: UniFoliReportSectionId, blocks: ReportContentBlock[]) {
    this.handle.replaceSection(sectionId, blocks);
  }

  focusSection(sectionId: UniFoliReportSectionId) {
    this.handle.focusSection(sectionId);
  }
}
