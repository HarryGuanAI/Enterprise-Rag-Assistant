from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.app_setting import AppSetting
from app.schemas.settings import AppSettingsSchema


def default_settings() -> AppSettingsSchema:
    """返回系统默认 RAG 参数。

    这份默认值同时服务于新库初始化和配置缺失时的兜底。
    """
    return AppSettingsSchema()


def get_or_create_settings(db: Session) -> AppSettingsSchema:
    setting = db.scalars(select(AppSetting).limit(1)).first()
    if setting is None:
        setting = AppSetting(settings_json=default_settings().model_dump())
        db.add(setting)
        db.commit()
        db.refresh(setting)

    return AppSettingsSchema.model_validate(setting.settings_json)


def update_settings(db: Session, payload: AppSettingsSchema) -> AppSettingsSchema:
    setting = db.scalars(select(AppSetting).limit(1)).first()
    if setting is None:
        setting = AppSetting(settings_json=payload.model_dump())
        db.add(setting)
    else:
        setting.settings_json = payload.model_dump()

    db.commit()
    return payload

