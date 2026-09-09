import type { FilterState } from '../lib/filters';
import { toggleArrayValue } from '../lib/filters';
import {
  CS_DISCIPLINES,
  formatDiscipline,
  REGION_LABELS,
  REGION_OPTIONS,
  type RegionId,
} from '../lib/labels';
import type { CareerLevel, MobilityFlag, WorkplaceType } from '../lib/types';
import {
  CAREER_LEVEL_LABELS,
  MOBILITY_LABELS,
  WORKPLACE_LABELS,
} from '../lib/types';

interface FilterPanelProps {
  filters: FilterState;
  disciplines: string[];
  onChange: (next: FilterState) => void;
  onReset: () => void;
  activeCount: number;
}

const CAREER_LEVELS = Object.keys(CAREER_LEVEL_LABELS) as CareerLevel[];
const WORKPLACE_TYPES = Object.keys(WORKPLACE_LABELS) as WorkplaceType[];
const MOBILITY_FLAGS = Object.keys(MOBILITY_LABELS) as MobilityFlag[];

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
  onChange,
  onReset,
  activeCount,
}: FilterPanelProps) {
  const update = (partial: Partial<FilterState>) => {
    onChange({ ...filters, ...partial, page: 1 });
  };

  const disciplineOptions =
    disciplines.length > 0 ? disciplines : [...CS_DISCIPLINES];

  return (
    <aside className="filter-panel" aria-label="Job filters">
      <div className="filter-panel__header">
        <h2>Refine</h2>
        {activeCount > 0 ? (
          <button type="button" className="btn btn--ghost btn--sm" onClick={onReset}>
            Clear ({activeCount})
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
          placeholder="Title, company, stack…"
          autoComplete="off"
        />
      </div>

      <div className="filter-quick">
        <button
          type="button"
          className="btn btn--secondary btn--sm"
          onClick={() => update({ disciplines: [...CS_DISCIPLINES] })}
        >
          CS track
        </button>
        <button
          type="button"
          className="btn btn--ghost btn--sm"
          onClick={() => update({ regions: ['na'] })}
        >
          NA
        </button>
        <button
          type="button"
          className="btn btn--ghost btn--sm"
          onClick={() => update({ regions: ['eu'] })}
        >
          EU
        </button>
        <button
          type="button"
          className="btn btn--ghost btn--sm"
          onClick={() => update({ regions: ['asia'] })}
        >
          Asia
        </button>
        <button
          type="button"
          className="btn btn--ghost btn--sm"
          onClick={() => update({ regions: ['remote'] })}
        >
          Remote
        </button>
      </div>

      <CheckboxGroup
        legend="Role type"
        options={CAREER_LEVELS}
        labels={CAREER_LEVEL_LABELS}
        selected={filters.careerLevels}
        onToggle={(value) =>
          update({ careerLevels: toggleArrayValue(filters.careerLevels, value) })
        }
      />

      <fieldset className="filter-group">
        <legend>Region</legend>
        <div className="filter-group__options">
          {REGION_OPTIONS.map((region) => {
            const id = `region-${region}`;
            return (
              <label key={region} htmlFor={id} className="filter-checkbox">
                <input
                  id={id}
                  type="checkbox"
                  checked={filters.regions.includes(region)}
                  onChange={() =>
                    update({
                      regions: toggleArrayValue(filters.regions, region as RegionId),
                    })
                  }
                />
                <span>{REGION_LABELS[region]}</span>
              </label>
            );
          })}
        </div>
      </fieldset>

      <fieldset className="filter-group">
        <legend>Discipline</legend>
        <div className="filter-group__options filter-group__options--scroll">
          {disciplineOptions.map((discipline) => {
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
                <span>{formatDiscipline(discipline)}</span>
              </label>
            );
          })}
        </div>
      </fieldset>

      <CheckboxGroup
        legend="Workplace"
        options={WORKPLACE_TYPES}
        labels={WORKPLACE_LABELS}
        selected={filters.workplaceTypes}
        onToggle={(value) =>
          update({ workplaceTypes: toggleArrayValue(filters.workplaceTypes, value) })
        }
      />

      <fieldset className="filter-group">
        <legend>Posted</legend>
        <label htmlFor="freshness" className="sr-only">
          Posted date filter
        </label>
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
      </fieldset>

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
        <legend>Your country</legend>
        <label htmlFor="origin-country" className="sr-only">
          Your origin country
        </label>
        <input
          id="origin-country"
          type="text"
          value={filters.originCountry}
          onChange={(event) => update({ originCountry: event.target.value })}
          placeholder="e.g. CA, Canada, India, UK"
        />
        <p className="filter-hint">Hides roles that explicitly exclude your country.</p>
      </fieldset>

      <fieldset className="filter-group">
        <legend>Saved</legend>
        <label className="filter-checkbox">
          <input
            type="checkbox"
            checked={filters.showSavedOnly}
            onChange={(event) => update({ showSavedOnly: event.target.checked })}
          />
          <span>Saved only</span>
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
