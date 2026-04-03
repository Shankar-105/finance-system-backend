from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserRole(StrEnum):
    VIEWER = "viewer"
    ANALYST = "analyst"
    ADMIN = "admin"


class RecordType(StrEnum):
    INCOME = "income"
    EXPENSE = "expense"


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: str
    exp: int
    typ: str
    jti: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str | None = None


class UserBase(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=50)


class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)
    role: UserRole = UserRole.VIEWER


class AdminUserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)
    role: UserRole = UserRole.VIEWER


class UserOut(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    role: UserRole
    is_active: bool
    created_at: datetime


class UserUpdate(BaseModel):
    role: UserRole | None = None
    is_active: bool | None = None


class FinancialRecordBase(BaseModel):
    amount: Decimal = Field(gt=0)
    record_type: RecordType
    category: str = Field(min_length=2, max_length=100)
    entry_date: date
    notes: str | None = Field(default=None, max_length=1000)


class FinancialRecordCreate(FinancialRecordBase):
    user_id: int | None = None


class FinancialRecordUpdate(BaseModel):
    amount: Decimal | None = Field(default=None, gt=0)
    record_type: RecordType | None = None
    category: str | None = Field(default=None, min_length=2, max_length=100)
    entry_date: date | None = None
    notes: str | None = Field(default=None, max_length=1000)


class FinancialRecordOut(FinancialRecordBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime


class DeletedFinancialRecordOut(FinancialRecordOut):
    deleted_at: datetime


class FinancialRecordListResponse(BaseModel):
    total: int
    offset: int
    limit: int
    items: list[FinancialRecordOut]


class DeletedFinancialRecordListResponse(BaseModel):
    total: int
    offset: int
    limit: int
    items: list[DeletedFinancialRecordOut]


class CSVImportRowError(BaseModel):
    row_index: int
    row_data: dict[str, str]
    errors: list[str]


class CSVImportResponse(BaseModel):
    status: str
    total_rows: int
    imported_count: int
    failed_count: int
    errors: list[CSVImportRowError]


class PaginationParams(BaseModel):
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=20, ge=1, le=100)


class MessageResponse(BaseModel):
    message: str


class SummaryTotals(BaseModel):
    total_income: Decimal
    total_expenses: Decimal
    net_balance: Decimal


class CategoryTotal(BaseModel):
    category: str
    total: Decimal


class MonthlyTrendPoint(BaseModel):
    month: str
    income: Decimal
    expense: Decimal


class RecentActivityItem(BaseModel):
    id: int
    amount: Decimal
    record_type: RecordType
    category: str
    entry_date: date
    user_id: int
    created_at: datetime
