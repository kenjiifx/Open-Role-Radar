import type { DataManifest, Job, ShardInfo } from './types';
import { bucketForJobId } from './sha256';

declare const __SITE_BASE__: string;

const DATA_BASE = `${__SITE_BASE__}data/`;

const shardCache = new Map<string, Job[]>();
const inflight = new Map<string, Promise<Job[]>>();

let manifestPromise: Promise<DataManifest> | null = null;
let manifestVersion = '';

export function getDataBaseUrl(): string {
  return DATA_BASE;
}

export async function loadManifest(): Promise<DataManifest> {
  if (!manifestPromise) {
    const bust = Date.now();
    manifestPromise = fetch(`${DATA_BASE}manifest.json?t=${bust}`, { cache: 'no-store' })
      .then(async (response) => {
        if (!response.ok) {
          throw new Error(`Failed to load manifest: ${response.status}`);
        }
        const manifest = (await response.json()) as DataManifest;
        manifestVersion = manifest.generated_at || String(bust);
        return manifest;
      })
      .catch((error) => {
        manifestPromise = null;
        throw error;
      });
  }
  return manifestPromise;
}

export function resetDataLoader(): void {
  manifestPromise = null;
  manifestVersion = '';
  shardCache.clear();
  inflight.clear();
}

export async function loadShard(filename: string): Promise<Job[]> {
  const cacheKey = `${filename}::${manifestVersion}`;
  const cached = shardCache.get(cacheKey);
  if (cached) return cached;

  const pending = inflight.get(cacheKey);
  if (pending) return pending;

  const version = encodeURIComponent(manifestVersion || String(Date.now()));
  const promise = fetch(`${DATA_BASE}${filename}?v=${version}`, { cache: 'no-store' })
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
