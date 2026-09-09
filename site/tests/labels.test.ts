import { describe, expect, it } from 'vitest';
import {
  formatDiscipline,
  jobMatchesRegions,
  regionsForJob,
} from '../src/lib/labels';

describe('labels', () => {
  it('formats discipline ids without underscores', () => {
    expect(formatDiscipline('full_stack')).toBe('Full Stack');
    expect(formatDiscipline('machine_learning')).toBe('Machine Learning');
    expect(formatDiscipline('software')).toBe('Software Engineering');
    expect(formatDiscipline('mystery_track')).toBe('Mystery Track');
  });

  it('maps jobs into NA / EU / Asia / remote regions', () => {
    expect(
      regionsForJob({
        workplace_type: 'hybrid',
        locations: [{ country_code: 'CA', country: 'Canada' }],
      }),
    ).toEqual(['na']);

    expect(
      regionsForJob({
        workplace_type: 'onsite',
        locations: [{ country_code: 'DE', country: 'Germany' }],
      }),
    ).toEqual(['eu']);

    expect(
      regionsForJob({
        workplace_type: 'remote',
        locations: [{ country_code: 'SG', country: 'Singapore' }],
      }),
    ).toEqual(['remote', 'asia']);
  });

  it('matches region filters', () => {
    const toronto = {
      workplace_type: 'hybrid',
      locations: [{ country_code: 'CA', country: 'Canada' }],
    };
    expect(jobMatchesRegions(toronto, [])).toBe(true);
    expect(jobMatchesRegions(toronto, ['na'])).toBe(true);
    expect(jobMatchesRegions(toronto, ['eu'])).toBe(false);
  });
});
