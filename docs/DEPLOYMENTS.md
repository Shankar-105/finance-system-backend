# 🚀 CI/CD Automation and Render Deployment

This document explains how the Finance Backend is tested, built, and deployed to production on Render.

---

## 📋 Overview

The application uses **two automated GitHub Actions workflows**:

1. **CI (Continuous Integration)**: Tests every push and PR
2. **CD (Continuous Deployment)**: Deploys to Render only after merging to main

```
┌─────────────────────────────────────────────────────────────────┐
│                    Developer Workflow                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. Create feature branch (any name)                            │
│     └─> git checkout -b bugfix/auth-issue                       │
│                                                                 │
│  2. Push commits                                                │
│     └─> Triggers CI: tests run on your branch                   │
│                                                                 │
│  3. Open PR to main                                             │
│     └─> Triggers CI: tests run on the merged state              │
│     └─> Required check: CI must pass                            │ 
│                                                                 │ 
│  4. If any Reviewrs are present they review & approves                                     │
│                                                                 │
│  5. Merge PR                                                    │
│     └─> Commit pushed to main                                   │
│     └─> Triggers CD: Deploy to Render begins                    │
│                                                                 │
│  6. Production live ✅                                           
│     └─> App running on Render                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🧪 CI Workflow: Continuous Integration

**File:** [.github/workflows/ci.yml](.github/workflows/ci.yml)

### When It Runs
- On **push to `main`**
- On **pull requests targeting `main`**

### What It Does

```
1. Checkout code
2. Set up Python 3.14 + pip caching
3. Install dependencies from requirements.txt
4. Start PostgreSQL 16 & Redis 7 service containers
5. Verify database connectivity with asyncpg
6. Run full pytest suite (47 tests)
7. Report pass/fail status
```
### Viewing CI Status
- **Pull Requests:** Check badge at bottom of PR (`Details` link shows logs)
- **Commits:** See green ✓ or red ✗ next to commit hash in GitHub
- **Full logs:** `.github/workflows/ci.yml` → Actions tab 
---

## 🚀 CD Workflow: Continuous Deployment

**File:** [.github/workflows/cd.yml](.github/workflows/cd.yml)

### When It Runs
- **Only after the CI workflow completes successfully on `main`**
- Triggered by the GitHub Actions `workflow_run` event
- **Not on pull requests**

### What It Does

```
1. Create GitHub Deployment record
   └─> Marks as "in_progress" in GitHub UI

2. Trigger Render deploy hook
   └─> Sends secure HTTPS POST to Render
   └─> Render rebuilds Docker image
   └─> Render runs: alembic upgrade head (migrations)
   └─> Render starts: uvicorn app.main:app --host 0.0.0.0 --port $PORT

3. Update GitHub Deployment status
   └─> On success: "success" + logs URL
   └─> On failure: "failure" + logs URL
   └─> Deployments tab shows timeline of all deploys
```

---


### Result
```
✓ No one can push directly to main
✓ PRs must pass CI tests
✓ At least 1 approval required
✓ Deploy only happens after merge
✓ Main stays protected & reliable
```

---

## 📊 Render Setup

### Render Service Info
- **Service Name:** `finance-api-*` (generated timestamp)
- **URL:** https://finance-api-*.onrender.com
- **Runtime:** Docker (builds from Dockerfile)
- **Pre-deploy Command:** `alembic upgrade head` (runs migrations)
- **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- **Health Check:** `/health` endpoint
- **Auto-deploy:** ❌ **Disabled** (CD workflow handles this)

### Render Database & Cache
- **PostgreSQL 16** (instance: `finance-pg-*`)
- **Redis 7 / Key-Value** (instance: `finance-kv-*`)
- **Internal Connection Strings** (used by app)
- **Automatic backups** (daily)
---

## 📚 Related Documentation

- [SETUP.md](SETUP.md) — Local development setup
- [TESTS.md](TESTS.md) — How to run & write tests
- [API_GUIDE.md](API_GUIDE.md) — API endpoints reference
- [CONTRIBUTING.md](CONTRIBUTING.md) — Contribution guidelines

---

## 🆘 Need Help?

Questions? Open an issue. I am always here on Github! 🚀
