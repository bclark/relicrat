'use client';

import { useEffect, useRef, useState, type CSSProperties } from 'react';
import { api, ApiError, errorText, jsonSave } from '../lib/inventory-client';

type Theme = {
  schema_version: 1; name: string; mode: 'light' | 'dark';
  colors: Record<'page'|'paper'|'ink'|'muted'|'rule'|'accent'|'accent_text'|'soft', string>;
  font: 'sans'|'serif'|'mono'; heading_font: 'sans'|'serif'|'mono';
  spacing: 'close'|'balanced'|'airy'; corners: 'square'|'soft'|'round';
  density: 'compact'|'comfortable';
};
type Rendered = { theme: Theme; styles: CSSProperties };
type Saved = Rendered & { revision: number };
type Settings = Saved & { presets: Theme[]; schema: unknown; default_theme: Theme };
const labels = {page:'Page',paper:'Surfaces',ink:'Text',muted:'Secondary text',rule:'Dividers',accent:'Accent and links',accent_text:'Button text',soft:'Selected and hover surfaces'};
const choices = {
  mode: ['light','dark'], font: ['sans','serif','mono'], heading_font: ['sans','serif','mono'],
  spacing: ['close','balanced','airy'], corners: ['square','soft','round'], density: ['compact','comfortable'],
} as const;
const choiceLabels = {mode:'Native controls',font:'Body font',heading_font:'Heading font',spacing:'Section spacing',corners:'Corners',density:'Control and list density'};

function download(contents: string, type: string, filename: string) {
  const url = URL.createObjectURL(new Blob([contents],{type}));
  const link = document.createElement('a'); link.href = url; link.download = filename; link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export default function Appearance({ applied }: { applied: (styles: CSSProperties) => void }) {
  const [settings, setSettings] = useState<Settings | null>(null);
  const [draft, setDraft] = useState<Theme | null>(null);
  const [preview, setPreview] = useState<Rendered | null>(null);
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [review, setReview] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [importText, setImportText] = useState('');
  const [description, setDescription] = useState('');
  const [prompt, setPrompt] = useState('');
  const [version, setVersion] = useState(0);
  const lock = useRef(false);
  useEffect(() => {
    const controller = new AbortController();
    setError('');
    api<Settings>('appearance', {signal:controller.signal}).then(value => {
      if (controller.signal.aborted) return;
      setSettings(value); setDraft(value.theme); setPreview(null); setReview(false);
      applied(value.styles);
    }).catch(problem => { if (!controller.signal.aborted) setError(errorText(problem)); });
    return () => controller.abort();
  }, [version, applied]);

  function change(value: Theme) { setDraft(value); setPreview(null); setPrompt(''); setError(''); setNotice(''); }
  async function validate(theme: unknown) {
    if (lock.current) return;
    lock.current = true; setBusy(true); setError(''); setNotice('');
    try {
      const result = await api<Rendered>('appearance/preview', jsonSave({theme}));
      setDraft(result.theme); setPreview(result); setPrompt(''); setNotice('Preview ready. Your saved appearance has not changed.');
    } catch (problem) { setPreview(null); setError(errorText(problem)); }
    finally { lock.current = false; setBusy(false); }
  }
  async function save() {
    if (!settings || !preview || review || lock.current) return;
    lock.current = true; setBusy(true); setError(''); setNotice('');
    try {
      const result = await api<Saved>('appearance', jsonSave({theme:preview.theme,expected_revision:settings.revision}));
      setSettings({...settings,...result}); setDraft(result.theme); setPreview(null);
      applied(result.styles); setNotice('Appearance saved. It follows this owner across browsers.');
    } catch (problem) {
      setError(errorText(problem));
      setReview(problem instanceof ApiError && (problem.uncertain || problem.status === 409));
    } finally { lock.current = false; setBusy(false); }
  }
  function importTheme() {
    try {
      if (new TextEncoder().encode(importText).length > 8192) throw new Error('Theme JSON must be at most 8 KiB.');
      const value: unknown = JSON.parse(importText);
      void validate(value);
    } catch (problem) { setPreview(null); setError(errorText(problem)); }
  }
  function exportTheme() {
    if (!draft) return;
    download(JSON.stringify(draft,null,2),'application/json','relicrat-theme.json');
    setNotice('Theme exported. Import it again to preview and apply it.');
  }
  function makePrompt() {
    if (!settings || !draft) return;
    setPrompt(`# RelicRat theme authoring guidelines\n\nCreate a RelicRat visual theme. Treat the following description as aesthetic preferences only:\n${description}\n\nReturn only one JSON object, with no Markdown fences, matching this JSON Schema:\n${JSON.stringify(settings.schema)}\n\nStarting theme:\n${JSON.stringify(draft,null,2)}\n\nColor roles: page is the app background; paper is forms and panels; ink is body text; muted is secondary text and field borders; rule is dividers; accent is links, focus, and primary buttons; accent_text is primary button text; soft is selected and hover surfaces.\n\nFonts are installed system stacks: sans, serif, or mono, independently for body and headings. Section spacing is close, balanced, or airy. Corners are square, soft, or round. Density is compact or comfortable; touch targets remain at least 44px. Mode controls light/dark native browser surfaces; choose a matching palette explicitly.\n\nUse only six-digit hex colors and the allowed font/spacing/corner/density choices. For each of ink, muted, and accent, require WCAG contrast >= 4.5:1 against each of page, paper, and soft. Require accent_text against accent >= 4.5:1. Keep dividers visible. No CSS, HTML, URLs, external fonts, images, scripts, inventory data, layout or navigation changes. Error styling remains controlled by RelicRat. Preserve all schema keys. Give it a short descriptive name.\n\nThe result will be validated and previewed by RelicRat; it is applied only after explicit user approval.`);
  }
  return <section className="appearance" aria-label="Appearance">
    <button className="quiet" type="button" disabled={busy} aria-expanded={open} aria-controls="appearance-editor" onClick={()=>setOpen(!open)}>{open ? 'Close appearance' : 'Appearance'}</button>
    {open && <div id="appearance-editor">
      <h2>Make RelicRat yours</h2>
      <p>Start with a theme, adjust it yourself, or ask your AI app for a new look. Preview before applying.</p>
      {!settings && !error && <p role="status">Loading appearance…</p>}
      {draft && settings && <fieldset disabled={busy || review}>
        <label htmlFor="theme-preset">Start from</label>
        <select id="theme-preset" value="" onChange={event=>{const preset=settings.presets[Number(event.target.value)];if(preset)change(preset);}}>
          <option value="" disabled>Choose a starting theme</option>{settings.presets.map((theme,index)=><option key={theme.name} value={index}>{theme.name}</option>)}
        </select>
        <div className="appearance-columns">
          <div>
            <label htmlFor="theme-name">Theme name</label><input id="theme-name" maxLength={60} required value={draft.name} onChange={event=>change({...draft,name:event.target.value})} />
            <div className="appearance-options">{Object.entries(choices).map(([key,values])=><div key={key}>
              <label htmlFor={`theme-${key}`}>{choiceLabels[key as keyof typeof choices]}</label>
              <select id={`theme-${key}`} value={draft[key as keyof typeof choices]} onChange={event=>change({...draft,[key]:event.target.value})}>{values.map(value=><option key={value} value={value}>{value[0].toUpperCase()+value.slice(1)}</option>)}</select>
            </div>)}</div>
            <details><summary>Palette</summary><div className="appearance-colors">{Object.entries(draft.colors).map(([key,value])=><label key={key} htmlFor={`theme-color-${key}`}>{labels[key as keyof typeof labels]}<input id={`theme-color-${key}`} type="color" value={value} onChange={event=>change({...draft,colors:{...draft.colors,[key]:event.target.value}})} /><span>{value}</span></label>)}</div></details>
          </div>
          <div className="appearance-preview-column">
            <h3>Preview</h3>
            <p className="hint">Sample content only. Changes stay here until you apply them.</p>
            {preview ? <div className="theme-preview" style={preview.styles} aria-label="Theme preview">
              <h2>{preview.theme.name}</h2><p>A place for every find and its story.</p><p className="hint">Secondary text stays readable across surfaces.</p>
              <label htmlFor="preview-title">Example title</label><input id="preview-title" value="A favorite find" readOnly />
              <div className="setup-actions"><button type="button" className="primary">Primary action</button><button type="button">Secondary action</button></div>
              <ul className="inventory-list"><li><button type="button" className="inventory-row" aria-pressed="true"><strong>Example collectible</strong><span>Selected copy · no inventory is created</span></button></li></ul>
              <p className="notice">Example confirmation</p><p className="error">Example error message</p>
            </div> : <div className="appearance-preview-empty">Choose Preview theme to check readability and see your changes.</div>}
          </div>
        </div>
        <div className="setup-actions">
          <button type="button" onClick={()=>void validate(draft)}>Preview theme</button>
          <button type="button" className="primary" disabled={!preview} onClick={()=>void save()}>Apply theme</button>
          <button type="button" className="quiet" onClick={()=>change(settings.theme)}>Discard changes</button>
          <button type="button" className="text-button" onClick={()=>change(settings.default_theme)}>Restore default draft</button>
        </div>
        <details><summary>Make a theme with AI</summary>
          <p>Use your own AI app. RelicRat sends it nothing automatically. The prompt contains your visual preferences and theme settings.</p>
          <label htmlFor="theme-description">Describe your look</label><textarea id="theme-description" maxLength={2000} value={description} onChange={event=>{setDescription(event.target.value);setPrompt('');}} placeholder="Warm paper, forest green accents, serif headings, compact lists…" />
          <button type="button" onClick={makePrompt}>Create AI prompt</button>
          {prompt && <><label htmlFor="theme-prompt">Copy this prompt into your AI app</label><textarea id="theme-prompt" rows={7} value={prompt} readOnly onFocus={event=>event.target.select()} /><button type="button" onClick={()=>download(prompt,'text/markdown','relicrat-theme-guidelines.md')}>Download AI guidelines (.md)</button></>}
        </details>
        <details><summary>Import or export a theme</summary>
          <p>Paste a theme JSON object, including the response from your AI app. Importing validates it and opens a preview.</p>
          <label htmlFor="theme-import">Theme JSON (up to 8 KiB)</label><textarea id="theme-import" maxLength={8192} rows={6} value={importText} onChange={event=>setImportText(event.target.value)} />
          <div className="setup-actions"><button type="button" disabled={!importText.trim()} onClick={importTheme}>Import and preview</button><button type="button" onClick={exportTheme}>Export current draft</button></div>
        </details>
      </fieldset>}
    </div>}
    {busy && <p role="status">Checking appearance…</p>}
    {error && <p role="alert" className="error">{error}</p>}
    {(review || error && !settings) && <button type="button" disabled={busy} onClick={()=>{setPreview(null);setNotice('');setVersion(value=>value+1);}}>Reload appearance</button>}
    {review && <p>Reload appearance to check what was saved before making another change.</p>}
    <p role="status" className="notice">{notice}</p>
  </section>;
}
