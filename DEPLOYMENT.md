# Deployment Guide

Complete step-by-step deployment guide for FM Dashboard.

## Prerequisites

### System Requirements

- Ubuntu 20.04+ / Debian 11+ (or similar)
- Python 3.8+
- Docker and Docker Compose
- Nginx
- 2GB+ RAM
- 10GB+ free disk space

### User Requirements

- User must be in `docker` group
- User must have access to FM stacks
- No root access required for operation

## Step-by-Step Deployment

### 1. Prepare System

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y python3 python3-pip python3-venv nginx docker.io docker-compose git

# Add user to docker group
sudo usermod -aG docker $USER

# Apply group changes (or logout/login)
newgrp docker

# Verify docker access
docker ps
```

### 2. Setup Application

```bash
# Navigate to application directory
cd /home/manager-pc/Desktop/dash

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Application

```bash
# Generate secure tokens
echo "Agent Token: $(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
echo "Dashboard Secret: $(python3 -c 'import secrets; print(secrets.token_hex(32))')"

# Edit configuration
nano config.yaml
```

**Important configurations to change:**

```yaml
security:
  token: "PASTE_AGENT_TOKEN_HERE"  # From step above

stacks:
  prod:
    path: /opt/fm/prod  # Your actual FM stack path
  dev:
    path: /opt/fm/dev   # Your actual FM stack path

backups:
  base_path: /backups   # Your backup directory

dashboard:
  secret_key: "PASTE_DASHBOARD_SECRET_HERE"  # From step above
  admin_username: admin
  admin_password: "STRONG_PASSWORD_HERE"  # Choose a strong password
```

### 4. Setup Backup Directory

```bash
# Create backup directory
sudo mkdir -p /backups

# Set ownership
sudo chown -R $USER:$USER /backups

# Set permissions
chmod 755 /backups
```

### 5. Test Services

#### Test Agent Service:

```bash
# Start agent manually
cd /home/manager-pc/Desktop/dash
source venv/bin/activate
python3 agent/main.py
```

In another terminal:

```bash
# Test agent (replace TOKEN with your actual token)
curl -H "Authorization: Bearer YOUR_TOKEN" http://127.0.0.1:9100/
curl -H "Authorization: Bearer YOUR_TOKEN" http://127.0.0.1:9100/stacks
```

Expected response: JSON with stack information

Press `Ctrl+C` to stop the agent.

#### Test Dashboard Service:

```bash
# Start dashboard manually
cd /home/manager-pc/Desktop/dash
source venv/bin/activate
python3 dashboard/main.py
```

Open browser: http://127.0.0.1:8000

- Should see login page
- Login with credentials from config.yaml
- Should see dashboard with stacks

Press `Ctrl+C` to stop the dashboard.

### 6. Install systemd Services

#### Update Service Files

Edit service files to use virtual environment:

```bash
# Edit agent service
sudo nano systemd/fm-agent.service
```

Change ExecStart line to:

```ini
ExecStart=/home/manager-pc/Desktop/dash/venv/bin/python3 -m uvicorn agent.main:app --host 127.0.0.1 --port 9100
```

```bash
# Edit dashboard service
sudo nano systemd/fm-dashboard.service
```

Change ExecStart line to:

```ini
ExecStart=/home/manager-pc/Desktop/dash/venv/bin/python3 -m uvicorn dashboard.main:app --host 127.0.0.1 --port 8000
```

#### Install Services

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

Expected output: Both services should be "active (running)"

### 7. Configure Nginx

#### Prepare Nginx Config

```bash
# Copy nginx config
sudo cp nginx/fm-dashboard.conf /etc/nginx/sites-available/

# Edit config - CHANGE 'dashboard.example.com' to your domain
sudo nano /etc/nginx/sites-available/fm-dashboard.conf
```

Replace all instances of `dashboard.example.com` with your actual domain.

#### For Local Testing (No Domain)

If testing locally without a domain, you can simplify the config:

```bash
# Create simple local config
sudo nano /etc/nginx/sites-available/fm-dashboard-local.conf
```

```nginx
upstream fm_dashboard {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name localhost;
    
    client_max_body_size 500M;
    proxy_connect_timeout 600;
    proxy_send_timeout 600;
    proxy_read_timeout 600;
    
    location / {
        proxy_pass http://fm_dashboard;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/fm-dashboard-local.conf /etc/nginx/sites-enabled/

# Test nginx config
sudo nginx -t

# Reload nginx
sudo systemctl reload nginx
```

Access via: http://YOUR_SERVER_IP

### 8. Setup SSL (Production Only)

#### Using Let's Encrypt:

```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Get certificate (replace with your domain)
sudo certbot --nginx -d dashboard.example.com

# Test auto-renewal
sudo certbot renew --dry-run
```

#### Using Cloudflare Origin Certificate:

1. Generate Origin Certificate in Cloudflare Dashboard
2. Save certificate and key:
   - `/etc/ssl/certs/cloudflare-origin.pem`
   - `/etc/ssl/private/cloudflare-origin-key.pem`
3. Update nginx config SSL paths
4. Reload nginx

### 9. Configure Firewall

```bash
# If using UFW
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 22/tcp  # SSH
sudo ufw enable
sudo ufw status

# Note: Ports 8000 and 9100 should NOT be exposed externally
# They should only be accessible via localhost
```

### 10. Verify Deployment

#### Check Services:

```bash
# Service status
sudo systemctl status fm-agent fm-dashboard nginx

# Check ports
sudo netstat -tulpn | grep -E ':(80|443|8000|9100)'
```

Expected:
- Port 80: nginx (0.0.0.0)
- Port 443: nginx (0.0.0.0) - if SSL configured
- Port 8000: python (127.0.0.1 ONLY)
- Port 9100: python (127.0.0.1 ONLY)

#### Check Logs:

```bash
# Agent logs
sudo journalctl -u fm-agent -n 50

# Dashboard logs
sudo journalctl -u fm-dashboard -n 50

# Nginx logs
sudo tail -f /var/log/nginx/fm-dashboard-access.log
```

#### Test Access:

1. Open browser
2. Navigate to your domain (or server IP if local)
3. Login with admin credentials
4. Verify:
   - Stacks are visible
   - Can navigate to stack details
   - Can see sites
   - Actions work (restart, backup, etc.)

## Post-Deployment

### Security Hardening

```bash
# Restrict config file permissions
chmod 600 /home/manager-pc/Desktop/dash/config.yaml

# Ensure backup directory is secure
chmod 755 /backups
```

### Setup Monitoring

```bash
# Monitor service logs
sudo journalctl -u fm-agent -f
sudo journalctl -u fm-dashboard -f

# Setup log rotation if needed
sudo nano /etc/logrotate.d/fm-dashboard
```

### Regular Maintenance

```bash
# Update dependencies monthly
cd /home/manager-pc/Desktop/dash
source venv/bin/activate
pip install -r requirements.txt --upgrade
sudo systemctl restart fm-agent fm-dashboard

# Check disk space
df -h

# Review logs for errors
sudo journalctl -u fm-agent --since "1 week ago" | grep -i error
sudo journalctl -u fm-dashboard --since "1 week ago" | grep -i error
```

### Backup Configuration

```bash
# Backup important files
tar -czf fm-dashboard-config-backup.tar.gz \
    config.yaml \
    systemd/ \
    nginx/

# Store securely
mv fm-dashboard-config-backup.tar.gz ~/backups/
```

## Troubleshooting Common Issues

### Issue: Service fails to start

```bash
# Check logs
sudo journalctl -u fm-agent -n 100
sudo journalctl -u fm-dashboard -n 100

# Common causes:
# 1. Port already in use
# 2. Python path incorrect
# 3. Config file not found
# 4. Permission issues
```

### Issue: Can't access via domain

```bash
# Check nginx is running
sudo systemctl status nginx

# Test nginx config
sudo nginx -t

# Check DNS resolution
nslookup dashboard.example.com

# Check firewall
sudo ufw status
```

### Issue: Agent returns 401 Unauthorized

```bash
# Verify token in config.yaml matches
cat config.yaml | grep token

# Check agent is receiving correct token
sudo journalctl -u fm-agent | grep -i auth
```

### Issue: Backup fails

```bash
# Check backup directory exists and is writable
ls -la /backups

# Check disk space
df -h

# Test docker exec manually
docker exec backend bench --version
```

## Rollback Procedure

If something goes wrong:

```bash
# Stop services
sudo systemctl stop fm-agent fm-dashboard

# Restore config from backup
tar -xzf fm-dashboard-config-backup.tar.gz

# Restart services
sudo systemctl start fm-agent fm-dashboard

# Check status
sudo systemctl status fm-agent fm-dashboard
```

## Support

For additional help:
1. Review README.md
2. Check application logs
3. Verify all prerequisites
4. Test each component individually

