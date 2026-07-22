"""
Google Drive upload module — uses service account to upload files.
"""
import json
import logging
from pathlib import Path
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

logger = logging.getLogger("google_drive")

SERVICE_ACCOUNT_FILE = Path(__file__).parent / "data" / "service-account.json"
SCOPES = ["https://www.googleapis.com/auth/drive.file"]


def get_drive_service():
    """Authenticate and return a Google Drive service."""
    if not SERVICE_ACCOUNT_FILE.exists():
        raise FileNotFoundError(
            f"Service account not found: {SERVICE_ACCOUNT_FILE}\n"
            "Copy your service-account.json to dashboard/data/"
        )
    creds = service_account.Credentials.from_service_account_file(
        str(SERVICE_ACCOUNT_FILE), scopes=SCOPES
    )
    return build("drive", "v3", credentials=creds)


def _find_or_create_folder(service, folder_name: str) -> str:
    """Find or create a folder in Drive. Returns folder ID."""
    # Search for existing folder
    query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    results = service.files().list(q=query, spaces="drive", fields="files(id, name)").execute()
    files = results.get("files", [])

    if files:
        return files[0]["id"]

    # Create folder
    folder_metadata = {
        "name": folder_name,
        "mimeType": "application/vnd.google-apps.folder",
    }
    folder = service.files().create(body=folder_metadata, fields="id").execute()
    logger.info(f"Created Drive folder: {folder_name} ({folder['id']})")
    return folder["id"]


async def upload_to_drive(file_path: Path, folder_name: str = "OMNI Exports") -> dict:
    """Upload a file to Google Drive inside the specified folder."""
    service = get_drive_service()
    folder_id = _find_or_create_folder(service, folder_name)

    file_metadata = {
        "name": file_path.name,
        "parents": [folder_id],
    }

    # Determine MIME type
    mime_map = {
        ".aif": "audio/aiff",
        ".aiff": "audio/aiff",
        ".mp3": "audio/mpeg",
        ".wav": "audio/wav",
        ".flac": "audio/flac",
        ".m4a": "audio/mp4",
    }
    mime_type = mime_map.get(file_path.suffix.lower(), "application/octet-stream")

    media = MediaFileUpload(str(file_path), mimetype=mime_type, resumable=True)

    file = service.files().create(
        body=file_metadata, media_body=media, fields="id, webViewLink"
    ).execute()

    file_id = file.get("id")
    drive_url = file.get("webViewLink", f"https://drive.google.com/file/d/{file_id}")

    logger.info(f"Uploaded {file_path.name} to Drive folder '{folder_name}'")
    return {"id": file_id, "url": drive_url, "name": file_path.name}
