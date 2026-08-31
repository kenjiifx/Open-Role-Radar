export function siteBase(): string {
  if (typeof import.meta !== 'undefined' && import.meta.env?.BASE_URL) {
    return import.meta.env.BASE_URL;
  }
  if (typeof __SITE_BASE__ !== 'undefined') {
    return __SITE_BASE__;
  }
  return '/';
}

export function companyUrl(slug: string): string {
  return `${siteBase()}company/${slug}/`;
}
