import os
import logging
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import json
import base64
from email.mime.text import MIMEText
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Define scopes needed for Gmail, Calendar, and Drive
SCOPES = [
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/drive'
]

# Service instances
gmail_service = None
calendar_service = None
drive_service = None

def initialize_google_services():
    """Initialize Google API services."""
    try:
        global gmail_service, calendar_service, drive_service
        
        # Check for credentials in environment
        client_id = os.environ.get("GOOGLE_CLIENT_ID")
        client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")
        
        if not client_id or not client_secret:
            logger.warning("Google API credentials not found in environment variables")
            return False
        
        # Initialize services (actual authentication happens per user)
        logger.info("Initializing Google API services")
        
        return True
    except Exception as e:
        logger.error(f"Error initializing Google services: {e}")
        raise

def get_user_credentials(user):
    """Get Google API credentials for a specific user."""
    try:
        if not user.google_credentials:
            logger.warning(f"No Google credentials found for user {user.id}")
            return None
        
        # Parse stored credentials
        creds_data = json.loads(user.google_credentials)
        creds = Credentials(
            token=creds_data.get('token'),
            refresh_token=creds_data.get('refresh_token'),
            token_uri=creds_data.get('token_uri', 'https://oauth2.googleapis.com/token'),
            client_id=os.environ.get("GOOGLE_CLIENT_ID"),
            client_secret=os.environ.get("GOOGLE_CLIENT_SECRET"),
            scopes=creds_data.get('scopes', SCOPES)
        )
        
        # Check if credentials are expired and refresh if possible
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            
            # Update stored credentials
            user.google_credentials = json.dumps({
                'token': creds.token,
                'refresh_token': creds.refresh_token,
                'token_uri': creds.token_uri,
                'client_id': creds.client_id,
                'client_secret': creds.client_secret,
                'scopes': creds.scopes
            })
            
            from app import db
            db.session.commit()
        
        return creds
    except Exception as e:
        logger.error(f"Error getting user credentials: {e}")
        return None

# Gmail Functions
def get_gmail_service(user):
    """Get Gmail API service for a specific user."""
    creds = get_user_credentials(user)
    if not creds:
        return None
    
    return build('gmail', 'v1', credentials=creds)

def list_messages(user, query="", max_results=10):
    """List Gmail messages for a user, with optional query."""
    service = get_gmail_service(user)
    if not service:
        return "Error: Gmail service not available"
    
    try:
        results = service.users().messages().list(
            userId='me', q=query, maxResults=max_results
        ).execute()
        
        messages = results.get('messages', [])
        
        if not messages:
            return "No messages found."
        
        message_list = []
        for msg in messages:
            message = service.users().messages().get(
                userId='me', id=msg['id'], format='metadata'
            ).execute()
            
            headers = {header['name']: header['value'] for header in message['payload']['headers']}
            
            message_list.append({
                'id': msg['id'],
                'snippet': message['snippet'],
                'from': headers.get('From', 'Unknown Sender'),
                'subject': headers.get('Subject', '(No Subject)'),
                'date': headers.get('Date', '')
            })
        
        return message_list
    except HttpError as error:
        logger.error(f"Error accessing Gmail: {error}")
        return f"Error accessing Gmail: {error}"

def send_email(user, to, subject, body):
    """Send an email using Gmail API."""
    service = get_gmail_service(user)
    if not service:
        return "Error: Gmail service not available"
    
    try:
        message = MIMEText(body)
        message['to'] = to
        message['subject'] = subject
        
        # Encode message
        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        
        # Send message
        send_message = service.users().messages().send(
            userId='me', body={'raw': encoded_message}
        ).execute()
        
        return f"Email sent successfully. Message ID: {send_message['id']}"
    except HttpError as error:
        logger.error(f"Error sending email: {error}")
        return f"Error sending email: {error}"

# Calendar Functions
def get_calendar_service(user):
    """Get Google Calendar API service for a specific user."""
    creds = get_user_credentials(user)
    if not creds:
        return None
    
    return build('calendar', 'v3', credentials=creds)

def list_events(user, time_min=None, time_max=None, max_results=10):
    """List Calendar events for a user."""
    service = get_calendar_service(user)
    if not service:
        return "Error: Calendar service not available"
    
    try:
        # Default to today if no time range specified
        if not time_min:
            time_min = datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
        if not time_max:
            time_max = (datetime.utcnow() + timedelta(days=7)).isoformat() + 'Z'
        
        events_result = service.events().list(
            calendarId='primary', timeMin=time_min, timeMax=time_max,
            maxResults=max_results, singleEvents=True, orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        if not events:
            return "No upcoming events found."
        
        event_list = []
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            event_list.append({
                'id': event['id'],
                'summary': event.get('summary', '(No Title)'),
                'start': start,
                'end': event['end'].get('dateTime', event['end'].get('date')),
                'location': event.get('location', ''),
                'description': event.get('description', '')
            })
        
        return event_list
    except HttpError as error:
        logger.error(f"Error accessing Calendar: {error}")
        return f"Error accessing Calendar: {error}"

def create_event(user, summary, start_time, end_time, description="", location=""):
    """Create a new calendar event."""
    service = get_calendar_service(user)
    if not service:
        return "Error: Calendar service not available"
    
    try:
        event = {
            'summary': summary,
            'location': location,
            'description': description,
            'start': {
                'dateTime': start_time,
                'timeZone': 'UTC',
            },
            'end': {
                'dateTime': end_time,
                'timeZone': 'UTC',
            },
        }
        
        event = service.events().insert(calendarId='primary', body=event).execute()
        return f"Event created: {event.get('htmlLink')}"
    except HttpError as error:
        logger.error(f"Error creating calendar event: {error}")
        return f"Error creating calendar event: {error}"

# Drive Functions
def get_drive_service(user):
    """Get Google Drive API service for a specific user."""
    creds = get_user_credentials(user)
    if not creds:
        return None
    
    return build('drive', 'v3', credentials=creds)

def list_files(user, query="", max_results=10):
    """List Drive files for a user, with optional query."""
    service = get_drive_service(user)
    if not service:
        return "Error: Drive service not available"
    
    try:
        results = service.files().list(
            q=query, pageSize=max_results, fields="files(id, name, mimeType, createdTime)"
        ).execute()
        
        items = results.get('files', [])
        
        if not items:
            return "No files found."
        
        file_list = []
        for item in items:
            file_list.append({
                'id': item['id'],
                'name': item['name'],
                'mimeType': item['mimeType'],
                'createdTime': item['createdTime']
            })
        
        return file_list
    except HttpError as error:
        logger.error(f"Error accessing Drive: {error}")
        return f"Error accessing Drive: {error}"

def create_file(user, name, mime_type, content=""):
    """Create a new file in Google Drive."""
    service = get_drive_service(user)
    if not service:
        return "Error: Drive service not available"
    
    try:
        from googleapiclient.http import MediaInMemoryUpload
        
        file_metadata = {
            'name': name,
            'mimeType': mime_type
        }
        
        media = MediaInMemoryUpload(content.encode(), mimetype=mime_type)
        
        file = service.files().create(
            body=file_metadata, media_body=media, fields='id, name, webViewLink'
        ).execute()
        
        return {
            'id': file.get('id'),
            'name': file.get('name'),
            'link': file.get('webViewLink')
        }
    except HttpError as error:
        logger.error(f"Error creating file: {error}")
        return f"Error creating file: {error}"

def share_file(user, file_id, email, role='reader'):
    """Share a Google Drive file with another user."""
    service = get_drive_service(user)
    if not service:
        return "Error: Drive service not available"
    
    try:
        # Create permission
        permission = {
            'type': 'user',
            'role': role,  # 'reader', 'writer', 'commenter'
            'emailAddress': email
        }
        
        # Add permission to the file
        result = service.permissions().create(
            fileId=file_id, body=permission, fields='id'
        ).execute()
        
        return f"File shared successfully with {email}"
    except HttpError as error:
        logger.error(f"Error sharing file: {error}")
        return f"Error sharing file: {error}"
