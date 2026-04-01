import json
from datetime import date
from decimal import Decimal

from redis.asyncio import Redis
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import FinancialRecord, RecordType
from app.schemas import CategoryTotal, MonthlyTrendPoint, RecentActivityItem, SummaryTotals

settings = get_settings()


def _decimal_to_str(value: Decimal) -> str:
	return str(value.quantize(Decimal("0.01")))


def _cache_key(name: str, start_date: date | None, end_date: date | None) -> str:
	start = start_date.isoformat() if start_date else "none"
	end = end_date.isoformat() if end_date else "none"
	return f"dashboard:{name}:{start}:{end}"


def _apply_date_filters(stmt, start_date: date | None, end_date: date | None):
	stmt = stmt.where(FinancialRecord.is_deleted.is_(False))
	if start_date:
		stmt = stmt.where(FinancialRecord.entry_date >= start_date)
	if end_date:
		stmt = stmt.where(FinancialRecord.entry_date <= end_date)
	return stmt


async def invalidate_dashboard_cache(redis: Redis) -> None:
	try:
		keys = await redis.keys("dashboard:*")
		if keys:
			await redis.delete(*keys)
	except Exception:
		return


async def get_summary_totals(
	db: AsyncSession,
	redis: Redis,
	start_date: date | None,
	end_date: date | None,
) -> SummaryTotals:
	key = _cache_key("totals", start_date, end_date)
	try:
		cached = await redis.get(key)
	except Exception:
		cached = None
	if cached:
		payload = json.loads(cached)
		return SummaryTotals(
			total_income=Decimal(payload["total_income"]),
			total_expenses=Decimal(payload["total_expenses"]),
			net_balance=Decimal(payload["net_balance"]),
		)

	stmt = select(
		func.coalesce(
			func.sum(case((FinancialRecord.record_type == RecordType.INCOME, FinancialRecord.amount), else_=0)),
			0,
		).label("total_income"),
		func.coalesce(
			func.sum(case((FinancialRecord.record_type == RecordType.EXPENSE, FinancialRecord.amount), else_=0)),
			0,
		).label("total_expenses"),
	)
	stmt = _apply_date_filters(stmt, start_date, end_date)
	row = (await db.execute(stmt)).one()

	total_income = Decimal(row.total_income)
	total_expenses = Decimal(row.total_expenses)
	net_balance = total_income - total_expenses
	result = SummaryTotals(
		total_income=total_income,
		total_expenses=total_expenses,
		net_balance=net_balance,
	)

	try:
		await redis.set(
			key,
			json.dumps(
				{
					"total_income": _decimal_to_str(total_income),
					"total_expenses": _decimal_to_str(total_expenses),
					"net_balance": _decimal_to_str(net_balance),
				}
			),
			ex=settings.dashboard_cache_ttl_seconds,
		)
	except Exception:
		pass
	return result


async def get_category_totals(
	db: AsyncSession,
	redis: Redis,
	start_date: date | None,
	end_date: date | None,
) -> list[CategoryTotal]:
	key = _cache_key("categories", start_date, end_date)
	try:
		cached = await redis.get(key)
	except Exception:
		cached = None
	if cached:
		payload = json.loads(cached)
		return [CategoryTotal(category=item["category"], total=Decimal(item["total"])) for item in payload]

	stmt = select(
		FinancialRecord.category,
		func.coalesce(func.sum(FinancialRecord.amount), 0).label("total"),
	).group_by(FinancialRecord.category)
	stmt = _apply_date_filters(stmt, start_date, end_date)
	rows = (await db.execute(stmt)).all()

	result = [CategoryTotal(category=row.category, total=Decimal(row.total)) for row in rows]
	try:
		await redis.set(
			key,
			json.dumps(
				[{"category": item.category, "total": _decimal_to_str(item.total)} for item in result]
			),
			ex=settings.dashboard_cache_ttl_seconds,
		)
	except Exception:
		pass
	return result


async def get_recent_activity(
	db: AsyncSession,
	limit: int = 10,
) -> list[RecentActivityItem]:
	stmt = (
		select(FinancialRecord)
		.where(FinancialRecord.is_deleted.is_(False))
		.order_by(FinancialRecord.created_at.desc())
		.limit(limit)
	)
	rows = (await db.execute(stmt)).scalars().all()
	return [
		RecentActivityItem(
			id=row.id,
			amount=Decimal(row.amount),
			record_type=row.record_type,
			category=row.category,
			entry_date=row.entry_date,
			user_id=row.user_id,
			created_at=row.created_at,
		)
		for row in rows
	]


async def get_monthly_trends(
	db: AsyncSession,
	redis: Redis,
	start_date: date | None,
	end_date: date | None,
) -> list[MonthlyTrendPoint]:
	key = _cache_key("monthly_trends", start_date, end_date)
	try:
		cached = await redis.get(key)
	except Exception:
		cached = None
	if cached:
		payload = json.loads(cached)
		return [
			MonthlyTrendPoint(
				month=item["month"],
				income=Decimal(item["income"]),
				expense=Decimal(item["expense"]),
			)
			for item in payload
		]

	month_expr = func.date_trunc("month", FinancialRecord.entry_date)
	stmt = (
		select(
			month_expr.label("month"),
			func.coalesce(
				func.sum(case((FinancialRecord.record_type == RecordType.INCOME, FinancialRecord.amount), else_=0)),
				0,
			).label("income"),
			func.coalesce(
				func.sum(case((FinancialRecord.record_type == RecordType.EXPENSE, FinancialRecord.amount), else_=0)),
				0,
			).label("expense"),
		)
		.group_by(month_expr)
		.order_by(month_expr.asc())
	)
	stmt = _apply_date_filters(stmt, start_date, end_date)
	rows = (await db.execute(stmt)).all()

	result = [
		MonthlyTrendPoint(
			month=row.month.strftime("%Y-%m"),
			income=Decimal(row.income),
			expense=Decimal(row.expense),
		)
		for row in rows
	]

	try:
		await redis.set(
			key,
			json.dumps(
				[
					{
						"month": item.month,
						"income": _decimal_to_str(item.income),
						"expense": _decimal_to_str(item.expense),
					}
					for item in result
				]
			),
			ex=settings.dashboard_cache_ttl_seconds,
		)
	except Exception:
		pass
	return result
