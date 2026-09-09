import type { ReactNode } from 'react';
import type { FilterState } from '../lib/filters';
import { toggleArrayValue } from '../lib/filters';
import {
  CS_DISCIPLINES,
  formatDiscipline,
  REGION_LABELS,
  REGION_OPTIONS,
  SEASON_TERMS,
  type RegionId,
} from '../lib/labels';
import type { FacetCounts } from '../lib/search';
import type { AcademicTerm, CareerLevel, MobilityFlag, WorkplaceType } from '../lib/types';
import {
  ACADEMIC_TERM_LABELS,
  CAREER_LEVEL_LABELS,
  MOBILITY_LABELS,
  WORKPLACE_LABELS,
} from '../lib/types';

interface FilterPanelProps {
  filters: FilterState;
  facets: FacetCounts;
  onChange: (next: FilterState) => void;
  onReset: () => void;
  activeCount: number;
}

const CAREER_LEVELS = Object.keys(CAREER_LEVEL_LABELS) as CareerLevel[];
const WORKPLACE_TYPES = Object.keys(WORKPLACE_LABELS) as WorkplaceType[];
const MOBILITY_FLAGS = Object.keys(MOBILITY_LABELS) as MobilityFlag[];

function FilterSection({
  title,
  children,
  defaultOpen = true,
}: {
  title: string;
  children: ReactNode;
  defaultOpen?: boolean;
}) {
  return (
    <details className="filter-section" open={defaultOpen}>
      <summary className="filter-section__summary">
        <span>{title}</span>
        <svg className="filter-section__chevron" width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <path d="M6 9l6 6 6-6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </summary>
      <div className="filter-section__body">{children}</div>
    </details>
  );
}

function CheckboxRow({
  id,
  label,
  checked,
  count,
  leading,
  onChange,
}: {
  id: string;
  label: string;
  checked: boolean;
  count?: number;
  leading?: ReactNode;
  onChange: () => void;
}) {
  return (
    <label htmlFor={id} className="filter-checkbox">
      <span className="filter-checkbox__main">
        <input id={id} type="checkbox" checked={checked} onChange={onChange} />
        {leading}
        <span>{label}</span>
      </span>
      {typeof count === 'number' ? (
        <span className="filter-checkbox__count">{count.toLocaleString()}</span>
      ) : null}
    </label>
  );
}

export default function FilterPanel({
  filters,
  facets,
  onChange,
  onReset,
  activeCount,
}: FilterPanelProps) {
  const update = (partial: Partial<FilterState>) => {
    onChange({ ...filters, ...partial, page: 1 });
  };

  const disciplineOptions =
    facets.disciplines.length > 0 ? facets.disciplines : [...CS_DISCIPLINES];

  return (
    <aside className="filter-panel" aria-label="Job filters">
      <div className="filter-panel__header">
        <h2>Filters</h2>
        <button type="button" className="btn-text" onClick={onReset}>
          Reset all
        </button>
      </div>

      <div className="filter-panel__search">
        <label htmlFor="search-query" className="sr-only">
          Search roles
        </label>
        <div className="filter-search-field">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="2" />
            <path d="M20 20l-3.5-3.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
          </svg>
          <input
            id="search-query"
            type="search"
            value={filters.q}
            onChange={(event) => update({ q: event.target.value })}
            placeholder="Search roles, companies, skills…"
            autoComplete="off"
          />
        </div>
      </div>

      <FilterSection title="Role type">
        <div className="filter-group__options">
          {CAREER_LEVELS.map((option) => {
            if (option === 'unknown') return null;
            return (
              <CheckboxRow
                key={option}
                id={`role-${option}`}
                label={CAREER_LEVEL_LABELS[option]}
                checked={filters.careerLevels.includes(option)}
                count={facets.careerLevels[option] ?? 0}
                onChange={() =>
                  update({ careerLevels: toggleArrayValue(filters.careerLevels, option) })
                }
              />
            );
          })}
        </div>
      </FilterSection>

      <FilterSection title="Season">
        <div className="filter-group__options">
          {SEASON_TERMS.map((term) => (
            <CheckboxRow
              key={term}
              id={`season-${term}`}
              label={ACADEMIC_TERM_LABELS[term as AcademicTerm]}
              checked={filters.academicTerms.includes(term)}
              count={facets.academicTerms[term] ?? 0}
              onChange={() =>
                update({
                  academicTerms: toggleArrayValue(filters.academicTerms, term as AcademicTerm),
                })
              }
            />
          ))}
        </div>
      </FilterSection>

      <FilterSection title="Company type">
        <CheckboxRow
          id="startup-only"
          label="Startups"
          checked={filters.startupsOnly}
          count={facets.startups}
          onChange={() => update({ startupsOnly: !filters.startupsOnly })}
        />
      </FilterSection>

      <FilterSection title="Location">
        <div className="filter-group__options">
          {REGION_OPTIONS.map((region) => (
            <CheckboxRow
              key={region}
              id={`region-${region}`}
              label={REGION_LABELS[region]}
              checked={filters.regions.includes(region)}
              count={facets.regions[region] ?? 0}
              onChange={() =>
                update({
                  regions: toggleArrayValue(filters.regions, region as RegionId),
                })
              }
            />
          ))}
        </div>
      </FilterSection>

      <FilterSection title="Discipline" defaultOpen={false}>
        <div className="filter-group__options filter-group__options--scroll">
          {disciplineOptions.map((discipline) => (
            <CheckboxRow
              key={discipline}
              id={`discipline-${discipline}`}
              label={formatDiscipline(discipline)}
              checked={filters.disciplines.includes(discipline)}
              onChange={() =>
                update({
                  disciplines: toggleArrayValue(filters.disciplines, discipline),
                })
              }
            />
          ))}
        </div>
      </FilterSection>

      <FilterSection title="Workplace" defaultOpen={false}>
        <div className="filter-group__options">
          {WORKPLACE_TYPES.map((option) => {
            if (option === 'unknown') return null;
            return (
              <CheckboxRow
                key={option}
                id={`workplace-${option}`}
                label={WORKPLACE_LABELS[option]}
                checked={filters.workplaceTypes.includes(option)}
                count={facets.workplaceTypes[option] ?? 0}
                onChange={() =>
                  update({
                    workplaceTypes: toggleArrayValue(filters.workplaceTypes, option),
                  })
                }
              />
            );
          })}
        </div>
      </FilterSection>

      <FilterSection title="Posted" defaultOpen={false}>
        <select
          id="freshness"
          value={filters.freshness}
          onChange={(event) =>
            update({ freshness: event.target.value as FilterState['freshness'] })
          }
        >
          <option value="all">Any time</option>
          <option value="24h">Last 24 hours</option>
          <option value="7d">Last 7 days</option>
          <option value="30d">Last 30 days</option>
          <option value="new_since_visit">New since last visit</option>
        </select>
      </FilterSection>

      <FilterSection title="Mobility" defaultOpen={false}>
        <div className="filter-group__options">
          {MOBILITY_FLAGS.map((option) => (
            <CheckboxRow
              key={option}
              id={`mobility-${option}`}
              label={MOBILITY_LABELS[option]}
              checked={filters.mobility.includes(option)}
              onChange={() =>
                update({ mobility: toggleArrayValue(filters.mobility, option) })
              }
            />
          ))}
        </div>
      </FilterSection>

      {activeCount > 0 ? (
        <p className="filter-active-hint">{activeCount} active filter{activeCount === 1 ? '' : 's'}</p>
      ) : null}
    </aside>
  );
}
