import openai
from typing import Dict, Optional, Tuple
import os
import re
from dotenv import load_dotenv

load_dotenv()

class EmailSummarizer:
    def __init__(self, api_key: str = None):
        """Initialize OpenAI client"""
        if api_key:
            self.client = openai.OpenAI(api_key=api_key)
        else:
            # Try to get from environment variable
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                raise ValueError("OpenAI API key is required. Set OPENAI_API_KEY environment variable or pass it directly.")
            self.client = openai.OpenAI(api_key=api_key)
    
    def summarize_email(self, email_data: Dict) -> Tuple[str, str]:
        """
        Summarize email content and extract action items
        Returns: (summary, action) tuple
        """
        subject = email_data.get('subject', '')
        snippet = email_data.get('snippet', '')
        body = email_data.get('body', '')
        is_important = email_data.get('is_important', False)
        
        # Clean and prepare content for summarization
        content = self._prepare_email_content(subject, snippet, body)
        
        # If content is too short or empty, return fallback
        if len(content.strip()) < 20:
            fallback_summary = self._create_fallback_summary(subject, snippet)
            return fallback_summary, "No action required."
        
        try:
            # Create prompts for both summary and action
            summary_prompt = self._create_summary_prompt(content, is_important)
            action_prompt = self._create_action_prompt(content, is_important)
            
            print(f"      🤖 Calling OpenAI for summary and action...")
            
            # Get summary
            summary_response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are an expert email summarizer. Rewrite the email content from the sender's first-person perspective as a concise summary. Write as if you are the sender speaking directly to the recipient. Do not use third-person phrases like 'The email' or 'The sender'. Start directly with the content."},
                    {"role": "user", "content": summary_prompt}
                ],
                temperature=0.3,
                max_tokens=100,
                timeout=15
            )
            
            # Get action items
            action_response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are an expert at identifying action items from emails. Extract any specific actions, requests, or tasks that require the recipient to do something. If no action is needed, respond with 'No action required.' Keep it to 1-2 sentences maximum."},
                    {"role": "user", "content": action_prompt}
                ],
                temperature=0.3,
                max_tokens=60,
                timeout=15
            )
            
            summary = summary_response.choices[0].message.content.strip()
            action = action_response.choices[0].message.content.strip()
            
            print(f"      ✅ Raw summary: {summary[:40]}...")
            print(f"      ✅ Raw action: {action}")
            
            # Clean up the responses
            summary = self._clean_summary_text(summary)
            action = self._clean_action_text(action)
            
            # Fallback if summary is empty or too generic
            if not summary or len(summary) < 15 or any(phrase in summary.lower() for phrase in ["i cannot", "sorry", "unable to"]):
                summary = self._create_fallback_summary(subject, snippet)
            
            return summary, action
            
        except Exception as e:
            print(f"      ❌ Error calling OpenAI: {e}")
            fallback_summary = self._create_fallback_summary(subject, snippet)
            return fallback_summary, "No action required."
    
    def _prepare_email_content(self, subject: str, snippet: str, body: str) -> str:
        """Combine and clean email content for summarization"""
        content_parts = []
        
        # Add subject if meaningful
        if subject and len(subject.strip()) > 3:
            cleaned_subject = self._clean_email_text(subject)
            if cleaned_subject:
                content_parts.append(f"Subject: {cleaned_subject}")
        
        # Prefer body over snippet, but use both if available
        if body and len(body.strip()) > 50:
            cleaned_body = self._clean_email_text(body)
            if len(cleaned_body.strip()) > 30:
                content_parts.append(f"Content: {cleaned_body[:1200]}")
        
        # Add snippet if we don't have good body content or as supplement
        if snippet and (not body or len(body.strip()) < 100):
            cleaned_snippet = self._clean_email_text(snippet)
            if cleaned_snippet and cleaned_snippet not in str(content_parts):
                content_parts.append(f"Preview: {cleaned_snippet}")
        
        return "\n".join(content_parts)
    
    def _clean_email_text(self, text: str) -> str:
        """Clean email text by removing common artifacts"""
        if not text:
            return ""
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', ' ', text)
        
        # Remove email signatures and footers
        text = re.sub(r'--[\r\n].*', '', text, flags=re.DOTALL)
        text = re.sub(r'(best regards|sincerely|thank you|thanks|cheers).*', '', text, flags=re.DOTALL | re.IGNORECASE)
        
        # Remove quoted text and replies
        text = re.sub(r'on.*wrote:.*', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'>.*', '', text, flags=re.MULTILINE)
        text = re.sub(r'from:.*sent:.*', '', text, flags=re.DOTALL | re.IGNORECASE)
        
        # Remove unsubscribe and footer links
        text = re.sub(r'(unsubscribe|click here|view in browser).*', '', text, flags=re.IGNORECASE | re.DOTALL)
        
        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\n\s*\n', '\n', text)
        
        return text.strip()
    
    def _create_summary_prompt(self, content: str, is_important: bool) -> str:
        """Create prompt for first-person summary"""
        importance_note = " This email is marked as important." if is_important else ""
        
        return f"""
Rewrite this email content as a concise first-person summary (max 150 words). Write from the sender's perspective, as if they are speaking directly to the recipient.

Examples of first-person style:
- Instead of "The sender is inviting..." → "I'm inviting you to..."
- Instead of "The email contains..." → "I wanted to share..."
- Instead of "They are requesting..." → "I need you to..."

{importance_note}

Email content to rewrite:
{content}

Provide a first-person summary:
"""
    
    def _create_action_prompt(self, content: str, is_important: bool) -> str:
        """Create prompt for action extraction"""
        importance_note = " This email is marked as important." if is_important else ""
        
        return f"""
Analyze this email and identify any specific actions, tasks, or requests that require the recipient to do something.

Look for:
- Meeting confirmations or RSVPs needed
- Documents to review or complete
- Decisions to make
- Responses required
- Tasks to complete
- Deadlines to meet
- Questions that need answers
- Forms to fill out
- Appointments to schedule

If there are actions needed, describe them clearly in 1-2 sentences.
If no action is required, respond with "No action required."

{importance_note}

Email content to analyze:
{content}

Action needed (if any):
"""
    
    def _clean_summary_text(self, text: str) -> str:
        """Final cleanup of summary text"""
        if not text:
            return ""
        
        # Remove quotes and system text
        text = text.strip('"\'')
        text = re.sub(r'^(summary|tldr):\s*', '', text, flags=re.IGNORECASE)
        
        # Remove third-person references that might slip through
        text = re.sub(r'^(the email|this email|the sender|they are).*?:', '', text, flags=re.IGNORECASE)
        
        # Ensure it's one paragraph
        text = re.sub(r'\n+', ' ', text)
        
        # Capitalize first letter
        if text:
            text = text[0].upper() + text[1:]
        
        # Ensure it ends with proper punctuation
        if text and not text.endswith(('.', '!', '?')):
            text += '.'
        
        return text.strip()
    
    def _clean_action_text(self, text: str) -> str:
        """Clean action text"""
        if not text:
            return "No action required."
        
        # Remove quotes and clean up
        text = text.strip('"\'')
        text = re.sub(r'^(action|action needed|actions?):\s*', '', text, flags=re.IGNORECASE)
        
        # Ensure proper capitalization
        if text and text.lower() != "no action required.":
            text = text[0].upper() + text[1:]
            if not text.endswith(('.', '!', '?')):
                text += '.'
        elif not text:
            text = "No action required."
        
        return text.strip()
    
    def _create_fallback_summary(self, subject: str, snippet: str) -> str:
        """Create fallback summary when LLM fails"""
        # Try snippet first
        if snippet and len(snippet.strip()) > 15:
            cleaned = self._clean_email_text(snippet)
            if len(cleaned) > 10:
                return self._clean_summary_text(cleaned)
        
        # Try subject
        if subject and len(subject.strip()) > 5:
            cleaned_subject = self._clean_email_text(subject)
            if cleaned_subject:
                return f"Regarding: {self._clean_summary_text(cleaned_subject)}"
        
        return "Email content preview not available."