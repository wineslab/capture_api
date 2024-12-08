import React, { useState, useEffect } from "react";
import axios from "axios";
import { io } from "socket.io-client";

const App = () => {
  const [interfaceName, setInterfaceName] = useState("");
  const [duration, setDuration] = useState(10);
  const [captureLink, setCaptureLink] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [showDialog, setShowDialog] = useState(false);
  const [packetsInfo, setPacketsInfo] = useState(null);


  useEffect(() => {
      const socket = io(`ws://${process.env.REACT_APP_API_HOST}`, {
        transports: ["websocket"], // Ensure WebSocket transport is used
      });
  
      socket.on("connect", () => {
        console.log("Connected to WebSocket server");
      });
  
      socket.on("disconnect", () => {
        console.log("Disconnected from WebSocket server");
      });
  
      socket.on("capture_completed", (data) => {
        console.log("Received event:", data);
        setCaptureLink(data.file);
        setPacketsInfo(data.packets_info); // Set packets info from the WebSocket message
        setShowDialog(true); // Open the dialog
        setLoading(false); // Stop the loading spinner
      });

    return () => {
      socket.close(); // Cleanup on component unmount
    };
  }, []);

  const handleCapture = async () => {
    setLoading(true);
    setCaptureLink("");
    setError("");

    try {
      const response = await axios.post(`http://${process.env.REACT_APP_API_HOST}/capture`, {
            interface: interfaceName,
            duration,
      });
      const filePath = response.data.file;
      setTimeout(() => {
        setCaptureLink(filePath);
        setLoading(false);
      }, duration * 1000);
    } catch (err) {
      setError("Failed to start capture. Please check the input and try again.");
      setLoading(false);
    }
  };

  return (
    <div style={styles.container}>
      <h1 style={styles.header}>Network Capture</h1>
      <div style={styles.form}>
        <label style={styles.label}>Interface:</label>
        <input
          type="text"
          value={interfaceName}
          onChange={(e) => setInterfaceName(e.target.value)}
          placeholder="e.g., ens3f1"
          style={styles.input}
        />
        <label style={styles.label}>Duration (seconds):</label>
        <input
          type="number"
          value={duration}
          onChange={(e) => setDuration(e.target.value)}
          min="1"
          style={styles.input}
        />
        <button
          onClick={handleCapture}
          style={styles.button}
          disabled={loading || !interfaceName || duration <= 0}
        >
          {loading ? "Capturing..." : "Start Capture"}
        </button>
      </div>

      {error && <p style={styles.error}>{error}</p>}

      {/* {captureLink && (
        <div style={styles.result}>
          <p>Capture complete! Download your file:</p>
          <a href={`${process.env.REACT_APP_API_HOST}${captureLink}`} download style={styles.link}>
            Download Capture
          </a>
        </div>
      )} */}

      {captureLink && showDialog && (
        <div style={styles.dialog}>
          <h2>Capture Complete!</h2>
          <p>File is ready for download:</p>
          <a
            href={`http://${process.env.REACT_APP_API_HOST}${captureLink}`}
            download
            style={styles.link}
          >
            Download Capture
          </a>
          {packetsInfo && (
            <div style={styles.packetsInfo}>
              <p>Packets Captured: {packetsInfo.packets_captured}</p>
              <p>Packets Received: {packetsInfo.packets_received}</p>
              <p>Packets Dropped: {packetsInfo.packets_dropped}</p>
            </div>
          )}
          <button style={styles.button} onClick={() => setShowDialog(false)}>
            Close
          </button>
        </div>
      )}

    </div>
  );
};

const styles = {
  container: {
    fontFamily: "Arial, sans-serif",
    textAlign: "center",
    padding: "20px",
    maxWidth: "600px",
    margin: "0 auto",
  },
  header: {
    color: "#333",
  },
  form: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    gap: "10px",
  },
  label: {
    fontSize: "16px",
    fontWeight: "bold",
  },
  input: {
    padding: "10px",
    fontSize: "16px",
    width: "200px",
  },
  button: {
    backgroundColor: "#007BFF",
    color: "#FFF",
    border: "none",
    padding: "10px 20px",
    fontSize: "16px",
    borderRadius: "5px",
    cursor: "pointer",
  },
  buttonDisabled: {
    backgroundColor: "#CCCCCC",
  },
  error: {
    color: "red",
    fontSize: "14px",
  },
  result: {
    marginTop: "20px",
    fontSize: "16px",
  },
  link: {
    color: "#007BFF",
    textDecoration: "none",
    fontWeight: "bold",
  },
};

export default App;
