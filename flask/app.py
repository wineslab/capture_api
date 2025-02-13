import os
import time
import re
import subprocess
from flask import Flask, request, jsonify, render_template, send_file
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from netmiko import ConnectHandler
import getpass

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'

socketio = SocketIO(app, logger=True, cors_allowed_origins="*")
CORS(app)

# Directory to store captures
CAPTURE_DIR = "./captures"
os.makedirs(CAPTURE_DIR, exist_ok=True)

#`capture_process` as a global variable
capture_process = None

# Fetching credentials from environment variables
switch_ip = os.getenv("SWITCH_IP")
username = os.getenv("SWITCH_USERNAME")
password = os.getenv("SWITCH_PASSWORD")

# Ensure the environment variables are set
if not switch_ip or not username or not password:
    raise ValueError("Environment variables SWITCH_IP, SWITCH_USERNAME, and SWITCH_PASSWORD must be set.")

# The rest of your script logic remains unchanged
print(f"Using Switch IP: {switch_ip}")
print(f"Using Username: {username}")


@app.route("/api/get_switch_ip", methods=["GET"])
def get_switch_ip():
    """Returns the configured Switch IP from environment variables."""
    switch_ip = os.getenv("SWITCH_IP", "Not Configured")
    return jsonify({"switch_ip": switch_ip})


# ----------------------- CONFIGURE MONITOR SESSION -----------------------

def configure_monitor_session(new_source):
    """
    Configures a monitor session by automatically detecting and removing the old source.
    """
    try:
        switch_ip = os.getenv("SWITCH_IP")
        username = os.getenv("SWITCH_USERNAME")
        password = os.getenv("SWITCH_PASSWORD")

        # Validate that credentials are set
        if not all([switch_ip, username, password]):
            return {"error": "Environment variables SWITCH_IP, SWITCH_USERNAME, and SWITCH_PASSWORD must be set."}
        
        device = {
            "device_type": "dell_os10",
            "ip": switch_ip,
            "username": username,
            "password": password,
            "session_log": "netmiko_debug.log",
            "global_delay_factor": 2,  # Helps with slow CLI response
            "fast_cli": False,  # Ensures commands complete
        }

        connection = ConnectHandler(**device)

        # Detect current CLI prompt
        base_prompt = connection.find_prompt()
        print(f"Detected Prompt: {base_prompt}")

        # Retrieve existing monitor session details
        monitor_output = connection.send_command_timing("show monitor session 1")

        # Extract the full source interface (including VLAN/slot details if present)
        match = re.search(r"(\d+)\s+ethernet([\d/:\d]+)", monitor_output)
        old_source = f"ethernet{match.group(2)}" if match else None

        print(f"Existing Source Interface: {'None' if not old_source else old_source}")

        # Enter configuration mode dynamically
        connection.send_command_timing("configure terminal")

        # Enter monitor session mode dynamically
        connection.send_command_timing("monitor session 1")

        # Remove old source interface if found
        if old_source:
            remove_cmd = f"no source interface {old_source}"
            connection.send_command_timing(remove_cmd)
            print(f"Removed old source: {old_source}")

        # Add new source interface
        add_cmd = f"source interface ethernet {new_source}"
        connection.send_command_timing(add_cmd)
        print(f"Added new source: ethernet{new_source}")

        # Retrieve updated monitor session info
        updated_monitor_output = connection.send_command_timing("show monitor session 1", read_timeout=15)

        connection.disconnect()
        return {
            "message": "Monitor session updated successfully",
            "old_source": old_source,
            "new_source": new_source,
            "show_session": updated_monitor_output
        }

    except Exception as e:
        return {"error": str(e)}

@app.route("/api/configure_monitor", methods=["POST"])
def configure_monitor():
    data = request.json
    new_source = data.get("new_source")
    if not new_source:
        return jsonify({"error": "Missing required parameter: new_source"}), 400
    print(f"Configuring monitor session for Switch IP: {os.getenv('SWITCH_IP')} with new source {new_source}")
    result = configure_monitor_session(new_source)
    return jsonify(result)

# ----------------------- NETWORK INTERFACE STATUS -----------------------

def get_interface_status():
    try:
        # Get credentials from environment variables
        switch_ip = os.getenv("SWITCH_IP")
        username = os.getenv("SWITCH_USERNAME")
        password = os.getenv("SWITCH_PASSWORD")

        if not all([switch_ip, username, password]):
            return jsonify({"error": "Environment variables SWITCH_IP, SWITCH_USERNAME, and SWITCH_PASSWORD must be set."}), 400
        device = {
            "device_type": "dell_os10",
            "ip": switch_ip,
            "username": username,
            "password": password,
        }

        connection = ConnectHandler(**device)
        output = connection.send_command("show interface status")
        connection.disconnect()

        print("Raw Output:\n", output)

        interfaces = []
        lines = output.splitlines()

        # Find header row dynamically
        header_index = None
        for i, line in enumerate(lines):
            if "Port" in line and "Description" in line and "Status" in line:
                header_index = i
                break

        if header_index is None:
            return jsonify({"error": "Header row not found in output"})

        header = lines[header_index]
        data_lines = lines[header_index + 1:]

        column_names = ["port", "description", "status", "speed", "duplex", "mode", "vlan", "tagged_vlans"]
        column_positions = [header.index(col) for col in ["Port", "Description", "Status", "Speed", "Duplex", "Mode", "Vlan", "Tagged-Vlans"]]
        column_positions.append(len(header))

        for line in data_lines:
            if not line.strip() or "----" in line:
                continue

            values = [line[column_positions[i]:column_positions[i+1]].strip() for i in range(len(column_positions)-1)]
            interface_entry = dict(zip(column_names, values))
            interfaces.append(interface_entry)

        json_output = jsonify({"interfaces": interfaces})
        print("JSON Output:\n", json_output.get_json())
        return json_output

    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/api/get_interfaces", methods=["POST"])
def get_interfaces():
    """
    API to retrieve network interface statuses.
    """
    print(f"Fetching interfaces for Switch IP: {os.getenv('SWITCH_IP')}")

    return get_interface_status()

# ----------------------- TCPDUMP PACKET CAPTURE -----------------------


def run_tcpdump(interface, duration, filename):
    try:
        cmd = ["sudo", "tcpdump", "-i", interface, "-j", "adapter_unsynced", "-ttt", "-nn", "-w", filename]
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        time.sleep(duration)
        process.terminate()
        stdout, stderr = process.communicate()

        packets_info = parse_tcpdump_output(stderr)
        socketio.emit('capture_completed', {
            "message": "Capture completed",
            "file": filename,
            "packets_info": packets_info
        })
    except Exception as e:
        print(f"Error during capture: {e}")

def parse_tcpdump_output(output):
    info = {}
    for line in output.splitlines():
        if "packets captured" in line:
            info["packets_captured"] = int(line.split()[0])
        elif "packets received by filter" in line:
            info["packets_received"] = int(line.split()[0])
        elif "packets dropped by kernel" in line:
            info["packets_dropped"] = int(line.split()[0])
    return info

@app.route("/api/capture", methods=["POST"])
def start_capture():
    global capture_process
    try:
        data = request.json
        interface = data.get("interface", "ens3f0")
        filename = os.path.join(CAPTURE_DIR, f"capture_{int(time.time())}.pcap")
	
        capture_process = subprocess.Popen(["tcpdump", "-i", interface, "-w", filename])
        socketio.emit("capture_started", {"interface": interface, "file": filename})
        return jsonify({
            "message": f"Capture started on {interface}.",
            "file": filename
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/stop_capture", methods=["POST"])
def stop_capture():
    global capture_process
    if capture_process:
        capture_process.terminate()  # Stop tcpdump
        capture_process = None
        return jsonify({"message": "Capture stopped successfully."}), 200
    return jsonify({"error": "No active capture to stop."}), 400


@app.route("/api/download_capture/<filename>")
def download_capture(filename):
    file_path = os.path.join(CAPTURE_DIR, filename)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    return jsonify({"error": "File not found"}), 404

## FMADIO API ##
## Hardcoded filter for M-Plane test
@app.route("/sysmaster/capture_start", methods=["GET"])
def start_capture():
    
    global capture_process
    try:
        interface = request.args.get("interface", "ens3f0")  # Use request.args for GET
        # Automatically assign the capture name
        capture_name = "Fava"
        now = datetime.now() # Get current timestamp
        filename = os.path.join(CAPTURE_DIR, f"{capture_name}_{now.strftime('%Y%m%d_%H%M')}.pcap") # Format filename correctly before starting tcpdump
        response_str = now.strftime("[%a %b %d %H:%M:%S %Y] successfully started capture [{}]").format(capture_name)
        cmd = ["tcpdump", "-i", interface, "-j", "adapter_unsynced", "-ttt", "-nn", "-s", "9000", "-w", filename, "ip or port 67 or port 68"]
        capture_process = subprocess.Popen(cmd)
        socketio.emit("capture_started", {"interface": interface, "file": filename})
        return jsonify({
            "message": response_str,  # Matches required response format
            "file": filename  # Filename in expected format
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/sysmaster/capture_stop", methods=["GET"])
def stop_capture():
    global capture_process
    if capture_process:
        capture_process.terminate()  # Stop tcpdump
        capture_process = None
        return jsonify({"message": "Capture stopped successfully."}), 200
    return jsonify({"error": "No active capture to stop."}), 400


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5001, allow_unsafe_werkzeug=True)

