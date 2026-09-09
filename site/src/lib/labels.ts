/** Region + discipline display helpers for CS-student-facing filters. */

import { slugifyCompany } from './types';
import type { AcademicTerm } from './types';

export type RegionId = 'na' | 'eu' | 'asia' | 'remote';

export const REGION_LABELS: Record<RegionId, string> = {
  na: 'North America',
  eu: 'Europe',
  asia: 'Asia',
  remote: 'Remote',
};

export const REGION_OPTIONS = Object.keys(REGION_LABELS) as RegionId[];

/** Season / academic-term filters students usually care about. */
export const SEASON_TERMS = [
  'summer',
  'fall',
  'winter',
  'spring',
] as const satisfies readonly AcademicTerm[];

export type SeasonTerm = (typeof SEASON_TERMS)[number];

/**
 * Curated startup ecosystem companies from config/sources.yml
 * (YC / a16z / early-stage section). Matched by company-name slug.
 */
const STARTUP_COMPANY_NAMES = [
  'Y Combinator',
  'Resend',
  'PostHog',
  'Railway',
  'Render',
  'Doppler',
  'Inngest',
  'Trigger.dev',
  'Nango',
  'Prefect',
  'Airbyte',
  'Hightouch',
  'Metabase',
  'Sanity',
  'Mux',
  'LiveKit',
  'Docker',
  'Orca Security',
  'Drata',
  'Secureframe',
  'Material Security',
  'Replit',
  'Attio',
  'Plain',
  'Incident.io',
  'Apollo.io',
  'Fireworks AI',
  'Recraft',
  'Character.AI',
  'Decagon',
  'Poolside',
  'Mercor',
  'Parallel',
  'Descript',
  'Gamma',
  'Elicit',
  'Labelbox',
  'Lightning AI',
  'Saronic',
  'Nava',
  'Astera Labs',
  'IonQ',
  'PathAI',
  'Warp',
  'Figure',
  'Linear',
  'Vercel',
  'Supabase',
  'Ramp',
  'Notion',
  'Plaid',
  'Anthropic',
  'Perplexity',
  'Scale AI',
  'Mercury',
  'Brex',
  'Rippling',
  'PlanetScale',
  'Retool',
] as const;

export const STARTUP_COMPANY_SLUGS = new Set(
  STARTUP_COMPANY_NAMES.map((name) => slugifyCompany(name)),
);

export function isStartupCompany(companyName: string): boolean {
  return STARTUP_COMPANY_SLUGS.has(slugifyCompany(companyName));
}

export const DISCIPLINE_LABELS: Record<string, string> = {
  software: 'Software Engineering',
  frontend: 'Frontend',
  backend: 'Backend',
  full_stack: 'Full Stack',
  mobile: 'Mobile',
  systems: 'Systems',
  infrastructure: 'Infrastructure',
  cloud: 'Cloud',
  devops: 'DevOps',
  sre: 'SRE',
  cybersecurity: 'Cybersecurity',
  networking: 'Networking',
  it: 'IT',
  technical_support: 'Technical Support',
  data_engineering: 'Data Engineering',
  data_science: 'Data Science',
  machine_learning: 'Machine Learning',
  artificial_intelligence: 'Artificial Intelligence',
  quantitative_development: 'Quantitative Development',
  quantitative_research: 'Quantitative Research',
  product: 'Product',
  hardware: 'Hardware',
  embedded: 'Embedded Systems',
  firmware: 'Firmware',
  robotics: 'Robotics',
  qa_automation: 'QA / Automation',
  other: 'Other',
};

/** Default CS / software tracks shown for students. */
export const CS_DISCIPLINES = [
  'software',
  'frontend',
  'backend',
  'full_stack',
  'mobile',
  'systems',
  'infrastructure',
  'cloud',
  'devops',
  'sre',
  'cybersecurity',
  'data_engineering',
  'data_science',
  'machine_learning',
  'artificial_intelligence',
  'quantitative_development',
  'quantitative_research',
  'hardware',
  'embedded',
  'firmware',
  'robotics',
  'qa_automation',
] as const;

const NA_CODES = new Set(['US', 'CA', 'MX']);
const EU_CODES = new Set([
  'GB',
  'IE',
  'FR',
  'DE',
  'NL',
  'ES',
  'IT',
  'SE',
  'NO',
  'DK',
  'FI',
  'CH',
  'AT',
  'BE',
  'PT',
  'PL',
  'CZ',
  'RO',
  'HU',
  'GR',
]);
const ASIA_CODES = new Set([
  'IN',
  'SG',
  'JP',
  'CN',
  'KR',
  'HK',
  'TW',
  'ID',
  'MY',
  'TH',
  'PH',
  'VN',
  'AE',
  'IL',
]);

export function formatDiscipline(id: string): string {
  if (DISCIPLINE_LABELS[id]) return DISCIPLINE_LABELS[id];
  return id
    .split('_')
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
}

export function regionsForJob(job: {
  workplace_type?: string;
  locations: Array<{
    continent?: string | null;
    country?: string | null;
    country_code?: string | null;
    raw?: string | null;
  }>;
}): RegionId[] {
  const found = new Set<RegionId>();
  if (job.workplace_type === 'remote') {
    found.add('remote');
  }

  for (const loc of job.locations) {
    const code = (loc.country_code || '').toUpperCase();
    const continent = (loc.continent || '').toLowerCase();
    const blob = `${loc.country || ''} ${loc.raw || ''}`.toLowerCase();

    if (NA_CODES.has(code) || continent.includes('north america')) {
      found.add('na');
    } else if (EU_CODES.has(code) || continent.includes('europe')) {
      found.add('eu');
    } else if (ASIA_CODES.has(code) || continent.includes('asia')) {
      found.add('asia');
    } else if (
      blob.includes('united states') ||
      blob.includes('canada') ||
      blob.includes('mexico')
    ) {
      found.add('na');
    } else if (
      blob.includes('united kingdom') ||
      blob.includes('germany') ||
      blob.includes('france') ||
      blob.includes('ireland') ||
      blob.includes('netherlands')
    ) {
      found.add('eu');
    } else if (
      blob.includes('india') ||
      blob.includes('singapore') ||
      blob.includes('japan') ||
      blob.includes('china') ||
      blob.includes('korea')
    ) {
      found.add('asia');
    }

    if (blob.includes('remote')) {
      found.add('remote');
    }
  }

  return [...found];
}

export function jobMatchesRegions(
  job: {
    workplace_type?: string;
    locations: Array<{
      continent?: string | null;
      country?: string | null;
      country_code?: string | null;
      raw?: string | null;
    }>;
  },
  regions: string[],
): boolean {
  if (regions.length === 0) return true;
  const jobRegions = regionsForJob(job);
  return regions.some((region) => jobRegions.includes(region as RegionId));
}
