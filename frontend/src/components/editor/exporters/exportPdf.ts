/**
 * PDF 내보내기
 * html2pdf.js를 사용하여 에디터 DOM을 PDF로 변환합니다.
 */

interface ExportPdfOptions {
  filename?: string;
  /** ProseMirror 에디터 영역의 HTML 문자열 */
  html: string;
}

export async function exportToPdf({ filename = '탐구보고서', html }: ExportPdfOptions): Promise<void> {
  // html2pdf.js는 ESM default export가 아닌 UMD이므로 dynamic import
  const html2pdf = (await import('html2pdf.js')).default;

  // 임시 DOM 컨테이너를 만들어 인쇄용 스타일 적용
  const container = document.createElement('div');
  container.innerHTML = html;

  // 인쇄용 스타일 주입
  Object.assign(container.style, {
    width: '210mm',
    padding: '25mm 20mm 30mm 20mm',
    fontFamily:
      "'Pretendard Variable', 'Pretendard', -apple-system, BlinkMacSystemFont, 'Noto Sans KR', sans-serif",
    fontSize: '11pt',
    lineHeight: '1.6',
    color: '#1e293b',
    wordBreak: 'keep-all',
    overflowWrap: 'break-word',
    background: '#ffffff',
  });

  // 테이블 스타일
  container.querySelectorAll('table').forEach((table) => {
    (table as HTMLElement).style.borderCollapse = 'collapse';
    (table as HTMLElement).style.width = '100%';
    (table as HTMLElement).style.margin = '1rem 0';
    (table as HTMLElement).style.fontSize = '10pt';
  });
  container.querySelectorAll('td, th').forEach((cell) => {
    (cell as HTMLElement).style.border = '1px solid #e2e8f0';
    (cell as HTMLElement).style.padding = '6px 10px';
    (cell as HTMLElement).style.verticalAlign = 'top';
  });
  container.querySelectorAll('th').forEach((th) => {
    (th as HTMLElement).style.fontWeight = '700';
    (th as HTMLElement).style.backgroundColor = '#f8fafc';
  });

  // Heading 스타일
  container.querySelectorAll('h1').forEach((h) => {
    (h as HTMLElement).style.fontSize = '22pt';
    (h as HTMLElement).style.fontWeight = '800';
    (h as HTMLElement).style.borderBottom = '2px solid #e2e8f0';
    (h as HTMLElement).style.paddingBottom = '0.4rem';
    (h as HTMLElement).style.marginTop = '1.5rem';
    (h as HTMLElement).style.marginBottom = '0.75rem';
  });
  container.querySelectorAll('h2').forEach((h) => {
    (h as HTMLElement).style.fontSize = '16pt';
    (h as HTMLElement).style.fontWeight = '700';
    (h as HTMLElement).style.borderBottom = '1px solid #f1f5f9';
    (h as HTMLElement).style.paddingBottom = '0.3rem';
  });
  container.querySelectorAll('h3').forEach((h) => {
    (h as HTMLElement).style.fontSize = '13pt';
    (h as HTMLElement).style.fontWeight = '700';
  });

  // blockquote
  container.querySelectorAll('blockquote').forEach((bq) => {
    (bq as HTMLElement).style.borderLeft = '4px solid #3b82f6';
    (bq as HTMLElement).style.background = '#f8fafc';
    (bq as HTMLElement).style.padding = '0.75rem 1rem';
    (bq as HTMLElement).style.margin = '1rem 0';
    (bq as HTMLElement).style.fontStyle = 'italic';
    (bq as HTMLElement).style.color = '#475569';
  });

  // img
  container.querySelectorAll('img').forEach((img) => {
    (img as HTMLElement).style.maxWidth = '100%';
    (img as HTMLElement).style.height = 'auto';
    (img as HTMLElement).style.display = 'block';
    (img as HTMLElement).style.margin = '1rem auto';
  });

  // hr
  container.querySelectorAll('hr').forEach((hr) => {
    (hr as HTMLElement).style.border = 'none';
    (hr as HTMLElement).style.borderTop = '1px solid #e2e8f0';
    (hr as HTMLElement).style.margin = '2rem 0';
  });

  document.body.appendChild(container);

  try {
    const pdfOptions = {
      margin: 0,
      filename: `${filename}.pdf`,
      image: { type: 'jpeg' as const, quality: 0.98 },
      html2canvas: {
        scale: 2,
        useCORS: true,
        letterRendering: true,
        logging: false,
      },
      jsPDF: {
        unit: 'mm',
        format: 'a4',
        orientation: 'portrait' as const,
      },
      pagebreak: { mode: ['avoid-all', 'css', 'legacy'] },
    };

    await html2pdf()
      .set(pdfOptions)
      .from(container)
      .save();
  } finally {
    document.body.removeChild(container);
  }
}
