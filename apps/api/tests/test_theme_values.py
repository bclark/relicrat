"""Theme parsing, accessibility and the only permitted CSS output."""
from copy import deepcopy
import pytest
from pydantic import ValidationError
from relicrat.theme_values import DEFAULT_THEME, PRESETS, Theme, contrast, theme_styles


def test_presets_and_contrast():
    assert contrast('#ffffff', '#000000') == 21
    assert contrast('#123456', '#123456') == 1
    for value in PRESETS:
        theme = Theme.model_validate(value)
        styles = theme_styles(theme)
        assert styles['--page'] == value['colors']['page']
        assert styles['colorScheme'] == value['mode']
        assert all(key.startswith('--') or key == 'colorScheme' for key in styles)


@pytest.mark.parametrize('patch', [
    {'schema_version': True}, {'schema_version': 2}, {'schema_version': '1'},
    {'name': ' '}, {'name': 'x'*61}, {'name': 'bad\x00name'},
    {'font': 'url(https://example.test/font)'}, {'spacing': '-100px'},
    {'density': 'tiny'}, {'corners': 4}, {'css': 'body { display:none }'},
])
def test_rejects_unsupported_values(patch):
    with pytest.raises(ValidationError):
        Theme.model_validate({**DEFAULT_THEME, **patch})


@pytest.mark.parametrize('key,value', [
    ('page', 'url(https://example.test/photo)'), ('page', '#fff'),
    ('ink', '#ffffff'), ('muted', '#dddddd'), ('accent', '#eeeeee'),
    ('accent_text', '#214fbd'), ('rule', None), ('unexpected', '#ffffff'),
])
def test_rejects_unsafe_or_unreadable_palette(key, value):
    theme = deepcopy(DEFAULT_THEME); theme['colors'][key] = value
    with pytest.raises(ValidationError):
        Theme.model_validate(theme)


def test_missing_keys_and_preview_choice_bounds():
    for key in DEFAULT_THEME:
        theme = deepcopy(DEFAULT_THEME); del theme[key]
        with pytest.raises(ValidationError): Theme.model_validate(theme)
    theme = Theme.model_validate({**DEFAULT_THEME, 'corners': 'square', 'density': 'compact', 'spacing':'airy'})
    styles = theme_styles(theme)
    assert styles['--radius'] == '0px' and styles['--row-pad'] == '10px'
    assert styles['--space'] == '44px'
