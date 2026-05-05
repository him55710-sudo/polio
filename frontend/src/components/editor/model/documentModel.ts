import type { JSONContent } from '@tiptap/react';

export type UniFoliDocumentTemplateId = 'basic' | 'academic';

export type DocumentSectionStatus =
  | 'not_started'
  | 'generating'
  | 'generated'
  | 'edited'
  | 'approved';

export type CitationSourceType =
  | 'website'
  | 'paper'
  | 'book'
  | 'report'
  | 'news'
  | 'other';

export type CitationStyleId = 'apa' | 'mla' | 'chicago' | 'numbered' | 'korean_report';

export interface UniFoliDocumentSection {
  id: string;
  title: string;
  status: DocumentSectionStatus;
  aiDraftMarkdown?: string;
  userEditedMarkdown?: string;
  lastEditedAt?: string | null;
  locked?: boolean;
}

export interface UniFoliCitationSource {
  id: string;
  type: CitationSourceType;
  title: string;
  authors: string[];
  year: string;
  publisher: string;
  url: string;
  accessedAt: string;
  doi: string;
  sourceOrigin: 'user' | 'ai';
  verificationStatus: 'verified' | 'needs_verification' | 'missing';
  usedInSectionIds: string[];
}

export interface UniFoliImageMeta {
  id: string;
  src: string;
  alt: string;
  caption: string;
  width?: number | null;
  height?: number | null;
  alignment: 'left' | 'center' | 'right';
  margin: string;
  uploadedAt: string;
}

export interface UniFoliDocumentModel {
  schemaVersion: 1;
  id: string;
  title: string;
  templateId: UniFoliDocumentTemplateId;
  contentJson: JSONContent | null;
  contentMarkdown: string;
  sections: UniFoliDocumentSection[];
  citations: UniFoliCitationSource[];
  bibliographyStyle: CitationStyleId;
  images: UniFoliImageMeta[];
  updatedAt: string;
}

export interface DocumentTemplateSection {
  id: string;
  title: string;
  description: string;
  defaultBody: string;
}

export interface DocumentTemplateDefinition {
  id: UniFoliDocumentTemplateId;
  label: string;
  description: string;
  sections: DocumentTemplateSection[];
  stylePreset: {
    fontFamily: string;
    bodyFontSizePt: number;
    lineHeight: number;
    headingNumbering: 'decimal' | 'academic' | 'none';
  };
}

export function createDocumentModel(params: {
  id: string;
  title: string;
  templateId: UniFoliDocumentTemplateId;
  contentMarkdown?: string;
  contentJson?: JSONContent | null;
  sections: DocumentTemplateSection[];
  citations?: UniFoliCitationSource[];
  images?: UniFoliImageMeta[];
  bibliographyStyle?: CitationStyleId;
}): UniFoliDocumentModel {
  const now = new Date().toISOString();
  return {
    schemaVersion: 1,
    id: params.id,
    title: params.title,
    templateId: params.templateId,
    contentJson: params.contentJson ?? null,
    contentMarkdown: params.contentMarkdown ?? '',
    sections: params.sections.map((section) => ({
      id: section.id,
      title: section.title,
      status: 'not_started',
      lastEditedAt: null,
    })),
    citations: params.citations ?? [],
    bibliographyStyle: params.bibliographyStyle ?? 'korean_report',
    images: params.images ?? [],
    updatedAt: now,
  };
}

export function markSectionsGenerated(
  sections: UniFoliDocumentSection[],
  markdown: string,
): UniFoliDocumentSection[] {
  const normalized = markdown.toLowerCase();
  return sections.map((section) => ({
    ...section,
    status: normalized.includes(section.title.toLowerCase()) ? 'generated' : section.status,
  }));
}
