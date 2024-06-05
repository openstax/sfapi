from sf.connection import Salesforce

FIELDS = ['Id', 'Name', 'Type']

def get_accounts():
    with Salesforce() as sf:
        accounts = sf.query(f"SELECT {', '.join(FIELDS)} FROM Account")['records']

        response = []
        for account in accounts:
            response.append({
                'id': account['Id'],
                'name': account['Name'],
                'type': account['Type']
            })
        return response
