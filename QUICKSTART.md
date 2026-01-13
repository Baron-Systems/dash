# Quick Start Guide

Get FM Dashboard up and running in 5 minutes!

## Prerequisites Check

```bash
# Check Python version (need 3.8+)
python3 --version

# Check Docker
docker --version

# Check Docker access
docker ps

# Check if in docker group
groups | grep docker
```

If any checks fail, see [DEPLOYMENT.md](DEPLOYMENT.md) for setup instructions.

## Installation (3 steps)

### Step 1: Run Setup Script

```bash
cd /home/manager-pc/Desktop/dash
bash scripts/setup.sh
```

This will:
- Create virtual environment
- Install dependencies
- Generate secure tokens
- Create configuration file
- Setup backup directory

**Important**: Save the generated tokens shown during setup!

### Step 2: Test Manually

```bash
# Terminal 1 - Start Agent
cd /home/manager-pc/Desktop/dash
source venv/bin/activate
python3 agent/main.py
```

```bash
# Terminal 2 - Start Dashboard
cd /home/manager-pc/Desktop/dash
source venv/bin/activate
python3 dashboard/main.py
```

```bash
# Terminal 3 - Test Agent
cd /home/manager-pc/Desktop/dash
bash scripts/test-agent.sh
```

Open browser: http://127.0.0.1:8000

Login with credentials from `config.yaml`

### Step 3: Install as Services (Optional - Production)

```bash
cd /home/manager-pc/Desktop/dash
sudo bash scripts/install-services.sh
```

This will:
- Install systemd services
- Enable auto-start on boot
- Start services

## Quick Configuration

Edit `config.yaml` to customize:

```yaml
stacks:
  your-stack-name:
    path: /path/to/your/fm/stack
    type: fm

backups:
  base_path: /your/backup/path

dashboard:
  admin_username: your-admin
  admin_password: your-password
```

Restart services after changes:

```bash
sudo systemctl restart fm-agent fm-dashboard
```

## Daily Usage

### Access Dashboard

```
http://localhost:8000           (local)
https://dashboard.example.com   (production with domain)
```

### Common Tasks

**Restart a stack:**
1. Go to Dashboard
2. Click "Restart" on stack card

**Backup a site:**
1. Go to stack detail
2. Find your site
3. Click "Backup Now"

**Schedule automatic backups:**
1. Go to "Scheduler" page
2. Select stack and site
3. Choose schedule (daily/weekly/monthly)
4. Set time
5. Click "Add Schedule"

**Download backups:**
1. Go to stack detail
2. Click "View Backups" for a site
3. Click "Download" on any backup

## Troubleshooting

### Services not starting?

```bash
# Check logs
sudo journalctl -u fm-agent -n 50
sudo journalctl -u fm-dashboard -n 50

# Check if ports are free
sudo netstat -tulpn | grep -E ':(8000|9100)'
```

### Can't login?

Check credentials in `config.yaml`:

```bash
grep -A 3 "dashboard:" config.yaml
```

### Agent errors?

Test agent connectivity:

```bash
cd /home/manager-pc/Desktop/dash
bash scripts/test-agent.sh
```

### Docker permission denied?

```bash
sudo usermod -aG docker $USER
newgrp docker
# Or logout and login again
```

## Useful Commands

```bash
# Service management
sudo systemctl status fm-agent fm-dashboard
sudo systemctl restart fm-agent fm-dashboard
sudo systemctl stop fm-agent fm-dashboard

# View logs
sudo journalctl -u fm-agent -f
sudo journalctl -u fm-dashboard -f

# Test agent
cd /home/manager-pc/Desktop/dash
bash scripts/test-agent.sh

# Manual start (for debugging)
cd /home/manager-pc/Desktop/dash
source venv/bin/activate
python3 agent/main.py           # Terminal 1
python3 dashboard/main.py       # Terminal 2
```

## Next Steps

- [ ] Configure your FM stacks in `config.yaml`
- [ ] Setup Nginx reverse proxy (see DEPLOYMENT.md)
- [ ] Configure SSL certificate
- [ ] Setup scheduled backups
- [ ] Test all functionality
- [ ] Backup your configuration file

## Getting Help

1. Check [README.md](README.md) for detailed documentation
2. Check [DEPLOYMENT.md](DEPLOYMENT.md) for deployment guide
3. Review logs for error messages
4. Verify all prerequisites are met

## Security Reminders

- ✅ Change default admin password
- ✅ Use strong random tokens
- ✅ Enable HTTPS in production
- ✅ Keep agent on localhost only (127.0.0.1)
- ✅ Regular updates
- ✅ Monitor logs

---

**That's it!** You're ready to manage your Frappe stacks from the web interface.

For advanced configuration and production deployment, see [DEPLOYMENT.md](DEPLOYMENT.md).

