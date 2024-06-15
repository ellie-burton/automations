import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from datetime import datetime, timedelta
import os
import random
import pandas as pd
from google.oauth2 import service_account
import requests
from googleapiclient.discovery import build
from google.auth.transport.requests import AuthorizedSession
from google_auth_oauthlib.flow import InstalledAppFlow

# Define scopes
SCOPES = ['https://www.googleapis.com/auth/photoslibrary', 'https://www.googleapis.com/auth/spreadsheets.readonly']

# Google Sheets ID and range
SPREADSHEET_ID = '1TwxovRJUFOn2m2a_zuQLd4zw_hAPP-jJjGMYlnBHmTA'  
RANGE_NAME = 'Sheet1!A:B'  

def fetch_happy_reasons():
    creds = service_account.Credentials.from_service_account_file('token.json', scopes=SCOPES)
    
    service = build('sheets', 'v4', credentials=creds)
    sheet = service.spreadsheets()
    result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=RANGE_NAME).execute()
    values = result.get('values', [])
    
    if not values:
        print('No data found.')
        return []
    else:
        # Convert the data to a DataFrame for easier manipulation
        df = pd.DataFrame(values[1:], columns=values[0])  # Skip the header row
        df['Date'] = pd.to_datetime(df['Date'], format='%m/%d/%Y')  # Adjust the format if necessary

        # Filter rows for the last 7 days
        one_week_ago = datetime.now() - timedelta(days=7)
        recent_df = df[df['Date'] >= one_week_ago]

        return recent_df['HappyReason'].tolist()

def fetch_random_photos():
    scopes=['https://www.googleapis.com/auth/photoslibrary']

    creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'client-secret.json', scopes)
            creds = flow.run_local_server()

    authed_session = AuthorizedSession(creds)

    # Get current date
    current_date = datetime.now()

    # Get one week ago
    one_week_ago = current_date - timedelta(weeks=1)

    # Extract day, month, and year from the current date
    current_day = current_date.day
    current_month = current_date.month
    current_year = current_date.year

    # Extract day, month, and year from one week ago
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
            headers = { 'content-type': 'application/json' },
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
        "mediaTypes": [
            "PHOTO"
        ]
        }
                }
            })
        
        response_json = response.json()
        media_items += response_json["mediaItems"]
        
        if not "nextPageToken" in response_json:
            break
            
        nextPageToken = response_json["nextPageToken"]

    photos_df = pd.DataFrame(media_items)
    photos_df = pd.concat([photos_df, pd.json_normalize(photos_df.mediaMetadata).rename(columns={"creationTime": "creationTime_metadata"})], axis=1)
    photos_df["creationTime_metadata_dt"] = photos_df.creationTime_metadata

    photos_total=len(photos_df.index)
    random_indices = random.sample(range(photos_total), 5)
    images = []

    for i, idx in enumerate(random_indices):
        URL = str(photos_df.baseUrl[idx])
        response = requests.get(URL)
        image_path = f"image{i + 1}.png"
        with open(image_path, "wb") as img_file:
            img_file.write(response.content)
        images.append(image_path)

    return images

def send_email(message, images):
    msg = MIMEMultipart('related')
    msg['Subject'] = datetime.today().strftime('%Y-%m-%d') + ' Weekly Recap'
    msg['From'] = 'ekate331@gmail.com'
    msg['To'] = 'aeburton3@crimson.ua.edu'

    email_message = ', '.join(message)
    email_message = "It was an awesome week! Here are all the reasons you were happy: " + email_message

    # Create the body with both plain text and HTML parts
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

    # Attach parts into message container.
    part1 = MIMEText(text, 'plain')
    part2 = MIMEText(html, 'html')

    msg_alternative.attach(part1)
    msg_alternative.attach(part2)

    # Send the message via an SMTP server.
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp_server:
        smtp_server.login("ekate331@gmail.com", "ugxf escp ohng fgro")
        smtp_server.sendmail("ekate331@gmail.com", 'aeburton3@crimson.ua.edu', msg.as_string())
        print("Message sent!")

# Example usage

message = fetch_happy_reasons()
images = fetch_random_photos()
send_email(message, images)
