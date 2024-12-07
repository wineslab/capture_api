from flask import Flask, request, jsonify
import subprocess
import threading
import os
import time
from flask_cors import CORS



app = Flask(__name__)

# Enable CORS for all routes
CORS(app)

# Directory to store captures
CAPTURE_DIR = "./captures"
os.makedirs(CAPTURE_DIR, exist_ok=True)

@app.route("/capture", methods=["POST"])
def start_capture():
    try:
        # Parse input
        data = request.json
        interface = data.get("interface", "ens3f0")
        duration = int(data.get("duration", 10))  # default to 10 seconds
        filename = os.path.join(CAPTURE_DIR, f"capture_{int(time.time())}.pcap")
        
        # Run tcpdump in a separate thread
        thread = threading.Thread(target=run_tcpdump, args=(interface, duration, filename))
        thread.start()
        
        return jsonify({"message": f"Capture started on {interface} for {duration} seconds.", "file": filename}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def run_tcpdump(interface, duration, filename):
    try:
        # Run tcpdump for the specified duration
        cmd = [
            "tcpdump",
            "-i", interface,
            "-j", "adapter_unsynced",
            "-ttt",
            "-nn",
            "-w", filename
        ]
        process = subprocess.Popen(cmd)
        time.sleep(duration)  # Wait for the duration of the capture
        process.terminate()  # Stop tcpdump
    except Exception as e:
        print(f"Error during capture: {e}")

if __name__ == "__main__":
    app.run(host="10.101.3.21", port=5000)
