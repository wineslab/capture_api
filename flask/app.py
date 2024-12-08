from flask import Flask, request, jsonify
import subprocess
import threading
import os
import time
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import eventlet


app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'

# Initialize SocketIO
socketio = SocketIO(app, logger=True, cors_allowed_origins="*")

# Enable CORS for all routes
CORS(app)

# Directory to store captures
CAPTURE_DIR = "./captures"
os.makedirs(CAPTURE_DIR, exist_ok=True)

@app.route("/capture", methods=["POST"])
def start_capture():
    try:
        print("B1", flush=True)
        # Parse input
        data = request.json
        interface = data.get("interface", "ens3f0")
        duration = int(data.get("duration", 10))  # default to 10 seconds
        filename = os.path.join(CAPTURE_DIR, f"capture_{int(time.time())}.pcap")
        
        # Run tcpdump in a separate thread
        thread = threading.Thread(target=run_tcpdump, args=(interface, duration, filename))
        thread.start()
        
        return jsonify({"message": f"Capture started on {interface} for {duration} seconds.", "file": filename[1:]}), 200
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
        print("A0", flush=True)
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        # Wait for the specified duration
        time.sleep(duration)
        print("A1", flush=True)
        # Terminate the process and wait for it to exit
        process.terminate()
        stdout, stderr = process.communicate()
        print("A2", flush=True)

        # Parse the output from tcpdump
        packets_info = parse_tcpdump_output(stderr)
        print("A3", flush=True)

        # Trigger the WebSocket event upon completion
        socketio.emit('capture_completed', {
            "message": "Capture completed",
            "file": filename,
            "packets_info": packets_info
        })
        print("A4", flush=True)
        socketio.emit('capture_completed', {"message": "Capture completed", "file": filename})
        print("A5", flush=True)

    except Exception as e:
        print(f"Error during capture: {e}")


def parse_tcpdump_output(output):
    """
    Parse the tcpdump output to extract packet statistics.
    Example output:
    135359 packets captured
    135416 packets received by filter
    0 packets dropped by kernel
    """
    info = {}
    for line in output.splitlines():
        if "packets captured" in line:
            info["packets_captured"] = int(line.split()[0])
        elif "packets received by filter" in line:
            info["packets_received"] = int(line.split()[0])
        elif "packets dropped by kernel" in line:
            info["packets_dropped"] = int(line.split()[0])
    return info

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)
