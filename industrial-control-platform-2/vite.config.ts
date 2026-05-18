import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'frontend/src'),
    },
  },
  build: {
    target: 'es2015',
    outDir: 'dist',
    assetsDir: 'assets',
    rollupOptions: {
      external: ['mqtt'],
      output: {
        manualChunks: {
          'element-plus': ['element-plus'],
          'echarts': ['echarts'],
          'three': ['three'],
        },
      },
    },
  },
  server: {
    port: 3000,
    host: '0.0.0.0',
    cors: true,
  },
  optimizeDeps: {
    include: ['element-plus', 'echarts', 'three'],
    exclude: ['mqtt'],
  },
  define: {
    global: 'globalThis',
  },
});
