from fastapi import APIRouter

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/health")
async def users_route_health() -> dict[str, str]:
    return {"status": "users routes ready"}
