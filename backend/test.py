from email_summarizer import EmailSummarizer

# Test the summarizer
test_email = {
    'subject': 'Team Meeting Tomorrow',
    'snippet': 'Hi everyone, we have our weekly team meeting scheduled for tomorrow at 2 PM. Please confirm your attendance.',
    'body': 'Hi team,\n\nJust a reminder that we have our weekly team meeting scheduled for tomorrow at 2:00 PM in Conference Room A.\n\nAgenda:\n- Project updates\n- Q4 planning\n- Budget review\n\nPlease confirm your attendance by replying to this email.\n\nThanks!',
    'is_important': False
}

try:
    summarizer = EmailSummarizer()
    summary, action = summarizer.summarize_email(test_email)
    print(f"Summary: {summary}")
    print(f"Action: {action}")
except Exception as e:
    print(f"Error: {e}")