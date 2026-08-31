import type {
  AcademicTerm,
  CareerLevel,
  EligibilityMatch,
  FilterState,
  FreshnessFilter,
  MobilityFlag,
  RemoteScope,
  ViewMode,
  WorkplaceType,
} from './types';

const DEFAULT_PAGE_SIZE = 25;

export const DEFAULT_FILTERS: FilterState = {
  q: '',
  careerLevels: [],
  disciplines: [],
  locations: [],
  workplaceTypes: [],
  remoteScopes: [],
  academicTerms: [],
  freshness: 'all',
  mobility: [],
  originCountry: '',
  eligibilityMatches: [],
  showSavedOnly: false,
  hideDismissed: true,
  page: 1,
  pageSize: DEFAULT_PAGE_SIZE,
  view: 'cards',
};

const ARRAY_KEYS = new Set([
  'careerLevels',
  'disciplines',
  'locations',
  'workplaceTypes',
  'remoteScopes',
  'academicTerms',
  'mobility',
  'eligibilityMatches',
]);

const BOOL_KEYS = new Set(['showSavedOnly', 'hideDismissed']);

const NUMBER_KEYS = new Set(['page', 'pageSize']);

function parseList<T extends string>(value: string | null): T[] {
  if (!value) return [];
  return value.split(',').filter(Boolean) as T[];
}

function serializeList(values: string[]): string | undefined {
  if (values.length === 0) return undefined;
  return values.join(',');
}

export function parseFiltersFromUrl(search: string): FilterState {
  const params = new URLSearchParams(search);
  const next: FilterState = { ...DEFAULT_FILTERS };

  for (const key of Object.keys(DEFAULT_FILTERS) as (keyof FilterState)[]) {
    const raw = params.get(key);
    if (raw === null) continue;

    if (ARRAY_KEYS.has(key)) {
      (next[key] as string[]) = parseList(raw);
      continue;
    }

    if (BOOL_KEYS.has(key)) {
      (next[key] as boolean) = raw === '1' || raw === 'true';
      continue;
    }

    if (NUMBER_KEYS.has(key)) {
      const num = Number.parseInt(raw, 10);
      if (!Number.isNaN(num) && num > 0) {
        (next[key] as number) = num;
      }
      continue;
    }

    if (key === 'freshness') {
      next.freshness = raw as FreshnessFilter;
      continue;
    }

    if (key === 'view') {
      next.view = raw as ViewMode;
      continue;
    }

    if (key === 'q' || key === 'originCountry') {
      next[key] = raw;
    }
  }

  return next;
}

export function serializeFiltersToUrl(filters: FilterState): string {
  const params = new URLSearchParams();

  for (const key of Object.keys(DEFAULT_FILTERS) as (keyof FilterState)[]) {
    const value = filters[key];
    const defaultValue = DEFAULT_FILTERS[key];

    if (ARRAY_KEYS.has(key)) {
      const serialized = serializeList(value as string[]);
      if (serialized) params.set(key, serialized);
      continue;
    }

    if (BOOL_KEYS.has(key)) {
      if (value !== defaultValue) {
        params.set(key, value ? '1' : '0');
      }
      continue;
    }

    if (NUMBER_KEYS.has(key)) {
      if (value !== defaultValue) {
        params.set(key, String(value));
      }
      continue;
    }

    if (key === 'q' || key === 'originCountry') {
      if (value && value !== defaultValue) {
        params.set(key, value as string);
      }
      continue;
    }

    if (value !== defaultValue) {
      params.set(key, String(value));
    }
  }

  const query = params.toString();
  return query ? `?${query}` : '';
}

export function filtersAreDefault(filters: FilterState): boolean {
  return serializeFiltersToUrl(filters) === '';
}

export function countActiveFilters(filters: FilterState): number {
  let count = 0;
  if (filters.q.trim()) count += 1;
  if (filters.careerLevels.length) count += 1;
  if (filters.disciplines.length) count += 1;
  if (filters.locations.length) count += 1;
  if (filters.workplaceTypes.length) count += 1;
  if (filters.remoteScopes.length) count += 1;
  if (filters.academicTerms.length) count += 1;
  if (filters.freshness !== 'all') count += 1;
  if (filters.mobility.length) count += 1;
  if (filters.originCountry) count += 1;
  if (filters.eligibilityMatches.length) count += 1;
  if (filters.showSavedOnly) count += 1;
  return count;
}

export function toggleArrayValue<T extends string>(values: T[], value: T): T[] {
  return values.includes(value)
    ? values.filter((item) => item !== value)
    : [...values, value];
}

export type {
  AcademicTerm,
  CareerLevel,
  EligibilityMatch,
  FilterState,
  FreshnessFilter,
  MobilityFlag,
  RemoteScope,
  ViewMode,
  WorkplaceType,
};
