#!/bin/bash

# HL7 Standards Development Dashboard Service Setup Script
# This script sets up the dashboard as a systemd service

set -e

echo "Setting up HL7 Standards Development Dashboard as a systemd service..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
SERVICE_NAME="hl7-standards-dev-dashboard"
SERVICE_FILE="${SERVICE_NAME}.service"
LOG_DIR="/var/log/hl7-standards-dev-dashboard"
APP_DIR="/home/ubuntu/code/hl7-standards-dev-dashboard"
VENV_PATH="/home/ubuntu/.venv"

echo -e "${YELLOW}Step 1: Creating log directory...${NC}"
sudo mkdir -p "$LOG_DIR"
sudo chown ubuntu:ubuntu "$LOG_DIR"
sudo chmod 755 "$LOG_DIR"

echo -e "${YELLOW}Step 2: Copying service file to systemd directory...${NC}"
sudo cp "$SERVICE_FILE" "/etc/systemd/system/"

echo -e "${YELLOW}Step 3: Reloading systemd daemon...${NC}"
sudo systemctl daemon-reload

echo -e "${YELLOW}Step 4: Enabling service to start on boot...${NC}"
sudo systemctl enable "$SERVICE_NAME"

echo -e "${YELLOW}Step 5: Starting the service...${NC}"
sudo systemctl start "$SERVICE_NAME"

echo -e "${GREEN}Service setup complete!${NC}"
echo ""
echo "Useful commands:"
echo "  Check status:     sudo systemctl status $SERVICE_NAME"
echo "  View logs:        sudo journalctl -u $SERVICE_NAME -f"
echo "  View app logs:    tail -f $LOG_DIR/app.log"
echo "  View error logs:  tail -f $LOG_DIR/error.log"
echo "  Restart service:  sudo systemctl restart $SERVICE_NAME"
echo "  Stop service:     sudo systemctl stop $SERVICE_NAME"
echo "  Disable service:  sudo systemctl disable $SERVICE_NAME"
echo ""
echo -e "${GREEN}Dashboard should now be running at: http://$(curl -s ifconfig.me):8000${NC}"
