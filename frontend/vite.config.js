import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const backendUrl = new URL(
    (env.VITE_WS_PROXY_TARGET || env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(
      /\/+$/,
      '',
    ),
  );
  const backendTarget = `${backendUrl.protocol}//${backendUrl.host}`;
  const backendPath = backendUrl.pathname === '/' ? '' : backendUrl.pathname.replace(/\/+$/, '');

  return {
    base: env.VITE_BASE_PATH || '/',
    plugins: [react()],
    server: {
      host: '0.0.0.0',
      port: 5173,
      watch: {
        usePolling: true,
      },
      allowedHosts: env.VITE_ALLOWED_HOSTS ? env.VITE_ALLOWED_HOSTS.split(',') : [],
      proxy: {
        '/results': {
          target: backendTarget,
          changeOrigin: true,
          ws: true,
          rewrite: (path) => `${backendPath}${path}`,
          configure(proxy) {
            proxy.on('proxyReqWs', (proxyReq) => {
              // The forwarding service rejects the browser's external Origin.
              proxyReq.removeHeader('origin');
            });
          },
        },
      },
    },
  };
});
