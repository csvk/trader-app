import json
from constants import defs

class ApiCreds():
    API_CREDS_FILE = defs.API_CREDS_FILE

    # Load API credentials
    with open(API_CREDS_FILE) as json_file:
        apicreds = json.load(json_file)

    API_KEY = apicreds['API_KEY']
    ACCOUNT_ID = apicreds['ACCOUNT_ID']
    OANDA_URL = apicreds['OANDA_URL']

    SECURE_HEADER = {
        'Authorization': f'Bearer {API_KEY}'
}