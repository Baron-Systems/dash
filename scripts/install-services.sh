#!/bin/bash

# Install systemd services for FM Dashboard

set -e

echo "=================================="
echo "FM Dashboard Service Installer"
echo "=================================="
echo ""

# Check if running with sudo
if [ "$EUID" -ne 0 ]; then 
    echo "⚠️  This script must be run with sudo"
    echo "Usage: sudo bash scripts/install-services.sh"
    exit 1
fi

# Get the actual user (not root when using sudo)
REAL_USER=${SUDO_USER:-$USER}
USER_HOME=$(getent passwd "$REAL_USER" | cut -d: -f6)

echo "Installing services for user: $REAL_USER"
echo "Home directory: $USER_HOME"
echo ""

# Determine the project directory
PROJECT_DIR="$USER_HOME/Desktop/dash"

if [ ! -d "$PROJECT_DIR" ]; then
    read -p "Project directory not found at $PROJECT_DIR. Enter correct path: " PROJECT_DIR
    if [ ! -d "$PROJECT_DIR" ]; then
        echo "❌ Directory not found: $PROJECT_DIR"
        exit 1
    fi
fi

echo "Project directory: $PROJECT_DIR"

# Check if virtual environment exists
VENV_PYTHON="$PROJECT_DIR/venv/bin/python3"

if [ ! -f "$VENV_PYTHON" ]; then
    echo "❌ Virtual environment not found at $PROJECT_DIR/venv"
    echo "Run setup.sh first to create virtual environment"
    exit 1
fi

echo "✅ Virtual environment found"

# Check if config exists
if [ ! -f "$PROJECT_DIR/config.yaml" ]; then
    echo "❌ Configuration file not found: $PROJECT_DIR/config.yaml"
    echo "Run setup.sh first to create configuration"
    exit 1
fi

echo "✅ Configuration found"

# Create service files with correct paths
echo ""
echo "📝 Creating service files..."

# Agent service
cat > /etc/systemd/system/fm-agent.service <<EOF
[Unit]
Description=FM Agent Service
After=network.target docker.service
Wants=docker.service

[Service]
Type=simple
User=$REAL_USER
Group=docker
WorkingDirectory=$PROJECT_DIR
Environment="CONFIG_PATH=$PROJECT_DIR/config.yaml"
Environment="PATH=/usr/local/bin:/usr/bin:/bin"

ExecStart=$VENV_PYTHON -m uvicorn agent.main:app --host 127.0.0.1 --port 9100

Restart=always
RestartSec=5

# Security settings
NoNewPrivileges=true
PrivateTmp=true

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=fm-agent

[Install]
WantedBy=multi-user.target
EOF

echo "✅ Created fm-agent.service"

# Dashboard service
cat > /etc/systemd/system/fm-dashboard.service <<EOF
[Unit]
Description=FM Dashboard Web Service
After=network.target fm-agent.service
Wants=fm-agent.service

[Service]
Type=simple
User=$REAL_USER
Group=$REAL_USER
WorkingDirectory=$PROJECT_DIR
Environment="CONFIG_PATH=$PROJECT_DIR/config.yaml"
Environment="PATH=/usr/local/bin:/usr/bin:/bin"

ExecStart=$VENV_PYTHON -m uvicorn dashboard.main:app --host 127.0.0.1 --port 8000

Restart=always
RestartSec=5

# Security settings
NoNewPrivileges=true
PrivateTmp=true

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=fm-dashboard

[Install]
WantedBy=multi-user.target
EOF

echo "✅ Created fm-dashboard.service"

# Reload systemd
echo ""
echo "🔄 Reloading systemd..."
systemctl daemon-reload

# Enable services
echo ""
echo "🔄 Enabling services..."
systemctl enable fm-agent
systemctl enable fm-dashboard

echo "✅ Services enabled (will start on boot)"

# Ask to start services now
echo ""
read -p "Start services now? (y/n) " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🚀 Starting services..."
    systemctl start fm-agent
    systemctl start fm-dashboard
    
    # Wait a moment for services to start
    sleep 2
    
    # Check status
    echo ""
    echo "📊 Service Status:"
    echo "=================="
    systemctl status fm-agent --no-pager -l
    echo ""
    systemctl status fm-dashboard --no-pager -l
    
    echo ""
    echo "✅ Services started"
else
    echo "ℹ️  Services not started. Start manually with:"
    echo "   sudo systemctl start fm-agent"
    echo "   sudo systemctl start fm-dashboard"
fi

echo ""
echo "=================================="
echo "✅ Installation Complete!"
echo "=================================="
echo ""
echo "Useful commands:"
echo "  sudo systemctl status fm-agent"
echo "  sudo systemctl status fm-dashboard"
echo "  sudo systemctl restart fm-agent"
echo "  sudo systemctl restart fm-dashboard"
echo "  sudo journalctl -u fm-agent -f"
echo "  sudo journalctl -u fm-dashboard -f"
echo ""

