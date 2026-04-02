import { Extension } from '@tiptap/core';

declare module '@tiptap/core' {
  interface Commands<ReturnType> {
    indent: {
      indent: () => ReturnType;
      outdent: () => ReturnType;
    };
  }
}

export const Indent = Extension.create({
  name: 'indent',

  addOptions() {
    return {
      types: ['paragraph', 'heading'],
      minLevel: 0,
      maxLevel: 6,
    };
  },

  addGlobalAttributes() {
    return [
      {
        types: this.options.types,
        attributes: {
          indent: {
            default: 0,
            parseHTML: (element: HTMLElement) => {
              const ml = element.style.marginLeft;
              if (!ml) return 0;
              return Math.round(parseInt(ml, 10) / 24);
            },
            renderHTML: (attributes: Record<string, any>) => {
              if (!attributes.indent || attributes.indent <= 0) return {};
              return { style: `margin-left: ${attributes.indent * 24}px` };
            },
          },
        },
      },
    ];
  },

  addCommands() {
    return {
      indent:
        () =>
        ({ commands }: any) => {
          return this.options.types.every((type: string) =>
            commands.updateAttributes(type, (attrs: any) => ({
              indent: Math.min((attrs.indent || 0) + 1, this.options.maxLevel),
            })),
          );
        },
      outdent:
        () =>
        ({ commands }: any) => {
          return this.options.types.every((type: string) =>
            commands.updateAttributes(type, (attrs: any) => ({
              indent: Math.max((attrs.indent || 0) - 1, this.options.minLevel),
            })),
          );
        },
    };
  },

  addKeyboardShortcuts() {
    return {
      Tab: () => {
        if (this.editor.isActive('listItem') || this.editor.isActive('taskItem')) return false;
        return this.editor.commands.indent();
      },
      'Shift-Tab': () => {
        if (this.editor.isActive('listItem') || this.editor.isActive('taskItem')) return false;
        return this.editor.commands.outdent();
      },
    };
  },
});
