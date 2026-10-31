"""Portable appearance values; never executable CSS, URLs, or inventory data."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Palette(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    page: str = Field(pattern=r'^#[0-9a-fA-F]{6}$')
    paper: str = Field(pattern=r'^#[0-9a-fA-F]{6}$')
    ink: str = Field(pattern=r'^#[0-9a-fA-F]{6}$')
    muted: str = Field(pattern=r'^#[0-9a-fA-F]{6}$')
    rule: str = Field(pattern=r'^#[0-9a-fA-F]{6}$')
    accent: str = Field(pattern=r'^#[0-9a-fA-F]{6}$')
    accent_text: str = Field(pattern=r'^#[0-9a-fA-F]{6}$')
    soft: str = Field(pattern=r'^#[0-9a-fA-F]{6}$')


def luminance(color: str) -> float:
    channels = [int(color[i:i+2], 16) / 255 for i in (1, 3, 5)]
    linear = [c / 12.92 if c <= .04045 else ((c + .055) / 1.055) ** 2.4 for c in channels]
    return sum(c * weight for c, weight in zip(linear, (.2126, .7152, .0722)))


def contrast(a: str, b: str) -> float:
    light, dark = sorted((luminance(a), luminance(b)), reverse=True)
    return (light + .05) / (dark + .05)


class Theme(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    schema_version: Literal[1]
    name: str = Field(min_length=1, max_length=60, pattern=r'^[^\x00-\x1f\x7f]+$')
    mode: Literal['light', 'dark']
    colors: Palette
    font: Literal['sans', 'serif', 'mono']
    heading_font: Literal['sans', 'serif', 'mono']
    spacing: Literal['close', 'balanced', 'airy']
    corners: Literal['square', 'soft', 'round']
    density: Literal['compact', 'comfortable']

    @field_validator('schema_version', mode='before')
    @classmethod
    def integer_version(cls, value):
        if type(value) is not int:
            raise ValueError('Schema version must be the integer 1')
        return value

    @model_validator(mode='after')
    def readable(self):
        for foreground in ('ink', 'muted', 'accent'):
            for background in ('page', 'paper', 'soft'):
                ratio = contrast(getattr(self.colors, foreground), getattr(self.colors, background))
                if ratio < 4.5:
                    raise ValueError(f'{foreground} on {background} needs contrast of at least 4.5:1 (currently {ratio:.2f}:1)')
        if contrast(self.colors.accent_text, self.colors.accent) < 4.5:
            raise ValueError('Button text on accent needs contrast of at least 4.5:1')
        if not self.name.strip():
            raise ValueError('Give the theme a name')
        return self


DEFAULT_THEME = {
    'schema_version': 1, 'name': 'RelicRat', 'mode': 'light',
    'colors': {'page': '#f1f4f8', 'paper': '#ffffff', 'ink': '#1b2a3d',
               'muted': '#53647a', 'rule': '#cdd6e2', 'accent': '#214fbd',
               'accent_text': '#ffffff', 'soft': '#e9effc'},
    'font': 'sans', 'heading_font': 'sans', 'spacing': 'balanced',
    'corners': 'soft', 'density': 'comfortable',
}
PRESETS = [DEFAULT_THEME, {
    **DEFAULT_THEME, 'name': 'Archive', 'heading_font': 'serif',
    'colors': {'page': '#f4efe4', 'paper': '#fffcf5', 'ink': '#292d24',
               'muted': '#555b4d', 'rule': '#c9c9b9', 'accent': '#285137',
               'accent_text': '#ffffff', 'soft': '#e8eddf'},
}, {
    **DEFAULT_THEME, 'name': 'After hours', 'mode': 'dark',
    'colors': {'page': '#111820', 'paper': '#1b2530', 'ink': '#edf2f7',
               'muted': '#b6c5d4', 'rule': '#4a5e72', 'accent': '#a7ccff',
               'accent_text': '#111820', 'soft': '#263443'},
}]

FONTS = {'sans': 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
         'serif': 'Georgia, "Times New Roman", serif',
         'mono': 'ui-monospace, SFMono-Regular, Consolas, monospace'}


def theme_styles(theme: Theme) -> dict[str, str]:
    styles = {'--' + key.replace('_', '-'): value for key, value in theme.colors.model_dump().items()}
    styles.update({'--hover': theme.colors.accent, '--focus': theme.colors.accent,
                   '--success': theme.colors.ink, '--font': FONTS[theme.font],
                   '--heading-font': FONTS[theme.heading_font],
                   '--space': {'close': '20px', 'balanced': '32px', 'airy': '44px'}[theme.spacing],
                   '--radius': {'square': '0px', 'soft': '6px', 'round': '14px'}[theme.corners],
                   '--panel-radius': {'square': '0px', 'soft': '12px', 'round': '20px'}[theme.corners],
                   '--row-pad': '10px' if theme.density == 'compact' else '18px',
                   '--control-pad': '7px' if theme.density == 'compact' else '10px',
                   'colorScheme': theme.mode})
    return styles


# Keep the migration's frozen copy consistent. IS TRUE rejects missing/null fields.
THEME_CHECK = "(" + " AND ".join([
    "jsonb_typeof(theme) = 'object'", "octet_length(theme::text) <= 4096",
    "theme - ARRAY['schema_version','name','mode','colors','font','heading_font','spacing','corners','density']::text[] = '{}'::jsonb",
    "theme->'schema_version' = '1'::jsonb",
    "jsonb_typeof(theme->'name') = 'string' AND char_length(btrim(theme->>'name')) BETWEEN 1 AND 60 AND (theme->>'name') !~ '[[:cntrl:]]'",
    "theme->>'mode' IN ('light','dark')",
    "theme->>'font' IN ('sans','serif','mono')",
    "theme->>'heading_font' IN ('sans','serif','mono')",
    "theme->>'spacing' IN ('close','balanced','airy')",
    "theme->>'corners' IN ('square','soft','round')",
    "theme->>'density' IN ('compact','comfortable')",
    "jsonb_typeof(theme->'colors') = 'object'",
    "(theme->'colors') - ARRAY['page','paper','ink','muted','rule','accent','accent_text','soft']::text[] = '{}'::jsonb",
    *[f"jsonb_typeof(theme->'colors'->'{key}') = 'string' AND (theme->'colors'->>'{key}') ~ '^#[0-9a-fA-F]{{6}}$'" for key in Palette.model_fields],
]) + ") IS TRUE"
