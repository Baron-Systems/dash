#!/bin/bash

# FM Dashboard - One Command Installation
# Auto-discovers everything, only asks for username/password

set -e

echo "╔════════════════════════════════════════════════════════════╗"
echo "║        FM Dashboard - تثبيت تلقائي كامل                   ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Get current directory
INSTALL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo -e "${BLUE}📂 Installation directory: $INSTALL_DIR${NC}"

# Check and fix permissions if needed
CURRENT_USER=$(whoami)
CURRENT_GROUP=$(id -gn)
DIR_OWNER=$(stat -c '%U' "$INSTALL_DIR" 2>/dev/null || echo "")

if [ "$DIR_OWNER" != "$CURRENT_USER" ] && [ "$DIR_OWNER" != "" ]; then
    echo -e "${YELLOW}⚠ Directory owned by $DIR_OWNER, fixing permissions...${NC}"
    if sudo chown -R $CURRENT_USER:$CURRENT_GROUP "$INSTALL_DIR" 2>/dev/null; then
        echo -e "${GREEN}   ✓ Permissions fixed${NC}"
    else
        echo -e "${RED}   ✗ Failed to fix permissions${NC}"
        echo -e "${YELLOW}   Run manually: sudo chown -R $CURRENT_USER:$CURRENT_GROUP $INSTALL_DIR${NC}"
    fi
fi

echo ""

# 1. Check Prerequisites
echo -e "${BLUE}🔍 Checking prerequisites...${NC}"

check_command() {
    if command -v $1 &> /dev/null; then
        echo -e "${GREEN}   ✓ $1 found${NC}"
        return 0
    else
        echo -e "${RED}   ✗ $1 not found${NC}"
        return 1
    fi
}

MISSING_DEPS=0

check_command python3 || MISSING_DEPS=1
check_command docker || MISSING_DEPS=1
check_command fm || { echo -e "${YELLOW}   ⚠ fm not found (optional)${NC}"; }

if [ $MISSING_DEPS -eq 1 ]; then
    echo -e "${RED}❌ Missing required dependencies${NC}"
    exit 1
fi

# Check docker group
if groups | grep -q docker; then
    echo -e "${GREEN}   ✓ User in docker group${NC}"
else
    echo -e "${YELLOW}   ⚠ User not in docker group${NC}"
    echo -e "${YELLOW}   Run: sudo usermod -aG docker $USER${NC}"
fi

echo ""

# 2. Auto-discover Python version
PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo -e "${GREEN}✓ Python $PYTHON_VERSION detected${NC}"
echo ""

# 3. Auto-discover FM stacks
echo -e "${BLUE}🔍 Auto-discovering FM stacks...${NC}"

FOUND_STACKS=()
STACK_PATHS=()

# Common locations to search
SEARCH_PATHS=(
    "$HOME"
    "/opt"
    "/home"
    "/srv"
)

for search_path in "${SEARCH_PATHS[@]}"; do
    if [ -d "$search_path" ]; then
        # Look for frappe-bench directories
        while IFS= read -r -d '' bench_path; do
            # Check if it's a valid FM/Frappe bench
            if [ -f "$bench_path/sites/common_site_config.json" ] || [ -f "$bench_path/docker-compose.yml" ]; then
                stack_name=$(basename $(dirname "$bench_path") 2>/dev/null || basename "$bench_path")
                echo -e "${GREEN}   ✓ Found: $bench_path${NC}"
                FOUND_STACKS+=("$stack_name")
                STACK_PATHS+=("$bench_path")
            fi
        done < <(find "$search_path" -maxdepth 3 -type d -name "frappe-bench" -o -name "*-bench" 2>/dev/null | head -10)
    fi
done

# Look for FM managed stacks
if command -v fm &> /dev/null; then
    FM_HOME="$HOME/.frappe"
    if [ -d "$FM_HOME" ]; then
        while IFS= read -r -d '' fm_stack; do
            stack_name=$(basename "$fm_stack")
            if [ -d "$fm_stack/workspace" ]; then
                bench_path="$fm_stack/workspace/frappe-bench"
                if [ -d "$bench_path" ]; then
                    echo -e "${GREEN}   ✓ Found FM stack: $fm_stack${NC}"
                    FOUND_STACKS+=("$stack_name")
                    STACK_PATHS+=("$fm_stack")
                fi
            fi
        done < <(find "$FM_HOME" -maxdepth 2 -type d 2>/dev/null)
    fi
fi

if [ ${#FOUND_STACKS[@]} -eq 0 ]; then
    echo -e "${YELLOW}   ⚠ No FM stacks found automatically${NC}"
    echo -e "${YELLOW}   Will create example configuration${NC}"
fi

echo ""

# 4. Get user credentials
echo -e "${BLUE}👤 Dashboard Credentials${NC}"
echo ""

read -p "Enter admin username [admin]: " ADMIN_USER
ADMIN_USER=${ADMIN_USER:-admin}

while true; do
    read -sp "Enter admin password: " ADMIN_PASS
    echo ""
    if [ -z "$ADMIN_PASS" ]; then
        echo -e "${RED}Password cannot be empty!${NC}"
        continue
    fi
    read -sp "Confirm password: " ADMIN_PASS_CONFIRM
    echo ""
    if [ "$ADMIN_PASS" = "$ADMIN_PASS_CONFIRM" ]; then
        break
    else
        echo -e "${RED}Passwords do not match!${NC}"
    fi
done

echo -e "${GREEN}✓ Credentials set${NC}"
echo ""

# 5. Create virtual environment
echo -e "${BLUE}📦 Setting up Python environment...${NC}"

cd "$INSTALL_DIR"

# Check if we can write to the directory
if [ ! -w "$INSTALL_DIR" ]; then
    echo -e "${YELLOW}⚠ Cannot write to $INSTALL_DIR, fixing permissions...${NC}"
    if sudo chown -R $CURRENT_USER:$CURRENT_GROUP "$INSTALL_DIR" 2>/dev/null; then
        echo -e "${GREEN}   ✓ Permissions fixed${NC}"
    else
        echo -e "${RED}   ✗ Failed to fix permissions${NC}"
        echo -e "${YELLOW}   Run manually: sudo chown -R $CURRENT_USER:$CURRENT_GROUP $INSTALL_DIR${NC}"
        exit 1
    fi
fi

# Remove existing venv if owned by wrong user
if [ -d "venv" ]; then
    VENV_OWNER=$(stat -c '%U' "venv" 2>/dev/null || echo "")
    if [ "$VENV_OWNER" != "$CURRENT_USER" ] && [ "$VENV_OWNER" != "" ]; then
        echo -e "${YELLOW}   ⚠ Removing venv owned by $VENV_OWNER...${NC}"
        rm -rf venv
    fi
fi

if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo -e "${GREEN}   ✓ Virtual environment created${NC}"
else
    echo -e "${YELLOW}   ⚠ Virtual environment already exists${NC}"
fi

source venv/bin/activate

# Install dependencies
echo -e "${BLUE}   Installing Python packages...${NC}"
pip install --upgrade pip -q
pip install -r requirements.txt -q
echo -e "${GREEN}   ✓ Dependencies installed${NC}"
echo ""

# 6. Generate secure secrets
echo -e "${BLUE}🔐 Generating secure secrets...${NC}"

AGENT_TOKEN=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
DASHBOARD_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")

echo -e "${GREEN}   ✓ Secrets generated${NC}"
echo ""

# 7. Determine backup path
BACKUP_PATH="/backups"
if [ ! -d "$BACKUP_PATH" ]; then
    echo -e "${BLUE}📁 Creating backup directory...${NC}"
    if sudo mkdir -p "$BACKUP_PATH" 2>/dev/null; then
        sudo chown -R $USER:$USER "$BACKUP_PATH"
        echo -e "${GREEN}   ✓ Backup directory created: $BACKUP_PATH${NC}"
    else
        BACKUP_PATH="$HOME/backups"
        mkdir -p "$BACKUP_PATH"
        echo -e "${YELLOW}   ⚠ Using alternative: $BACKUP_PATH${NC}"
    fi
else
    echo -e "${GREEN}   ✓ Backup directory exists: $BACKUP_PATH${NC}"
fi
echo ""

# 8. Create config.yaml
echo -e "${BLUE}📝 Creating configuration file...${NC}"

cat > config.yaml <<EOF
agent:
  name: $(hostname)
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
EOF

# Add discovered stacks
if [ ${#FOUND_STACKS[@]} -gt 0 ]; then
    for i in "${!FOUND_STACKS[@]}"; do
        stack_name="${FOUND_STACKS[$i]}"
        stack_path="${STACK_PATHS[$i]}"
        cat >> config.yaml <<EOF
  ${stack_name}:
    path: ${stack_path}
    type: fm
EOF
    done
else
    # Add example stack
    cat >> config.yaml <<EOF
  example:
    path: /home/$USER/frappe-bench
    type: fm
EOF
fi

cat >> config.yaml <<EOF

backups:
  base_path: ${BACKUP_PATH}
  retention_days: 30

dashboard:
  listen: 0.0.0.0
  port: 8000
  secret_key: ${DASHBOARD_SECRET}
  admin_username: ${ADMIN_USER}
  admin_password: ${ADMIN_PASS}
EOF

chmod 600 config.yaml
echo -e "${GREEN}   ✓ Configuration created${NC}"
echo ""

# 9. Test services
echo -e "${BLUE}🧪 Testing services...${NC}"

# Test agent in background
python agent/main.py &
AGENT_PID=$!
sleep 2

if kill -0 $AGENT_PID 2>/dev/null; then
    echo -e "${GREEN}   ✓ Agent service starts successfully${NC}"
    kill $AGENT_PID
    wait $AGENT_PID 2>/dev/null
else
    echo -e "${RED}   ✗ Agent service failed to start${NC}"
fi

# Test dashboard in background
python dashboard/main.py &
DASHBOARD_PID=$!
sleep 2

if kill -0 $DASHBOARD_PID 2>/dev/null; then
    echo -e "${GREEN}   ✓ Dashboard service starts successfully${NC}"
    kill $DASHBOARD_PID
    wait $DASHBOARD_PID 2>/dev/null
else
    echo -e "${RED}   ✗ Dashboard service failed to start${NC}"
fi

echo ""

# 10. Create startup scripts
echo -e "${BLUE}📜 Creating startup scripts...${NC}"

cat > start-agent.sh <<EOF
#!/bin/bash
cd "$INSTALL_DIR"
source venv/bin/activate
python agent/main.py
EOF

cat > start-dashboard.sh <<EOF
#!/bin/bash
cd "$INSTALL_DIR"
source venv/bin/activate
python dashboard/main.py
EOF

cat > start-all.sh <<EOF
#!/bin/bash
cd "$INSTALL_DIR"

echo "Starting FM Dashboard..."

# Start agent in background
bash start-agent.sh &
AGENT_PID=\$!
echo "Agent started (PID: \$AGENT_PID)"

# Start dashboard in background
bash start-dashboard.sh &
DASHBOARD_PID=\$!
echo "Dashboard started (PID: \$DASHBOARD_PID)"

echo ""
echo "Services are running!"
echo "Dashboard: http://$(hostname -I | awk '{print $1}'):8000"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Wait for interrupt
trap "kill \$AGENT_PID \$DASHBOARD_PID; exit" INT TERM
wait
EOF

chmod +x start-agent.sh start-dashboard.sh start-all.sh

echo -e "${GREEN}   ✓ Startup scripts created${NC}"
echo ""

# 11. Get local IP
LOCAL_IP=$(hostname -I | awk '{print $1}')

# 12. Installation complete
echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║              ✅ التثبيت اكتمل بنجاح!                      ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo -e "${GREEN}📊 Summary:${NC}"
echo "   Installation: $INSTALL_DIR"
echo "   Config file: $INSTALL_DIR/config.yaml"
echo "   Backups: $BACKUP_PATH"
echo "   Stacks found: ${#FOUND_STACKS[@]}"
if [ ${#FOUND_STACKS[@]} -gt 0 ]; then
    for stack in "${FOUND_STACKS[@]}"; do
        echo "      - $stack"
    done
fi
echo ""
echo -e "${BLUE}🚀 Quick Start:${NC}"
echo ""
echo "   1. Start all services:"
echo "      ${GREEN}cd $INSTALL_DIR && bash start-all.sh${NC}"
echo ""
echo "   2. Or start individually:"
echo "      Terminal 1: ${GREEN}bash start-agent.sh${NC}"
echo "      Terminal 2: ${GREEN}bash start-dashboard.sh${NC}"
echo ""
echo -e "${BLUE}🌐 Access Dashboard:${NC}"
echo "   ${GREEN}http://$LOCAL_IP:8000${NC}"
echo "   ${GREEN}http://localhost:8000${NC}"
echo ""
echo -e "${BLUE}🔑 Login Credentials:${NC}"
echo "   Username: ${GREEN}$ADMIN_USER${NC}"
echo "   Password: ${GREEN}(the one you entered)${NC}"
echo ""
echo -e "${BLUE}📚 Documentation:${NC}"
echo "   README.md - Full documentation"
echo "   QUICKSTART.md - Quick reference"
echo "   SECURITY.md - Security guidelines"
echo ""
echo -e "${YELLOW}⚠️  Security Note:${NC}"
echo "   Dashboard is accessible from network (0.0.0.0:8000)"
echo "   For production, use Nginx + SSL (see DEPLOYMENT.md)"
echo ""
echo -e "${BLUE}📝 Configuration:${NC}"
echo "   Edit: ${GREEN}nano config.yaml${NC}"
echo "   Then restart services"
echo ""
echo -e "${GREEN}🎉 Ready to use!${NC}"
echo ""

