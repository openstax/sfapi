# OpenStax Salesforce API
This repo contains the OpenStax Salesforce API. It is a RESTful API that provides access to Salesforce data and functionality.

## Getting Started
To get started, you will need to have a Salesforce account and a connected app. You will also need to have a user account with the appropriate permissions to access the data you need.

### Prerequisites
- Salesforce account
- Connected app
- User account with appropriate permissions
- Python 3.6 or later
- Virtualenv (optional but highly recommended)

### Installation
1. Clone the repo
```sh
git clone https://github.com/openstax/sfapi
```
2. Install the required packages (in a virtual environment)
```sh
mkvirtualenv sfapi
pip install -r requirements.txt
```
3. Create a `.env` file in the root of the project and add the following environment variables:
```sh
SALESFORCE_CLIENT_ID=<your_client_id>
SALESFORCE_CLIENT_SECRET=<your_client
SALESFORCE_USERNAME=<your_username>
SALESFORCE_PASSWORD=<your_password>
SALESFORCE_SECURITY_TOKEN=<your_security_token>
```
4. Run the server
```sh
python manage.py runserver
```
