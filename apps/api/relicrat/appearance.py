"""Owner appearance: explicit preview and conflict-checked apply, no inventory writes."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session
from relicrat.database import get_db
from relicrat.models import AppearanceSettings
from relicrat.theme_values import DEFAULT_THEME, PRESETS, Theme, theme_styles

router = APIRouter(prefix='/api/v1/appearance', tags=['appearance'])


class Preview(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    theme: Theme


class SaveAppearance(Preview):
    expected_revision: int = Field(ge=0, le=2147483646, strict=True)


def rendered(theme: Theme):
    return {'theme': theme.model_dump(), 'styles': theme_styles(theme)}


def saved_info(settings):
    try:
        return {**rendered(Theme.model_validate(settings.theme)), 'revision': settings.revision}
    except ValidationError:
        raise HTTPException(503, 'Saved appearance is invalid. Ask the operator to restore its settings.')


@router.get('')
def read_appearance(db: Session = Depends(get_db)):
    settings = db.get(AppearanceSettings, 1)
    if settings is None:
        raise HTTPException(503, 'Appearance settings are unavailable')
    return {**saved_info(settings), 'presets': PRESETS,
            'schema': Theme.model_json_schema(), 'default_theme': DEFAULT_THEME}


@router.post('/preview')
def preview(payload: Preview):
    return rendered(payload.theme)


@router.post('')
def save_appearance(payload: SaveAppearance, db: Session = Depends(get_db)):
    try:
        settings = db.scalar(select(AppearanceSettings).where(AppearanceSettings.id == 1)
                             .with_for_update().execution_options(populate_existing=True))
        if settings is None:
            raise HTTPException(503, 'Appearance settings are unavailable')
        if settings.revision != payload.expected_revision:
            raise HTTPException(409, 'Appearance changed elsewhere. Reload appearance and review your theme.')
        if settings.theme != payload.theme.model_dump():
            settings.theme = payload.theme.model_dump()
            settings.revision += 1
        # Serialize before commit; a failed response does not trigger a second write.
        result = saved_info(settings)
        db.commit()
        return result
    except Exception:
        db.rollback()
        raise
