import type { DataManifest, Job, ShardInfo } from './types';
import { bucketForJobId } from './sha256';

declare const __SITE_BASE__: string;

/** Prefer sources that update immediately after sync (bypass Pages CDN lag). */
const FEED_BASES = [
  'https://raw.githubusercontent.com/kenjiifx/Open-Role-Radar/live-feed/',
  'https://cdn.jsdelivr.net/gh/kenjiifx/Open-Role-Radar@live-feed/',
  `${__SITE_BASE__}data/`,
] as const;

type FeedBase = (typeof FEED_BASES)[number];

const shardCache = new Map<string, Job[]>();
const inflight = new Map<string, Promise<Job[]>>();

let manifestPromise: Promise<DataManifest> | null = null;
let manifestVersion = '';
let activeDataBase: string = FEED_BASES[2];

export function getDataBaseUrl(): string {
  return activeDataBase;
}

async function fetchManifestFrom(base: string, bust: number): Promise<DataManifest | null> {
  try {
    const response = await fetch(`${base}manifest.json?t=${bust}`, {
      cache: 'no-store',
      headers: { Accept: 'application/json' },
    });
    if (!response.ok) return null;
    const manifest = (await response.json()) as DataManifest;
    if (!manifest || !Array.isArray(manifest.shards)) return null;
    return manifest;
  } catch {
    return null;
  }
}

function manifestTime(manifest: DataManifest): number {
  const stamp = Date.parse(manifest.generated_at);
  return Number.isNaN(stamp) ? 0 : stamp;
}

export async function loadManifest(): Promise<DataManifest> {
  if (!manifestPromise) {
    const bust = Date.now();
    manifestPromise = (async () => {
      const results = await Promise.all(
        FEED_BASES.map(async (base) => {
          const manifest = await fetchManifestFrom(base, bust);
          return manifest ? { base, manifest } : null;
        }),
      );
      const available: { base: FeedBase; manifest: DataManifest }[] = [];
      for (const item of results) {
        if (item) available.push(item);
      }
      if (available.length === 0) {
        throw new Error('Failed to load job feed from live-feed, jsDelivr, or Pages');
      }
      available.sort((a, b) => manifestTime(b.manifest) - manifestTime(a.manifest));
      const winner = available[0];
      activeDataBase = winner.base;
      manifestVersion = winner.manifest.generated_at || String(bust);
      return winner.manifest;
    })().catch((error) => {
      manifestPromise = null;
      throw error;
    });
  }
  return manifestPromise;
}

export function resetDataLoader(): void {
  manifestPromise = null;
  manifestVersion = '';
  activeDataBase = FEED_BASES[2];
  shardCache.clear();
  inflight.clear();
}

/** Fetch the newest manifest without clearing the in-memory shard cache. */
export async function peekNewestManifest(): Promise<DataManifest> {
  const bust = Date.now();
  const results = await Promise.all(
    FEED_BASES.map(async (base) => {
      const manifest = await fetchManifestFrom(base, bust);
      return manifest ? { base, manifest } : null;
    }),
  );
  const available = results.filter(
    (item): item is { base: FeedBase; manifest: DataManifest } => item !== null,
  );
  if (available.length === 0) {
    throw new Error('Failed to load job feed from live-feed, jsDelivr, or Pages');
  }
  available.sort((a, b) => manifestTime(b.manifest) - manifestTime(a.manifest));
  return available[0].manifest;
}

export async function loadShard(filename: string): Promise<Job[]> {
  const cacheKey = `${activeDataBase}::${filename}::${manifestVersion}`;
  const cached = shardCache.get(cacheKey);
  if (cached) return cached;

  const pending = inflight.get(cacheKey);
  if (pending) return pending;

  const version = encodeURIComponent(manifestVersion || String(Date.now()));
  const bust = Date.now();
  const promise = fetch(`${activeDataBase}${filename}?v=${version}&t=${bust}`, {
    cache: 'no-store',
    headers: { Accept: 'application/json' },
  })
    .then(async (response) => {
      if (!response.ok) {
        throw new Error(`Failed to load shard ${filename}: ${response.status}`);
      }
      const jobs = (await response.json()) as Job[];
      shardCache.set(cacheKey, jobs);
      inflight.delete(cacheKey);
      return jobs;
    })
    .catch((error) => {
      inflight.delete(cacheKey);
      throw error;
    });

  inflight.set(cacheKey, promise);
  return promise;
}

export async function loadAllJobs(manifest?: DataManifest): Promise<Job[]> {
  const resolvedManifest = manifest ?? (await loadManifest());
  if (resolvedManifest.shards.length === 0) return [];

  const shardResults = await Promise.all(
    resolvedManifest.shards.map((shard) => loadShard(shard.filename)),
  );
  return shardResults.flat();
}

export async function loadJobsForBuckets(
  buckets: Set<number>,
  manifest?: DataManifest,
): Promise<Job[]> {
  const resolvedManifest = manifest ?? (await loadManifest());
  const shards = resolvedManifest.shards.filter((shard) => buckets.has(shard.bucket));
  if (shards.length === 0) return [];

  const shardResults = await Promise.all(shards.map((shard) => loadShard(shard.filename)));
  return shardResults.flat();
}

export function shardFilenamesForBuckets(
  shards: ShardInfo[],
  buckets: Set<number>,
): string[] {
  return shards.filter((shard) => buckets.has(shard.bucket)).map((shard) => shard.filename);
}

export function bucketsFromJobIds(
  jobIds: Iterable<string>,
  hashBuckets: number,
): Set<number> {
  const buckets = new Set<number>();
  for (const jobId of jobIds) {
    buckets.add(bucketForJobId(jobId, hashBuckets));
  }
  return buckets;
}

export { bucketForJobId };
