import companySeeds from '../data/company-domains.json';
import { slugifyCompany, type Job } from './types';

const ATS_HOST =
  /greenhouse|lever\.co|ashbyhq|myworkdayjobs|workdayjobs|workable\.com|smartrecruiters|icims\.com|ultipro|successfactors|taleo|jobvite|bamboohr|recruitee|comeet|myworkday\.com/i;

type CompanySeed = {
  company: string;
  domain: string;
  tenant: string;
};

function hostname(value?: string | null): string | null {
  if (!value) return null;
  try {
    return new URL(value).hostname.replace(/^www\./i, '').toLowerCase();
  } catch {
    return null;
  }
}

function logoDomain(domain: string): string {
  return domain.replace(/^(www|about|careers|jobs)\./i, '').toLowerCase();
}

function tenantFromPath(url: string | null | undefined, hostPart: string): string | null {
  if (!url) return null;
  try {
    const parsed = new URL(url);
    if (!parsed.hostname.toLowerCase().includes(hostPart)) return null;
    const parts = parsed.pathname.split('/').filter(Boolean);
    const skip = new Set(['jobs', 'job', 'boards', 'embed', 'v2', 'api']);
    const tenant = parts.find((part) => !skip.has(part.toLowerCase()));
    return tenant && /^[a-z0-9-]+$/i.test(tenant) ? tenant.toLowerCase() : null;
  } catch {
    return null;
  }
}

const domainBySlug = new Map<string, string>();
const domainByTenant = new Map<string, string>();

for (const seed of companySeeds as CompanySeed[]) {
  const domain = logoDomain(seed.domain);
  if (!domain) continue;
  domainBySlug.set(slugifyCompany(seed.company), domain);
  if (seed.tenant && /^[a-z0-9-]+$/i.test(seed.tenant)) {
    domainByTenant.set(seed.tenant.toLowerCase(), domain);
  }
}

type JobUrls = Pick<Job, 'company_name' | 'careers_url' | 'source_url' | 'job_url' | 'apply_url'>;

/** Best-effort first-party domain for logo lookups. */
export function companyDomain(job: JobUrls): string | null {
  const fromSeed = domainBySlug.get(slugifyCompany(job.company_name));
  if (fromSeed) return fromSeed;

  const candidates = [job.careers_url, job.source_url, job.job_url, job.apply_url];
  for (const url of candidates) {
    const host = hostname(url);
    if (host && !ATS_HOST.test(host)) return logoDomain(host);
  }

  const urls = [job.job_url, job.apply_url, job.source_url, job.careers_url];
  for (const url of urls) {
    const greenhouse = tenantFromPath(url, 'greenhouse');
    if (greenhouse) return domainByTenant.get(greenhouse) ?? `${greenhouse}.com`;
    const lever = tenantFromPath(url, 'lever.co');
    if (lever) return domainByTenant.get(lever) ?? `${lever}.com`;
    const ashby = tenantFromPath(url, 'ashby');
    if (ashby) return domainByTenant.get(ashby) ?? `${ashby}.com`;
  }

  return null;
}

export function companyLogoUrls(domain: string): string[] {
  const encoded = encodeURIComponent(domain);
  const page = encodeURIComponent(`https://${domain}`);
  return [
    `https://t2.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=${page}&size=128`,
    `https://icons.duckduckgo.com/ip3/${encoded}.ico`,
    `https://www.google.com/s2/favicons?sz=128&domain=${encoded}`,
  ];
}

export function companyLogoUrl(domain: string): string {
  return companyLogoUrls(domain)[0];
}

export function companyInitials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return '?';
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
}
