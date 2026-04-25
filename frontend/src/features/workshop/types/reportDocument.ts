export type UniFoliReportSectionId =
  | 'cover'
  | 'table_of_contents'
  | 'motivation'
  | 'research_purpose'
  | 'research_question'
  | 'background_theory'
  | 'prior_research'
  | 'research_method'
  | 'research_process'
  | 'data_analysis'
  | 'result'
  | 'conclusion'
  | 'limitation'
  | 'future_research'
  | 'student_record_connection'
  | 'references'
  | 'appendix';

export type ReportTemplateId = 'standard_research' | 'academic' | 'engineering' | 'freeform';
export type SourceReliability = 'low' | 'medium' | 'high';
export type PatchStatus = 'pending' | 'accepted' | 'rejected' | 'applied' | 'superseded';
export type PatchApprovalStatus = PatchStatus;
export type ConfidenceLevel = 'low' | 'medium' | 'high';

export interface ReportMetadata {
  title: string;
  subtitle: string;
  schoolName: string;
  grade: string;
  className: string;
  studentName: string;
  studentId: string;
  teacherName: string;
  date: string;
  targetMajor: string;
  targetUniversity: string;
}

export interface ReportFormatProfile {
  templateId: ReportTemplateId;
  cover: {
    enabled: boolean;
    requireTitle: boolean;
    preserveUserEnteredIdentityFields: boolean;
  };
  typography: {
    bodyFontSizePt: number;
    lineHeight: number;
    fontFamily: string;
    headingFontFamily: string;
  };
  numbering: {
    chapter: 'roman' | 'decimal' | 'none';
    subsection: 'decimal' | 'roman' | 'none';
    useTableOfContents: boolean;
    managedByTemplateEngine: boolean;
  };
  citation: {
    required: boolean;
    style: 'korean_school' | 'apa' | 'simple_url' | 'mla' | 'ieee' | 'freeform';
    requireReferencesSection: boolean;
  };
  math: {
    enabled: boolean;
    renderer: 'latex_katex';
    requireValidLatex: boolean;
  };
  figures: {
    enabled: boolean;
    requireCaption: boolean;
    requireSource: boolean;
    requireAltText: boolean;
  };
  freedom: {
    level: 'strict' | 'guided' | 'flexible';
    allowSectionRename: boolean;
    allowSectionReorder: boolean;
  };
}

export interface SourceRecord {
  id: string;
  title: string;
  authors: string[];
  year: string;
  publisher: string;
  journal: string;
  url: string;
  accessedAt: string;
  sourceType: 'paper' | 'book' | 'website' | 'news' | 'report' | 'dataset';
  reliability: SourceReliability;
  usedInSections: UniFoliReportSectionId[];
  citationText: string;
  metadata?: Record<string, unknown>;
}

export interface ConversationInsight {
  id: string;
  sourceMessageIds: string[];
  insightType:
    | 'user_preference'
    | 'research_direction'
    | 'personal_motivation'
    | 'evidence_request'
    | 'format_preference'
    | 'revision_instruction';
  summary: string;
  suggestedTargetSections: UniFoliReportSectionId[];
  confidence: ConfidenceLevel;
  shouldReflectInDocument: boolean;
}

export interface ResearchCandidate {
  id: string;
  title: string;
  summary: string;
  sectionTarget: UniFoliReportSectionId;
  whyUseful: string;
  sourceIds: string[];
  confidence: ConfidenceLevel;
  cautionNote: string;
}

interface ReportContentBlockBase {
  id?: string;
  sourceIds?: string[];
}

export interface ParagraphContentBlock extends ReportContentBlockBase {
  type: 'paragraph';
  text: string;
}

export interface HeadingContentBlock extends ReportContentBlockBase {
  type: 'heading';
  level: 1 | 2 | 3 | 4;
  text: string;
}

export interface ListContentBlock extends ReportContentBlockBase {
  type: 'list';
  ordered: boolean;
  items: string[];
}

export interface QuoteContentBlock extends ReportContentBlockBase {
  type: 'quote';
  text: string;
}

export interface TableContentBlock extends ReportContentBlockBase {
  type: 'table';
  headers: string[];
  rows: string[][];
  caption?: string;
}

export interface MathContentBlock extends ReportContentBlockBase {
  type: 'math';
  latex: string;
  displayMode: 'inline' | 'block';
  caption: string;
}

export interface FigureContentBlock extends ReportContentBlockBase {
  type: 'figure';
  imageUrl: string;
  caption: string;
  sourceId: string;
  altText: string;
}

export type ReportContentBlock =
  | ParagraphContentBlock
  | HeadingContentBlock
  | ListContentBlock
  | QuoteContentBlock
  | TableContentBlock
  | MathContentBlock
  | FigureContentBlock;

export interface ContentPatch {
  type: 'content';
  patchId: string;
  targetSection: UniFoliReportSectionId;
  action: 'insert' | 'append' | 'replace' | 'rewrite' | 'create_section';
  contentBlocks: ReportContentBlock[];
  contentMarkdown?: string;
  sourceIds: string[];
  selectedCandidateIds: string[];
  rationale: string;
  evidenceBoundaryNote: string;
  requiresApproval: boolean;
  status: PatchStatus;
}

export interface FormatPatch {
  type: 'format';
  patchId: string;
  target: 'cover' | 'toc' | 'typography' | 'numbering' | 'citation' | 'math' | 'figures' | 'freedom';
  changes: Record<string, unknown>;
  rationale: string;
  requiresApproval: boolean;
  status: PatchStatus;
}

export type ReportPatch = ContentPatch | FormatPatch;

export interface ReportSectionState {
  id: UniFoliReportSectionId;
  title: string;
  contentBlocks: ReportContentBlock[];
  sourceIds: string[];
  studentAuthoredText?: string;
  aiGeneratedText?: string;
  locked?: boolean;
}

export interface ReportDocumentState {
  metadata: ReportMetadata;
  formatProfile: ReportFormatProfile;
  sections: Record<UniFoliReportSectionId, ReportSectionState>;
  sectionOrder: UniFoliReportSectionId[];
  sources: SourceRecord[];
  figures: FigureContentBlock[];
  mathBlocks: MathContentBlock[];
  conversationInsights: ConversationInsight[];
  pendingPatches: ReportPatch[];
  acceptedPatches: ReportPatch[];
  rejectedPatches: ReportPatch[];
}

export const STANDARD_REPORT_SECTION_ORDER: UniFoliReportSectionId[] = [
  'cover',
  'table_of_contents',
  'motivation',
  'research_purpose',
  'research_question',
  'background_theory',
  'prior_research',
  'research_method',
  'research_process',
  'data_analysis',
  'result',
  'conclusion',
  'limitation',
  'future_research',
  'student_record_connection',
  'references',
  'appendix',
];

export const ROMAN_REPORT_SECTION_ORDER: UniFoliReportSectionId[] = [
  'motivation',
  'background_theory',
  'research_method',
  'result',
  'conclusion',
  'references',
];

export function createEmptyReportMetadata(): ReportMetadata {
  return {
    title: '',
    subtitle: '',
    schoolName: '',
    grade: '',
    className: '',
    studentName: '',
    studentId: '',
    teacherName: '',
    date: '',
    targetMajor: '',
    targetUniversity: '',
  };
}

export function createDefaultReportFormatProfile(
  templateId: ReportTemplateId = 'standard_research',
): ReportFormatProfile {
  return {
    templateId,
    cover: {
      enabled: true,
      requireTitle: true,
      preserveUserEnteredIdentityFields: true,
    },
    typography: {
      bodyFontSizePt: 11,
      lineHeight: 1.5,
      fontFamily: 'system-ui',
      headingFontFamily: 'system-ui',
    },
    numbering: {
      chapter: 'roman',
      subsection: 'decimal',
      useTableOfContents: true,
      managedByTemplateEngine: true,
    },
    citation: {
      required: true,
      style: 'korean_school',
      requireReferencesSection: true,
    },
    math: {
      enabled: true,
      renderer: 'latex_katex',
      requireValidLatex: true,
    },
    figures: {
      enabled: true,
      requireCaption: true,
      requireSource: true,
      requireAltText: true,
    },
    freedom: {
      level: templateId === 'freeform' ? 'flexible' : 'guided',
      allowSectionRename: templateId === 'freeform',
      allowSectionReorder: templateId === 'freeform',
    },
  };
}

export function createInitialReportDocumentState(
  overrides: Partial<ReportDocumentState> = {},
): ReportDocumentState {
  const metadata = overrides.metadata ?? createEmptyReportMetadata();
  const formatProfile = overrides.formatProfile ?? createDefaultReportFormatProfile();
  const sectionOrder = overrides.sectionOrder ?? STANDARD_REPORT_SECTION_ORDER;
  const sections = STANDARD_REPORT_SECTION_ORDER.reduce(
    (acc, sectionId) => {
      acc[sectionId] = {
        id: sectionId,
        title: sectionId,
        contentBlocks: [],
        sourceIds: [],
      };
      return acc;
    },
    {} as Record<UniFoliReportSectionId, ReportSectionState>,
  );

  return {
    metadata,
    formatProfile,
    sections,
    sectionOrder,
    sources: [],
    figures: [],
    mathBlocks: [],
    conversationInsights: [],
    pendingPatches: [],
    acceptedPatches: [],
    rejectedPatches: [],
    ...overrides,
  };
}
