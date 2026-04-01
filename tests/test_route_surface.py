from app.main import app


def test_expected_route_surface_present():
    paths = {route.path for route in app.routes}
    expected = {
        "/health",
        "/api/v1/users/register",
        "/api/v1/users/login",
        "/api/v1/users/refresh",
        "/api/v1/users/logout",
        "/api/v1/users/me",
        "/api/v1/users/admin/ping",
        "/api/v1/users/admin/online-users",
        "/api/v1/financial-records",
        "/api/v1/financial-records/{record_id}",
        "/api/v1/dashboard/summary",
        "/api/v1/dashboard/categories",
        "/api/v1/dashboard/recent-activity",
        "/api/v1/dashboard/monthly-trends",
        "/ws/presence",
    }
    assert expected.issubset(paths)
