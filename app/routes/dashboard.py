from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db, get_redis
from app.dependencies import require_roles
from app.models import User, UserRole
from app.schemas import CategoryTotal, MonthlyTrendPoint, RecentActivityItem, SummaryTotals
from app.services.dashboard_service import (
    get_category_totals,
    get_monthly_trends,
    get_recent_activity,
    get_summary_totals,
)

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/summary", response_model=SummaryTotals)
async def summary_totals(
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    _: User = Depends(require_roles(UserRole.VIEWER, UserRole.ANALYST, UserRole.ADMIN)),
) -> SummaryTotals:
    if start_date and end_date and start_date > end_date:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="start_date cannot be after end_date")
    return await get_summary_totals(db, redis, start_date, end_date)


@router.get("/categories", response_model=list[CategoryTotal])
async def category_totals(
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    _: User = Depends(require_roles(UserRole.VIEWER, UserRole.ANALYST, UserRole.ADMIN)),
) -> list[CategoryTotal]:
    if start_date and end_date and start_date > end_date:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="start_date cannot be after end_date")
    return await get_category_totals(db, redis, start_date, end_date)


@router.get("/recent-activity", response_model=list[RecentActivityItem])
async def recent_activity(
    limit: int = Query(default=10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles(UserRole.VIEWER, UserRole.ANALYST, UserRole.ADMIN)),
) -> list[RecentActivityItem]:
    return await get_recent_activity(db, limit)


@router.get("/monthly-trends", response_model=list[MonthlyTrendPoint])
async def monthly_trends(
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    _: User = Depends(require_roles(UserRole.VIEWER, UserRole.ANALYST, UserRole.ADMIN)),
) -> list[MonthlyTrendPoint]:
    if start_date and end_date and start_date > end_date:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="start_date cannot be after end_date")
    return await get_monthly_trends(db, redis, start_date, end_date)
