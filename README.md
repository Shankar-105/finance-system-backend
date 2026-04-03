# Finance Data Processing and Access Control Backend 🚀

Modern async finance backend with secure auth, role-based access control, analytics-ready dashboard APIs, recycle-bin safety for records, and reliable automated testing.

---

![Python](https://img.shields.io/badge/Python-3.14-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-Async-green?logo=fastapi)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-blue?logo=postgresql)
![Redis](https://img.shields.io/badge/Redis-7-red?logo=redis)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)
![Tests](https://img.shields.io/badge/Tests-55%20Passing-success)

## 🔥 Start Here: App Workflow

If you want to understand how this backend actually behaves from login to role-based usage, read:

**[docs/BASIC_FLOW.md](docs/BASIC_FLOW.md)**

It explains the real journey for `viewer`, `analyst`, and `admin`, including auth lifecycle, record lifecycle, dashboard usage order, and websocket presence flow.

## 🌟 What You Get

- Secure JWT auth with refresh rotation and revocation.
- RBAC with controlled role governance (viewer, analyst, admin).
- Dashboard APIs for summary, category distribution, trends, and recent activity.
- Recycle-bin workflow for deleted records with restore + retention policy.
- CSV import/export for bulk onboarding and reporting workflows.
- Search across records by category and notes.
- Redis-backed cache and rate limiting.
- Fully async architecture from routes to data layer.

---

## 📘 Documentation

- **Full Features Documented**: [docs/FEATURES.md](docs/FEATURES.md)
- **Complete API Endpoints reference**: [docs/API_GUIDE.md](docs/API_GUIDE.md)
- **Setup guide**: [docs/SETUP.md](docs/SETUP.md)
- **Testing guide using pytests**: [docs/TESTS.md](docs/TESTS.md)
- **Contribution guide**: [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md)
- **Deployment & CI/CD Pipeline:** [docs/DEPLOYMENTS.md](docs/DEPLOYMENTS.md)

---

## 📝 Project Context

This repository was developed as part of an internship assessment by [Zorvyn Fintech](https://zorvyn.io/) focused on secure backend engineering, role-based access control, and practical financial data workflows.

## ⚖️ Technology Choice

I thought to build this in Spring Boot because it is widely used in enterprise financial systems. But for this assessment, development speed mattered most, and I am currently much stronger with FastAPI and async Python. So I chose FastAPI to deliver a cleaner and more complete implementation within the timeline, while still following production-style backend practices.

## 🙏 Acknowledgement

I am genuinely thankful for this problem statement. Building it end-to-end gave me practical experience with RBAC. While I have previously explored caching, rate-limiting, and other system design concepts in my past projects, I had never worked on an RBAC project before, and this gave me great experience truly thankful.