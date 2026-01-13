#!/bin/bash

# FM Dashboard Setup Script
# This script helps automate the initial setup

set -e

echo "=================================="
echo "FM Dashboard Setup Script"
echo "=================================="
echo ""

# Check if running as root
if [ "$EUID" -eq 0 ]; then 
    echo "⚠️  Please do not run this script as root"
    exit 1
fi

# Check Python version
PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
REQUIRED_VERSION="3.8"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo "❌ Python 3.8+ is required. Current version: $PYTHON_VERSION"
    exit 1
fi

echo "✅ Python version: $PYTHON_VERSION"

# Check if docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed"
    echo "Install with: sudo apt install docker.io"
    exit 1
fi

echo "✅ Docker is installed"

# Check if user is in docker group
if ! groups | grep -q docker; then
    echo "⚠️  Current user is not in docker group"
    echo "Add user to docker group with:"
    echo "  sudo usermod -aG docker $USER"
    echo "  newgrp docker"
    exit 1
fi

echo "✅ User is in docker group"

# Check if fm is installed
if ! command -v fm &> /dev/null; then
    echo "⚠️  Frappe Manager (fm) is not installed or not in PATH"
    echo "Please install fm first: https://github.com/rtcamp/Frappe-Manager"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    echo "✅ Frappe Manager (fm) is installed"
fi

# Create virtual environment
echo ""
echo "📦 Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install dependencies
echo ""
echo "📦 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "✅ Dependencies installed"

# Generate secrets
echo ""
echo "🔐 Generating secure secrets..."
AGENT_TOKEN=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')
DASHBOARD_SECRET=$(python3 -c 'import secrets; print(secrets.token_hex(32))')

echo ""
echo "Generated secrets (save these!):"
echo "=================================="
echo "Agent Token: $AGENT_TOKEN"
echo "Dashboard Secret: $DASHBOARD_SECRET"
echo "=================================="
echo ""

# Prompt for configuration
echo "📝 Configuration Setup"
echo ""

read -p "Enter backup directory path [/backups]: " BACKUP_PATH
BACKUP_PATH=${BACKUP_PATH:-/backups}

read -p "Enter admin username [admin]: " ADMIN_USER
ADMIN_USER=${ADMIN_USER:-admin}

read -sp "Enter admin password: " ADMIN_PASS
echo ""

if [ -z "$ADMIN_PASS" ]; then
    echo "❌ Admin password cannot be empty"
    exit 1
fi

# Ask for FM stack paths
echo ""
echo "Enter your FM stack configurations (press Enter with empty name to finish):"
STACK_CONFIG=""
STACK_COUNT=0

while true; do
    read -p "Stack name (or Enter to finish): " STACK_NAME
    if [ -z "$STACK_NAME" ]; then
        break
    fi
    
    read -p "Stack path: " STACK_PATH
    
    if [ ! -d "$STACK_PATH" ]; then
        echo "⚠️  Warning: Path $STACK_PATH does not exist"
        read -p "Continue anyway? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            continue
        fi
    fi
    
    STACK_CONFIG="${STACK_CONFIG}  ${STACK_NAME}:
    path: ${STACK_PATH}
    type: fm
"
    STACK_COUNT=$((STACK_COUNT + 1))
done

if [ $STACK_COUNT -eq 0 ]; then
    echo "⚠️  No stacks configured. Adding example stacks."
    STACK_CONFIG="  prod:
    path: /opt/fm/prod
    type: fm
  dev:
    path: /opt/fm/dev
    type: fm
"
fi

# Create config.yaml
echo ""
echo "📝 Creating config.yaml..."

cat > config.yaml <<EOF
agent:
  name: host-01
  listen: 127.0.0.1
  port: 9100

security:
  token: ${AGENT_TOKEN}
  allowed_actions:
    - restart_stack
    - restart_site
    - migrate_site
    - backup_site
    - update_stack
    - list_sites
    - get_stack_status

stacks:
${STACK_CONFIG}

backups:
  base_path: ${BACKUP_PATH}
  retention_days: 30

dashboard:
  listen: 127.0.0.1
  port: 8000
  secret_key: ${DASHBOARD_SECRET}
  admin_username: ${ADMIN_USER}
  admin_password: ${ADMIN_PASS}
EOF

echo "✅ Configuration created"

# Create backup directory
echo ""
echo "📁 Creating backup directory..."
if [ ! -d "$BACKUP_PATH" ]; then
    sudo mkdir -p "$BACKUP_PATH"
    sudo chown -R $USER:$USER "$BACKUP_PATH"
    echo "✅ Backup directory created: $BACKUP_PATH"
else
    echo "✅ Backup directory exists: $BACKUP_PATH"
fi

# Set permissions
chmod 600 config.yaml

echo ""
echo "=================================="
echo "✅ Setup Complete!"
echo "=================================="
echo ""
echo "Next steps:"
echo "1. Test the services manually:"
echo "   source venv/bin/activate"
echo "   python3 agent/main.py"
echo ""
echo "2. In another terminal:"
echo "   source venv/bin/activate"
echo "   python3 dashboard/main.py"
echo ""
echo "3. Access dashboard: http://127.0.0.1:8000"
echo "   Username: $ADMIN_USER"
echo "   Password: (the one you entered)"
echo ""
echo "4. For production deployment, see DEPLOYMENT.md"
echo ""
echo "Configuration saved to: config.yaml"
echo "Secrets saved above - store them securely!"
echo ""

