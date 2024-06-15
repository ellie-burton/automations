import os
from datetime import datetime
from google.oauth2 import service_account
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# Define scopes
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

# Google Sheets ID and range
SPREADSHEET_ID = '1TwxovRJUFOn2m2a_zuQLd4zw_hAPP-jJjGMYlnBHmTA'
RANGE_NAME = 'Sheet1!A:B'  # Adjust range as necessary

def authenticate_google_sheets():
    creds = None
    if os.path.exists('token.json'):
        creds = service_account.Credentials.from_service_account_file('token.json', scopes=SCOPES)
    else:
        flow = InstalledAppFlow.from_client_secrets_file('client_secret.json', SCOPES)
        creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    
    return creds

def get_user_input():
    happy_reason = input("Enter a reason you were happy today: ")
    current_date = datetime.now().strftime('%Y-%m-%d')
    return current_date, happy_reason

def write_to_google_sheets(data):
    creds = authenticate_google_sheets()
    service = build('sheets', 'v4', credentials=creds)
    sheet = service.spreadsheets()

    body = {
        "values": data
    }

    result = sheet.values().append(
        spreadsheetId=SPREADSHEET_ID, 
        range=RANGE_NAME,
        valueInputOption="RAW",
        body=body
    ).execute()

    print(f"{result.get('updates').get('updatedCells')} cells updated.")

date, happy_reason = get_user_input()
data = [[date, happy_reason]]
write_to_google_sheets(data)
