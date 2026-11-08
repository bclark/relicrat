import type { GameContents } from '../lib/inventory-client';

const components = {
  media: 'Cartridge or disc',
  packaging: 'Box or case',
  manual: 'Manual',
  inserts: 'Inserts',
} as const;
const statuses = {
  present: 'Present',
  missing: 'Missing',
  not_applicable: 'Not applicable',
} as const;

export function GameContentsFields({value, change}: {value: GameContents; change: (value: GameContents) => void}) {
  return <fieldset><legend>What’s included with this copy</legend>
    {Object.entries(components).map(([key, label]) => {
      const component = key as keyof GameContents;
      return <label key={component}>{label}
        <select value={value[component] || ''} onChange={event => {
          const next = {...value};
          if (event.target.value) next[component] = event.target.value as keyof typeof statuses;
          else delete next[component];
          change(next);
        }}>
          <option value="">Unknown</option>
          {Object.entries(statuses).map(([status, name]) => <option key={status} value={status}>{name}</option>)}
        </select>
      </label>;
    })}
  </fieldset>;
}

export function GameContentsSummary({value}: {value: GameContents}) {
  return <dl aria-label="What’s included with this copy">
    {Object.entries(components).map(([key, label]) => {
      const status = value[key as keyof GameContents];
      return <div key={key}><dt>{label}</dt><dd>{status ? statuses[status] : 'Unknown'}</dd></div>;
    })}
  </dl>;
}
