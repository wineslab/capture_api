# Base image
FROM python:3.11-slim

# Install required system packages
RUN apt-get update && apt-get install -y \
    tcpdump libcap2-bin \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy application code
COPY app.py /app/app.py

# Create directory for captures
RUN mkdir -p /app/captures

# Install Python dependencies
RUN pip install flask flask-cors

# Expose the port the app runs on
EXPOSE 5000

# Add capability to use tcpdump without root inside the container
RUN setcap cap_net_raw,cap_net_admin=eip $(which tcpdump)

# Command to run the app
CMD ["python", "app.py"]
