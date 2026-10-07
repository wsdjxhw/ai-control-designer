import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  base: '/static/',
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  build: {
    // ✅ 两级上溯：ai-control-designer/web/ → bisai/backend/static
    outDir: '../../backend/static',
    emptyOutDir: true,
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        // 与 start.bat 一致
        target: 'http://localhost:8001',
        changeOrigin: true,
      }
    }
  }
});