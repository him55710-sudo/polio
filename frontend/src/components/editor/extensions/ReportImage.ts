import Image from '@tiptap/extension-image';

export const ReportImage = Image.extend({
  addAttributes() {
    return {
      ...this.parent?.(),
      caption: {
        default: '',
        parseHTML: (element: HTMLElement) => element.getAttribute('data-caption') || '',
        renderHTML: (attributes: Record<string, unknown>) =>
          attributes.caption ? { 'data-caption': String(attributes.caption) } : {},
      },
      width: {
        default: null,
        parseHTML: (element: HTMLElement) => element.getAttribute('width') || element.style.width || null,
        renderHTML: (attributes: Record<string, unknown>) => (attributes.width ? { width: attributes.width } : {}),
      },
      height: {
        default: null,
        parseHTML: (element: HTMLElement) => element.getAttribute('height') || null,
        renderHTML: (attributes: Record<string, unknown>) => (attributes.height ? { height: attributes.height } : {}),
      },
      alignment: {
        default: 'center',
        parseHTML: (element: HTMLElement) => element.getAttribute('data-alignment') || 'center',
        renderHTML: (attributes: Record<string, unknown>) => ({ 'data-alignment': String(attributes.alignment || 'center') }),
      },
      margin: {
        default: '12px auto',
        parseHTML: (element: HTMLElement) => element.style.margin || '12px auto',
        renderHTML: (attributes: Record<string, unknown>) => ({ 'data-margin': String(attributes.margin || '12px auto') }),
      },
      uploadedAt: {
        default: null,
        parseHTML: (element: HTMLElement) => element.getAttribute('data-uploaded-at'),
        renderHTML: (attributes: Record<string, unknown>) =>
          attributes.uploadedAt ? { 'data-uploaded-at': String(attributes.uploadedAt) } : {},
      },
    };
  },

  renderHTML({ HTMLAttributes }) {
    const alignment = String(HTMLAttributes.alignment || 'center');
    const margin =
      alignment === 'left'
        ? '12px auto 12px 0'
        : alignment === 'right'
          ? '12px 0 12px auto'
          : '12px auto';
    const width = HTMLAttributes.width ? String(HTMLAttributes.width) : 'auto';
    return [
      'img',
      {
        ...HTMLAttributes,
        style: `max-width: 100%; width: ${width}; height: auto; display: block; margin: ${margin};`,
      },
    ];
  },
});
