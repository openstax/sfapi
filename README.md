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
SALESFORCE_CLIENT_SECRET=<your_client
SALESFORCE_USERNAME=<your_username>
SALESFORCE_PASSWORD=<your_password>
SALESFORCE_SECURITY_TOKEN=<your_security_token>
SSO_COOKIE_NAME="<oxa_env>"
SSO_SIGNATURE_PUBLIC_KEY="<public_key_for_accounts>"
SSO_ENCRYPTION_PRIVATE_KEY="<private_key_for_accounts>"
SENTRY_DSN="<sentry_dsn>" # not required and will cause a lot of noise in Sentry
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
python manage.py create_api_key --name="my-key-name" --scopes="read:books,write:cases"
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

#### Rate Limiting
The API is rate limited to prevent abuse. The rate limit is currently set at **5 requests per minute, per user**.\
If a user exceeds the rate limit, they will receive a 429 status code and a message indicating that they have exceeded the rate limit.\
This can be modified in `api/api_v1.py` by changing the `SalesforceAPIRateThrottle` class.

#### Error Handling
The API uses standard HTTP status codes to indicate the success or failure of a request.\
The API also returns a JSON object with a `message` key to provide more information about the error.\
A non-logged in user will receive a 401 status code and a message indicating that they need to log in.

### Deployment
SFAPI is deployed using [bit-deployment](https://github.com/openstax/bit-deployment).
