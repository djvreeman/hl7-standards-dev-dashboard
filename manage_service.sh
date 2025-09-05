#!/bin/bash

# HL7 Standards Development Dashboard Service Management Script

SERVICE_NAME="hl7-standards-dev-dashboard"
LOG_DIR="/var/log/hl7-standards-dev-dashboard"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

show_help() {
    echo "HL7 Standards Development Dashboard Service Manager"
    echo ""
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  status     - Show service status"
    echo "  start      - Start the service"
    echo "  stop       - Stop the service"
    echo "  restart    - Restart the service"
    echo "  logs       - Show live logs from journalctl"
    echo "  app-logs   - Show application logs"
    echo "  error-logs - Show error logs"
    echo "  enable     - Enable service to start on boot"
    echo "  disable    - Disable service from starting on boot"
    echo "  help       - Show this help message"
}

case "$1" in
    status)
        echo -e "${BLUE}Service Status:${NC}"
        sudo systemctl status "$SERVICE_NAME"
        ;;
    start)
        echo -e "${YELLOW}Starting service...${NC}"
        sudo systemctl start "$SERVICE_NAME"
        echo -e "${GREEN}Service started!${NC}"
        ;;
    stop)
        echo -e "${YELLOW}Stopping service...${NC}"
        sudo systemctl stop "$SERVICE_NAME"
        echo -e "${GREEN}Service stopped!${NC}"
        ;;
    restart)
        echo -e "${YELLOW}Restarting service...${NC}"
        sudo systemctl restart "$SERVICE_NAME"
        echo -e "${GREEN}Service restarted!${NC}"
        ;;
    logs)
        echo -e "${BLUE}Live service logs (Ctrl+C to exit):${NC}"
        sudo journalctl -u "$SERVICE_NAME" -f
        ;;
    app-logs)
        echo -e "${BLUE}Application logs (Ctrl+C to exit):${NC}"
        tail -f "$LOG_DIR/app.log"
        ;;
    error-logs)
        echo -e "${BLUE}Error logs (Ctrl+C to exit):${NC}"
        tail -f "$LOG_DIR/error.log"
        ;;
    enable)
        echo -e "${YELLOW}Enabling service to start on boot...${NC}"
        sudo systemctl enable "$SERVICE_NAME"
        echo -e "${GREEN}Service enabled!${NC}"
        ;;
    disable)
        echo -e "${YELLOW}Disabling service from starting on boot...${NC}"
        sudo systemctl disable "$SERVICE_NAME"
        echo -e "${GREEN}Service disabled!${NC}"
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo -e "${RED}Unknown command: $1${NC}"
        echo ""
        show_help
        exit 1
        ;;
esac
