import csv
import io
from decimal import Decimal, InvalidOperation

from pydantic import ValidationError

from app.models import FinancialRecord, RecordType
from app.schemas import FinancialRecordCreate

CSV_EXPORT_HEADERS = [
    "id",
    "amount",
    "record_type",
    "category",
    "entry_date",
    "notes",
    "created_at",
    "updated_at",
    "user_id",
]


class CSVParseError(ValueError):
    """Raised when CSV payload cannot be parsed safely."""


def serialize_financial_records_to_csv(records: list[FinancialRecord]) -> str:
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(CSV_EXPORT_HEADERS)

    for row in records:
        writer.writerow(
            [
                row.id,
                str(row.amount),
                row.record_type.value,
                row.category,
                row.entry_date.isoformat(),
                row.notes or "",
                row.created_at.isoformat(),
                row.updated_at.isoformat(),
                row.user_id,
            ]
        )

    return output.getvalue()


def parse_financial_records_csv(text: str) -> list[dict[str, str]]:
    normalized = text.lstrip("\ufeff").strip()
    if not normalized:
        raise CSVParseError("CSV body is empty")

    reader = csv.DictReader(io.StringIO(normalized))
    if reader.fieldnames is None:
        raise CSVParseError("CSV header row is required")

    headers = {name.strip() for name in reader.fieldnames if name is not None}
    required_headers = {"amount", "record_type", "category", "entry_date"}
    allowed_headers = required_headers | {"notes", "user_id"}

    missing_headers = required_headers - headers
    if missing_headers:
        raise CSVParseError(f"Missing required CSV headers: {', '.join(sorted(missing_headers))}")

    unknown_headers = headers - allowed_headers
    if unknown_headers:
        raise CSVParseError(f"Unsupported CSV headers: {', '.join(sorted(unknown_headers))}")

    rows: list[dict[str, str]] = []
    for raw_row in reader:
        row = {
            key.strip(): (value.strip() if isinstance(value, str) else "")
            for key, value in raw_row.items()
            if key is not None
        }
        if not any(row.values()):
            continue
        rows.append(row)

    if not rows:
        raise CSVParseError("CSV contains no data rows")

    return rows


def validate_financial_record_csv_rows(
    rows: list[dict[str, str]],
) -> tuple[list[tuple[int, FinancialRecordCreate, dict[str, str]]], list[dict[str, object]]]:
    valid_rows: list[tuple[int, FinancialRecordCreate, dict[str, str]]] = []
    errors: list[dict[str, object]] = []

    for row_index, row in enumerate(rows, start=2):
        row_errors: list[str] = []

        user_id: int | None = None
        raw_user_id = row.get("user_id")
        if raw_user_id:
            try:
                user_id = int(raw_user_id)
            except ValueError:
                row_errors.append("user_id must be an integer when provided")

        try:
            payload = FinancialRecordCreate(
                amount=Decimal(row.get("amount", "")),
                record_type=RecordType(row.get("record_type", "")),
                category=row.get("category", ""),
                entry_date=row.get("entry_date", ""),
                notes=row.get("notes") or None,
                user_id=user_id,
            )
            if row_errors:
                errors.append({"row_index": row_index, "row_data": row, "errors": row_errors})
                continue
            valid_rows.append((row_index, payload, row))
        except (InvalidOperation, ValidationError, ValueError) as exc:
            row_errors.append(str(exc))
            errors.append({"row_index": row_index, "row_data": row, "errors": row_errors})

    return valid_rows, errors
