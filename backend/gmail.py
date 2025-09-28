import os
import base64
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import json

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Add Firebase and Summarizer imports
from firebase_db import FirebaseEmailDB
from email_summarizer import EmailSummarizer

class GmailConnector:
    # Gmail API scope for reading emails
    SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
    
    def __init__(self, credentials_file: str = 'credentials.json', token_file: str = 'token.json'):
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.service = None
        self.db = FirebaseEmailDB()
        
        # Initialize email summarizer
        try:
            self.summarizer = EmailSummarizer()
            print("✅ Email summarizer initialized")
        except ValueError as e:
            print(f"⚠️  Email summarizer not available: {e}")
            print("   Set OPENAI_API_KEY environment variable to enable AI summaries")
            self.summarizer = None
    
    def authenticate(self) -> bool:
        """Authenticate with Gmail API"""
        creds = None
        
        # Load existing token
        if os.path.exists(self.token_file):
            creds = Credentials.from_authorized_user_file(self.token_file, self.SCOPES)
        
        # If no valid credentials, get new ones
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(self.credentials_file):
                    print(f"Please download credentials.json from Google Cloud Console")
                    print("1. Go to https://console.cloud.google.com/")
                    print("2. Create a new project or select existing one")
                    print("3. Enable Gmail API")
                    print("4. Create OAuth 2.0 credentials (Desktop app)")
                    print("5. Download and save as 'credentials.json'")
                    return False
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, self.SCOPES)
                creds = flow.run_local_server(port=0)
            
            # Save credentials for next run
            with open(self.token_file, 'w') as token:
                token.write(creds.to_json())
        
        try:
            self.service = build('gmail', 'v1', credentials=creds)
            return True
        except HttpError as error:
            print(f'An error occurred during authentication: {error}')
            return False
    
    def get_recent_unread_emails(self, hours: int = 24) -> List[Dict]:
        """
        Fetch unread emails and generate first-person summaries and actions
        """
        if not self.service:
            print("Please authenticate first")
            return []
        
        # Calculate time range
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        start_timestamp = int(start_time.timestamp())
        
        try:
            # Search for unread emails in time range
            query = f'is:unread after:{start_timestamp}'
            
            result = self.service.users().messages().list(
                userId='me',
                q=query
            ).execute()
            
            messages = result.get('messages', [])
            
            if not messages:
                print(f"No unread emails found in the last {hours} hours")
                return []
            
            print(f"Found {len(messages)} unread emails in the last {hours} hours")
            
            # Fetch full email details and generate summaries + actions
            emails = []
            
            if self.summarizer:
                print("🤖 Generating first-person summaries and action items...")
            
            for i, message in enumerate(messages, 1):
                print(f"   Processing email {i}/{len(messages)}...")
                email_data = self._get_email_details(message['id'])
                
                if email_data:
                    # Generate AI summary and action items
                    if self.summarizer:
                        try:
                            summary, action = self.summarizer.summarize_email(email_data)
                            email_data['summary'] = summary
                            email_data['action'] = action
                            print(f"   ✅ Summary: {summary[:50]}...")
                            if action and action != "No action required.":
                                print(f"   🎯 Action: {action[:40]}...")
                        except Exception as e:
                            print(f"   ⚠️  Failed to summarize: {e}")
                            # Fallback
                            cleaned_snippet = self._clean_snippet(email_data.get('snippet', ''))
                            email_data['summary'] = cleaned_snippet or 'Summary not available'
                            email_data['action'] = ''
                    else:
                        # Fallback if no AI summarizer
                        cleaned_snippet = self._clean_snippet(email_data.get('snippet', ''))
                        email_data['summary'] = cleaned_snippet or 'AI summarizer not available'
                        email_data['action'] = ''
                    
                    emails.append(email_data)
            
            return emails
            
        except HttpError as error:
            print(f'An error occurred while fetching emails: {error}')
            return []
    
    def _clean_snippet(self, snippet: str) -> str:
        """Clean snippet to remove sender info and focus on content"""
        if not snippet:
            return ""
        
        import re
        snippet = re.sub(r'^.*?:\s*', '', snippet)  # Remove "Sender Name: " pattern
        snippet = re.sub(r'from.*?sent.*?:', '', snippet, flags=re.IGNORECASE)
        
        return snippet.strip()
    
    def _get_email_details(self, message_id: str) -> Optional[Dict]:
        """Get detailed information about a specific email"""
        try:
            message = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()
            
            # Extract headers
            headers = {h['name']: h['value'] for h in message['payload']['headers']}
            
            # Extract body
            body = self._extract_body(message['payload'])
            
            # Get labels
            labels = message.get('labelIds', [])
            
            # Check if important
            is_important = 'IMPORTANT' in labels
            
            email_data = {
                'id': message['id'],
                'thread_id': message['threadId'],
                'sender': headers.get('From', ''),
                'subject': headers.get('Subject', ''),
                'snippet': message.get('snippet', ''),
                'body': body,
                'received_date': datetime.fromtimestamp(int(message['internalDate']) / 1000),
                'is_read': 'UNREAD' not in labels,
                'is_important': is_important,
                'labels': json.dumps(labels)
            }
            
            return email_data
            
        except HttpError as error:
            print(f'An error occurred while fetching email details: {error}')
            return None
    
    def _extract_body(self, payload: Dict) -> str:
        """Extract email body from payload"""
        body = ""
        
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    if 'data' in part['body']:
                        body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                        break
                elif part['mimeType'] == 'text/html' and not body:
                    if 'data' in part['body']:
                        body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
        else:
            if payload['mimeType'] == 'text/plain' and 'data' in payload['body']:
                body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')
        
        return body
    
    def save_emails_to_firebase(self, emails: List[Dict], user_id: str = 'default') -> int:
        """Save emails to Firebase"""
        return self.db.save_emails(emails, user_id)
    
    def get_emails_from_firebase(self, user_id: str = 'default') -> List[Dict]:
        """Get recent emails from Firebase (for flashcard interface)"""
        return self.db.get_recent_emails(user_id, hours=24)
    
    def cleanup_read_emails_from_firebase(self, user_id: str = 'default') -> int:
        """Remove emails from Firebase that are now read in Gmail"""
        if not self.service:
            print("Please authenticate first")
            return 0
        
        return self.db.cleanup_read_emails(self.service, user_id)
    
    # Flashcard action methods
    def swipe_right_read_email(self, doc_id: str, user_id: str = 'default') -> bool:
        """User swiped right - mark email as read (processed)"""
        return self.db.mark_email_read(doc_id, user_id)
    
    def swipe_left_discard_email(self, doc_id: str, user_id: str = 'default') -> bool:
        """User swiped left - mark email for discard (delete ads/spam)"""
        return self.db.mark_email_discard(doc_id, user_id)
    
    def toggle_flag_email(self, doc_id: str, user_id: str = 'default') -> bool:
        """User clicked flag button - toggle flag for later review"""
        return self.db.toggle_email_flag(doc_id, user_id)
    
    def get_flagged_emails(self, user_id: str = 'default') -> List[Dict]:
        """Get all flagged emails for review"""
        return self.db.get_flagged_emails(user_id)
    
    def get_discarded_emails(self, user_id: str = 'default') -> List[Dict]:
        """Get all emails marked for discard"""
        return self.db.get_discarded_emails(user_id)

def main():
    """Morning email routine"""
    gmail = GmailConnector()
    
    # Step 1: Authenticate with Gmail
    print("🌅 Good morning! Let's check your emails...")
    print("🔐 Authenticating with Gmail...")
    if not gmail.authenticate():
        print("❌ Authentication failed!")
        return
    
    print("✅ Authentication successful!")
    
    # Step 2: Sync with Gmail - remove emails that are now read 
    print("🔄 Syncing with Gmail - removing read emails...")
    gmail.cleanup_read_emails_from_firebase()
    
    # Step 3: Fetch unread emails with first-person summaries and actions
    print("📧 Fetching emails from the last 24 hours...")
    emails = gmail.get_recent_unread_emails(hours=24)
    
    if not emails:
        print("🎉 Great news! No new emails in the last 24 hours. You're all caught up!")
        return
    
    # Step 4: Save emails with summaries and actions to Firebase
    print(f"💾 Saving {len(emails)} emails with summaries and actions...")
    saved_count = gmail.save_emails_to_firebase(emails)
    print(f"✅ Successfully saved {saved_count} emails!")
    
    # Step 5: Morning summary
    important_count = sum(1 for email in emails if email.get('is_important', False))
    action_count = sum(1 for email in emails if email.get('action', '') and email.get('action', '') != 'No action required.')
    
    print("\n" + "="*60)
    print("☀️  YOUR MORNING EMAIL SUMMARY")
    print("="*60)
    print(f"📈 In the last 24 hours, you missed {len(emails)} emails!")
    if important_count > 0:
        print(f"⚠️  {important_count} of them are marked as important")
    if action_count > 0:
        print(f"🎯 {action_count} emails require action from you")
    print(f"🗓️  Time range: {(datetime.now() - timedelta(hours=24)).strftime('%Y-%m-%d %H:%M')} to now")
    print("\n📱 Flashcard Actions:")
    print("   ➡️  Swipe Right: Mark as read (you're done with this email)")
    print("   ⬅️  Swipe Left: Discard email (delete ads, spam, etc.)")
    print("   🏴 Flag Button: Flag for later review")
    print("="*60)
    
    # Step 6: Preview emails with first-person summaries and actions
    print(f"\n📋 Preview of your emails:")
    for i, email in enumerate(emails[:3], 1):
        importance_icon = "⚠️ " if email.get('is_important', False) else ""
        action_icon = "🎯 " if email.get('action', '') and email.get('action', '') != 'No action required.' else ""
        
        print(f"\n{i}. {importance_icon}{action_icon}From: {email['sender'][:40]}")
        print(f"   Subject: {email['subject'][:50]}")
        print(f"   💬 Summary: {email.get('summary', 'No summary available')}")
        
        if email.get('action', '') and email.get('action', '') != 'No action required.':
            print(f"   🎯 Action: {email.get('action', '')}")
    
    if len(emails) > 3:
        print(f"\n   ... and {len(emails) - 3} more emails with summaries and actions")
    
    print(f"\n🚀 Ready to start processing? Launch your flashcard interface!")

if __name__ == "__main__":
    main()