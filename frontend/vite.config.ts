import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';
import path from 'path';

export default defineConfig({
  plugins: [sveltekit()],
  resolve: {
    alias: {
      // Expose spec tokens without a parallel copy (PROCESS.md §2.4 consumer discipline).
      '@tokens': path.resolve(__dirname, '../specs/UI/mockups/_shared/tokens.css'),
      // Brand identity SVG sources.
      '@brand': path.resolve(__dirname, '../specs/brand/identity'),
    },
  },
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
});
