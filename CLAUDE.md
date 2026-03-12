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

# Lint / format
ruff check .
ruff format --check .
ruff format .          # auto-fix formatting

# Database migrations
python manage.py migrate

# Sync Salesforce data to local DB
python manage.py sync_all             # run all syncs in dependency order (accounts → contacts → opportunities → adoptions)
python manage.py sync_accounts        # schools/institutions
python manage.py sync_books           # textbooks
python manage.py sync_contacts        # user contacts
python manage.py sync_opportunities   # opportunities
python manage.py sync_adoptions       # adoptions
python manage.py sync_accounts --force       # force full sync (marks missing records as soft-deleted)
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
1. **Sync commands** query Salesforce models → bulk `update_or_create()` into local `db` models
2. **API requests** read exclusively from local `db` models (no SF fallback)
3. **Contact lookup**: SSO cookie → `accounts_uuid` → local Contact → cache in Redis (15 min)
4. **Adoptions** are cached in Redis (1 hour) with key pattern `sfapi:adoptions{confirmed}:{assumed}:{contact_id}`
5. **SSO enrichment**: `/me` endpoint calls Accounts API directly (OAuth token + `/api/users?` query) for fields like `faculty_status`, `adopter_status`, `assignable_user`, `assignable_school_integrated`

### Sync Architecture
- **`sync_all`** is the primary sync command — runs `sync_accounts → sync_contacts → sync_opportunities → sync_adoptions` in dependency order with a single kill switch / API usage check at the top
- Individual sync commands support `--skip-usage-check` (used by `sync_all` to avoid redundant checks)
- `sync_books` runs independently (weekly) since books have no FK dependencies
- All sync commands use `.only(*SF_ONLY_FIELDS)` to minimize SOQL field selection
- Incremental syncs use a 2-hour lookback buffer from the latest `last_modified_date`

### SF API Usage Monitoring (`sf/api_usage.py`)
- **`track_sf_calls(source)`**: Context manager that counts SF queries via Django's `execute_wrapper`. Stack-based to support nesting without double-counting. Logs counts to `SFAPIUsageLog`.
- **`get_sf_api_usage()`**: Hits the SF REST `/limits/` endpoint to get org-wide daily API usage (used, limit).
- **`should_sync()`**: Checks the admin kill switch (`SyncConfig.sync_enabled`) and API usage threshold before allowing syncs to proceed.
- **`SyncConfig`** (singleton model): Admin-configurable kill switch + pause threshold (default 85% of 285k limit)
- **`SFAPIUsageLog`**: Daily per-source call counts (e.g., `sync_accounts`, `api_case_create`, `limits_check`)

### Authentication
- `combined_auth` (`api/auth.py`): Accepts either SSO cookie or API key (Bearer token). Used on all authenticated endpoints.
  - `SSOAuth`: Validates OpenStax Accounts SSO cookie via `get_logged_in_user_uuid()`
  - `ServiceAuth`: Validates API keys (model `APIKey` with hashed keys + scoped permissions)
- `has_scope(request, scope)`: Checks if the authenticated request has a specific permission scope (e.g., `read:books`, `write:cases`)
- **OpenStax Accounts** (`openstax_accounts` v1.1.2): Provides `decrypt_cookie`, `get_logged_in_user_uuid`, `get_token`. The `/me` endpoint calls the Accounts API directly for enrichment fields (`salesforce_contact_id`, `faculty_status`, etc.).

### Scheduled Jobs (django_crontab)
- `sync_all` — daily at 5:00 AM (accounts → contacts → opportunities → adoptions)
- `sync_books` — weekly Saturday at 11:45 PM
- `cleanup_logs` — weekly Sunday at 3:00 AM

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
