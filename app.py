from flask import Flask, request, jsonify, render_template_string
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

app = Flask(__name__)
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

# HTML template with modern and minimalistic styling
HTML_TEMPLATE = '''
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>CV Sorter || The Placement Cell, SRCC</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.0/socket.io.js"></script>
    <style>
        /* General Reset */
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }
        body {
            font-family: 'Segoe UI', sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            background: linear-gradient(120deg, #e8f0f8, #d1e3f1);
            color: #333;
            animation: fadeIn 0.8s ease-in-out;
        }

        /* Container and Header Styling */
        .container {
            width: 90%;
            max-width: 500px;
            padding: 40px;
            background: #ffffff;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
            border-radius: 15px;
            text-align: center;
            transition: all 0.3s ease-in-out;
            transform: translateY(0);
        }
        .container:hover {
            transform: translateY(-5px);
            box-shadow: 0 15px 40px rgba(0, 0, 0, 0.25);
        }
        h1 {
            font-size: 28px;
            color: #2b6777;
            margin-bottom: 20px;
            font-weight: 600;
        }

        /* Input Boxes and Button Styling */
        .input-box {
            margin-top: 20px;
            text-align: left;
        }
        textarea, input[type="text"] {
            width: 100%;
            padding: 12px;
            margin-top: 10px;
            font-size: 16px;
            border: 1px solid #ddd;
            border-radius: 8px;
            transition: box-shadow 0.3s ease, border-color 0.3s ease;
        }
        textarea:focus, input[type="text"]:focus {
            border-color: #2b6777;
            box-shadow: 0px 0px 8px rgba(43, 103, 119, 0.5);
            outline: none;
        }

        /* Button Styling */
        button {
            background-color: #2b6777;
            color: white;
            padding: 12px 24px;
            font-size: 16px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            margin-top: 20px;
            transition: background-color 0.3s ease, transform 0.2s ease;
        }
        button:hover {
            background-color: #23515a;
            transform: translateY(-3px);
        }

        /* Progress Bar Styling */
        .progress-container {
            width: 100%;
            margin-top: 20px;
            background: #e0e8f0;
            border-radius: 10px;
            position: relative;
        }
        .progress-bar {
            height: 30px;
            width: 0%;
            background-color: #2b6777;
            color: white;
            line-height: 30px;
            border-radius: 10px;
            text-align: center;
            transition: width 0.4s ease;
        }

        /* Processing Status */
        .status, .timer {
            font-size: 16px;
            margin-top: 10px;
            color: #2b6777;
        }

/* Popup Notification */
.popup {
    display: none;
    position: fixed;
    top: 20px; /* Position it at the top */
    left: 50%;
    transform: translateX(-50%);
    background: #2b6777;
    color: white;
    padding: 15px 40px;
    font-size: 16px;
    border-radius: 10px;
    box-shadow: 0 5px 15px rgba(0, 0, 0, 0.2);
    opacity: 0;
    transition: opacity 0.4s ease, transform 0.4s ease;
    display: flex;
    align-items: center;
}

.popup.show {
    display: flex;
    opacity: 1;
    transform: translateX(-50%) translateY(10px);
}

/* Tick Animation */
.popup .tick-icon {
    width: 24px;
    height: 24px;
    border-radius: 50%;
    background: #ffffff;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-right: 10px;
    position: relative;
}

.popup .tick-icon::before {
    content: '';
    width: 12px;
    height: 6px;
    border-left: 3px solid #2b6777;
    border-bottom: 3px solid #2b6777;
    transform: rotate(-45deg);
    opacity: 0;
    animation: tickAnimation 0.5s forwards ease 0.2s;
}

@keyframes tickAnimation {
    from { opacity: 0; }
    to { opacity: 1; }
}

        /* Fade In Animation */
        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>CV Sorter || The Placement Cell, SRCC</h1>
        <form id="download-form" onsubmit="startDownload(); return false;">
            <div class="input-box">
                <label for="company_name">Enter Company Name:</label>
                <input type="text" id="company_name" name="company_name" placeholder="Company Name" required>
            </div>
            <div class="input-box">
                <label for="file_names">Enter The Roll Numbers:</label>
                <textarea id="file_names" rows="8" placeholder="2XBCXXX A&#10;2XBCXXX B&#10; .&#10; .&#10; ." required></textarea>
            </div>
            <button type="submit">Click The Button To Sort CVs</button>
        </form>
        <div id="progress-area" style="display:none;">
            <div class="progress-container">
                <div class="progress-bar" id="progress-bar">0%</div>
            </div>
            <p class="status" id="file-status">Processing...</p>
            <p class="timer" id="time-left">Estimated Time Remaining: Calculating...</p>
        </div>
        <div id="result" class="result" style="display:none;"></div>
    </div>

<!-- Popup Notification for Completion -->
<div id="popup" class="popup">
    <div class="tick-icon"></div>
    Processing Complete!
</div>

    <script>
        const socket = io();
        let startTime, totalFiles;

        function startDownload() {
            document.getElementById("progress-area").style.display = "block";
            document.getElementById("progress-bar").style.width = "0%";
            document.getElementById("progress-bar").innerText = "0%";
            document.getElementById("file-status").innerText = "Starting...";
            document.getElementById("time-left").innerText = "Estimated Time Remaining: Calculating...";
            document.getElementById("result").style.display = "none";

            const company_name = document.getElementById('company_name').value;
            const file_names = document.getElementById('file_names').value;
            startTime = Date.now();
            totalFiles = file_names.split("\\n").length;

            fetch('/download_cvs', {
                method: 'POST',
                headers: {'Content-Type': 'application/x-www-form-urlencoded'},
                body: `file_names=${encodeURIComponent(file_names)}&company_name=${encodeURIComponent(company_name)}`
            })
            .then(response => response.json())
            .then(data => {
                if (data.link) {
                    document.getElementById("result").innerHTML = `<br><strong>Success:</strong> ${data.sorted_count} CVs have been sorted in the folder named "${data.folder_name}".<br><br><a href="${data.link}" target="_blank">Click Here To Access.</a>`;

                    if (data.missing_files && data.missing_files.length > 0) {
                        document.getElementById("result").innerHTML += `<br><br><strong>Missing CVs:</strong> ${data.missing_files.length} CVs missing.<br>
                        ${data.missing_files.join('<br>')}`;
                    }
                    document.getElementById("result").style.display = "block";
                    showPopup("Processing Complete!");
                } else {
                    document.getElementById("result").innerHTML = `<strong>Error:</strong> ${data.error}`;
                    document.getElementById("result").style.display = "block";
                }
            })
            .catch(error => console.error('Error:', error));
        }

function showPopup(message) {
    const popup = document.getElementById("popup");
    popup.innerText = message;
    popup.classList.add("show");
    setTimeout(() => popup.classList.remove("show"), 3000);
}


        // Progress Update
        socket.on('progress_update', (data) => {
            const percent = Math.min(100, Math.round((data.total_files_processed / totalFiles) * 100));
            document.getElementById('progress-bar').style.width = percent + "%";
            document.getElementById('progress-bar').innerText = percent + "%";
            document.getElementById('file-status').innerText = `Processing ${data.file_name} (${percent}%)`;
            const elapsedTime = (Date.now() - startTime) / 1000;
            const estimatedTimeLeft = (elapsedTime / data.total_files_processed) * (totalFiles - data.total_files_processed);
            document.getElementById('time-left').innerText = `Estimated Time Remaining: ${Math.round(estimatedTimeLeft)}s`;
        });

        socket.on('complete', () => {
            document.getElementById('file-status').innerText = "All files processed successfully!";
            document.getElementById('time-left').style.display = "none";
        });
    </script>
</body>
</html>
'''
@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

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
