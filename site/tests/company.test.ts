import { describe, expect, it } from 'vitest';
import { companyDomain, companyInitials, companyLogoUrl } from '../src/lib/company';
import type { Job } from '../src/lib/types';

function job(overrides: Partial<Job> = {}): Job {
  return {
    job_id: '1',
    source_job_id: '1',
    company_id: 'stripe',
    company_name: 'Stripe',
    title: 'Intern',
    job_url: 'https://job-boards.greenhouse.io/stripe/jobs/1',
    apply_url: 'https://job-boards.greenhouse.io/stripe/jobs/1',
    career_level: 'internship',
    career_level_confidence: 1,
    disciplines: { primary: 'software', secondary: [], confidence: 1 },
    locations: [],
    workplace_type: 'remote',
    remote_scope: 'worldwide',
    remote_allowed_countries: [],
    remote_allowed_regions: [],
    first_seen_at: new Date().toISOString(),
    last_seen_at: new Date().toISOString(),
    academic_term: 'summer',
    eligibility: {
      explicit_allowed_countries: [],
      explicit_excluded_countries: [],
      citizenship_requirements: [],
      residency_requirements: [],
      language_requirements: [],
      origin_match: 'unknown',
    },
    mobility: {
      visa_sponsorship: { status: 'unknown', confidence: 0 },
      immigration_assistance: { status: 'unknown', confidence: 0 },
      international_candidates: { status: 'unknown', confidence: 0 },
      relocation_assistance: { status: 'unknown', confidence: 0 },
      relocation_stipend: { status: 'unknown', confidence: 0 },
      moving_expenses: { status: 'unknown', confidence: 0 },
      airfare: { status: 'unknown', confidence: 0 },
      travel_reimbursement: { status: 'unknown', confidence: 0 },
      housing_provided: { status: 'unknown', confidence: 0 },
      housing_stipend: { status: 'unknown', confidence: 0 },
      temporary_housing: { status: 'unknown', confidence: 0 },
      fully_funded_relocation: { status: 'unknown', confidence: 0 },
    },
    provenance: {
      adapter: 'greenhouse',
      source_id: 's',
      source_job_id: '1',
      fetched_at: new Date().toISOString(),
      parser_version: '1',
      classification_version: '1',
      content_hash: 'h',
      source_health_at_fetch: 'healthy',
      first_party_verified: true,
    },
    lifecycle: 'open',
    ...overrides,
  };
}

describe('company logos', () => {
  it('prefers first-party careers domains over ATS hosts', () => {
    expect(
      companyDomain(
        job({
          company_name: 'Coinbase',
          careers_url: 'https://www.coinbase.com/careers',
          job_url: 'https://boards.greenhouse.io/coinbase/jobs/1',
        }),
      ),
    ).toBe('coinbase.com');
  });

  it('falls back to greenhouse tenant as a .com domain', () => {
    expect(companyDomain(job())).toBe('stripe.com');
  });

  it('resolves first-party domains from the seed company map', () => {
    expect(
      companyDomain(
        job({
          company_name: 'Coinbase',
          job_url: 'https://example.invalid/nope',
          apply_url: 'https://example.invalid/nope',
        }),
      ),
    ).toBe('coinbase.com');
  });

  it('builds a favicon lookup url', () => {
    expect(companyLogoUrl('nvidia.com')).toContain('nvidia.com');
    expect(companyInitials('Coinbase')).toBe('CO');
    expect(companyInitials('NVIDIA')).toBe('NV');
  });
});
