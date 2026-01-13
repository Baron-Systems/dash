# Installation Checklist

Use this checklist to verify your FM Dashboard installation is complete and working correctly.

## ✅ Pre-Installation Verification

### System Requirements
- [ ] Python 3.8+ installed: `python3 --version`
- [ ] Docker installed: `docker --version`
- [ ] Docker Compose installed: `docker-compose --version`
- [ ] User in docker group: `groups | grep docker`
- [ ] FM (Frappe Manager) installed: `fm --version`
- [ ] Nginx installed (for production): `nginx -v`

### Permissions
- [ ] Can run docker without sudo: `docker ps`
- [ ] Can access FM stacks: `ls -la /opt/fm/` (or your stack path)
- [ ] Can create backup directory: `mkdir -p /backups && touch /backups/test && rm /backups/test`

## ✅ Project Files Verification

### Core Files
- [ ] `agent/main.py` exists
- [ ] `dashboard/main.py` exists
- [ ] `requirements.txt` exists
- [ ] `config.yaml` exists (or `config.example.yaml` to copy from)

### Templates (7 files)
- [ ] `dashboard/templates/base.html`
- [ ] `dashboard/templates/login.html`
- [ ] `dashboard/templates/dashboard.html`
- [ ] `dashboard/templates/stack_detail.html`
- [ ] `dashboard/templates/backups.html`
- [ ] `dashboard/templates/scheduler.html`
- [ ] `dashboard/templates/error.html`

### Documentation (7 files)
- [ ] `README.md`
- [ ] `QUICKSTART.md`
- [ ] `DEPLOYMENT.md`
- [ ] `SECURITY.md`
- [ ] `ARCHITECTURE.md`
- [ ] `PROJECT_SUMMARY.md`
- [ ] `INSTALLATION_CHECKLIST.md`

### Scripts (3 files)
- [ ] `scripts/setup.sh` (executable)
- [ ] `scripts/install-services.sh` (executable)
- [ ] `scripts/test-agent.sh` (executable)

### Deployment Files
- [ ] `systemd/fm-agent.service`
- [ ] `systemd/fm-dashboard.service`
- [ ] `nginx/fm-dashboard.conf`

## ✅ Installation Steps

### 1. Initial Setup
- [ ] Ran `bash scripts/setup.sh` successfully
- [ ] Virtual environment created: `ls -la venv/`
- [ ] Dependencies installed: `source venv/bin/activate && pip list`
- [ ] Configuration file created: `ls -la config.yaml`
- [ ] Backup directory created: `ls -la /backups/` (or your path)

### 2. Configuration
- [ ] Changed admin password in `config.yaml`
- [ ] Generated and set secure agent token
- [ ] Generated and set secure dashboard secret_key
- [ ] Updated stack paths to match your FM installations
- [ ] Updated backup path if different from `/backups`
- [ ] File permissions set: `ls -la config.yaml` (should show 600)

### 3. Manual Testing
- [ ] Agent starts without errors: `python3 agent/main.py`
- [ ] Dashboard starts without errors: `python3 dashboard/main.py`
- [ ] Can access dashboard at http://127.0.0.1:8000
- [ ] Can login with configured credentials
- [ ] Stacks are visible on dashboard
- [ ] Agent test passes: `bash scripts/test-agent.sh`

### 4. Service Installation (Production)
- [ ] Ran `sudo bash scripts/install-services.sh`
- [ ] Services installed: `systemctl list-unit-files | grep fm-`
- [ ] Services enabled: `systemctl is-enabled fm-agent fm-dashboard`
- [ ] Services started: `systemctl is-active fm-agent fm-dashboard`
- [ ] Services running: `sudo systemctl status fm-agent fm-dashboard`
- [ ] No errors in logs: `sudo journalctl -u fm-agent -u fm-dashboard -n 50`

### 5. Nginx Setup (Production)
- [ ] Nginx config copied to `/etc/nginx/sites-available/`
- [ ] Domain name updated in config
- [ ] Symlink created in `/etc/nginx/sites-enabled/`
- [ ] Nginx config tested: `sudo nginx -t`
- [ ] Nginx reloaded: `sudo systemctl reload nginx`
- [ ] Can access via domain (if configured)

### 6. SSL Setup (Production)
- [ ] SSL certificate obtained (Let's Encrypt or Cloudflare)
- [ ] Certificate paths updated in nginx config
- [ ] HTTPS works: `curl -I https://dashboard.example.com`
- [ ] HTTP redirects to HTTPS
- [ ] SSL certificate auto-renewal configured

### 7. Firewall Setup (Production)
- [ ] Firewall enabled: `sudo ufw status`
- [ ] Port 80 allowed: `sudo ufw status | grep 80`
- [ ] Port 443 allowed: `sudo ufw status | grep 443`
- [ ] Ports 8000 and 9100 NOT exposed externally

## ✅ Functionality Testing

### Basic Operations
- [ ] Login to dashboard works
- [ ] Can view all configured stacks
- [ ] Stack status shows correctly (running/stopped)
- [ ] Can navigate to stack detail page
- [ ] Sites are listed for each stack
- [ ] Docker containers are shown (if stack is running)

### Stack Actions
- [ ] Restart stack works
- [ ] Update stack works (pulls latest images)
- [ ] Action notifications appear
- [ ] Page refreshes after action

### Site Actions
- [ ] Restart site works
- [ ] Migrate site works
- [ ] Backup site works
- [ ] Actions complete without errors

### Backup Management
- [ ] Can navigate to backups page
- [ ] Existing backups are listed
- [ ] Can create new backup via UI
- [ ] Backup appears in list after creation
- [ ] Can download backup file
- [ ] Downloaded file is valid (.sql.gz)

### Scheduler
- [ ] Can access scheduler page
- [ ] Stacks load in dropdown
- [ ] Sites load when stack selected
- [ ] Can create scheduled backup
- [ ] Schedule appears in list
- [ ] Next run time is correct
- [ ] Can remove schedule

### Authentication & Security
- [ ] Cannot access dashboard without login
- [ ] Logout works
- [ ] Session persists across page refreshes
- [ ] Agent requires token (test without token should fail)
- [ ] Agent is on localhost only (127.0.0.1)
- [ ] Dashboard is on localhost only (127.0.0.1)

## ✅ Post-Installation Verification

### Services
```bash
# All should show "active (running)"
sudo systemctl status fm-agent
sudo systemctl status fm-dashboard
sudo systemctl status nginx
```

### Ports
```bash
# Should show localhost binding only for 8000 and 9100
sudo netstat -tulpn | grep -E ":(80|443|8000|9100)"
```

Expected:
- `127.0.0.1:8000` - dashboard
- `127.0.0.1:9100` - agent
- `0.0.0.0:80` - nginx (only if production)
- `0.0.0.0:443` - nginx (only if production with SSL)

### Logs
```bash
# Should show no critical errors
sudo journalctl -u fm-agent -n 20
sudo journalctl -u fm-dashboard -n 20
sudo tail -n 20 /var/log/nginx/fm-dashboard-error.log  # If nginx configured
```

### Auto-Start on Boot
```bash
# Both should show "enabled"
systemctl is-enabled fm-agent
systemctl is-enabled fm-dashboard
```

### File Permissions
```bash
# config.yaml should be 600 (rw-------)
ls -la config.yaml

# backup directory should be accessible
ls -la /backups/
```

## ✅ Scheduled Backup Test

### Create Test Schedule
- [ ] Create a scheduled backup for a test site
- [ ] Set it to run in 5 minutes
- [ ] Wait for scheduled time
- [ ] Check logs: `sudo journalctl -u fm-dashboard | grep backup`
- [ ] Verify backup was created: `ls -la /backups/`
- [ ] Remove test schedule

## ✅ Integration Test

### Complete Workflow Test
1. [ ] Login to dashboard
2. [ ] Navigate to a stack
3. [ ] Create a backup for a site
4. [ ] Download the backup
5. [ ] Verify backup file is valid
6. [ ] Schedule automatic backup
7. [ ] Restart a site
8. [ ] Check logs for any errors
9. [ ] Logout
10. [ ] Login again (verify session works)

## ✅ Documentation Review

### Read Documentation
- [ ] Read README.md completely
- [ ] Read QUICKSTART.md
- [ ] Skim through DEPLOYMENT.md
- [ ] Review SECURITY.md for best practices
- [ ] Understand ARCHITECTURE.md

### Understand Configuration
- [ ] Know how to add new stacks
- [ ] Know how to change admin password
- [ ] Know how to rotate tokens
- [ ] Know how to view logs
- [ ] Know how to restart services

## ✅ Backup & Recovery

### Backup Your Setup
- [ ] Backup config.yaml: `cp config.yaml config.yaml.backup`
- [ ] Document your setup (stacks, paths, domain)
- [ ] Save tokens and passwords securely
- [ ] Note any customizations made

### Test Recovery
- [ ] Know how to restore from backup
- [ ] Know how to restart services if they fail
- [ ] Know how to check logs for errors
- [ ] Have emergency access plan (if dashboard is down)

## ✅ Monitoring Setup

### Regular Checks
- [ ] Setup log monitoring (weekly review)
- [ ] Setup disk space monitoring
- [ ] Setup backup verification (monthly)
- [ ] Document maintenance procedures

### Create Monitoring Script (Optional)
```bash
#!/bin/bash
# Check FM Dashboard health
echo "=== FM Dashboard Health Check ==="
echo "Services:"
systemctl status fm-agent | grep Active
systemctl status fm-dashboard | grep Active
echo ""
echo "Ports:"
sudo netstat -tulpn | grep -E ":(8000|9100)"
echo ""
echo "Disk Space:"
df -h /backups
echo ""
echo "Recent Errors:"
sudo journalctl -u fm-agent -u fm-dashboard --since "1 hour ago" | grep -i error
```

## ✅ Final Verification

### All Systems Go
- [ ] All services running
- [ ] All tests passed
- [ ] Documentation reviewed
- [ ] Configuration backed up
- [ ] Monitoring in place
- [ ] Know how to troubleshoot
- [ ] Ready for production use

## 🎉 Installation Complete!

If all items are checked, your FM Dashboard is successfully installed and ready for production use!

### Next Steps
1. Use the dashboard regularly
2. Monitor logs weekly
3. Update dependencies monthly
4. Review security quarterly
5. Keep backups of your configuration

### Quick Reference
- **Dashboard URL**: https://dashboard.example.com (or http://localhost:8000)
- **Admin User**: (check config.yaml)
- **Restart Services**: `sudo systemctl restart fm-agent fm-dashboard`
- **View Logs**: `sudo journalctl -u fm-agent -f`
- **Test Agent**: `bash scripts/test-agent.sh`

---

✅ **Checklist Last Updated**: 2026-01-13
📚 **Documentation**: README.md, QUICKSTART.md, DEPLOYMENT.md
🔒 **Security**: SECURITY.md
🏗️ **Architecture**: ARCHITECTURE.md

