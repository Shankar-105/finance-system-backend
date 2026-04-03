from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from redis.asyncio import Redis
from sqlalchemy import delete, func, or_, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_db, get_redis
from app.dependencies import get_current_user, sensitive_route_limiter
from app.models import FinancialRecord, RecordType, User, UserRole
from app.schemas import (
    DeletedFinancialRecordListResponse,
    DeletedFinancialRecordOut,
    CSVImportResponse,
    FinancialRecordCreate,
    FinancialRecordListResponse,
    FinancialRecordOut,
    FinancialRecordUpdate,
    MessageResponse,
)
from app.services.csv_service import (
    CSVParseError,
    parse_financial_records_csv,
    serialize_financial_records_to_csv,
    validate_financial_record_csv_rows,
)
from app.services.dashboard_service import invalidate_dashboard_cache

router = APIRouter(prefix="/financial-records", tags=["Financial Records"])


def _assert_can_read_records(user: User) -> None:
    if user.role not in (UserRole.ANALYST, UserRole.ADMIN):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")


def _assert_admin(user: User) -> None:
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")


async def _purge_expired_deleted_records(db: AsyncSession) -> None:
    settings = get_settings()
    cutoff = datetime.now(timezone.utc) - timedelta(days=settings.recycle_bin_retention_days)
    await db.execute(
        delete(FinancialRecord).where(
            FinancialRecord.is_deleted.is_(True),
            FinancialRecord.deleted_at.is_not(None),
            FinancialRecord.deleted_at <= cutoff,
        )
    )
    await db.commit()


async def _safe_commit(db: AsyncSession, *, integrity_detail: str, generic_detail: str) -> None:
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=integrity_detail) from exc
    except SQLAlchemyError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=generic_detail) from exc


@router.post("", response_model=FinancialRecordOut, status_code=status.HTTP_201_CREATED)
async def create_financial_record(
    payload: FinancialRecordCreate,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    current_user: User = Depends(get_current_user),
    _: None = Depends(sensitive_route_limiter),
) -> FinancialRecordOut:
    _assert_admin(current_user)
    await _purge_expired_deleted_records(db)

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
    await _safe_commit(
        db,
        integrity_detail="Unable to create record with provided data",
        generic_detail="Failed to create financial record",
    )
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
    search: str | None = Query(default=None, min_length=1, max_length=100),
    record_type: RecordType | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FinancialRecordListResponse:
    _assert_can_read_records(current_user)
    await _purge_expired_deleted_records(db)

    if start_date and end_date and start_date > end_date:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="start_date cannot be after end_date")

    filters = [FinancialRecord.is_deleted.is_(False)]
    if start_date:
        filters.append(FinancialRecord.entry_date >= start_date)
    if end_date:
        filters.append(FinancialRecord.entry_date <= end_date)
    if category:
        filters.append(FinancialRecord.category == category)
    if search:
        search_pattern = f"%{search}%"
        filters.append(
            or_(
                FinancialRecord.category.ilike(search_pattern),
                FinancialRecord.notes.ilike(search_pattern),
            )
        )
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


@router.get("/export")
async def export_financial_records_csv(
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    category: str | None = Query(default=None, min_length=2, max_length=100),
    search: str | None = Query(default=None, min_length=1, max_length=100),
    record_type: RecordType | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    _assert_can_read_records(current_user)
    await _purge_expired_deleted_records(db)

    if start_date and end_date and start_date > end_date:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="start_date cannot be after end_date")

    filters = [FinancialRecord.is_deleted.is_(False)]
    if start_date:
        filters.append(FinancialRecord.entry_date >= start_date)
    if end_date:
        filters.append(FinancialRecord.entry_date <= end_date)
    if category:
        filters.append(FinancialRecord.category == category)
    if search:
        search_pattern = f"%{search}%"
        filters.append(
            or_(
                FinancialRecord.category.ilike(search_pattern),
                FinancialRecord.notes.ilike(search_pattern),
            )
        )
    if record_type:
        filters.append(FinancialRecord.record_type == RecordType(record_type.value))

    stmt = (
        select(FinancialRecord)
        .where(*filters)
        .order_by(FinancialRecord.entry_date.desc(), FinancialRecord.id.desc())
    )
    rows = (await db.execute(stmt)).scalars().all()

    csv_content = serialize_financial_records_to_csv(rows)
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="financial_records_export.csv"'},
    )


@router.post("/import", response_model=CSVImportResponse)
async def import_financial_records_csv(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    current_user: User = Depends(get_current_user),
    _: None = Depends(sensitive_route_limiter),
) -> CSVImportResponse:
    _assert_admin(current_user)
    await _purge_expired_deleted_records(db)

    content_type = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    if content_type != "text/csv":
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Content-Type must be text/csv")

    raw_body = await request.body()
    if not raw_body:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="CSV body is empty")
    if len(raw_body) > get_settings().max_csv_import_bytes:
        raise HTTPException(status_code=status.HTTP_413_CONTENT_TOO_LARGE, detail="CSV body too large")

    try:
        csv_text = raw_body.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="CSV must be UTF-8 encoded") from exc

    try:
        parsed_rows = parse_financial_records_csv(csv_text)
    except CSVParseError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    valid_rows, errors = validate_financial_record_csv_rows(parsed_rows)

    user_ids = {payload.user_id for _, payload, _ in valid_rows if payload.user_id is not None}
    if user_ids:
        existing_user_ids = set((await db.execute(select(User.id).where(User.id.in_(user_ids)))).scalars().all())
        missing_user_ids = user_ids - existing_user_ids
        if missing_user_ids:
            retained_rows: list[tuple[int, FinancialRecordCreate, dict[str, str]]] = []
            for row_index, payload, row_data in valid_rows:
                if payload.user_id in missing_user_ids:
                    errors.append(
                        {
                            "row_index": row_index,
                            "row_data": row_data,
                            "errors": ["Target user not found"],
                        }
                    )
                else:
                    retained_rows.append((row_index, payload, row_data))
            valid_rows = retained_rows

    imported_count = 0
    if valid_rows:
        created_rows = [
            FinancialRecord(
                amount=payload.amount,
                record_type=RecordType(payload.record_type.value),
                category=payload.category,
                entry_date=payload.entry_date,
                notes=payload.notes,
                user_id=payload.user_id or current_user.id,
            )
            for _, payload, _ in valid_rows
        ]
        db.add_all(created_rows)
        await _safe_commit(
            db,
            integrity_detail="CSV contains rows that violate data constraints",
            generic_detail="Failed to import CSV records",
        )
        imported_count = len(created_rows)
        await invalidate_dashboard_cache(redis)

    failed_count = len(errors)
    if failed_count > 0 and imported_count > 0:
        response.status_code = status.HTTP_207_MULTI_STATUS
        status_value = "partial_success"
    elif failed_count > 0:
        response.status_code = status.HTTP_400_BAD_REQUEST
        status_value = "failed"
    else:
        response.status_code = status.HTTP_201_CREATED
        status_value = "success"

    normalized_errors = [
        {
            "row_index": int(error["row_index"]),
            "row_data": dict(error["row_data"]),
            "errors": [str(item) for item in error["errors"]],
        }
        for error in errors
    ]

    return CSVImportResponse(
        status=status_value,
        total_rows=len(parsed_rows),
        imported_count=imported_count,
        failed_count=failed_count,
        errors=normalized_errors,
    )


@router.get("/{record_id}", response_model=FinancialRecordOut)
async def get_financial_record(
    record_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FinancialRecordOut:
    _assert_can_read_records(current_user)
    await _purge_expired_deleted_records(db)

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
    await _purge_expired_deleted_records(db)

    row = await db.get(FinancialRecord, record_id)
    if row is None or row.is_deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")

    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if key == "record_type" and value is not None:
            setattr(row, key, RecordType(value.value))
        else:
            setattr(row, key, value)

    await _safe_commit(
        db,
        integrity_detail="Unable to update record with provided data",
        generic_detail="Failed to update financial record",
    )
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
    await _purge_expired_deleted_records(db)

    row = await db.get(FinancialRecord, record_id)
    if row is None or row.is_deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")

    row.is_deleted = True
    row.deleted_at = datetime.now(timezone.utc)
    await db.commit()
    await invalidate_dashboard_cache(redis)
    return MessageResponse(message="Record soft-deleted successfully")


@router.get("/bin/records", response_model=DeletedFinancialRecordListResponse)
async def list_deleted_financial_records(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DeletedFinancialRecordListResponse:
    _assert_admin(current_user)
    await _purge_expired_deleted_records(db)

    filters = [FinancialRecord.is_deleted.is_(True)]
    total_stmt = select(func.count(FinancialRecord.id)).where(*filters)
    total = (await db.execute(total_stmt)).scalar_one()

    stmt = (
        select(FinancialRecord)
        .where(*filters)
        .order_by(FinancialRecord.deleted_at.desc(), FinancialRecord.id.desc())
        .offset(offset)
        .limit(limit)
    )
    rows = (await db.execute(stmt)).scalars().all()

    return DeletedFinancialRecordListResponse(
        total=total,
        offset=offset,
        limit=limit,
        items=[DeletedFinancialRecordOut.model_validate(row) for row in rows],
    )


@router.post("/bin/records/{record_id}/restore", response_model=FinancialRecordOut)
async def restore_financial_record(
    record_id: int,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    current_user: User = Depends(get_current_user),
    _: None = Depends(sensitive_route_limiter),
) -> FinancialRecordOut:
    _assert_admin(current_user)
    await _purge_expired_deleted_records(db)

    row = await db.get(FinancialRecord, record_id)
    if row is None or not row.is_deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deleted record not found")

    row.is_deleted = False
    row.deleted_at = None
    await db.commit()
    await db.refresh(row)
    await invalidate_dashboard_cache(redis)
    return FinancialRecordOut.model_validate(row)
