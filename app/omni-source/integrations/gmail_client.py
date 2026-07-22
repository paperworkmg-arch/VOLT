import os
import pickle
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# We request full access to send, read, and manage emails
SCOPES = ['https://mail.google.com/']

class GmailClient:
    def __init__(self):
        self.creds = None
        self.config_dir = os.path.expanduser("~/Omni-Studio/config")
        self.credentials_path = os.path.join(self.config_dir, "gmail_credentials.json")
        self.token_path = os.path.join(self.config_dir, "token.pickle")
        self.authenticate()

    def authenticate(self):
        # 1. Check if we already have a valid token saved
        if os.path.exists(self.token_path):
            with open(self.token_path, 'rb') as token:
                self.creds = pickle.load(token)
        
        # 2. If no valid credentials available, let the user log in.
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                if not os.path.exists(self.credentials_path):
                    print(f"🛑 CRITICAL: Cannot find {self.credentials_path}")
                    print("Please download your OAuth 2.0 Client ID JSON from Google Cloud Console and save it there.")
                    exit(1)
                
                # Fire up the browser for the user to approve
                flow = InstalledAppFlow.from_client_secrets_file(self.credentials_path, SCOPES)
                self.creds = flow.run_local_server(port=0)
            
            # Save the credentials for the next run
            with open(self.token_path, 'wb') as token:
                pickle.dump(self.creds, token)
        
        print("✅ Gmail OAuth2 Authentication Successful! Token saved.")
        return build('gmail', 'v1', credentials=self.creds)

if __name__ == "__main__":
    GmailClient()
