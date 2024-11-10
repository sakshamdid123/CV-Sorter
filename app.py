from flask import Flask, request, jsonify, render_template
from flask_socketio import SocketIO, emit
import zipfile
import os
import json
from google.oauth2 import service_account
import io
import time
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload


app = Flask(__name__, static_folder='static', template_folder='templates')
socketio = SocketIO(app, cors_allowed_origins="*")

# Google Drive API credentials
service_account_info = {
    "type": os.getenv("GOOGLE_SERVICE_ACCOUNT_TYPE"),
    "project_id": os.getenv("GOOGLE_SERVICE_ACCOUNT_PROJECT_ID"),
    "private_key_id": os.getenv("GOOGLE_SERVICE_ACCOUNT_PRIVATE_KEY_ID"),
    "private_key": os.getenv("GOOGLE_SERVICE_ACCOUNT_PRIVATE_KEY").replace("\\n", "\n"),  # Ensure correct formatting
    "client_email": os.getenv("GOOGLE_SERVICE_ACCOUNT_CLIENT_EMAIL"),
    "client_id": os.getenv("GOOGLE_SERVICE_ACCOUNT_CLIENT_ID"),
    "auth_uri": os.getenv("GOOGLE_SERVICE_ACCOUNT_AUTH_URI"),
    "token_uri": os.getenv("GOOGLE_SERVICE_ACCOUNT_TOKEN_URI"),
    "auth_provider_x509_cert_url": os.getenv("GOOGLE_SERVICE_ACCOUNT_AUTH_PROVIDER_X509_CERT_URL"),
    "client_x509_cert_url": os.getenv("GOOGLE_SERVICE_ACCOUNT_CLIENT_X509_CERT_URL")
}
SCOPES = ['https://www.googleapis.com/auth/drive']
creds = service_account.Credentials.from_service_account_info(service_account_info, scopes=SCOPES)
drive_service = build('drive', 'v3', credentials=creds)

# Google Drive Folder IDs
DRIVE_FOLDER_ID = '1h8fYQZjAgGMx_WYDp-6C5IqTOsp7pxUc'
ADDITIONAL_DRIVE_FOLDER_ID = '1w_WX90_ZEK3RwSWDVIIUDSwIhgmNZt3m'
ZIP_FOLDER_ID = '1UoDiEOLAnPuw1pbjkk5IokJ-bqKlgm1z'

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/download_cvs', methods=['POST'])
def download_cvs():
    try:
        start_time = time.time()
        file_names_text = request.form.get('file_names')
        company_name = request.form.get('company_name')
        file_names = [line.strip() for line in file_names_text.splitlines() if line.strip()]
        
        missing_files = []  # List to store missing files
        sorted_count = 0

        # Step 1: Create a new folder in Google Drive for the company
        folder_metadata = {
            'name': f"Vetted CVs || {company_name}",
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [ZIP_FOLDER_ID]  # Set the parent folder where the new folder will be created
        }
        company_folder = drive_service.files().create(body=folder_metadata, fields='id').execute()
        company_folder_id = company_folder.get('id')

        # Step 2: Find, download, and upload each CV file into the new company folder
        for i, file_name in enumerate(file_names):
            # Search for the file in Google Drive
            query = f"name contains '{file_name}' and (('{DRIVE_FOLDER_ID}' in parents) or ('{ADDITIONAL_DRIVE_FOLDER_ID}' in parents)) and trashed=false"
            response = drive_service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
            files = response.get('files', [])
            
            if files:
                file_id = files[0].get('id')
                file_request = drive_service.files().get_media(fileId=file_id)
                fh = io.BytesIO()
                downloader = MediaIoBaseDownload(fh, file_request)

                done = False
                while not done:
                    status, done = downloader.next_chunk()

                # Step 3: Upload the file into the new company folder
                fh.seek(0)
                file_metadata = {
                    'name': files[0]['name'],
                    'parents': [company_folder_id]  # Set the parent to the new folder for the company
                }
                media = MediaIoBaseUpload(fh, mimetype='application/pdf')  # Set appropriate MIME type
                drive_service.files().create(body=file_metadata, media_body=media).execute()
                sorted_count += 1

                # Emit progress update
                socketio.emit('progress_update', {
                    "file_name": files[0]['name'],
                    "total_files_processed": i + 1
                })
            else:
                # Append the missing file name to the list
                missing_files.append(file_name)

        elapsed_time = time.time() - start_time
        print(f"Total time taken: {elapsed_time:.2f} seconds")

        socketio.emit('progress_update', {
          "file_name": "Completed",
          "total_files_processed": len(file_names)
        })

        # Step 4: Return both the download link and the missing files (if any)
        result = {
            "link": f"https://drive.google.com/drive/folders/{company_folder_id}?usp=sharing",
            "folder_name": f"Vetted CVs || {company_name}",
            "sorted_count": sorted_count
        }
        if missing_files:
            result["missing_files"] = missing_files  # Include missing files list if there are any

        return jsonify(result)

    except HttpError as error:
        print(f"An error occurred: {error}")
        return jsonify({"error": str(error)})

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
