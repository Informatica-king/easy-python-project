# easy-python-project

## Cursor Cloud specific instructions

### Current state
This repository is currently an empty Python project skeleton. Aside from `README.md`
and this file, there is no application code, no dependency manifest
(`requirements.txt` / `pyproject.toml`), no tests, and no services yet.

### Development environment
- Python `3.12` is the target runtime.
- A virtual environment lives at `.venv/` (git-ignored). The startup update script
  creates it and installs dependencies if/when a manifest is added.
- Activate it with `source .venv/bin/activate`, or call binaries directly via
  `.venv/bin/python` / `.venv/bin/pip`.
- Creating the venv requires the system package `python3.12-venv`. This is a system
  dependency (not part of the update script). If `python3 -m venv .venv` fails with an
  `ensurepip is not available` error, install it with
  `sudo apt-get install -y python3.12-venv`.

### Lint / test / build / run
No tooling is configured yet because the project has no source code. Once code and a
manifest are added:
- Prefer installing dev tools into `.venv` and add them to a `requirements*.txt` or
  `pyproject.toml` so the update script picks them up automatically.
- Run tools through the venv, e.g. `.venv/bin/pytest`, `.venv/bin/ruff check`.
