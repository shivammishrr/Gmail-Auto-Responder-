import os
import time
import random
import json
import base64
from email.mime.text import MIMEText
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# Set up the Gmail API credentials
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']
TOKEN_FILE = 'token.json'
CREDENTIALS_FILE = 'credentials.json'

def get_gmail_service():
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
    
    return build('gmail', 'v1', credentials=creds)

def check_for_new_emails(service, user_id='me'):
    response = service.users().messages().list(userId=user_id, q='is:unread').execute()
    messages = response.get('messages', [])
    return messages

def mark_email_as_replied(service, email_id, label_id):
    message = service.users().messages().modify(userId='me', id=email_id, body={'addLabelIds': [label_id]}).execute()
    return message

def reply_to_email(service, email_id, message_text):
    # Get the email address of the sender of the original email
    email_info = service.users().messages().get(userId='me', id=email_id).execute()
    headers = email_info['payload']['headers']
    sender = next(header['value'] for header in headers if header['name'] == 'From')

    # Create the reply message
    message = MIMEText(message_text)
    message['to'] = sender
    message['subject'] = 'Re: Vacation Auto-Responder'
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

    # Send the reply
    response = service.users().messages().send(
        userId='me',
        body={'raw': raw_message}
    ).execute()

    return response


def create_message(sender, recipient, subject, message_text):
    message = MIMEText(message_text)
    message['to'] = recipient
    message['from'] = sender
    message['subject'] = subject
    return {'raw': base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')}

def main():
    gmail_id = 'shivammishrrr@gmail.com'
    label_name = 'Vacation Auto-Responder'
    message_text = 'Thank you for your email. I am currently on vacation and will respond to your message when I return. Best regards, Shivam'
    
    service = get_gmail_service()
    
    # Create the label if it doesn't exist
    labels = service.users().labels().list(userId='me').execute().get('labels', [])
    label_id = None
    for label in labels:
        if label['name'] == label_name:
            label_id = label['id']
            break
    if not label_id:
        label = {'name': label_name, 'labelListVisibility': 'labelShow'}
        label = service.users().labels().create(userId='me', body=label).execute()
        label_id = label['id']
    
    while True:
        new_emails = check_for_new_emails(service)
        for email in new_emails:
            email_info = service.users().messages().get(userId='me', id=email['id']).execute()
            headers = email_info['payload']['headers']
            subject = [header['value'] for header in headers if header['name'] == 'Subject']
            reply_info = service.users().messages().list(userId='me', q='in:Sent subject:"{}"'.format(subject)).execute()
            
            if 'messages' not in reply_info or len(reply_info['messages']) == 0:
                reply_to_email(service, email['id'], message_text)
                mark_email_as_replied(service, email['id'], label_id)
        
        # Sleep for random interval between 45 and 120 seconds
        interval = random.randint(45, 120)
        time.sleep(interval)

if __name__ == '__main__':
    main()
