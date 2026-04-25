import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import path from 'path';
import {defineConfig, loadEnv} from 'vite';
import { visualizer } from 'rollup-plugin-visualizer';

export default defineConfig(({mode}) => {
  const env = loadEnv(mode, '.', '');
  const shouldAnalyzeBundle = env.ANALYZE === 'true';
  return {
    plugins: [
      react(),
      tailwindcss(),
      ...(shouldAnalyzeBundle
        ? [visualizer({ open: false, filename: 'stats.html', gzipSize: true, brotliSize: true })]
        : []),
    ],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, '.'),
        '@shared-contracts': path.resolve(__dirname, '../packages/shared-contracts/src'),
      },
    },
    server: {
      // HMR is disabled in AI Studio via DISABLE_HMR env var.
      // Do not modify—file watching is disabled to prevent flickering during agent edits.
      hmr: process.env.DISABLE_HMR !== 'true',
    },
    build: {
      chunkSizeWarningLimit: 2000, // 늘어난 에디터와 기능들을 수용하기 위해 2000kb로 상향
      rollupOptions: {
        output: {
          manualChunks(id) {
            // Tiptap 관련 라이브러리 분리
            if (id.includes('@tiptap') || id.includes('prosemirror')) {
              return 'editor-core';
            }
            // 그 외 대형 외부 라이브러리 분리
            if (id.includes('node_modules')) {
              if (id.includes('lucide-react') || id.includes('framer-motion')) {
                return 'ui-vendor';
              }
              return 'vendor';
            }
          },
        },
      },
    },
  };
});
