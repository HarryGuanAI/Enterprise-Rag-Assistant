from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.stats import StatsResponse
from app.services.stats_service import get_stats as build_stats

router = APIRouter()


@router.get("", response_model=StatsResponse)
def get_stats(
    guest_id: str | None = Query(default=None, max_length=120),
    db: Session = Depends(get_db),
) -> StatsResponse:
    return build_stats(db, guest_id=guest_id)
