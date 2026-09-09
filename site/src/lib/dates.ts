import type { Job } from './types';

/** Prefer the ATS posting date; fall back to when we first crawled it. */
export function postedAt(job: Pick<Job, 'source_posted_at' | 'first_seen_at'>): string {
  return job.source_posted_at || job.first_seen_at;
}

export function formatDate(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

export function formatRelative(iso: string, now = Date.now()): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return '';
  const deltaMs = now - date.getTime();
  const abs = Math.abs(deltaMs);
  const seconds = Math.round(abs / 1000);
  const minutes = Math.round(abs / 60_000);
  const hours = Math.round(abs / 3_600_000);
  const days = Math.round(abs / 86_400_000);

  if (seconds < 45) return 'just now';
  if (minutes < 60) return `${minutes}m ago`;
  if (hours < 48) return `${hours}h ago`;
  if (days < 30) return `${days}d ago`;
  return formatDate(iso);
}

export type FreshnessTier = 'hot' | 'warm' | 'cool';

/** How freshly this role appeared on radar / the ATS. */
export function openedFreshness(
  job: Pick<Job, 'source_posted_at' | 'first_seen_at'>,
  now = Date.now(),
): { tier: FreshnessTier; label: string } {
  const firstSeen = Date.parse(job.first_seen_at);
  const posted = Date.parse(postedAt(job));
  const ageMs = Math.min(
    Number.isNaN(firstSeen) ? Number.POSITIVE_INFINITY : now - firstSeen,
    Number.isNaN(posted) ? Number.POSITIVE_INFINITY : now - posted,
  );

  if (ageMs < 2 * 60 * 60 * 1000) {
    return { tier: 'hot', label: 'Just opened' };
  }
  if (ageMs < 24 * 60 * 60 * 1000) {
    return { tier: 'warm', label: 'Opened today' };
  }
  return { tier: 'cool', label: '' };
}

export function formatUpdatedLabel(iso: string, now = Date.now()): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return '—';
  const relative = formatRelative(iso, now);
  if (relative === 'just now' || relative.endsWith('m ago') || relative.endsWith('h ago')) {
    return `Updated ${relative}`;
  }
  return `Updated ${formatDate(iso)}`;
}
