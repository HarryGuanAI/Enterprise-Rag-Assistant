from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.db.session import get_db
from app.schemas.settings import AppSettingsSchema
from app.services.settings_service import get_or_create_settings, update_settings as persist_settings

router = APIRouter()


@router.get("", response_model=AppSettingsSchema)
def get_settings(db: Session = Depends(get_db)) -> AppSettingsSchema:
    return get_or_create_settings(db)


@router.put("", response_model=AppSettingsSchema)
def update_settings(
    payload: AppSettingsSchema,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_admin),
) -> AppSettingsSchema:
    return persist_settings(db, payload)
