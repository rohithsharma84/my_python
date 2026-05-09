# Copilot instructions for my_python

Purpose: help future Copilot sessions navigate and act in this repository.

---

1) Build, test, and lint commands

- No repository-level build or CI workflows detected in .github/
- Tests: many small example scripts live under `tests/`. They can be executed with pytest or directly.
  - Run full test collection: python -m pytest tests/ -q
  - Run a single test file: python -m pytest tests\test_lists.py -q
  - Run a single test function (if present): python -m pytest tests\file.py::test_name -q
- Game (Pygame Zero): game-shoot-the-fruit/shoot.py
  - Run with pgzero/pgzrun: pgzrun game-shoot-the-fruit\shoot.py  (requires pgzero/pygame)
- Django toy app: tests/test-django/mywebsite is a local demo Django project.
  - Run Django tests from that folder: cd tests\test-django\mywebsite && python manage.py test
- Linting: no linter or config detected. No automatic lint command observed.

---

2) High-level architecture (big picture)

- This repository is a collection of small Python examples and demos (not a single packaged library).
- Top-level notable items:
  - game-shoot-the-fruit/: a Pygame Zero (pgzero) based demo game.
  - tests/: assorted example scripts and demos; includes a small Django app under tests/test-django/mywebsite. Many "tests" are plain Python scripts used for demonstration rather than strict unit tests.
- No src/ package layout or pyproject/setup configuration was detected; code is runnable as standalone scripts.

---

3) Key conventions and repo-specific notes

- "tests/" contains runnable example scripts (often named test-*.py) that may not follow pytest's assert-based style; treat them as examples or entry points.
- Filenames sometimes use hyphens (e.g., test-webScraping.py). When invoking from the shell, use the path with backslashes on Windows.
- The Django demo includes a SQLite DB and templates under tests/test-django — running those tests may require installing Django and any imports used by the example views.
- The Pygame Zero demo depends on the pgzero/pygame runtime; it's not runnable via pytest and should be launched with pgzrun or by running the module under an environment with the appropriate runtime.
- No repository-level dependency manifest (requirements.txt, pyproject.toml, Pipfile) or linter config detected. Installing dependencies is manual and per-demo.

---

Other assistant-related files checked

- No CLAUDE.md, AGENTS.md, .cursorrules, .windsurfrules, CONVENTIONS.md, or other AI-assistant config files were found in the repo root or expected locations.

---

If an automated test/CI matrix or dependency manifest is added later (pyproject.toml, requirements.txt, tox.ini, GitHub Actions workflows), include the canonical install and test commands in this file so Copilot can run them automatically.

