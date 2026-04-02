# Finance Data Processing and Access Control Backend 🚀

Modern async finance backend with secure auth, role-based access control, analytics-ready dashboard APIs, recycle-bin safety for records, and reliable automated testing.

---

![Python](https://img.shields.io/badge/Python-3.14-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-Async-green?logo=fastapi)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-blue?logo=postgresql)
![Redis](https://img.shields.io/badge/Redis-7-red?logo=redis)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)
![Tests](https://img.shields.io/badge/Tests-47%20Passing-success)

## 🌟 What You Get

- Secure JWT auth with refresh rotation and revocation.
- RBAC with controlled role governance (viewer, analyst, admin).
- Dashboard APIs for summary, category distribution, trends, and recent activity.
- Recycle-bin workflow for deleted records with restore + retention policy.
- Redis-backed cache and rate limiting.
- Fully async architecture from routes to data layer.

---

## 📘 Documentation

- Full Features Documented: [docs/FEATURES.md](docs/FEATURES.md)
- Complete API Endpoints reference: [docs/API_GUIDE.md](docs/API_GUIDE.md)
- Dashboard deep-dive: [docs/DASHBOARD_GUIDE.md](docs/DASHBOARD_GUIDE.md)
- Setup guide: [docs/SETUP.md](docs/SETUP.md)
- Testing guide using pytests: [docs/TESTS.md](docs/TESTS.md)
- Contribution guide: [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md)

---
## ⚙️ CI

GitHub Actions workflow: [.github/workflows/ci.yml](.github/workflows/ci.yml)

Runs service containers, installs dependencies, validates connectivity, and executes the full test suite on push and pull request.