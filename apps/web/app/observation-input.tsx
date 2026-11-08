'use client';

import { useEffect, useRef, useState } from 'react';
import { api, type TypeField } from '../lib/inventory-client';

type Props = { id: string; field: Pick<TypeField, 'max_length' | 'placeholder' | 'input' | 'options'> & {key?: TypeField['key']}; value: string; change: (value: string) => void; suggestionsPath?: string; required?: boolean };

export default function ObservationInput({ id, field, value, change, suggestionsPath, required }: Props) {
  const choices = field.options || [];
  const [custom, setCustom] = useState(false);
  const customInput = useRef<HTMLInputElement>(null);
  const otherSelected = custom || (!!value && !choices.includes(value));
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [unavailable, setUnavailable] = useState(false);
  const path = suggestionsPath || (field.input === 'autocomplete'
    ? `collection-settings/${field.key==='studio' ? 'studio' : field.key==='publisher' ? 'publisher' : 'artist'}-suggestions`
    : undefined);
  useEffect(() => {
    if (!path) return;
    const controller = new AbortController();
    setSuggestions([]); setUnavailable(false);
    const timer = setTimeout(() => {
      api<string[]>(`${path}?q=${encodeURIComponent(value)}`, {signal:controller.signal})
        .then(values => { if (!controller.signal.aborted) setSuggestions(values); })
        .catch(() => { if (!controller.signal.aborted) setUnavailable(true); });
    }, 200);
    return () => { clearTimeout(timer); controller.abort(); };
  }, [path, value]);
  if (field.input === 'select') return <>
    <select id={id} value={otherSelected ? '__other__' : value} onChange={event=>{
      const other = event.target.value === '__other__'; setCustom(other); change(other ? '' : event.target.value);
      if(other) requestAnimationFrame(()=>customInput.current?.focus());
    }}><option value="">Not specified</option>{choices.map(choice=><option key={choice} value={choice}>{choice}</option>)}<option value="__other__">Other…</option></select>
    {otherSelected && <><label htmlFor={`${id}-other`}>Other format</label><input ref={customInput} id={`${id}-other`} value={value} maxLength={field.max_length} onChange={event=>change(event.target.value)} /></>}
  </>;
  return <>
    <input id={id} required={required} maxLength={field.max_length} placeholder={field.placeholder} value={value} onChange={event=>change(event.target.value)}
      list={path ? `${id}-suggestions` : undefined} autoComplete={path ? 'off' : undefined} aria-describedby={unavailable ? `${id}-hint` : undefined} />
    {path && <datalist id={`${id}-suggestions`}>{suggestions.map(suggestion=><option key={suggestion} value={suggestion} />)}</datalist>}
    {unavailable && <p id={`${id}-hint`} className="hint" role="status">Suggestions unavailable. You can still type here.</p>}
  </>;
}
