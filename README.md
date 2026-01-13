# FM Dashboard - Frappe Manager Control Panel

A secure web-based dashboard for managing multiple Frappe stacks (fm + Docker) from anywhere, without SSH. Provides full control over benches, sites, backups, and scheduling.

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![Python](https://img.shields.io/badge/python-3.8+-green)
![License](https://img.shields.io/badge/license-MIT-blue)

## 🎯 Features

### Stack & Site Management
- ✅ Auto-discover and manage FM stacks
- ✅ View stack status and Docker containers
- ✅ Restart stacks and individual sites
- ✅ Run site migrations
- ✅ Update stacks (pull latest images)

### Backup System
- ✅ Manual backup creation via UI
- ✅ Download backups directly from browser
- ✅ Organized backup storage
- ✅ Automatic backup retention

### Scheduler
- ✅ Schedule automatic backups (daily/weekly/monthly)
- ✅ Configurable backup times
- ✅ Persistent job storage
- ✅ View upcoming backup schedules

### Security
- ✅ Login authentication system
- ✅ Session-based auth
- ✅ Token-based agent communication
- ✅ No SSH, sudo, or root required
- ✅ HTTPS-only access
- ✅ Command whitelist (no arbitrary shell execution)

## 🏗️ Architecture

```
[ User Browser ]
       ↓
[ Web Dashboard (Port 8000) ]
       ↓
[ Nginx Reverse Proxy + SSL ]
       ↓
[ Agent Service (Port 9100, localhost-only) ]
       ↓
[ FM / Docker / Filesystem ]
```

## 📋 Prerequisites

- Python 3.8+
- Docker and Docker Compose
- Frappe Manager (fm) installed
- Nginx (for production)
- User account with Docker group access

## 🚀 Installation

### 1. Clone or Download

```bash
cd /home/manager-pc/Desktop/dash
```

### 2. Install Dependencies

```bash
# Install Python packages
pip3 install -r requirements.txt

# Or use virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure

Edit `config.yaml`:

```yaml
agent:
  name: host-01
  listen: 127.0.0.1
  port: 9100

security:
  token: YOUR_SUPER_SECRET_TOKEN_HERE  # CHANGE THIS!
  allowed_actions:
    - restart_stack
    - restart_site
    - migrate_site
    - backup_site
    - update_stack
    - list_sites
    - get_stack_status

stacks:
  prod:
    path: /opt/fm/prod  # CHANGE to your FM stack path
    type: fm
  dev:
    path: /opt/fm/dev   # CHANGE to your FM stack path
    type: fm

backups:
  base_path: /backups  # CHANGE to your backup directory
  retention_days: 30

dashboard:
  listen: 127.0.0.1
  port: 8000
  secret_key: YOUR_DASHBOARD_SECRET_KEY_HERE  # CHANGE THIS!
  admin_username: admin
  admin_password: admin123  # CHANGE THIS!
```

### 4. Create Backup Directory

```bash
sudo mkdir -p /backups
sudo chown -R $USER:$USER /backups
```

### 5. Test Services Manually

#### Test Agent:

```bash
cd /home/manager-pc/Desktop/dash
python3 agent/main.py
```

Open another terminal and test:

```bash
curl -H "Authorization: Bearer YOUR_TOKEN" http://127.0.0.1:9100/stacks
```

#### Test Dashboard:

```bash
cd /home/manager-pc/Desktop/dash
python3 dashboard/main.py
```

Visit: http://127.0.0.1:8000

## 🔧 Production Deployment

### 1. Install as systemd Services

```bash
# Copy service files
sudo cp systemd/fm-agent.service /etc/systemd/system/
sudo cp systemd/fm-dashboard.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable services (start on boot)
sudo systemctl enable fm-agent
sudo systemctl enable fm-dashboard

# Start services
sudo systemctl start fm-agent
sudo systemctl start fm-dashboard

# Check status
sudo systemctl status fm-agent
sudo systemctl status fm-dashboard
```

### 2. Configure Nginx

```bash
# Install Nginx (if not installed)
sudo apt update
sudo apt install nginx certbot python3-certbot-nginx

# Copy Nginx configuration
sudo cp nginx/fm-dashboard.conf /etc/nginx/sites-available/

# Edit the configuration and change 'dashboard.example.com' to your domain
sudo nano /etc/nginx/sites-available/fm-dashboard.conf

# Enable site
sudo ln -s /etc/nginx/sites-available/fm-dashboard.conf /etc/nginx/sites-enabled/

# Test Nginx configuration
sudo nginx -t

# Reload Nginx
sudo systemctl reload nginx
```

### 3. Setup SSL Certificate

```bash
# Using Let's Encrypt
sudo certbot --nginx -d dashboard.example.com

# Or using Cloudflare (if using Cloudflare proxy)
# Just update the SSL paths in nginx config to your Cloudflare origin certificate
```

### 4. Verify Installation

```bash
# Check services are running
sudo systemctl status fm-agent fm-dashboard nginx

# Check logs
sudo journalctl -u fm-agent -f
sudo journalctl -u fm-dashboard -f
```

## 🎮 Usage

### Access Dashboard

1. Open your browser
2. Navigate to: `https://dashboard.example.com`
3. Login with credentials from `config.yaml`

### Managing Stacks

1. **View Stacks**: Main dashboard shows all configured stacks
2. **Restart Stack**: Click "Restart" on any stack card
3. **Update Stack**: Click "Update" to pull latest Docker images
4. **View Details**: Click "View" to see sites and containers

### Managing Sites

1. Navigate to a stack's detail page
2. For each site you can:
   - **Restart**: Restart the backend container
   - **Migrate**: Run bench migrate
   - **Backup**: Create immediate backup
   - **View Backups**: See all available backups

### Scheduling Backups

1. Go to **Scheduler** page
2. Select:
   - Stack
   - Site
   - Schedule type (Daily/Weekly/Monthly)
   - Time
3. Click "Add Schedule"
4. View and manage scheduled jobs in the table below

### Downloading Backups

1. Navigate to a site's backup page
2. Click "Download" on any backup file
3. Backup will download as `.sql.gz` file

## 🔐 Security Best Practices

### Production Checklist

- [ ] Change `admin_password` in `config.yaml`
- [ ] Generate strong random `secret_key` and `token`
- [ ] Use HTTPS only (configure SSL certificate)
- [ ] Keep agent on localhost only (127.0.0.1)
- [ ] Regularly update dependencies
- [ ] Monitor logs for suspicious activity
- [ ] Set up firewall rules
- [ ] Backup the `/backups` directory

### Generate Secure Secrets

```bash
# Generate random token
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# Generate secret key
python3 -c "import secrets; print(secrets.token_hex(32))"
```

## 📁 Directory Structure

```
dash/
├── agent/
│   └── main.py              # Agent service
├── dashboard/
│   ├── main.py              # Dashboard service
│   └── templates/           # HTML templates
│       ├── base.html
│       ├── login.html
│       ├── dashboard.html
│       ├── stack_detail.html
│       ├── backups.html
│       ├── scheduler.html
│       └── error.html
├── systemd/
│   ├── fm-agent.service     # Agent systemd service
│   └── fm-dashboard.service # Dashboard systemd service
├── nginx/
│   └── fm-dashboard.conf    # Nginx configuration
├── config.yaml              # Main configuration
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

## 🛠️ Troubleshooting

### Service Won't Start

```bash
# Check service status
sudo systemctl status fm-agent
sudo systemctl status fm-dashboard

# View logs
sudo journalctl -u fm-agent -n 50
sudo journalctl -u fm-dashboard -n 50

# Check if ports are available
sudo netstat -tulpn | grep 8000
sudo netstat -tulpn | grep 9100
```

### Agent Can't Execute Commands

```bash
# Ensure user is in docker group
sudo usermod -aG docker $USER
newgrp docker

# Test docker access
docker ps

# Verify FM is installed
fm --version
```

### Backup Fails

```bash
# Check backup directory permissions
ls -la /backups

# Ensure user can write
sudo chown -R $USER:$USER /backups

# Check disk space
df -h
```

### Can't Connect to Agent

```bash
# Test agent endpoint
curl -H "Authorization: Bearer YOUR_TOKEN" http://127.0.0.1:9100/

# Check if agent is listening
sudo netstat -tulpn | grep 9100

# Verify token matches in config
cat config.yaml | grep token
```

## 📊 Logs

### View Real-time Logs

```bash
# Agent logs
sudo journalctl -u fm-agent -f

# Dashboard logs
sudo journalctl -u fm-dashboard -f

# Nginx access logs
sudo tail -f /var/log/nginx/fm-dashboard-access.log

# Nginx error logs
sudo tail -f /var/log/nginx/fm-dashboard-error.log
```

## 🔄 Updating

```bash
# Pull latest code
cd /home/manager-pc/Desktop/dash
git pull  # if using git

# Update dependencies
pip install -r requirements.txt --upgrade

# Restart services
sudo systemctl restart fm-agent
sudo systemctl restart fm-dashboard
```

## 🧪 Development

### Run in Development Mode

```bash
# Terminal 1 - Agent
cd /home/manager-pc/Desktop/dash
python3 agent/main.py

# Terminal 2 - Dashboard
cd /home/manager-pc/Desktop/dash
python3 dashboard/main.py
```

### Development with Auto-reload

```bash
# Agent with auto-reload
uvicorn agent.main:app --reload --host 127.0.0.1 --port 9100

# Dashboard with auto-reload
uvicorn dashboard.main:app --reload --host 127.0.0.1 --port 8000
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📝 License

This project is licensed under the MIT License.

## ⚠️ Disclaimer

This software is provided "as is" without warranty. Always test in a development environment first. Ensure you have proper backups before performing any operations on production systems.

## 🆘 Support

For issues and questions:
1. Check the troubleshooting section
2. Review logs for errors
3. Ensure all prerequisites are met
4. Verify configuration is correct

## 🚧 Future Enhancements (Not Implemented)

- Multi-server support
- Remote agents
- RBAC (viewer/operator/admin roles)
- Metrics (CPU, RAM, disk usage)
- Telegram/Email notifications
- Backup encryption
- Backup retention policies
- Site creation/deletion
- App installation management

## 📚 References

- [Frappe Manager Documentation](https://github.com/rtcamp/Frappe-Manager)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Docker Documentation](https://docs.docker.com/)
- [Nginx Documentation](https://nginx.org/en/docs/)

