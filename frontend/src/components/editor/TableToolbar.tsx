import React from 'react';
import { Columns, Heading1, Plus, Rows, Trash2 } from 'lucide-react';
import type { Editor } from '@tiptap/react';
import { cn } from '../../lib/cn';

interface TableToolbarProps {
  editor: Editor;
}

function ToolButton({ title, onClick, children, danger = false }: {
  title: string;
  onClick: () => void;
  children: React.ReactNode;
  danger?: boolean;
}) {
  return (
    <button
      type="button"
      onMouseDown={(event) => event.preventDefault()}
      onClick={onClick}
      title={title}
      className={cn(
        'flex h-8 min-w-8 items-center justify-center rounded-lg px-2 text-xs font-black text-slate-600 transition hover:bg-white hover:text-slate-900',
        danger && 'text-red-600 hover:bg-red-50 hover:text-red-700',
      )}
    >
      {children}
    </button>
  );
}

export function TableToolbar({ editor }: TableToolbarProps) {
  if (!editor.isActive('table')) return null;
  return (
    <div className="flex items-center gap-0.5 overflow-x-auto border-t border-slate-100 bg-blue-50/50 px-3 py-1">
      <span className="mr-1 shrink-0 text-[10px] font-black text-blue-700">표 편집</span>
      <ToolButton title="왼쪽에 열 추가" onClick={() => editor.chain().focus().addColumnBefore().run()}><Plus size={13} /></ToolButton>
      <ToolButton title="오른쪽에 열 추가" onClick={() => editor.chain().focus().addColumnAfter().run()}><Columns size={13} /></ToolButton>
      <ToolButton title="열 삭제" onClick={() => editor.chain().focus().deleteColumn().run()} danger><Trash2 size={13} /></ToolButton>
      <div className="mx-1 h-5 w-px bg-blue-100" />
      <ToolButton title="위에 행 추가" onClick={() => editor.chain().focus().addRowBefore().run()}><Plus size={13} /></ToolButton>
      <ToolButton title="아래에 행 추가" onClick={() => editor.chain().focus().addRowAfter().run()}><Rows size={13} /></ToolButton>
      <ToolButton title="행 삭제" onClick={() => editor.chain().focus().deleteRow().run()} danger><Trash2 size={13} /></ToolButton>
      <div className="mx-1 h-5 w-px bg-blue-100" />
      <ToolButton title="헤더 행 전환" onClick={() => editor.chain().focus().toggleHeaderRow().run()}><Heading1 size={13} /></ToolButton>
      <ToolButton title="셀 병합" onClick={() => editor.chain().focus().mergeCells().run()}>병합</ToolButton>
      <ToolButton title="셀 분할" onClick={() => editor.chain().focus().splitCell().run()}>분할</ToolButton>
      <div className="mx-1 h-5 w-px bg-blue-100" />
      <ToolButton title="표 삭제" onClick={() => editor.chain().focus().deleteTable().run()} danger><Trash2 size={13} /></ToolButton>
    </div>
  );
}
