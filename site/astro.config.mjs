import { defineConfig } from 'astro/config';
import react from '@astrojs/react';
import sitemap from '@astrojs/sitemap';

const base = process.env.ASTRO_BASE ?? '/Open-Role-Radar/';
const repo = process.env.GITHUB_REPOSITORY ?? 'moosacodes/Open-Role-Radar';
const owner = repo.split('/')[0] || 'moosacodes';

export default defineConfig({
  site: process.env.ASTRO_SITE ?? `https://${owner}.github.io`,
  base,
  output: 'static',
  integrations: [react(), sitemap()],
  vite: {
    define: {
      __SITE_BASE__: JSON.stringify(base),
      __GITHUB_REPO__: JSON.stringify(repo),
    },
  },
});
