import { postedAt } from './dates';
import type { FilterState } from './filters';
import { bucketForJobId } from './sha256';
import type {
  CompanySummary,
  Job,
  MobilityBenefits,
  MobilityFlag,
  SearchIndexEntry,
  SiteStats,
  SortMode,
} from './types';
import {
  getMobilityFlags,
  MOBILITY_CLAIM_KEYS,
  slugifyCompany,
} from './types';

const FRESHNESS_MS: Record<string, number> = {
  '24h': 24 * 60 * 60 * 1000,
  '7d': 7 * 24 * 60 * 60 * 1000,
  '30d': 30 * 24 * 60 * 60 * 1000,
};

export function buildSearchIndex(jobs: Job[], hashBuckets = 32): SearchIndexEntry[] {
  return jobs.map((job) => ({
    job_id: job.job_id,
    company_id: job.company_id,
    company_name: job.company_name,
    company_slug: slugifyCompany(job.company_name),
    title: job.title,
    title_lower: job.title.toLowerCase(),
    career_level: job.career_level,
    discipline: job.disciplines.primary,
    location_text: job.locations
      .map((loc) => [loc.city, loc.region, loc.country, loc.raw].filter(Boolean).join(', '))
      .join(' | ')
      .toLowerCase(),
    workplace_type: job.workplace_type,
    posted_at: postedAt(job),
    first_seen_at: job.first_seen_at,
    mobility_flags: getMobilityFlags(job.mobility),
    bucket: bucketForJobId(job.job_id, hashBuckets),
  }));
}

export function tokenizeQuery(query: string): string[] {
  return query
    .toLowerCase()
    .split(/\s+/)
    .map((token) => token.trim())
    .filter((token) => token.length >= 2);
}

export function matchesQuery(entry: SearchIndexEntry, tokens: string[]): boolean {
  if (tokens.length === 0) return true;
  const haystack = `${entry.title_lower} ${entry.company_name.toLowerCase()} ${entry.location_text} ${entry.discipline}`;
  return tokens.every((token) => haystack.includes(token));
}

export function matchesFreshness(
  dateIso: string,
  freshness: FilterState['freshness'],
  lastVisit: string | null,
): boolean {
  if (freshness === 'all') return true;
  const seen = Date.parse(dateIso);
  if (Number.isNaN(seen)) return true;

  if (freshness === 'new_since_visit') {
    if (!lastVisit) return true;
    const visit = Date.parse(lastVisit);
    return !Number.isNaN(visit) && seen > visit;
  }

  const windowMs = FRESHNESS_MS[freshness];
  if (!windowMs) return true;
  return Date.now() - seen <= windowMs;
}

export function matchesMobility(job: Job, flags: MobilityFlag[]): boolean {
  if (flags.length === 0) return true;
  return flags.every((flag) => {
    const claim = job.mobility[MOBILITY_CLAIM_KEYS[flag]];
    return claim.status === 'confirmed';
  });
}

export function sortJobs(jobs: Job[], sort: SortMode): Job[] {
  const copy = [...jobs];
  if (sort === 'company') {
    return copy.sort(
      (a, b) =>
        a.company_name.localeCompare(b.company_name) ||
        a.title.localeCompare(b.title),
    );
  }
  if (sort === 'title') {
    return copy.sort(
      (a, b) =>
        a.title.localeCompare(b.title) ||
        a.company_name.localeCompare(b.company_name),
    );
  }
  return copy.sort((a, b) => {
    const diff = Date.parse(postedAt(b)) - Date.parse(postedAt(a));
    if (diff !== 0) return diff;
    return a.job_id.localeCompare(b.job_id);
  });
}

export function filterJobs(
  jobs: Job[],
  index: SearchIndexEntry[],
  filters: FilterState,
  options: {
    savedJobIds?: Set<string>;
    dismissedJobIds?: Set<string>;
    lastVisit?: string | null;
  } = {},
): Job[] {
  const indexById = new Map(index.map((entry) => [entry.job_id, entry]));
  const tokens = tokenizeQuery(filters.q);
  const saved = options.savedJobIds ?? new Set<string>();
  const dismissed = options.dismissedJobIds ?? new Set<string>();

  const filtered = jobs.filter((job) => {
    const entry = indexById.get(job.job_id);
    if (!entry) return false;

    if (filters.hideDismissed && dismissed.has(job.job_id)) return false;
    if (filters.showSavedOnly && !saved.has(job.job_id)) return false;
    if (!matchesQuery(entry, tokens)) return false;

    if (
      filters.careerLevels.length > 0 &&
      !filters.careerLevels.includes(job.career_level)
    ) {
      return false;
    }

    if (
      filters.disciplines.length > 0 &&
      !filters.disciplines.includes(job.disciplines.primary)
    ) {
      return false;
    }

    if (filters.locations.length > 0) {
      const locationHaystack = entry.location_text;
      const locationMatch = filters.locations.some((loc) =>
        locationHaystack.includes(loc.toLowerCase()),
      );
      if (!locationMatch) return false;
    }

    if (
      filters.workplaceTypes.length > 0 &&
      !filters.workplaceTypes.includes(job.workplace_type)
    ) {
      return false;
    }

    if (!matchesFreshness(entry.posted_at, filters.freshness, options.lastVisit ?? null)) {
      return false;
    }

    if (!matchesMobility(job, filters.mobility)) return false;

    if (filters.originCountry) {
      const country = filters.originCountry.toLowerCase();
      const allowed = job.eligibility.explicit_allowed_countries.map((c) => c.toLowerCase());
      const excluded = job.eligibility.explicit_excluded_countries.map((c) => c.toLowerCase());
      if (excluded.includes(country)) return false;
      if (allowed.length > 0 && !allowed.includes(country)) return false;
    }

    return true;
  });

  return sortJobs(filtered, filters.sort);
}

export function paginateJobs<T>(items: T[], page: number, pageSize: number): T[] {
  const safePage = Math.max(1, page);
  const start = (safePage - 1) * pageSize;
  return items.slice(start, start + pageSize);
}

export function totalPages(count: number, pageSize: number): number {
  return Math.max(1, Math.ceil(count / pageSize));
}

export function computeStats(
  jobs: Job[],
  lastVisit: string | null,
  generatedAt: string,
): SiteStats {
  const companies = new Set(jobs.map((job) => job.company_id));
  const withVisa = jobs.filter(
    (job) => job.mobility.visa_sponsorship.status === 'confirmed',
  ).length;
  const withRelocation = jobs.filter(
    (job) => job.mobility.relocation_assistance.status === 'confirmed',
  ).length;
  const remoteCount = jobs.filter((job) => job.workplace_type === 'remote').length;
  const newSinceVisit = lastVisit
    ? jobs.filter((job) => matchesFreshness(postedAt(job), 'new_since_visit', lastVisit))
        .length
    : 0;

  return {
    totalJobs: jobs.length,
    totalCompanies: companies.size,
    withVisa,
    withRelocation,
    remoteCount,
    newSinceVisit,
    generatedAt,
  };
}

export function aggregateCompanies(jobs: Job[]): CompanySummary[] {
  const map = new Map<string, CompanySummary>();
  for (const job of jobs) {
    const existing = map.get(job.company_id);
    if (existing) {
      existing.job_count += 1;
    } else {
      map.set(job.company_id, {
        company_id: job.company_id,
        name: job.company_name,
        slug: slugifyCompany(job.company_name),
        job_count: 1,
      });
    }
  }
  return [...map.values()].sort((a, b) => a.name.localeCompare(b.name));
}

export function collectFacetValues(jobs: Job[]): {
  disciplines: string[];
  locations: string[];
} {
  const disciplines = new Set<string>();
  const locations = new Set<string>();

  for (const job of jobs) {
    if (job.disciplines.primary && job.disciplines.primary !== 'other') {
      disciplines.add(job.disciplines.primary);
    }
    for (const loc of job.locations) {
      for (const part of [loc.city, loc.region, loc.country]) {
        if (part) locations.add(part);
      }
    }
  }

  return {
    disciplines: [...disciplines].sort(),
    locations: [...locations].sort((a, b) => a.localeCompare(b)),
  };
}

export function getMobilityClaims(
  mobility: MobilityBenefits,
  flag: MobilityFlag,
) {
  return mobility[MOBILITY_CLAIM_KEYS[flag]];
}
