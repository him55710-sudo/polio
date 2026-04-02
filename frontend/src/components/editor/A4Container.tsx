import React from 'react';
import { cn } from '../../lib/cn';

interface A4ContainerProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
  pageNumber?: number;
}

export function A4Container({ children, className, pageNumber = 1, ...props }: A4ContainerProps) {
  return (
    <div className={cn('flex w-full flex-col items-center bg-slate-100 py-8', className)} {...props}>
      {/* A4 page simulation */}
      <div
        className="a4-page relative bg-white transition-shadow duration-300"
        style={{
          width: '210mm',
          minHeight: '297mm',
          padding: '25mm 20mm 30mm 20mm',
          boxShadow:
            '0 1px 3px rgba(0,0,0,0.04), 0 4px 16px rgba(0,0,0,0.08), 0 12px 48px rgba(0,0,0,0.04)',
        }}
      >
        {children}

        {/* Page footer */}
        <div
          className="absolute bottom-0 left-0 right-0 flex items-center justify-between px-[20mm] pb-[10mm]"
          style={{ pointerEvents: 'none' }}
        >
          <span className="text-[10px] font-medium text-slate-300">Uni Folia Document</span>
          <span className="text-[10px] font-medium text-slate-300">{pageNumber}</span>
        </div>
      </div>
    </div>
  );
}
