# ⍺lphaMail

This application provides an intelligent, at-a-glance summary of your overnight emails. It features a Python backend that fetches, analyzes, and summarizes emails using an LLM, and a Next.js frontend that presents them in a clean, flashcard-style interface for rapid inbox management.

## Features

-   **Secure Gmail Integration**: Connects to your Gmail account using OAuth 2.0 to fetch emails on your behalf.
-   **Automated Fetching**: A backend script runs periodically to fetch unread emails from a specified time range (e.g., overnight).
-   **AI-Powered Summaries**: Leverages an LLM to analyze and summarize the content of each email, extracting the key information.
-   **Intelligent Triage**: Automatically identifies important emails and flags them for action.
-   **Modern Web Interface**: A responsive frontend built with Next.js displays emails as easy-to-read summary cards.
-   **Instant Inbox Clearing**: Quickly action emails (mark as read, archive, etc.) directly from the web interface.
-   **Secure & Scalable**: Uses Google Cloud Firestore for data storage and Firebase for backend services.

## System Design and Data Flow

The application consists of two main components:

1.  **Backend (Python)**: A Python script responsible for:
    -   Authenticating with the Gmail API.
    -   Fetching new, unread emails.
    -   Summarizing email content using an LLM (e.g., OpenAI, Google AI).
    -   Storing the structured email data and summaries in Google Cloud Firestore.

2.  **Frontend (Next.js)**: A web application that:
    -   Provides the user interface for viewing and managing emails.
    -   Fetches summarized email data from Firestore via Next.js API Routes.
    -   Allows users to perform actions on emails, which are then communicated back to the Gmail API.

The data flows through the system as follows:

1.  **Email Fetching**: A scheduled job executes the Python backend script (`gmail.py`).
2.  **Authentication**: The script uses user-provided OAuth 2.0 credentials (`credentials.json`) to authenticate with the Gmail API.
3.  **Processing & Summarization**: It fetches unread emails, extracts key details (sender, subject, body), and sends the body content to an LLM for summarization.
4.  **Data Storage**: The script uses a Firebase Service Account to connect to Firestore and stores the original email content along with its AI-generated summary in the `emails` collection.
5.  **Frontend Rendering**: The user opens the Next.js web app, which calls its internal API endpoint (`/api/emails`).
6.  **Data Retrieval**: The API route securely queries Firestore for the user's summarized, unread emails.
7.  **User Interaction**: The emails are displayed as summary cards. The user can then perform actions like "Mark as Read" or "Archive", which will eventually trigger calls back to the Gmail API.

## Project Structure

```
├── backend/
│   ├── gmail.py             # Main Python script for fetching and processing emails
│   ├── requirements.txt     # Python dependencies
│   └── credentials.json     # User-level Gmail API credentials (gitignored)
│
└── frontend/
    ├── src/
    │   ├── app/
    │   │   ├── api/emails/    # API routes for email actions
    │   │   │   └── route.ts
    │   │   ├── components/    # React components for the UI
    │   │   └── page.tsx       # Main page component
    │   └── lib/
    │       ├── firebase-admin.ts # Firebase Admin SDK initialization (server-side)
    │       └── types.ts        # TypeScript type definitions
    ├── .env.local             # Environment variables (gitignored)
    └── next.config.js         # Next.js configuration
```

## Technology Stack

*   **Backend**: Python, Google Cloud SDK, Firebase Admin SDK
-   **Frontend**: Next.js, React, TypeScript, Tailwind CSS
-   **Database**: Google Cloud Firestore
-   **APIs**: Gmail API, Google AI / OpenAI

## Getting Started

Follow these instructions to set up and run the project on your local machine.

### Prerequisites

-   Python 3.8+
-   Node.js 18.17+
-   Google Cloud SDK (`gcloud` CLI)

### 1. Cloud & API Setup

This project requires both user-level Gmail access (OAuth 2.0) and server-level Firebase access (Service Account).

#### A. Enable APIs
1.  Go to the Google Cloud Console.
2.  Create a new project or select an existing one.
3.  Enable the **Gmail API** and **Cloud Firestore API**.
    -   Navigate to "APIs & Services" > "Library".
    -   Search for each API and click "Enable".

#### B. Gmail API Credentials (OAuth 2.0)
This allows the backend script to access your Gmail account on your behalf.
1.  Go to "APIs & Services" > "Credentials".
2.  Click "Create Credentials" > "OAuth client ID".
3.  Select "Desktop application" for the application type.
4.  Download the JSON file. Rename it to `credentials.json` and place it in the `backend` folder.

#### C. Firebase Credentials (Service Account)
This allows the backend script and frontend server to securely access Firestore.
1.  In your Google Cloud project, go to "IAM & Admin" > "Service Accounts".
2.  Click "Create Service Account", give it a name, and grant it the **Cloud Datastore User** role.
3.  After creating the service account, go to its "Keys" tab, click "Add Key" > "Create new key", and choose JSON.
4.  A JSON file will be downloaded. This file contains sensitive credentials.

### 2. Backend Setup

The backend script fetches and processes your emails.

```bash
# Navigate to the backend directory
cd backend

# Install Python dependencies
pip install -r requirements.txt

# Set up environment variables
# Create a .env file in the 'backend' directory and add the following:
# FIREBASE_SERVICE_ACCOUNT='<PASTE_THE_ENTIRE_CONTENTS_OF_THE_SERVICE_ACCOUNT_JSON_FILE_HERE>'
# OPENAI_API_KEY='<YOUR_OPENAI_API_KEY>'
```

To run the backend script:
```bash
python gmail.py
```
The first time you run it, a browser window will open for Gmail authentication. You'll need to grant the requested permissions to allow the application to read your emails.

### 3. Frontend Setup

The frontend is a Next.js application that displays your summarized emails.

```bash
# Navigate to the frontend directory
cd frontend

# Install Node.js dependencies
npm install

# Set up environment variables
# Create a .env.local file in the 'frontend' directory and add the following:
# FIREBASE_SERVICE_ACCOUNT='<PASTE_THE_ENTIRE_CONTENTS_OF_THE_SERVICE_ACCOUNT_JSON_FILE_HERE>'
# NEXT_PUBLIC_FIREBASE_PROJECT_ID='<YOUR_GOOGLE_CLOUD_PROJECT_ID>'
# NEXT_PUBLIC_API_BASE_URL='http://localhost:3000'
```

To run the frontend development server:
```bash
npm run dev
```
Open http://localhost:3000 with your browser to see the result.

## Deployment

The easiest way to deploy the Next.js frontend is to use the Vercel Platform.

The backend script can be deployed as a scheduled job on a server or using a serverless function (e.g., Google Cloud Functions) triggered by Cloud Scheduler.

## Future Work

1.  Implement email action capabilities (mark as read, archive, delete) from the frontend.
2.  Add user authentication to support multiple users.
3.  Refine the AI summarization prompts for better accuracy and conciseness.
4.  Modify the database to store full emails from different mailboxes to make this app function as a ultimate hub.
