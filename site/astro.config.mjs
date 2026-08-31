import { defineConfig } from 'astro/config';
import react from '@astrojs/react';
import sitemap from '@astrojs/sitemap';

const base = process.env.ASTRO_BASE ?? '/Open-Role-Radar/';

export default defineConfig({
  site: process.env.ASTRO_SITE ?? 'https://kenjiifx.github.io',
  base,
  output: 'static',
  integrations: [react(), sitemap()],
  vite: {
    define: {
      __SITE_BASE__: JSON.stringify(base),
    },
  },
});
