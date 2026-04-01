from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from redis.asyncio import Redis
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db, get_redis
from app.dependencies import get_current_user, sensitive_route_limiter
from app.models import FinancialRecord, RecordType, User, UserRole
from app.schemas import (
    FinancialRecordCreate,
    FinancialRecordListResponse,
    FinancialRecordOut,
    FinancialRecordUpdate,
    MessageResponse,
)
from app.services.dashboard_service import invalidate_dashboard_cache

router = APIRouter(prefix="/financial-records", tags=["Financial Records"])


def _assert_can_read_records(user: User) -> None:
    if user.role not in (UserRole.ANALYST, UserRole.ADMIN):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")


def _assert_admin(user: User) -> None:
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")


@router.post("", response_model=FinancialRecordOut, status_code=status.HTTP_201_CREATED)
async def create_financial_record(
    payload: FinancialRecordCreate,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    current_user: User = Depends(get_current_user),
    _: None = Depends(sensitive_route_limiter),
) -> FinancialRecordOut:
    _assert_admin(current_user)

    target_user_id = payload.user_id or current_user.id
    target_user = await db.get(User, target_user_id)
    if target_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target user not found")

    row = FinancialRecord(
        amount=payload.amount,
        record_type=RecordType(payload.record_type.value),
        category=payload.category,
        entry_date=payload.entry_date,
        notes=payload.notes,
        user_id=target_user_id,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    await invalidate_dashboard_cache(redis)
    return FinancialRecordOut.model_validate(row)


@router.get("", response_model=FinancialRecordListResponse)
async def list_financial_records(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    category: str | None = Query(default=None, min_length=2, max_length=100),
    record_type: RecordType | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FinancialRecordListResponse:
    _assert_can_read_records(current_user)

    if start_date and end_date and start_date > end_date:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="start_date cannot be after end_date")

    filters = [FinancialRecord.is_deleted.is_(False)]
    if start_date:
        filters.append(FinancialRecord.entry_date >= start_date)
    if end_date:
        filters.append(FinancialRecord.entry_date <= end_date)
    if category:
        filters.append(FinancialRecord.category == category)
    if record_type:
        filters.append(FinancialRecord.record_type == RecordType(record_type.value))

    total_stmt = select(func.count(FinancialRecord.id)).where(*filters)
    total = (await db.execute(total_stmt)).scalar_one()

    stmt = (
        select(FinancialRecord)
        .where(*filters)
        .order_by(FinancialRecord.entry_date.desc(), FinancialRecord.id.desc())
        .offset(offset)
        .limit(limit)
    )
    rows = (await db.execute(stmt)).scalars().all()

    return FinancialRecordListResponse(
        total=total,
        offset=offset,
        limit=limit,
        items=[FinancialRecordOut.model_validate(row) for row in rows],
    )


@router.get("/{record_id}", response_model=FinancialRecordOut)
async def get_financial_record(
    record_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FinancialRecordOut:
    _assert_can_read_records(current_user)

    row = await db.get(FinancialRecord, record_id)
    if row is None or row.is_deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")

    return FinancialRecordOut.model_validate(row)


@router.patch("/{record_id}", response_model=FinancialRecordOut)
async def update_financial_record(
    record_id: int,
    payload: FinancialRecordUpdate,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    current_user: User = Depends(get_current_user),
    _: None = Depends(sensitive_route_limiter),
) -> FinancialRecordOut:
    _assert_admin(current_user)

    row = await db.get(FinancialRecord, record_id)
    if row is None or row.is_deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")

    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if key == "record_type" and value is not None:
            setattr(row, key, RecordType(value.value))
        else:
            setattr(row, key, value)

    await db.commit()
    await db.refresh(row)
    await invalidate_dashboard_cache(redis)
    return FinancialRecordOut.model_validate(row)


@router.delete("/{record_id}", response_model=MessageResponse)
async def soft_delete_financial_record(
    record_id: int,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    current_user: User = Depends(get_current_user),
    _: None = Depends(sensitive_route_limiter),
) -> MessageResponse:
    _assert_admin(current_user)

    row = await db.get(FinancialRecord, record_id)
    if row is None or row.is_deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")

    row.is_deleted = True
    row.deleted_at = datetime.now(timezone.utc)
    await db.commit()
    await invalidate_dashboard_cache(redis)
    return MessageResponse(message="Record soft-deleted successfully")
