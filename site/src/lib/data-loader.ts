import type { DataManifest, Job, ShardInfo } from './types';
import { bucketForJobId } from './sha256';

declare const __SITE_BASE__: string;

const DATA_BASE = `${__SITE_BASE__}data/`;

const shardCache = new Map<string, Job[]>();
const inflight = new Map<string, Promise<Job[]>>();

let manifestPromise: Promise<DataManifest> | null = null;

export function getDataBaseUrl(): string {
  return DATA_BASE;
}

export async function loadManifest(): Promise<DataManifest> {
  if (!manifestPromise) {
    manifestPromise = fetch(`${DATA_BASE}manifest.json`, { cache: 'no-cache' })
      .then(async (response) => {
        if (!response.ok) {
          throw new Error(`Failed to load manifest: ${response.status}`);
        }
        return (await response.json()) as DataManifest;
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
  shardCache.clear();
  inflight.clear();
}

export async function loadShard(filename: string): Promise<Job[]> {
  const cached = shardCache.get(filename);
  if (cached) return cached;

  const pending = inflight.get(filename);
  if (pending) return pending;

  const promise = fetch(`${DATA_BASE}${filename}`, { cache: 'force-cache' })
    .then(async (response) => {
      if (!response.ok) {
        throw new Error(`Failed to load shard ${filename}: ${response.status}`);
      }
      const jobs = (await response.json()) as Job[];
      shardCache.set(filename, jobs);
      inflight.delete(filename);
      return jobs;
    })
    .catch((error) => {
      inflight.delete(filename);
      throw error;
    });

  inflight.set(filename, promise);
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
