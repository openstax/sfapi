# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SFAPI is a Django-based REST API that bridges Salesforce and OpenStax systems. It caches Salesforce data (schools, contacts, books, adoptions) in a local PostgreSQL database and serves it via django-ninja endpoints. Authentication is cookie-based via OpenStax Accounts SSO.

## Common Commands

```bash
# Run dev server (auto-sets DEBUG=True, uses dummy cache)
python manage.py runserver

# Run dev server with SQL query logging
python manage.py runserver_plus

# Run tests (requires local PostgreSQL and Redis)
coverage run --source='.' manage.py test --settings=sfapi.settings.test
coverage report

# Run a single test
python manage.py test api.tests.TestClassName --settings=sfapi.settings.test

# Database migrations
python manage.py migrate

# Sync Salesforce data to local DB
python manage.py sync_accounts        # schools/institutions
python manage.py sync_books           # textbooks
python manage.py sync_contacts        # user contacts (currently disabled in cron)
python manage.py sync_accounts --force       # force full sync
python manage.py sync_accounts --forcedelete # reset and resync
```

## Architecture

### Dual Database Design
- **`default` (PostgreSQL)**: Local cache of Salesforce data, served to API consumers
- **`salesforce`**: Direct Salesforce ORM connection via `django-salesforce-agpl`, used for syncing and fallback lookups
- `salesforce.router.ModelRouter` routes queries to the correct database based on model type

### App Structure
- **`api/`** — django-ninja REST endpoints and response schemas (`api_v1.py`, `schemas.py`). API docs at `/api/v1/docs/`
- **`db/`** — Local PostgreSQL models (Account, Book, Contact, Opportunity, Adoption) that mirror Salesforce objects
- **`sf/`** — Salesforce ORM models (`sf/models/`) and management commands for data sync (`sf/management/commands/`)
- **`users/`** — Custom Django user model with OpenStax Accounts integration
- **`sfapi/`** — Django project config. Settings in `sfapi/settings/base.py` with optional `local.py` override

### Key Data Flow
1. **Sync commands** query Salesforce models → `update_or_create()` into local `db` models
2. **API requests** read from local `db` models first, falling back to Salesforce if not cached
3. **Contact lookup**: SSO cookie → `accounts_uuid` → local Contact → fallback to SF Contact → cache locally
4. **Adoptions** are cached in Redis (1 hour) with key pattern `sfapi:adoptions{confirmed}:{assumed}:{contact_id}`

### Authentication
- `has_auth`: Checks OpenStax Accounts SSO cookie via `get_logged_in_user_uuid()`
- `has_super_auth`: Restricts to hardcoded UUID list in `settings.SUPER_USERS` (books, cases endpoints)
- In test mode (`IS_TESTING=True`), auth is bypassed

### Environment Detection
Settings auto-detect environment from CLI args: `test` in argv → test mode, `runserver` in argv → local mode. The `ENVIRONMENT` env var controls deployed environments (dev, staging, prod). Local mode uses dummy cache (no Redis needed).

### API Versioning
All v1 endpoints live in `api/api_v1.py`. Breaking changes require a new `api_v2.py` — never exceed `1.x.x` in the existing file.

## Test Configuration

Tests use `sfapi.settings.test` which:
- Points both `default` and `salesforce` databases to local PostgreSQL (db: `sfapi`, user: `sfapi`)
- Requires Redis at `127.0.0.1:6379`
- Sets `SALESFORCE_DB_ALIAS = 'default'` so SF models query the local DB
- CI runs on GitHub Actions with PostgreSQL 14 and Redis services
