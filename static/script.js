const url = `https://cvsorter-d83j.onrender.com/`; // Replace with your Render URL
const interval = 30000; // Interval in milliseconds (30 seconds)

//Reloader Function
function reloadWebsite() {
  axios.get(url)
    .then(response => {
      console.log(`Reloaded at ${new Date().toISOString()}: Status Code ${response.status}`);
    })
    .catch(error => {
      console.error(`Error reloading at ${new Date().toISOString()}:`, error.message);
    });
}
setInterval(reloadWebsite, interval);

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
