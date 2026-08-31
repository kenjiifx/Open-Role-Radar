import type { FilterState } from '../lib/filters';
import { toggleArrayValue } from '../lib/filters';
import type {
  AcademicTerm,
  CareerLevel,
  EligibilityMatch,
  MobilityFlag,
  RemoteScope,
  WorkplaceType,
} from '../lib/types';
import {
  ACADEMIC_TERM_LABELS,
  CAREER_LEVEL_LABELS,
  ELIGIBILITY_MATCH_LABELS,
  MOBILITY_LABELS,
  REMOTE_SCOPE_LABELS,
  WORKPLACE_LABELS,
} from '../lib/types';

interface FilterPanelProps {
  filters: FilterState;
  disciplines: string[];
  locations: string[];
  onChange: (next: FilterState) => void;
  onReset: () => void;
  activeCount: number;
}

const CAREER_LEVELS = Object.keys(CAREER_LEVEL_LABELS) as CareerLevel[];
const WORKPLACE_TYPES = Object.keys(WORKPLACE_LABELS) as WorkplaceType[];
const REMOTE_SCOPES = Object.keys(REMOTE_SCOPE_LABELS) as RemoteScope[];
const ACADEMIC_TERMS = Object.keys(ACADEMIC_TERM_LABELS) as AcademicTerm[];
const MOBILITY_FLAGS = Object.keys(MOBILITY_LABELS) as MobilityFlag[];
const ELIGIBILITY_MATCHES = Object.keys(ELIGIBILITY_MATCH_LABELS) as EligibilityMatch[];

function CheckboxGroup<T extends string>({
  legend,
  options,
  labels,
  selected,
  onToggle,
}: {
  legend: string;
  options: T[];
  labels: Record<T, string>;
  selected: T[];
  onToggle: (value: T) => void;
}) {
  return (
    <fieldset className="filter-group">
      <legend>{legend}</legend>
      <div className="filter-group__options">
        {options.map((option) => {
          if (option === 'unknown') return null;
          const id = `${legend}-${option}`;
          return (
            <label key={option} htmlFor={id} className="filter-checkbox">
              <input
                id={id}
                type="checkbox"
                checked={selected.includes(option)}
                onChange={() => onToggle(option)}
              />
              <span>{labels[option]}</span>
            </label>
          );
        })}
      </div>
    </fieldset>
  );
}

export default function FilterPanel({
  filters,
  disciplines,
  locations,
  onChange,
  onReset,
  activeCount,
}: FilterPanelProps) {
  const update = (partial: Partial<FilterState>) => {
    onChange({ ...filters, ...partial, page: 1 });
  };

  return (
    <aside className="filter-panel" aria-label="Job filters">
      <div className="filter-panel__header">
        <h2>Filters</h2>
        {activeCount > 0 ? (
          <button type="button" className="btn btn--ghost btn--sm" onClick={onReset}>
            Clear all ({activeCount})
          </button>
        ) : null}
      </div>

      <div className="filter-panel__search">
        <label htmlFor="search-query">Search</label>
        <input
          id="search-query"
          type="search"
          value={filters.q}
          onChange={(event) => update({ q: event.target.value })}
          placeholder="Title, company, skills…"
          autoComplete="off"
        />
      </div>

      <CheckboxGroup
        legend="Career level"
        options={CAREER_LEVELS}
        labels={CAREER_LEVEL_LABELS}
        selected={filters.careerLevels}
        onToggle={(value) =>
          update({ careerLevels: toggleArrayValue(filters.careerLevels, value) })
        }
      />

      {disciplines.length > 0 ? (
        <fieldset className="filter-group">
          <legend>Discipline</legend>
          <div className="filter-group__options">
            {disciplines.map((discipline) => {
              const id = `discipline-${discipline}`;
              return (
                <label key={discipline} htmlFor={id} className="filter-checkbox">
                  <input
                    id={id}
                    type="checkbox"
                    checked={filters.disciplines.includes(discipline)}
                    onChange={() =>
                      update({
                        disciplines: toggleArrayValue(filters.disciplines, discipline),
                      })
                    }
                  />
                  <span>{discipline}</span>
                </label>
              );
            })}
          </div>
        </fieldset>
      ) : null}

      {locations.length > 0 ? (
        <fieldset className="filter-group">
          <legend>Location</legend>
          <div className="filter-group__options filter-group__options--scroll">
            {locations.slice(0, 40).map((location) => {
              const id = `location-${location}`;
              return (
                <label key={location} htmlFor={id} className="filter-checkbox">
                  <input
                    id={id}
                    type="checkbox"
                    checked={filters.locations.includes(location)}
                    onChange={() =>
                      update({
                        locations: toggleArrayValue(filters.locations, location),
                      })
                    }
                  />
                  <span>{location}</span>
                </label>
              );
            })}
          </div>
        </fieldset>
      ) : null}

      <CheckboxGroup
        legend="Workplace"
        options={WORKPLACE_TYPES}
        labels={WORKPLACE_LABELS}
        selected={filters.workplaceTypes}
        onToggle={(value) =>
          update({ workplaceTypes: toggleArrayValue(filters.workplaceTypes, value) })
        }
      />

      <CheckboxGroup
        legend="Remote scope"
        options={REMOTE_SCOPES}
        labels={REMOTE_SCOPE_LABELS}
        selected={filters.remoteScopes}
        onToggle={(value) =>
          update({ remoteScopes: toggleArrayValue(filters.remoteScopes, value) })
        }
      />

      <fieldset className="filter-group">
        <legend>Freshness</legend>
        <label htmlFor="freshness" className="sr-only">
          Freshness filter
        </label>
        <select
          id="freshness"
          value={filters.freshness}
          onChange={(event) =>
            update({ freshness: event.target.value as FilterState['freshness'] })
          }
        >
          <option value="all">All time</option>
          <option value="24h">Last 24 hours</option>
          <option value="7d">Last 7 days</option>
          <option value="30d">Last 30 days</option>
          <option value="new_since_visit">New since your last visit</option>
        </select>
      </fieldset>

      <CheckboxGroup
        legend="Academic term"
        options={ACADEMIC_TERMS}
        labels={ACADEMIC_TERM_LABELS}
        selected={filters.academicTerms}
        onToggle={(value) =>
          update({ academicTerms: toggleArrayValue(filters.academicTerms, value) })
        }
      />

      <CheckboxGroup
        legend="Mobility"
        options={MOBILITY_FLAGS}
        labels={MOBILITY_LABELS}
        selected={filters.mobility}
        onToggle={(value) =>
          update({ mobility: toggleArrayValue(filters.mobility, value) })
        }
      />

      <fieldset className="filter-group">
        <legend>Origin country</legend>
        <label htmlFor="origin-country" className="sr-only">
          Your origin country (ISO code or name)
        </label>
        <input
          id="origin-country"
          type="text"
          value={filters.originCountry}
          onChange={(event) => update({ originCountry: event.target.value })}
          placeholder="e.g. Canada, IN, United Kingdom"
        />
      </fieldset>

      <CheckboxGroup
        legend="Eligibility match"
        options={ELIGIBILITY_MATCHES}
        labels={ELIGIBILITY_MATCH_LABELS}
        selected={filters.eligibilityMatches}
        onToggle={(value) =>
          update({
            eligibilityMatches: toggleArrayValue(filters.eligibilityMatches, value),
          })
        }
      />

      <fieldset className="filter-group">
        <legend>Display</legend>
        <label className="filter-checkbox">
          <input
            type="checkbox"
            checked={filters.showSavedOnly}
            onChange={(event) => update({ showSavedOnly: event.target.checked })}
          />
          <span>Saved jobs only</span>
        </label>
        <label className="filter-checkbox">
          <input
            type="checkbox"
            checked={filters.hideDismissed}
            onChange={(event) => update({ hideDismissed: event.target.checked })}
          />
          <span>Hide dismissed</span>
        </label>
      </fieldset>
    </aside>
  );
}
