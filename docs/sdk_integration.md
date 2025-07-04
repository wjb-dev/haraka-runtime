# SDK Integration Guide

This guide shows how to use the Haraka Adapter SDK (the **haraka-runtime** package) to scaffold, test, and publish your own adapter.

---

## 1. Install the SDK

From the root of the **haraka-runtime** repository, install the SDK in editable mode so you can iterate on both SDK and adapters:

```bash
cd path/to/haraka-runtime
pip install -e .
```

> **What this does:**  
> - Installs the local SDK code into your virtual environment  
> - Allows you to update SDK code without re-installing

---

## 2. Scaffold a New Adapter

Copy the provided example into a new folder and rename it:

```bash
# From the SDK root:
cp -R examples/sample_adapter examples/my_adapter
cd examples/my_adapter
```

This directory contains:

- **`pyproject.toml`** — your adapter’s metadata and dependencies  
- **`app/main.py`** — a minimal `Adapter` subclass  
- **`README.md`** — adapter-specific docs  
- **`tests/`** — pytest fixtures and tests

---

## 3. Run Tests Against the Runtime

Ensure your adapter works end-to-end by running its tests within the SDK environment:

```bash
# Still in examples/my_adapter/
pip install -r requirements.txt   # if you have one, otherwise skip
pytest --maxfail=1 --disable-warnings -q \
  --cov=app --cov-report=term-missing tests/
```

You should see:

- All fixtures (e.g. mock `Orchestrator`) exercised  
- Lifecycle tests for `startup()` and `shutdown()`  
- The `main()` entrypoint tested  
- Coverage ≥ 80% on `app/main.py`

---

## 4. Publish to PyPI (or Internal Repo)

Once tests and lint pass, build and publish your adapter:

```bash
# Build distributions
python -m build .

# Upload to public PyPI
twine upload dist/*

# — or — upload to an internal repository
twine upload --repository-url https://internal.repo/simple dist/*
```

> **Tip:** You can use [Test PyPI](https://test.pypi.org/) (with `--repository-url`) to validate publishing before going live.
