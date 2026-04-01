from fastapi import APIRouter

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/health")
async def dashboard_route_health() -> dict[str, str]:
    return {"status": "dashboard routes ready"}
