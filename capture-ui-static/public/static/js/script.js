var socket = io.connect("http://" + document.domain + ":" + location.port);

// Fetch the configured Switch IP from the backend
function fetchSwitchIP() {
    fetch("/api/get_switch_ip")
        .then(response => response.json())
        .then(data => {
            document.getElementById("switchIP").textContent = data.switch_ip || "Not Configured";
        })
        .catch(error => console.error("Error fetching switch IP:", error));
}

// Fetch interfaces
document.getElementById("fetchInterfaces").addEventListener("click", function() {
    var fetchButton = document.getElementById("fetchInterfaces");
    var loadingMessage = document.getElementById("loadingMessage");

    // Disable button and show loading message
    fetchButton.disabled = true;
    loadingMessage.style.display = "block";

    fetch("/api/get_interfaces", {
        method: "POST",
        headers: { "Content-Type": "application/json" }
    })
    .then(response => response.json())
    .then(data => {
        fetchButton.disabled = false;
        loadingMessage.style.display = "none";

        if (data.error) {
            alert("Error fetching interfaces: " + data.error);
            return;
        }

        var tableBody = document.getElementById("interfaceTableBody");
        tableBody.innerHTML = ""; // Clear previous data

        data.interfaces.forEach(interface => {
            var row = `
                <tr onclick="selectPort('${interface.port}', this)">
                    <td>${interface.port}</td>
                    <td>${interface.description}</td>
                    <td>${interface.status}</td>
                    <td>${interface.speed}</td>
                    <td>${interface.duplex}</td>
                    <td>${interface.mode}</td>
                    <td>${interface.vlan}</td>
                    <td>${interface.tagged_vlans}</td>
                </tr>`;
            tableBody.innerHTML += row;
        });

        document.getElementById("interfaceContainer").style.display = "block";
    })
    .catch(error => {
        fetchButton.disabled = false;
        loadingMessage.style.display = "none";
        console.error("Error fetching interfaces:", error);
    });
});

// Select port by clicking on the table row
function selectPort(port, row) {
    var cleanPort = port.replace("Eth ", ""); // Remove "Eth " prefix
    document.getElementById("new_source").value = cleanPort;  // Set only the cleaned port name

    // Remove highlight from previous selection
    var rows = document.querySelectorAll("#interfaceTableBody tr");
    rows.forEach(r => r.classList.remove("selected"));

    // Highlight the clicked row
    row.classList.add("selected");
}

// Configure monitor session
document.getElementById("monitorForm").addEventListener("submit", function(event) {
    event.preventDefault();

    var newSource = document.getElementById("new_source").value;

    if (!newSource) {
        alert("Please select a port from the table!");
        return;
    }

    fetch("/api/configure_monitor", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ new_source: newSource })
    })
    .then(response => response.json())
    .then(data => {
        var monitorMessage = document.getElementById("monitorMessage");
        if (data.error) {
            monitorMessage.innerHTML = "Error: " + data.error;
            monitorMessage.style.color = "red";
        } else {
            monitorMessage.innerHTML = "Monitor session updated successfully! <br> Old Source: " + data.old_source + "<br> New Source: " + data.new_source;
            monitorMessage.style.color = "green";
        }
        monitorMessage.style.display = "block";
    })
    .catch(error => console.error("Error configuring monitor session:", error));
});

// Handle starting packet capture
document.getElementById("captureForm").addEventListener("submit", function(event) {
    event.preventDefault(); 

    var interface = document.getElementById("interface").value;
    var captureCommandDisplay = document.getElementById("captureCommand");
    var url = `/sysmaster/capture_start?interface=${encodeURIComponent(interface)}`;
    console.log("Fetching from URL:", url); // Log request URL

    fetch(url, { method: "GET" })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }
        // Ensure it's JSON
        if (response.headers.get("content-type")?.includes("application/json")) {
            return response.json();
        } else {
            throw new Error("Response is not JSON");
        }
    })
    .then(data => {
        console.log("Received JSON:", data);  //Log JSON response
        alert("Status: " + data.Status + "\n" + data.Str);

        if (data.file) {
            var filename = data.file.replace(/^.*[\\/]/, ""); 
            console.log("Setting download button data-file to:", filename);
            
            socket.emit("capture_started", { interface: interface });
            document.getElementById("downloadCapture").setAttribute("data-file", data.file);
            document.getElementById("downloadCapture").style.display = "block";
            document.getElementById("stopCapture").style.display = "inline-block";
            
            captureCommandDisplay.textContent = "Command: sudo tcpdump -i " + interface + " -w " + data.file;
            captureCommandDisplay.style.display = "block";
        } else {
            console.warn("No file field in response. Capture may not have started correctly.");
        }
    })
    .catch(error => console.error("Error starting capture:", error));
});

// Handle stopping packet capture
document.getElementById("stopCapture").addEventListener("click", function() {
    fetch("/sysmaster/capture_stop", { method: "GET" })
    .then(response => response.json())
    .then(data => {
        alert(data.message);
        document.getElementById("stopCapture").style.display = "none";
    })
    .catch(error => console.error("Error stopping capture:", error));
});

// Handle capture completion
socket.on("capture_completed", function(data) {
    alert("Capture completed! File: " + data.file);
    document.getElementById("downloadCapture").setAttribute("data-file", data.file);
    document.getElementById("downloadCapture").style.display = "block";
    document.getElementById("stopCapture").style.display = "none";
});

// Handle download
//document.getElementById("downloadCapture").addEventListener("click", function() {
  //  var filename = this.getAttribute("data-file");
    //if (filename) {
      //  window.location.href = "/api/download_capture/" + filename.split("/").pop();
    //}
//});

document.getElementById("downloadCapture").addEventListener("click", function() {
    var filePath = this.getAttribute("data-file"); // Get stored filename
    console.log("Download button clicked, file path:", filePath); // ✅ Debugging

    if (!filePath) {
        alert("No capture file available for download.");
        return;
    }

    // ✅ Extract only the filename (remove ./captures/)
    var filename = filePath.replace(/^.*[\\/]/, ""); 
    console.log("Extracted filename for API call:", filename); // ✅ Debugging

    var url = `/api/v1/pcap/single?StreamName=${encodeURIComponent(filename)}`;
    console.log("Downloading from URL:", url);

    // Create a hidden link to trigger file download
    var downloadLink = document.createElement("a");
    downloadLink.href = url;
    downloadLink.download = filename;
    document.body.appendChild(downloadLink);
    downloadLink.click();
    document.body.removeChild(downloadLink);
});


// Fetch the Switch IP on page load
fetchSwitchIP();

