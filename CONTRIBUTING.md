# Contributing

Thank you for contributing to the Finance Data Processing and Access Control Backend.

## Contributor Workflow

1. Fork and clone repository.
2. Create a feature branch.
3. Implement changes with tests.
4. Run full test suite.
5. Open pull request.

## Branch Naming

Use descriptive branch names:

- feat/rbac-audit-logs
- fix/refresh-token-reuse
- docs/api-guide-update
- test/dashboard-filters

## Local Development Checklist

Before coding:

1. Follow setup in SETUP.md.
2. Confirm migrations are at head.
3. Confirm tests pass before and after your change.

## Code Standards

- Keep everything async for route, service, and persistence paths.
- Enforce RBAC at dependency or route layer, not only in client assumptions.
- Use schema validation for request and response contracts.
- Keep services focused and routes thin.
- Prefer clear error messages and correct HTTP status codes.

## Database Change Process

When changing models:

1. Update app/models.py.
2. Create Alembic revision.
3. Verify upgrade and downgrade locally.
4. Add or update tests for changed behavior.

## Testing Rules

- All feature changes must include tests.
- Do not break existing tests.
- Use fixtures in tests/conftest.py for DB and Redis isolation.
- Prefer behavior-driven test names:
- test_refresh_reuse_old_token_fails
- test_list_records_viewer_forbidden

## Pull Request Quality Bar

PR should include:

- clear summary
- why the change is needed
- endpoints/models affected
- test evidence (pytest output)
- migration notes if schema changed

## CI Requirements

PRs are expected to pass GitHub Actions workflow:

- .github/workflows/ci.yml

## Recommended Commit Message Style

- feat: add monthly trend cache invalidation
- fix: handle redis outage in rate limiter
- test: add refresh token replay tests
- docs: update setup and api guide

## Security Notes

- Never commit .env.
- Avoid logging tokens, secrets, or passwords.
- Keep auth and RBAC checks explicit.

## Need Help

Open an issue with:

- expected behavior
- actual behavior
- steps to reproduce
- logs or traceback
