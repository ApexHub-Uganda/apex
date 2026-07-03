import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

const resolveDevApiProxy = (env) => {
  if (env.VITE_DEV_API_PROXY) {
    return env.VITE_DEV_API_PROXY.replace(/\/$/, '');
  }

  const configured = env.VITE_API_BASE_URL || '';
  if (configured.startsWith('http://') || configured.startsWith('https://')) {
    return configured.replace(/\/api\/v1\/?$/, '').replace(/\/$/, '') || 'http://localhost:8000';
  }

  return 'http://localhost:8000';
};

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const apiTarget = resolveDevApiProxy(env);

  return {
    plugins: [react()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
      },
    },
    server: {
      port: 3000,
      proxy: {
        '/api': {
          target: apiTarget,
          changeOrigin: true,
          secure: false,
        },
      },
    },
    build: {
      outDir: 'dist',
      sourcemap: false,
      rollupOptions: {
        output: {
          manualChunks: {
            vendor: ['react', 'react-dom', 'react-router-dom'],
            charts: ['chart.js', 'react-chartjs-2'],
            motion: ['framer-motion'],
          },
        },
      },
    },
  };
});