[![OpenStax](https://img.shields.io/badge/OpenStax-Salesforce-00A6C9?style=for-the-badge&logo=openstax&logoColor=white)](https://openstax.lightning.force.com/one/one.app)\
[![codecov](https://codecov.io/gh/openstax/sfapi/graph/badge.svg?token=lEbEFIOfIR)](https://codecov.io/gh/openstax/sfapi)
![tests workflow](https://github.com/openstax/sfapi/actions/workflows/tests.yml/badge.svg)
![AWS CodeBuild](https://codebuild.us-east-1.amazonaws.com/badges?uuid=eyJlbmNyeXB0ZWREYXRhIjoiTUhjbUx0VUtYR0ZZb3RRUEQ2QzJENHZNUXhveWVwb3FvRDl4K2VQTGZHblpQSm1oakwwQU1laW13YWwrWUh6Y2RGdG8vNTBqSG5Ia2NSTExHOHprZXo0PSIsIml2UGFyYW1ldGVyU3BlYyI6ImZ0UTZWSVZZNWw2QmUydVEiLCJtYXRlcmlhbFNldFNlcmlhbCI6MX0%3D&branch=main)
![](https://img.shields.io/github/v/tag/openstax/sfapi?label=latest%20tag)

# OpenStax Salesforce API
## Getting Started
To get started, you will need to have a Salesforce account and a connected app.\
You will also need to have an OpenStax user account with a matching Salesforce Contact in the environment you are using.

### Prerequisites
- Salesforce account
- Salesforce connected app with the following permissions:
  - Access and manage your data (api)
  - Perform requests on your behalf at any time (refresh_token, offline_access)
  - Full access (full)
- OpenStax user account or locally running accounts server
- User account with appropriate permissions
- Python 3.11 or later
- Virtualenv (optional but highly recommended)

### Installation
1. Clone the repo
```sh
git clone https://github.com/openstax/sfapi
```
2. Install the required packages (in a virtual environment)
```sh
mkvirtualenv sfapi
pip install -r requirements/dev.txt
```
3. Create a `.env` file in the root of the project and add the following environment variables:
```sh
SALESFORCE_CLIENT_ID=<your_client_id>
SALESFORCE_CLIENT_SECRET=<your_client_secret>
SALESFORCE_USERNAME=<your_username>
SALESFORCE_PASSWORD=<your_password>
SALESFORCE_SECURITY_TOKEN=<your_security_token>
SSO_COOKIE_NAME="<oxa_env>"
SSO_SIGNATURE_PUBLIC_KEY="<public_key_for_accounts>"
SSO_ENCRYPTION_PRIVATE_KEY="<private_key_for_accounts>"
SENTRY_DSN="<sentry_dsn>" # not required and will cause a lot of noise in Sentry

# Accounts API (for user lookups — salesforce_contact_id, faculty_status, etc.)
ACCOUNTS_URL="https://dev.accounts.openstax.org"  # or http://localhost:2999 for local
ACCOUNTS_CLIENT_ID="<oauth_client_id>"
ACCOUNTS_CLIENT_SECRET="<oauth_client_secret>"

# Local dev only — bypass SSO cookie validation and authenticate as this UUID
DEV_USER_UUID="<your_accounts_uuid>"
```
4. Run the server
```sh
python manage.py runserver
```

## Usage
#### Endpoint Documentation
The API is a RESTful API that provides access to Salesforce data and functionality. It is designed to be easy to use and understand. 
The API is documented using OpenAPI and can be accessed at `/api/v1/docs/`.

The API is versioned and the version is specified in the URL. The current version is `v1`.\
**Any changes to the API that are not backwards compatible should result in a new version being created.**

#### Authentication
The API supports two authentication methods:

**1. SSO Cookie** — Users logged in to OpenStax Accounts are authenticated automatically via the `oxa` cookie.

**2. API Key** — For service-to-service access, use a Bearer token in the `Authorization` header.

To create an API key with all scopes:
```sh
python manage.py create_api_key --name="my-key-name" --scopes="read:books,read:info,write:cases"
```

Then use it in requests:
```sh
curl -H "Authorization: Bearer <your-api-key>" http://localhost:8000/api/v1/books
```

Available scopes:
- `read:books` — required for `GET /api/v1/books`
- `read:info` — required for `GET /api/v1/info`
- `write:cases` — required for `POST /api/v1/case`

Endpoints like `/contact` and `/adoptions` require authentication but no specific scope. The `/schools` endpoint is public.

Super users (SSO users with all scopes) are managed via the Django admin under **Super Users**.

#### Local Development

For local development, you can bypass SSO cookie validation entirely by setting `DEV_USER_UUID` in your `.env` to your OpenStax Accounts UUID. This removes the need to run Accounts locally or deal with cookie domain/crypto issues. This only works when `DEBUG=True` (i.e., `runserver`).

#### Debugging

**`GET /api/v1/me`** — Public endpoint that shows your current authentication status. When logged in, enriches the response with data from the Accounts API:
- `salesforce_contact_id`, `faculty_status`, `adopter_status`
- `self_reported_role`, `school_type`, `school_location`
- `assignable_user`, `assignable_school_integrated` — flags for personalizing the Assignable journey

When not logged in, includes a `debug` section with diagnostics:
- Whether the SSO cookie is present
- Whether the signature and encryption keys are configured
- Step-by-step decryption/verification results to pinpoint failures

**`GET /api/v1/info`** (requires `read:info` scope) — Admin endpoint that shows system status including:
- `sso_config` — SSO cookie configuration: cookie name, key presence, key types, and whether the dev bypass is active
- `accounts_api` — Accounts API connection status: whether OAuth credentials are configured and if token retrieval succeeds
- `api_usage` — Current Salesforce API usage (from SF `/limits/` endpoint)
- `release_information` — Version and environment details

#### Data Sync & API Usage Monitoring

Salesforce data is synced to a local PostgreSQL cache via management commands. The primary command is `sync_all`, which runs all interdependent syncs in dependency order:

```sh
python manage.py sync_all              # accounts → contacts → opportunities → adoptions
python manage.py sync_all --force      # force full sync of all objects
python manage.py sync_books            # books sync independently (no FK dependencies)
```

**Kill switch & API usage threshold**: Syncs can be paused via the Django admin (`SyncConfig`). If daily SF API usage exceeds the configured threshold (default 85% of 285k), syncs are automatically skipped. API call counts are tracked per-source per-day in the admin (`SF API Usage Log`).

Scheduled jobs (via `django_crontab`):
- `sync_all` — daily at 5:00 AM
- `sync_books` — weekly Saturday at 11:45 PM
- `cleanup_logs` — weekly Sunday at 3:00 AM

#### Rate Limiting
The API is rate limited to prevent abuse. The rate limit is currently set at **5 requests per minute, per user**.\
If a user exceeds the rate limit, they will receive a 429 status code and a message indicating that they have exceeded the rate limit.\
This can be modified in `api/api_v1.py` by changing the `SalesforceAPIRateThrottle` class.

#### Error Handling
The API uses standard HTTP status codes to indicate the success or failure of a request.\
The API also returns a JSON object with a `message` key to provide more information about the error.\
A non-logged in user will receive a 401 status code and a message indicating that they need to log in.

#### Pardot Data Health Dashboard (Camp Campaign)

The `pardot` app provides a marketing data health tracker for Pardot/Account Engagement. It syncs marketing assets (campaigns, forms, landing pages, emails, etc.) and Salesforce health metrics into local tables, computes a health scorecard, and serves a camp-themed dashboard.

**Dashboard**: `https://<host>/pardot/` (requires SSO login + SuperUser status)

**API**: 29 JSON endpoints under `/api/v1/pardot/` — briefing, engagement, assets, campaigns, health-score, issues, tasks, etc.

**Sync commands**:
```sh
python manage.py camp_sync              # Tier 1: assets + SF health (~20 API calls)
python manage.py camp_sync --scout      # Tier 2: + top 500 prospects
python manage.py camp_sync --survey     # Tier 3: full prospect + activity sync
python manage.py camp_sync --entities forms,lists   # Selective sync
```

**Configuration**: Team roster, demerit weights, grade thresholds, and issue templates are managed via Django admin at `/admin/pardot/`.

Pardot API v5 auth reuses the existing Salesforce database connection. The only additional `.env` variable needed:
```sh
SALESFORCE_PARDOT_BUSINESS_UNIT=<Pardot Business Unit ID>
```

### Deployment
SFAPI is deployed using [bit-deployment](https://github.com/openstax/bit-deployment).
