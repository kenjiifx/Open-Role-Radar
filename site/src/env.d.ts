/// <reference types="astro/client" />

declare const __SITE_BASE__: string;

interface ImportMetaEnv {
  readonly BASE_URL: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
