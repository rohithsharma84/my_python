# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

A collection of small Python demos and learning projects — not a single packaged library. Each sub-project is a standalone script or app.

## Running Projects

**Calculator CLI**
```
python calculator-cli/calculator.py
```

**Pygame Zero game** (requires `pgzero` and `pygame`)
```
pgzrun game-shoot-the-fruit/shoot.py
```

**Example scripts under `tests/`** (many are demos, not strict unit tests)
```
python -m pytest tests/ -q
python -m pytest tests\test_lists.py -q
python -m pytest tests\file.py::test_name -q
```

**Customer Orders** (course-end project for Python Refresher with AI)
```
python customer-orders/main.py
```

**Django demo app** (requires `django`; navigate into the project first)
```
cd tests\test-django\mywebsite
python manage.py runserver
python manage.py test
```

## Architecture

- **`game-shoot-the-fruit/`** — Pygame Zero event-handler pattern (`draw`, `update`, `on_mouse_down`). Global mutable game state; assets in `images/` and `sounds/`.
- **`tests/test-django/mywebsite/`** — Django 6.0.5 app with a single `bank` app. Uses request sessions for state (no database models for accounts). Templates live in `bank/templates/bank/`.
- **`tests/`** — Standalone scripts covering OOP (`test-class.py`), list manipulation, web scraping (BeautifulSoup4), and a Jupyter notebook. Filenames use hyphens (`test-webScraping.py`), which requires quoting on some shells.
- **`calculator-cli/`** — Single-file CLI script with an infinite input loop.
- **`customer-orders/`** — Course-end project for Python Refresher with AI. Manages customer order data using core Python concepts.

## Key Notes

- No repo-level `requirements.txt` or `pyproject.toml`. Dependencies (pgzero, bs4, django) must be installed manually per demo.
- No linter configured.
- Filenames with hyphens (e.g., `test-webScraping.py`) are not importable as Python modules; run them directly with `python`.
- The Pygame Zero demo cannot be run via pytest — it requires the `pgzrun` launcher.
