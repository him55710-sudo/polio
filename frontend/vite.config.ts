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
      // Do not modifyâfile watching is disabled to prevent flickering during agent edits.
      hmr: process.env.DISABLE_HMR !== 'true',
    },
  };
});
