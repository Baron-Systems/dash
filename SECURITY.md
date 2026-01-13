# Security Guide

Security considerations and best practices for FM Dashboard.

## Architecture Security

### Three-Layer Security Model

```
Internet → Nginx (SSL) → Dashboard (localhost:8000) → Agent (localhost:9100) → System
```

**Layer 1: Nginx (Public)**
- Only component exposed to internet
- SSL/TLS encryption
- Rate limiting
- Security headers

**Layer 2: Dashboard (localhost only)**
- Session-based authentication
- Password protection
- Input validation
- CSRF protection (via session)

**Layer 3: Agent (localhost only)**
- Token-based authentication
- Command whitelist
- No shell=True
- Limited permissions

## Security Features

### ✅ Implemented

1. **No SSH Required**
   - All operations via HTTP API
   - No SSH keys needed
   - No remote shell access

2. **No Root/Sudo**
   - Runs as regular user
   - Uses docker group for container access
   - No privilege escalation

3. **No Arbitrary Commands**
   - Whitelist of allowed actions only
   - No shell=True in subprocess calls
   - Command parameters validated

4. **Localhost-Only Agent**
   - Agent binds to 127.0.0.1 only
   - Not accessible from network
   - Only dashboard can communicate

5. **Authentication**
   - Login required for dashboard
   - Bearer token for agent
   - Session management

6. **HTTPS Enforcement**
   - Nginx forces HTTPS redirect
   - SSL/TLS encryption
   - Secure headers

## Configuration Security

### 1. Secure Tokens

Generate strong random tokens:

```bash
# Agent token
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# Dashboard secret key
python3 -c "import secrets; print(secrets.token_hex(32))"
```

**Requirements:**
- Minimum 32 characters
- Random generation
- Never commit to git
- Rotate periodically

### 2. Strong Passwords

Admin password should be:
- At least 12 characters
- Mix of upper/lower/numbers/symbols
- Not dictionary word
- Unique to this system

```bash
# Generate strong password
python3 -c "import secrets, string; chars = string.ascii_letters + string.digits + string.punctuation; print(''.join(secrets.choice(chars) for i in range(16)))"
```

### 3. File Permissions

```bash
# Restrict config file
chmod 600 config.yaml
chown $USER:$USER config.yaml

# Backup directory
chmod 755 /backups
chown $USER:$USER /backups

# Ensure backups are readable only by owner
find /backups -type f -exec chmod 600 {} \;
```

## Network Security

### Firewall Configuration

```bash
# Using UFW
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow only necessary ports
sudo ufw allow 22/tcp    # SSH (from specific IPs if possible)
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS

# Enable firewall
sudo ufw enable

# Verify
sudo ufw status verbose
```

**Important:** Ports 8000 and 9100 should NEVER be exposed externally.

### Verify Port Binding

```bash
# Check that agent and dashboard bind to localhost only
sudo netstat -tulpn | grep -E ':(8000|9100)'
```

Expected output:
```
tcp  0  0  127.0.0.1:8000  0.0.0.0:*  LISTEN  (dashboard)
tcp  0  0  127.0.0.1:9100  0.0.0.0:*  LISTEN  (agent)
```

If you see `0.0.0.0:8000` or `0.0.0.0:9100`, this is a security issue!

### Nginx Security Headers

In nginx config:

```nginx
# Security headers
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
```

## Application Security

### 1. Input Validation

The application validates:
- Stack names (must exist in config)
- Site names (alphanumeric)
- File names (no path traversal)
- Actions (whitelist only)

### 2. Path Traversal Prevention

```python
# In agent/main.py
def download_backup(stack_name: str, site_name: str, filename: str):
    # Security: prevent path traversal
    if ".." in filename or "/" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
```

### 3. Command Injection Prevention

```python
# Safe: Using list arguments, no shell=True
subprocess.run(["docker", "exec", "backend", "bench", "--site", site_name, "backup"])

# UNSAFE (never do this):
subprocess.run(f"docker exec backend bench --site {site_name} backup", shell=True)
```

## SSL/TLS Configuration

### Let's Encrypt (Recommended)

```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d dashboard.example.com

# Auto-renewal is configured automatically
# Test renewal
sudo certbot renew --dry-run
```

### Cloudflare Origin Certificate

1. Generate certificate in Cloudflare dashboard
2. Install certificate and key on server
3. Configure nginx to use them
4. Enable "Full (strict)" SSL mode in Cloudflare

### Self-Signed (Development Only)

```bash
# Generate self-signed certificate
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /etc/ssl/private/dashboard.key \
  -out /etc/ssl/certs/dashboard.crt
```

**Never use self-signed certificates in production!**

## Monitoring & Auditing

### 1. Log Monitoring

```bash
# Monitor authentication attempts
sudo journalctl -u fm-dashboard | grep -i "login"

# Monitor agent requests
sudo journalctl -u fm-agent | grep -i "action"

# Check for errors
sudo journalctl -u fm-agent -u fm-dashboard --since "1 hour ago" | grep -i error
```

### 2. Failed Login Attempts

Check nginx access logs:

```bash
# Failed logins (look for POST /login followed by 200 with redirect back to login)
sudo grep "POST /login" /var/log/nginx/fm-dashboard-access.log
```

### 3. Unauthorized Access Attempts

Check for 401 responses:

```bash
sudo journalctl -u fm-agent | grep "401"
sudo grep "401" /var/log/nginx/fm-dashboard-access.log
```

## Regular Security Maintenance

### Weekly

- [ ] Review access logs for suspicious activity
- [ ] Check for failed login attempts
- [ ] Verify services are running with correct users

### Monthly

- [ ] Update dependencies: `pip install -r requirements.txt --upgrade`
- [ ] Review and rotate logs
- [ ] Check disk space
- [ ] Verify backups are being created

### Quarterly

- [ ] Rotate secrets (agent token, dashboard secret)
- [ ] Change admin password
- [ ] Review and update firewall rules
- [ ] Update system packages
- [ ] Review user access

## Incident Response

### If Token Compromised

1. Generate new token:
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

2. Update `config.yaml`
3. Restart services:
```bash
sudo systemctl restart fm-agent fm-dashboard
```

4. Review logs for unauthorized access:
```bash
sudo journalctl -u fm-agent --since "7 days ago" | grep "401"
```

### If Password Compromised

1. Update password in `config.yaml`
2. Restart dashboard:
```bash
sudo systemctl restart fm-dashboard
```

3. Review access logs:
```bash
sudo grep "POST /login" /var/log/nginx/fm-dashboard-access.log
```

### If Server Compromised

1. **Immediately** stop services:
```bash
sudo systemctl stop fm-agent fm-dashboard nginx
```

2. Disconnect from network if possible

3. Review all logs for suspicious activity

4. Check for unauthorized changes:
```bash
sudo find /home/manager-pc/Desktop/dash -type f -mtime -7
```

5. Reinstall from clean source

6. Rotate ALL credentials

## Security Checklist

### Deployment

- [ ] Changed default admin password
- [ ] Generated random agent token
- [ ] Generated random dashboard secret
- [ ] Agent binds to 127.0.0.1 only
- [ ] Dashboard binds to 127.0.0.1 only
- [ ] Nginx configured with SSL
- [ ] Firewall enabled and configured
- [ ] File permissions set correctly (600 for config.yaml)

### Ongoing

- [ ] Regular log reviews
- [ ] Dependencies kept updated
- [ ] Backups tested and verified
- [ ] SSL certificate auto-renewal working
- [ ] No unnecessary ports exposed
- [ ] Services running as non-root user

## Common Security Mistakes

### ❌ DON'T

1. **Don't expose agent port (9100) to network**
   ```yaml
   # BAD
   agent:
     listen: 0.0.0.0  # NEVER DO THIS
   ```

2. **Don't use weak tokens**
   ```yaml
   # BAD
   security:
     token: "password123"  # NEVER DO THIS
   ```

3. **Don't disable SSL in production**
   ```nginx
   # BAD
   listen 80;  # Only for development
   ```

4. **Don't run as root**
   ```ini
   # BAD
   [Service]
   User=root  # NEVER DO THIS
   ```

5. **Don't commit secrets to git**
   ```bash
   # ALWAYS check before committing
   git diff config.yaml
   ```

### ✅ DO

1. **Use strong random tokens**
2. **Bind to localhost only**
3. **Use HTTPS in production**
4. **Run as regular user**
5. **Keep secrets out of version control**
6. **Monitor logs regularly**
7. **Keep software updated**

## Compliance Considerations

### Data Protection

- Backups may contain sensitive data
- Ensure proper encryption and access control
- Consider backup retention policies
- Implement secure deletion when needed

### Access Control

- Implement principle of least privilege
- Consider role-based access (future enhancement)
- Log all administrative actions
- Regular access reviews

## Additional Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [CIS Docker Benchmark](https://www.cisecurity.org/benchmark/docker)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [Nginx Security](https://nginx.org/en/docs/http/ngx_http_ssl_module.html)

## Reporting Security Issues

If you discover a security vulnerability:

1. **DO NOT** create a public issue
2. Document the issue privately
3. Include steps to reproduce
4. Suggest a fix if possible

---

**Remember:** Security is a continuous process, not a one-time setup. Regular monitoring and updates are essential.

