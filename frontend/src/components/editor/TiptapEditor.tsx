import React, { useCallback, useRef, useMemo, useImperativeHandle, forwardRef } from 'react';
import { useEditor, EditorContent } from '@tiptap/react';
import type { JSONContent } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import Underline from '@tiptap/extension-underline';
import TextAlign from '@tiptap/extension-text-align';
import { TextStyle } from '@tiptap/extension-text-style';
import { Color } from '@tiptap/extension-color';
import Highlight from '@tiptap/extension-highlight';
import FontFamily from '@tiptap/extension-font-family';
import { Table } from '@tiptap/extension-table';
import TableCell from '@tiptap/extension-table-cell';
import TableHeader from '@tiptap/extension-table-header';
import TableRow from '@tiptap/extension-table-row';
import Image from '@tiptap/extension-image';
import Link from '@tiptap/extension-link';
import TaskList from '@tiptap/extension-task-list';
import TaskItem from '@tiptap/extension-task-item';
import Placeholder from '@tiptap/extension-placeholder';

import { FontSize } from './extensions/FontSize';
import { LineHeight } from './extensions/LineHeight';
import { EditorToolbar } from './EditorToolbar';
import { A4Container } from './A4Container';
import { getResearchReportTemplate } from './templates/researchReport';

import './TiptapEditor.css';

export interface TiptapEditorHandle {
  getJSON: () => JSONContent;
  getHTML: () => string;
  insertTemplate: () => void;
}

interface TiptapEditorProps {
  initialContent?: JSONContent | string | null;
  onUpdate?: (json: JSONContent) => void;
  readOnly?: boolean;
}

export const TiptapEditor = forwardRef<TiptapEditorHandle, TiptapEditorProps>(
  function TiptapEditor({ initialContent, onUpdate, readOnly = false }, ref) {
    const contentRef = useRef<JSONContent | null>(null);

    // Resolve initial content — if it's a string (markdown/html), 
    // use it directly (Tiptap will parse HTML). If null, use template.
    const resolvedInitial = useMemo(() => {
      if (initialContent && typeof initialContent === 'object') {
        return initialContent as JSONContent;
      }
      if (typeof initialContent === 'string' && initialContent.trim()) {
        // Tiptap can parse HTML strings
        return initialContent;
      }
      return getResearchReportTemplate();
    }, [initialContent]);

    const extensions = useMemo(
      () => [
        StarterKit.configure({
          heading: { levels: [1, 2, 3] },
          bulletList: { keepMarks: true, keepAttributes: false },
          orderedList: { keepMarks: true, keepAttributes: false },
          blockquote: {},
          horizontalRule: {},
        }),
        Underline,
        TextStyle,
        Color,
        Highlight.configure({ multicolor: true }),
        FontFamily.configure({ types: ['textStyle'] }),
        FontSize,
        LineHeight,
        TextAlign.configure({ types: ['heading', 'paragraph'] }),
        Table.configure({ resizable: true }),
        TableRow,
        TableHeader,
        TableCell,
        Image.configure({ inline: false, allowBase64: true }),
        Link.configure({ openOnClick: false }),
        TaskList,
        TaskItem.configure({ nested: true }),
        Placeholder.configure({
          placeholder: ({ node }) => {
            if (node.type.name === 'heading') return '제목을 입력하세요...';
            return '이곳에 내용을 작성하세요...';
          },
        }),
      ],
      [],
    );

    const editor = useEditor({
      extensions,
      content: resolvedInitial,
      editable: !readOnly,
      onUpdate: ({ editor: e }) => {
        const json = e.getJSON();
        contentRef.current = json;
        onUpdate?.(json);
      },
      editorProps: {
        attributes: {
          class: 'tiptap-editor-content focus:outline-none',
          spellcheck: 'false',
        },
      },
    });

    const insertTemplate = useCallback(() => {
      if (!editor) return;
      const template = getResearchReportTemplate();
      editor.chain().focus().setContent(template).run();
    }, [editor]);

    // Expose imperative handle so parent can call getJSON / insertTemplate
    useImperativeHandle(
      ref,
      () => ({
        getJSON: () => contentRef.current || editor?.getJSON() || { type: 'doc', content: [] },
        getHTML: () => editor?.getHTML() || '',
        insertTemplate,
      }),
      [editor, insertTemplate],
    );

    return (
      <div className="flex h-full w-full flex-col overflow-hidden rounded-xl bg-white shadow-sm ring-1 ring-slate-200/80">
        {!readOnly && <EditorToolbar editor={editor} onInsertTemplate={insertTemplate} />}

        <div className="flex-1 overflow-y-auto">
          <A4Container>
            {editor && <EditorContent editor={editor} />}
          </A4Container>
        </div>
      </div>
    );
  },
);
