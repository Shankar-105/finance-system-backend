# 🤝 Contributing Guide

> ✅ Goal: keep changes reliable, test-backed, and easy to review.

---

## 🚀 Contribution Flow

1. **Create a branch from main**
   ```bash
   git checkout -b my-feature-name
   ```
2. **Implement your change and commit**
   ```bash
   git add .
   git commit -m "Clear description of changes"
   ```
3. **Push and open a pull request**
   ```bash
   git push origin my-feature-name
   ```
4. **Wait for CI to pass** (all green checks)
5. **Request and address review feedback**
6. **Merge when approved** (Squash and merge or merge commit)
7. **Confirm deployment in GitHub Deployments tab**

---

## 🧰 Local Readiness Checklist

Before coding:

- Setup is complete using [SETUP.md](SETUP.md)
- Migrations are at head (`alembic upgrade head`)
- Baseline tests pass before your change
---

## 🗃️ Database Change Process

When changing models:

1. Update `app/models.py`
2. Create Alembic revision
3. Verify upgrade and downgrade locally
4. Add or update tests for changed behavior

---

## 🧪 Testing

- Every feature change must not break existing tests and add new tests if possible.

---


## 🔁 CI Expectations

All pull requests are expected to pass:

- [.github/workflows/ci.yml](../.github/workflows/ci.yml)

---

## 🆘 Need Help?

Open an issue!