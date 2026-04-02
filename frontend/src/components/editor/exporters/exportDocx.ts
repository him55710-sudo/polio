/**
 * DOCX 내보내기
 *
 * Tiptap JSON → docx 라이브러리의 Paragraph/TextRun 변환
 * 지원: heading, paragraph, bulletList, orderedList, blockquote,
 *       table, horizontalRule, taskList, image, marks (bold/italic/underline/strike/color/fontSize/highlight/link)
 */

import {
  Document,
  Packer,
  Paragraph,
  TextRun,
  HeadingLevel,
  AlignmentType,
  Table as DocxTable,
  TableRow as DocxTableRow,
  TableCell as DocxTableCell,
  WidthType,
  BorderStyle,
  ExternalHyperlink,
  LevelFormat,
  convertInchesToTwip,
  type IParagraphOptions,
} from 'docx';
import { saveAs } from 'file-saver';
import type { JSONContent } from '@tiptap/react';

// ── Constants ──
const HEADING_MAP: Record<number, (typeof HeadingLevel)[keyof typeof HeadingLevel]> = {
  1: HeadingLevel.HEADING_1,
  2: HeadingLevel.HEADING_2,
  3: HeadingLevel.HEADING_3,
};

const ALIGN_MAP: Record<string, (typeof AlignmentType)[keyof typeof AlignmentType]> = {
  left: AlignmentType.LEFT,
  center: AlignmentType.CENTER,
  right: AlignmentType.RIGHT,
  justify: AlignmentType.JUSTIFIED,
};

// ── Mark → TextRun options ──
function resolveMarks(marks?: Array<{ type: string; attrs?: Record<string, any> }>): Record<string, any> {
  const opts: Record<string, any> = {};
  if (!marks) return opts;

  for (const mark of marks) {
    switch (mark.type) {
      case 'bold':
        opts.bold = true;
        break;
      case 'italic':
        opts.italics = true;
        break;
      case 'underline':
        opts.underline = { type: 'single' };
        break;
      case 'strike':
        opts.strike = true;
        break;
      case 'textStyle': {
        if (mark.attrs?.fontSize) {
          const pt = parseInt(mark.attrs.fontSize, 10);
          if (!isNaN(pt)) opts.size = pt * 2; // half-points
        }
        if (mark.attrs?.color) {
          opts.color = mark.attrs.color.replace('#', '');
        }
        if (mark.attrs?.fontFamily) {
          opts.font = mark.attrs.fontFamily;
        }
        break;
      }
      case 'highlight': {
        opts.highlight = 'yellow';
        break;
      }
      case 'link': {
        break;
      }
    }
  }
  return opts;
}

// ── Inline content → TextRun[] ──
function convertInlineContent(node: JSONContent): (TextRun | ExternalHyperlink)[] {
  if (!node.content) return [new TextRun({ text: '' })];

  const runs: (TextRun | ExternalHyperlink)[] = [];
  for (const child of node.content) {
    if (child.type === 'text') {
      const markOpts = resolveMarks(child.marks);
      const linkMark = child.marks?.find((m) => m.type === 'link');

      if (linkMark?.attrs?.href) {
        runs.push(
          new ExternalHyperlink({
            children: [
              new TextRun({
                text: child.text || '',
                style: 'Hyperlink',
                ...markOpts,
              }),
            ],
            link: linkMark.attrs.href,
          }),
        );
      } else {
        runs.push(new TextRun({ text: child.text || '', ...markOpts }));
      }
    } else if (child.type === 'hardBreak') {
      runs.push(new TextRun({ text: '', break: 1 }));
    }
  }
  return runs;
}

// ── Node → Paragraph(s) ──
function convertNode(node: JSONContent, listLevel = -1): (Paragraph | DocxTable)[] {
  const results: (Paragraph | DocxTable)[] = [];

  switch (node.type) {
    case 'heading': {
      const level = node.attrs?.level ?? 1;
      const alignment = ALIGN_MAP[node.attrs?.textAlign] || AlignmentType.LEFT;
      results.push(
        new Paragraph({
          heading: HEADING_MAP[level] || HeadingLevel.HEADING_1,
          alignment,
          children: convertInlineContent(node) as TextRun[],
          spacing: { before: 240, after: 120 },
        }),
      );
      break;
    }

    case 'paragraph': {
      const alignment = ALIGN_MAP[node.attrs?.textAlign] || AlignmentType.LEFT;

      // Build spacing
      let lineSpacing: Record<string, number> = { after: 80 };
      if (node.attrs?.lineHeight) {
        const lh = parseFloat(node.attrs.lineHeight);
        if (!isNaN(lh)) {
          lineSpacing = { ...lineSpacing, line: Math.round(lh * 240) };
        }
      }

      results.push(
        new Paragraph({
          alignment,
          children: convertInlineContent(node) as TextRun[],
          spacing: lineSpacing,
        }),
      );
      break;
    }

    case 'bulletList': {
      if (node.content) {
        for (const listItem of node.content) {
          if (listItem.content) {
            for (const child of listItem.content) {
              const paras = convertNode(child, listLevel + 1);
              for (const p of paras) {
                if (p instanceof Paragraph) {
                  results.push(
                    new Paragraph({
                      ...((p as any).options || {}),
                      bullet: { level: Math.max(0, listLevel + 1) },
                      children: (p as any).options?.children || [],
                    }),
                  );
                } else {
                  results.push(p);
                }
              }
            }
          }
        }
      }
      break;
    }

    case 'orderedList': {
      if (node.content) {
        let index = 0;
        for (const listItem of node.content) {
          if (listItem.content) {
            for (const child of listItem.content) {
              const paras = convertNode(child, listLevel + 1);
              for (const p of paras) {
                if (p instanceof Paragraph) {
                  results.push(
                    new Paragraph({
                      numbering: { reference: 'ordered-list', level: Math.max(0, listLevel + 1) },
                      children: convertInlineContent(child) as TextRun[],
                    }),
                  );
                } else {
                  results.push(p);
                }
              }
            }
          }
          index++;
        }
      }
      break;
    }

    case 'taskList': {
      if (node.content) {
        for (const taskItem of node.content) {
          const checked = taskItem.attrs?.checked ? '☑' : '☐';
          const inlines = taskItem.content
            ? taskItem.content.flatMap((c) => convertInlineContent(c))
            : [];
          results.push(
            new Paragraph({
              children: [
                new TextRun({ text: `${checked} `, font: 'Segoe UI Symbol' }),
                ...(inlines as TextRun[]),
              ],
              spacing: { after: 60 },
            }),
          );
        }
      }
      break;
    }

    case 'blockquote': {
      if (node.content) {
        for (const child of node.content) {
          const paras = convertNode(child);
          for (const p of paras) {
            if (p instanceof Paragraph) {
              results.push(
                new Paragraph({
                  indent: { left: convertInchesToTwip(0.5) },
                  border: {
                    left: { style: BorderStyle.SINGLE, size: 6, color: '3b82f6', space: 8 },
                  },
                  children: convertInlineContent(child) as TextRun[],
                  spacing: { before: 80, after: 80 },
                }),
              );
            } else {
              results.push(p);
            }
          }
        }
      }
      break;
    }

    case 'horizontalRule': {
      results.push(
        new Paragraph({
          border: {
            bottom: { style: BorderStyle.SINGLE, size: 1, color: 'e2e8f0' },
          },
          spacing: { before: 200, after: 200 },
        }),
      );
      break;
    }

    case 'table': {
      if (node.content) {
        const rows = node.content
          .filter((r) => r.type === 'tableRow')
          .map((row) => {
            const cells = (row.content || [])
              .filter((c) => c.type === 'tableCell' || c.type === 'tableHeader')
              .map((cell) => {
                const isHeader = cell.type === 'tableHeader';
                const cellParas = cell.content
                  ? cell.content.flatMap((c) => convertNode(c))
                  : [new Paragraph({})];

                return new DocxTableCell({
                  children: cellParas.filter((p) => p instanceof Paragraph) as Paragraph[],
                  shading: isHeader ? { fill: 'f8fafc' } : undefined,
                  width: { size: 0, type: WidthType.AUTO },
                });
              });

            return new DocxTableRow({ children: cells });
          });

        if (rows.length > 0) {
          results.push(
            new DocxTable({
              rows,
              width: { size: 100, type: WidthType.PERCENTAGE },
            }),
          );
        }
      }
      break;
    }

    case 'image': {
      // Images in DOCX from URLs need to be fetched; skip for now and add placeholder
      const altText = node.attrs?.alt || '이미지';
      const src = node.attrs?.src || '';
      results.push(
        new Paragraph({
          children: [
            new TextRun({
              text: `[이미지: ${altText}] (${src})`,
              italics: true,
              color: '94a3b8',
            }),
          ],
          spacing: { before: 120, after: 120 },
          alignment: AlignmentType.CENTER,
        }),
      );
      break;
    }

    case 'doc': {
      if (node.content) {
        for (const child of node.content) {
          results.push(...convertNode(child));
        }
      }
      break;
    }

    default: {
      // Unknown node — try to recurse into children
      if (node.content) {
        for (const child of node.content) {
          results.push(...convertNode(child));
        }
      }
      break;
    }
  }

  return results;
}

// ── Main export function ──
export async function exportToDocx(json: JSONContent, filename = '탐구보고서'): Promise<void> {
  const children = convertNode(json);

  const doc = new Document({
    numbering: {
      config: [
        {
          reference: 'ordered-list',
          levels: [
            {
              level: 0,
              format: LevelFormat.DECIMAL,
              text: '%1.',
              alignment: AlignmentType.LEFT,
              style: { paragraph: { indent: { left: convertInchesToTwip(0.5), hanging: convertInchesToTwip(0.25) } } },
            },
            {
              level: 1,
              format: LevelFormat.LOWER_LETTER,
              text: '%2)',
              alignment: AlignmentType.LEFT,
              style: { paragraph: { indent: { left: convertInchesToTwip(1), hanging: convertInchesToTwip(0.25) } } },
            },
          ],
        },
      ],
    },
    styles: {
      default: {
        document: {
          run: {
            font: 'Malgun Gothic',
            size: 22, // 11pt in half-points
          },
          paragraph: {
            spacing: { line: 384 }, // ~1.6 line height
          },
        },
        heading1: {
          run: { size: 44, bold: true, font: 'Malgun Gothic' },
          paragraph: { spacing: { before: 360, after: 180 } },
        },
        heading2: {
          run: { size: 32, bold: true, font: 'Malgun Gothic' },
          paragraph: { spacing: { before: 280, after: 120 } },
        },
        heading3: {
          run: { size: 26, bold: true, font: 'Malgun Gothic' },
          paragraph: { spacing: { before: 240, after: 100 } },
        },
      },
    },
    sections: [
      {
        properties: {
          page: {
            margin: {
              top: convertInchesToTwip(1),
              right: convertInchesToTwip(0.8),
              bottom: convertInchesToTwip(1.2),
              left: convertInchesToTwip(0.8),
            },
          },
        },
        children: children as (Paragraph | DocxTable)[],
      },
    ],
  });

  const blob = await Packer.toBlob(doc);
  saveAs(blob, `${filename}.docx`);
}
