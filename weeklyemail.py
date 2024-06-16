import os
import pickle
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from datetime import datetime, timedelta
import random
import pandas as pd
from google.oauth2 import service_account
import requests
from googleapiclient.discovery import build
from google.auth.transport.requests import AuthorizedSession, Request
from google_auth_oauthlib.flow import InstalledAppFlow

# Define scopes
SCOPES = ['https://www.googleapis.com/auth/photoslibrary', 'https://www.googleapis.com/auth/spreadsheets.readonly']

# Google Sheets ID and range
SPREADSHEET_ID = '1TwxovRJUFOn2m2a_zuQLd4zw_hAPP-jJjGMYlnBHmTA'
RANGE_NAME = 'Sheet1!A:B'

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
GSHEETS_PATH = os.path.join(BASE_DIR, 'gsheets.json')
CLIENT_SECRET_PATH = os.path.join(BASE_DIR, 'gphotos.json')
TOKEN_PATH = os.path.join(BASE_DIR, 'token.pickle')

def authenticate_google_sheets():
    creds = service_account.Credentials.from_service_account_file(GSHEETS_PATH, scopes=SCOPES)
    return creds

def authenticate_google_photos():
    creds = None
    if os.path.exists(TOKEN_PATH):
        with open(TOKEN_PATH, 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_PATH, SCOPES)
            flow.redirect_uri = "http://localhost:8080"
            creds = flow.run_local_server(port=8080)
        with open(TOKEN_PATH, 'wb') as token:
            pickle.dump(creds, token)
    return creds

def fetch_happy_reasons():
    creds = authenticate_google_sheets()
    service = build('sheets', 'v4', credentials=creds)
    sheet = service.spreadsheets()
    result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=RANGE_NAME).execute()
    values = result.get('values', [])

    if not values:
        print('No data found.')
        return []
    else:
        df = pd.DataFrame(values[1:], columns=values[0])
        df['Date'] = pd.to_datetime(df['Date'], format='%Y-%m-%d')
        one_week_ago = datetime.now() - timedelta(days=7)
        recent_df = df[df['Date'] >= one_week_ago]
        return recent_df['HappyReason'].tolist()

def fetch_random_photos():
    creds = authenticate_google_photos()
    authed_session = AuthorizedSession(creds)

    current_date = datetime.now()
    one_week_ago = current_date - timedelta(weeks=1)
    current_day = current_date.day
    current_month = current_date.month
    current_year = current_date.year
    week_ago_day = one_week_ago.day
    week_ago_month = one_week_ago.month
    week_ago_year = one_week_ago.year

    nextPageToken = None
    idx = 0
    media_items = []
    while True:
        idx += 1
        response = authed_session.post(
            'https://photoslibrary.googleapis.com/v1/mediaItems:search',
            headers={'content-type': 'application/json'},
            json={
                "pageSize": 100,
                "pageToken": nextPageToken,
                "filters": {
                    "dateFilter": {
                        "ranges": [{
                            "startDate": {
                                "year": week_ago_year,
                                "month": week_ago_month,
                                "day": week_ago_day,
                            },
                            "endDate": {
                                "year": current_year,
                                "month": current_month,
                                "day": current_day,
                            }
                        }]
                    },
                    "mediaTypeFilter": {
                        "mediaTypes": ["PHOTO"]
                    }
                }
            })

        response_json = response.json()
        media_items += response_json.get("mediaItems", [])

        if "nextPageToken" not in response_json:
            break

        nextPageToken = response_json["nextPageToken"]

    photos_df = pd.DataFrame(media_items)
    photos_df = pd.concat([photos_df, pd.json_normalize(photos_df.mediaMetadata).rename(columns={"creationTime": "creationTime_metadata"})], axis=1)
    photos_df["creationTime_metadata_dt"] = photos_df.creationTime_metadata

    photos_total = len(photos_df.index)
    random_indices = random.sample(range(photos_total), 5)
    images = []

    for i, idx in enumerate(random_indices):
        URL = str(photos_df.baseUrl[idx])
        response = requests.get(URL)
        image_path = f"WeeklyPics/image{i + 1}.png"
        image_path = os.path.join(BASE_DIR, image_path)
        with open(image_path, "wb") as img_file:
            img_file.write(response.content)
        images.append(image_path)

    return images

def send_email(message, images):
    msg = MIMEMultipart('related')
    msg['Subject'] = datetime.today().strftime('%Y-%m-%d') + ' Weekly Recap'
    msg['From'] = 'ekate331@gmail.com'
    msg['To'] = 'aeburton3@crimson.ua.edu'

    count = len(message)
    str_msg = ''.join([f"{i+1}. {m}\n" for i, m in enumerate(message)])
    email_message = f"It was an awesome week! You logged being happy {count} times. Here are all the reasons: {str_msg}"

    msg_alternative = MIMEMultipart('alternative')
    msg.attach(msg_alternative)

    text = email_message
    html = f"<html><body><p>{email_message}</p>"
    for i, image in enumerate(images):
        with open(image, 'rb') as img:
            mime_image = MIMEImage(img.read())
            mime_image.add_header('Content-ID', f'<image{i+1}>')
            msg.attach(mime_image)
        html += f'<br><img src="cid:image{i+1}"><br>'
    html += "</body></html>"

    part1 = MIMEText(text, 'plain')
    part2 = MIMEText(html, 'html')

    msg_alternative.attach(part1)
    msg_alternative.attach(part2)

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp_server:
        smtp_server.login("ekate331@gmail.com", "ugxf escp ohng fgro")
        smtp_server.sendmail("ekate331@gmail.com", 'aeburton3@crimson.ua.edu', msg.as_string())
        print("Message sent!")

message = fetch_happy_reasons()
images = fetch_random_photos()
send_email(message, images)
