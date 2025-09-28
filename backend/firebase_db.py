import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import json
import os
import logging

# Suppress Firebase internal warnings
logging.getLogger('google.cloud.firestore_v1.base_collection').setLevel(logging.ERROR)
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'firebase-credentials.json'

class FirebaseEmailDB:
    def __init__(self, credentials_path: str = 'firebase-credentials.json'):
        """Initialize Firebase connection"""
        if not firebase_admin._apps:
            if os.path.exists(credentials_path):
                cred = credentials.Certificate(credentials_path)
                firebase_admin.initialize_app(cred)
                print("✅ Firebase initialized with credentials file")
            else:
                print(f"❌ Firebase credentials file not found: {credentials_path}")
                print("Please download firebase-credentials.json from Firebase Console")
                raise FileNotFoundError(f"Firebase credentials not found: {credentials_path}")
        
        self.db = firestore.client()
        self.collection = 'emails'
        print("✅ Firestore client connected")
    
    def save_emails(self, emails: List[Dict], user_id: str = 'default') -> int:
        """Save emails to Firebase with clean schema including action field"""
        if not emails:
            return 0
        
        print(f"💾 Saving {len(emails)} emails to Firestore...")
        
        saved_count = 0
        batch = self.db.batch()
        
        for email in emails:
            # Use Gmail message ID as document ID to prevent duplicates
            doc_ref = self.db.collection(self.collection).document(f"{user_id}_{email['id']}")
            
            email_data = {
                # Gmail data
                'gmail_id': email['id'],
                'thread_id': email['thread_id'],
                'sender': email['sender'],
                'subject': email['subject'],
                'snippet': email['snippet'],
                'body': email['body'],
                'received_date': email['received_date'],
                'is_important': email['is_important'],
                'labels': email['labels'],
                'user_id': user_id,
                'created_at': datetime.now(),
                
                # Clean schema fields for flashcard actions
                'is_read': email.get('is_read', False),     # Gmail read status
                'summary': email.get('summary', ''),        # LLM-generated first-person summary
                'action': email.get('action', ''),          # LLM-generated action items
                'flag': False,                              # User can flag for later review via button
                'discard': False                            # User can swipe left to discard
            }
            
            batch.set(doc_ref, email_data, merge=True)
            saved_count += 1
        
        try:
            # Commit batch write
            batch.commit()
            print(f"✅ Successfully saved {saved_count} emails to Firestore")
            return saved_count
        except Exception as e:
            print(f"❌ Error saving to Firestore: {e}")
            return 0
    
    def get_recent_emails(self, user_id: str = 'default', hours: int = 24) -> List[Dict]:
        """Get emails from last X hours for flashcard interface"""
        try:
            print(f"📖 Fetching emails from Firestore for last {hours} hours...")
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            # Get unread, non-discarded emails from Firebase (ready for flashcard processing)
            emails_ref = (self.db.collection(self.collection)
                         .where(filter=firestore.FieldFilter('user_id', '==', user_id))
                         .where(filter=firestore.FieldFilter('received_date', '>=', cutoff_time))
                         .where(filter=firestore.FieldFilter('is_read', '==', False))
                         .where(filter=firestore.FieldFilter('discard', '==', False)))
            
            docs = emails_ref.stream()
            
            emails = []
            for doc in docs:
                email_data = doc.to_dict()
                email_data['doc_id'] = doc.id
                emails.append(email_data)
            
            # Sort by received date (newest first)
            emails.sort(key=lambda x: x['received_date'], reverse=True)
            
            print(f"✅ Found {len(emails)} emails ready for flashcard processing")
            return emails
            
        except Exception as e:
            print(f"❌ Error fetching emails from Firestore: {e}")
            return []
    
    def mark_email_read(self, doc_id: str, user_id: str = 'default') -> bool:
        """Mark email as read (swipe right action)"""
        try:
            doc_ref = self.db.collection(self.collection).document(doc_id)
            doc_ref.update({
                'is_read': True,
                'processed_at': datetime.now(),
                'action_type': 'swipe_right_read'
            })
            print(f"✅ Email marked as read (swipe right)")
            return True
        except Exception as e:
            print(f"❌ Error marking email as read: {e}")
            return False
    
    def mark_email_discard(self, doc_id: str, user_id: str = 'default') -> bool:
        """Mark email for discard (swipe left action)"""
        try:
            doc_ref = self.db.collection(self.collection).document(doc_id)
            doc_ref.update({
                'discard': True,
                'processed_at': datetime.now(),
                'action_type': 'swipe_left_discard'
            })
            print(f"✅ Email marked for discard (swipe left)")
            return True
        except Exception as e:
            print(f"❌ Error marking email for discard: {e}")
            return False
    
    def toggle_email_flag(self, doc_id: str, user_id: str = 'default') -> bool:
        """Toggle flag on email (flag button action)"""
        try:
            doc_ref = self.db.collection(self.collection).document(doc_id)
            doc = doc_ref.get()
            
            if doc.exists:
                current_flag = doc.to_dict().get('flag', False)
                new_flag = not current_flag
                
                doc_ref.update({
                    'flag': new_flag,
                    'flagged_at': datetime.now() if new_flag else None
                })
                
                action = "flagged" if new_flag else "unflagged"
                print(f"✅ Email {action} for later review")
                return True
            else:
                print(f"❌ Email document not found")
                return False
                
        except Exception as e:
            print(f"❌ Error toggling email flag: {e}")
            return False
    
    def cleanup_read_emails(self, gmail_service, user_id: str = 'default') -> int:
        """Remove emails from Firebase that are now read in Gmail"""
        try:
            print("🔄 Syncing with Gmail - checking read status of stored emails...")
            
            emails_ref = (self.db.collection(self.collection)
                         .where(filter=firestore.FieldFilter('user_id', '==', user_id)))
            
            docs = emails_ref.stream()
            
            deleted_count = 0
            batch = self.db.batch()
            
            for doc in docs:
                email_data = doc.to_dict()
                gmail_id = email_data['gmail_id']
                
                try:
                    message = gmail_service.users().messages().get(
                        userId='me',
                        id=gmail_id,
                        format='minimal'
                    ).execute()
                    
                    labels = message.get('labelIds', [])
                    
                    if 'UNREAD' not in labels:
                        batch.delete(doc.reference)
                        deleted_count += 1
                        print(f"   📧 Email from {email_data.get('sender', 'Unknown')[:30]} is now read - removing from Firebase")
                        
                except Exception as e:
                    if "404" in str(e) or "Not Found" in str(e):
                        batch.delete(doc.reference)
                        deleted_count += 1
                        print(f"   📧 Email {gmail_id[:10]}... was deleted from Gmail - removing from Firebase")
            
            if deleted_count > 0:
                batch.commit()
                print(f"✅ Removed {deleted_count} read/deleted emails from Firebase")
            else:
                print("ℹ️  All stored emails are still unread in Gmail")
            
            return deleted_count
            
        except Exception as e:
            print(f"❌ Error syncing with Gmail: {e}")
            return 0
    
    def get_flagged_emails(self, user_id: str = 'default') -> List[Dict]:
        """Get all flagged emails for later review"""
        try:
            emails_ref = (self.db.collection(self.collection)
                         .where(filter=firestore.FieldFilter('user_id', '==', user_id))
                         .where(filter=firestore.FieldFilter('flag', '==', True))
                         .where(filter=firestore.FieldFilter('discard', '==', False)))
            
            docs = emails_ref.stream()
            
            emails = []
            for doc in docs:
                email_data = doc.to_dict()
                email_data['doc_id'] = doc.id
                emails.append(email_data)
            
            return sorted(emails, key=lambda x: x['received_date'], reverse=True)
            
        except Exception as e:
            print(f"❌ Error fetching flagged emails: {e}")
            return []
    
    def get_discarded_emails(self, user_id: str = 'default') -> List[Dict]:
        """Get all emails marked for discard"""
        try:
            emails_ref = (self.db.collection(self.collection)
                         .where(filter=firestore.FieldFilter('user_id', '==', user_id))
                         .where(filter=firestore.FieldFilter('discard', '==', True)))
            
            docs = emails_ref.stream()
            
            emails = []
            for doc in docs:
                email_data = doc.to_dict()
                email_data['doc_id'] = doc.id
                emails.append(email_data)
            
            return sorted(emails, key=lambda x: x['received_date'], reverse=True)
            
        except Exception as e:
            print(f"❌ Error fetching discarded emails: {e}")
            return []
    
    def test_connection(self):
        """Test Firebase connection"""
        try:
            test_ref = self.db.collection(self.collection).limit(1)
            list(test_ref.stream())
            print("✅ Firebase connection test successful!")
            return True
        except Exception as e:
            print(f"❌ Firebase connection test failed: {e}")
            return False