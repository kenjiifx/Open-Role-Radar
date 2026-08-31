import { defineConfig } from 'vitest/config';
import { resolve } from 'node:path';

export default defineConfig({
  test: {
    globals: true,
    environment: 'node',
    include: ['tests/**/*.test.ts'],
  },
  define: {
    __SITE_BASE__: JSON.stringify('/Open-Role-Radar/'),
  },
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
  },
});
