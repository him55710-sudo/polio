import React, { useCallback, useRef, useState } from 'react';
import { type Editor } from '@tiptap/react';
import {
  AlignCenter,
  AlignJustify,
  AlignLeft,
  AlignRight,
  Bold,
  CheckSquare,
  FileDown,
  Heading1,
  Heading2,
  Heading3,
  Highlighter,
  Image as ImageIcon,
  IndentDecrease,
  IndentIncrease,
  Italic,
  Link as LinkIcon,
  List,
  ListOrdered,
  Minus,
  PaintbrushVertical,
  Quote,
  Redo,
  SeparatorHorizontal,
  Sigma,
  Strikethrough,
  Table as TableIcon,
  Underline,
  Undo,
} from 'lucide-react';
import { cn } from '../../lib/cn';
import { TableToolbar } from './TableToolbar';
import { REPORT_TABLE_TEMPLATES, tableTemplateToTiptapContent } from './tableTemplates';

interface EditorToolbarProps {
  editor: Editor | null;
  onInsertTemplate?: () => void;
}

const FONT_FAMILIES = [
  { label: 'Pretendard', value: 'Pretendard' },
  { label: 'Noto Sans KR', value: 'Noto Sans KR' },
  { label: 'Nanum Gothic', value: 'NanumGothic' },
  { label: 'Inter', value: 'Inter' },
  { label: 'Georgia', value: 'Georgia' },
  { label: 'Times New Roman', value: 'Times New Roman' },
];

const FONT_SIZES = ['10px', '11px', '12px', '14px', '16px', '18px', '20px', '24px', '28px', '32px', '36px'];
const LINE_HEIGHTS = ['1', '1.15', '1.5', '1.75', '2', '2.5', '3'];
const PRESET_COLORS = [
  '#000000',
  '#434343',
  '#666666',
  '#999999',
  '#cccccc',
  '#1a73e8',
  '#0b8043',
  '#ea4335',
  '#f9ab00',
  '#9334e6',
  '#d93025',
  '#188038',
  '#1967d2',
  '#fbbc04',
  '#a142f4',
];

function ToolbarButton({
  onClick,
  active = false,
  disabled = false,
  children,
  title,
  className,
}: {
  onClick: () => void;
  active?: boolean;
  disabled?: boolean;
  children: React.ReactNode;
  title?: string;
  className?: string;
}) {
  return (
    <button
      type="button"
      onMouseDown={(event) => event.preventDefault()}
      onClick={onClick}
      disabled={disabled}
      title={title}
      className={cn(
        'flex h-8 w-8 shrink-0 items-center justify-center rounded-md text-slate-500 transition-all duration-200 hover:bg-slate-200/50 hover:text-slate-900 disabled:pointer-events-none disabled:opacity-20',
        active && 'bg-indigo-50 text-indigo-600 shadow-[inset_0_1px_2px_rgba(79,70,229,0.1)] hover:bg-indigo-100/70',
        className,
      )}
    >
      {children}
    </button>
  );
}

function ToolbarDivider() {
  return <div className="mx-1.5 h-4 w-[1px] shrink-0 bg-slate-200/60" />;
}

function ColorPicker({
  currentColor,
  onSelect,
  title,
  icon,
}: {
  currentColor: string;
  onSelect: (color: string) => void;
  title: string;
  icon: React.ReactNode;
}) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="relative">
      <button
        type="button"
        onMouseDown={(event) => event.preventDefault()}
        onClick={() => setIsOpen((value) => !value)}
        title={title}
        className="flex h-8 w-8 flex-col items-center justify-center rounded-md text-slate-500 transition-all hover:bg-slate-200/50"
      >
        {icon}
        <span className="mt-0.5 h-[2.5px] w-3.5 rounded-full" style={{ backgroundColor: currentColor || '#000000' }} />
      </button>
      {isOpen ? (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setIsOpen(false)} />
          <div className="absolute left-0 top-full z-50 mt-1 w-[172px] rounded-lg border border-slate-200 bg-white p-2 shadow-xl">
            <div className="grid grid-cols-5 gap-1">
              {PRESET_COLORS.map((color) => (
                <button
                  key={color}
                  type="button"
                  className="h-6 w-6 rounded-md border border-slate-200 transition-transform hover:scale-110"
                  style={{ backgroundColor: color }}
                  onClick={() => {
                    onSelect(color);
                    setIsOpen(false);
                  }}
                />
              ))}
            </div>
            <input
              type="color"
              className="mt-2 h-7 w-full cursor-pointer rounded border border-slate-100 bg-white"
              value={currentColor || '#000000'}
              onChange={(event) => {
                onSelect(event.target.value);
                setIsOpen(false);
              }}
            />
          </div>
        </>
      ) : null}
    </div>
  );
}

export function EditorToolbar({ editor, onInsertTemplate }: EditorToolbarProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const addImage = useCallback(() => {
    if (!editor) return;
    const url = window.prompt('이미지 URL을 입력하세요. 취소하면 파일 선택을 사용할 수 있습니다.');
    if (url) {
      const alt = window.prompt('이미지 alt text를 입력하세요.') || 'report image';
      const caption = window.prompt('이미지 캡션을 입력하세요. 비워도 됩니다.') || '';
      editor.chain().focus().setImage({ src: url, alt, caption, alignment: 'center', uploadedAt: new Date().toISOString() } as any).run();
      if (caption) {
        editor.chain().focus().insertContent({
          type: 'paragraph',
          attrs: { textAlign: 'center' },
          content: [{ type: 'text', text: `그림. ${caption}` }],
        }).run();
      }
      return;
    }
    fileInputRef.current?.click();
  }, [editor]);

  const handleFileChange = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
    if (!editor) return;
    const file = event.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (readerEvent) => {
      const src = readerEvent.target?.result as string;
      if (src) {
        editor.chain().focus().setImage({
          src,
          alt: file.name,
          caption: '',
          alignment: 'center',
          uploadedAt: new Date().toISOString(),
        } as any).run();
      }
    };
    reader.readAsDataURL(file);
    event.target.value = '';
  }, [editor]);

  const setLink = useCallback(() => {
    if (!editor) return;
    const previousUrl = editor.getAttributes('link').href;
    const url = window.prompt('링크 URL을 입력하세요.', previousUrl);
    if (url === null) return;
    if (url === '') {
      editor.chain().focus().extendMarkRange('link').unsetLink().run();
      return;
    }
    editor.chain().focus().extendMarkRange('link').setLink({ href: url }).run();
  }, [editor]);

  const insertFormula = useCallback(() => {
    if (!editor) return;
    const latex = window.prompt('수식을 LaTeX로 입력하세요. 예: E = mc^2');
    if (!latex) return;
    editor.chain().focus().insertContent({
      type: 'codeBlock',
      attrs: { language: 'latex' },
      content: [{ type: 'text', text: latex }],
    }).run();
  }, [editor]);

  if (!editor) return null;

  const currentFontSize = editor.getAttributes('textStyle').fontSize || '16px';
  const currentFontFamily = editor.getAttributes('textStyle').fontFamily || 'Pretendard';
  const currentLineHeight = editor.getAttributes('paragraph').lineHeight || '1.6';
  const currentColor = editor.getAttributes('textStyle').color || '#000000';
  const currentHighlight = editor.getAttributes('highlight').color || '#fdd663';

  return (
    <div className="sticky top-0 z-30 border-b border-slate-200/60 bg-white/80 px-2 py-2 backdrop-blur-xl sm:px-4">
      <input ref={fileInputRef} type="file" className="hidden" accept="image/*" onChange={handleFileChange} />

      <div className="flex items-center gap-1 overflow-x-auto pb-1 [&::-webkit-scrollbar]:h-0">
        <ToolbarButton onClick={() => editor.chain().focus().undo().run()} disabled={!editor.can().undo()} title="실행 취소">
          <Undo size={15} />
        </ToolbarButton>
        <ToolbarButton onClick={() => editor.chain().focus().redo().run()} disabled={!editor.can().redo()} title="다시 실행">
          <Redo size={15} />
        </ToolbarButton>
        <ToolbarDivider />

        <select className="h-8 min-w-[110px] rounded-md border border-slate-200/60 bg-white px-2 text-[11px] font-bold text-slate-600 shadow-sm outline-none hover:border-slate-300 transition-colors" value={currentFontFamily} onChange={(event) => editor.chain().focus().setFontFamily(event.target.value).run()} onMouseDown={(event) => event.stopPropagation()}>
          {FONT_FAMILIES.map((font) => <option key={font.value} value={font.value}>{font.label}</option>)}
        </select>
        <select className="h-8 w-14 rounded-md border border-slate-200/60 bg-white px-1 text-[11px] font-bold text-slate-600 shadow-sm outline-none hover:border-slate-300 transition-colors" value={currentFontSize} onChange={(event) => editor.chain().focus().setFontSize(event.target.value).run()} onMouseDown={(event) => event.stopPropagation()}>
          {FONT_SIZES.map((size) => <option key={size} value={size}>{size.replace('px', '')}</option>)}
        </select>
        <ToolbarDivider />

        <ToolbarButton active={editor.isActive('bold')} onClick={() => editor.chain().focus().toggleBold().run()} title="굵게"><Bold size={15} /></ToolbarButton>
        <ToolbarButton active={editor.isActive('italic')} onClick={() => editor.chain().focus().toggleItalic().run()} title="기울임"><Italic size={15} /></ToolbarButton>
        <ToolbarButton active={editor.isActive('underline')} onClick={() => editor.chain().focus().toggleUnderline().run()} title="밑줄"><Underline size={15} /></ToolbarButton>
        <ToolbarButton active={editor.isActive('strike')} onClick={() => editor.chain().focus().toggleStrike().run()} title="취소선"><Strikethrough size={15} /></ToolbarButton>
        <ColorPicker currentColor={currentColor} onSelect={(color) => editor.chain().focus().setColor(color).run()} title="글자색" icon={<PaintbrushVertical size={14} />} />
        <ColorPicker currentColor={currentHighlight} onSelect={(color) => editor.chain().focus().toggleHighlight({ color }).run()} title="형광펜" icon={<Highlighter size={14} />} />
        <ToolbarDivider />

        <ToolbarButton active={editor.isActive('heading', { level: 1 })} onClick={() => editor.chain().focus().toggleHeading({ level: 1 }).run()} title="제목 1"><Heading1 size={15} /></ToolbarButton>
        <ToolbarButton active={editor.isActive('heading', { level: 2 })} onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()} title="제목 2"><Heading2 size={15} /></ToolbarButton>
        <ToolbarButton active={editor.isActive('heading', { level: 3 })} onClick={() => editor.chain().focus().toggleHeading({ level: 3 }).run()} title="제목 3"><Heading3 size={15} /></ToolbarButton>
        <ToolbarButton active={editor.isActive('blockquote')} onClick={() => editor.chain().focus().toggleBlockquote().run()} title="인용문"><Quote size={15} /></ToolbarButton>
        <ToolbarDivider />

        <ToolbarButton active={editor.isActive({ textAlign: 'left' })} onClick={() => editor.chain().focus().setTextAlign('left').run()} title="왼쪽 정렬"><AlignLeft size={15} /></ToolbarButton>
        <ToolbarButton active={editor.isActive({ textAlign: 'center' })} onClick={() => editor.chain().focus().setTextAlign('center').run()} title="가운데 정렬"><AlignCenter size={15} /></ToolbarButton>
        <ToolbarButton active={editor.isActive({ textAlign: 'right' })} onClick={() => editor.chain().focus().setTextAlign('right').run()} title="오른쪽 정렬"><AlignRight size={15} /></ToolbarButton>
        <ToolbarButton active={editor.isActive({ textAlign: 'justify' })} onClick={() => editor.chain().focus().setTextAlign('justify').run()} title="양쪽 정렬"><AlignJustify size={15} /></ToolbarButton>
        <select className="h-9 w-16 rounded-lg border border-slate-200 bg-white px-1 text-[12px] font-semibold text-slate-700 shadow-sm outline-none" value={currentLineHeight} onChange={(event) => editor.chain().focus().setLineHeight(event.target.value).run()} onMouseDown={(event) => event.stopPropagation()} title="줄간격">
          {LINE_HEIGHTS.map((lineHeight) => <option key={lineHeight} value={lineHeight}>{lineHeight}</option>)}
        </select>
        <ToolbarButton onClick={() => editor.chain().focus().indent().run()} title="들여쓰기"><IndentIncrease size={15} /></ToolbarButton>
        <ToolbarButton onClick={() => editor.chain().focus().outdent().run()} title="내어쓰기"><IndentDecrease size={15} /></ToolbarButton>
        <ToolbarDivider />

        <ToolbarButton active={editor.isActive('bulletList')} onClick={() => editor.chain().focus().toggleBulletList().run()} title="글머리표"><List size={15} /></ToolbarButton>
        <ToolbarButton active={editor.isActive('orderedList')} onClick={() => editor.chain().focus().toggleOrderedList().run()} title="번호 목록"><ListOrdered size={15} /></ToolbarButton>
        <ToolbarButton active={editor.isActive('taskList')} onClick={() => editor.chain().focus().toggleTaskList().run()} title="체크리스트"><CheckSquare size={15} /></ToolbarButton>
        <ToolbarDivider />

        <ToolbarButton active={editor.isActive('link')} onClick={setLink} title="링크 삽입"><LinkIcon size={15} /></ToolbarButton>
        <ToolbarButton onClick={addImage} title="이미지 삽입"><ImageIcon size={15} /></ToolbarButton>
        <ToolbarButton onClick={() => editor.chain().focus().insertTable({ rows: 3, cols: 3, withHeaderRow: true }).run()} title="3x3 표 삽입"><TableIcon size={15} /></ToolbarButton>
        <select
          className="h-9 min-w-[130px] rounded-lg border border-slate-200 bg-white px-2 text-[12px] font-semibold text-slate-700 shadow-sm outline-none"
          defaultValue=""
          onChange={(event) => {
            const template = REPORT_TABLE_TEMPLATES.find((item) => item.id === event.target.value);
            if (template) editor.chain().focus().insertContent(tableTemplateToTiptapContent(template)).run();
            event.currentTarget.value = '';
          }}
          onMouseDown={(event) => event.stopPropagation()}
          title="보고서용 표 템플릿"
        >
          <option value="" disabled>표 템플릿</option>
          {REPORT_TABLE_TEMPLATES.map((template) => <option key={template.id} value={template.id}>{template.label}</option>)}
        </select>
        <ToolbarButton onClick={insertFormula} title="수식 삽입"><Sigma size={15} /></ToolbarButton>
        <ToolbarButton onClick={() => editor.chain().focus().setHorizontalRule().run()} title="구분선"><Minus size={15} /></ToolbarButton>
        <ToolbarButton onClick={() => editor.chain().focus().setPageBreak().run()} title="페이지 나누기"><SeparatorHorizontal size={15} /></ToolbarButton>

        {onInsertTemplate ? (
          <>
            <ToolbarDivider />
            <button type="button" onMouseDown={(event) => event.preventDefault()} onClick={onInsertTemplate} className="flex h-8 items-center gap-1 rounded-md bg-blue-50 px-2 text-[11px] font-bold text-blue-700 transition-colors hover:bg-blue-100" title="보고서 템플릿 삽입">
              <FileDown size={13} />
              템플릿
            </button>
          </>
        ) : null}
      </div>

      <TableToolbar editor={editor} />
    </div>
  );
}
