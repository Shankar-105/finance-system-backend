from fastapi import APIRouter

router = APIRouter(prefix="/financial-records", tags=["Financial Records"])


@router.get("/health")
async def financial_records_route_health() -> dict[str, str]:
    return {"status": "financial records routes ready"}
