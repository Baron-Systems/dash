# System Architecture

## High-Level Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        Internet                              │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTPS (443)
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                    Nginx Reverse Proxy                       │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ • SSL/TLS Termination                                  │ │
│  │ • Security Headers                                     │ │
│  │ • Rate Limiting                                        │ │
│  │ • Access Logging                                       │ │
│  └────────────────────────────────────────────────────────┘ │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP (localhost:8000)
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                    Dashboard Service                         │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ FastAPI + Jinja2 + HTMX                                │ │
│  │                                                        │ │
│  │ • Session Authentication                               │ │
│  │ • User Interface                                       │ │
│  │ • Job Scheduler (APScheduler)                          │ │
│  │ • Backup Downloads                                     │ │
│  └────────────────────────────────────────────────────────┘ │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP (localhost:9100)
                           │ Authorization: Bearer TOKEN
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                      Agent Service                           │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ FastAPI                                                │ │
│  │                                                        │ │
│  │ • Token Authentication                                 │ │
│  │ • Command Execution                                    │ │
│  │ • Action Whitelist                                     │ │
│  │ • Filesystem Access                                    │ │
│  └────────────────────────────────────────────────────────┘ │
└──────────────────────────┬──────────────────────────────────┘
                           │
            ┌──────────────┼──────────────┐
            │              │              │
            ▼              ▼              ▼
    ┌──────────┐   ┌──────────┐   ┌──────────┐
    │   FM     │   │  Docker  │   │  Backup  │
    │  Stacks  │   │Container │   │   Files  │
    └──────────┘   └──────────┘   └──────────┘
```

## Component Interactions

### 1. User → Dashboard

```
User Browser
    │
    ├─ Login: POST /login
    │   ↓
    │  Session Created
    │   ↓
    ├─ View Stacks: GET /dashboard
    │   ↓
    │  Render stacks.html
    │   ↓
    ├─ Actions: POST /stack/{name}/restart
    │   ↓
    │  Call Agent API
    │   ↓
    └─ Response: JSON {success, message}
```

### 2. Dashboard → Agent

```
Dashboard Service
    │
    ├─ Authenticate with Bearer Token
    │   ↓
    ├─ GET /stacks
    │   ↓
    │  Agent returns stack info
    │   ↓
    ├─ POST /action
    │   ↓
    │  Agent executes command
    │   ↓
    └─ GET /backups/{stack}/{site}/{file}
        ↓
       Agent streams file
```

### 3. Agent → System

```
Agent Service
    │
    ├─ Validate action (whitelist)
    │   ↓
    ├─ Execute via subprocess
    │   ├─ fm commands
    │   ├─ docker commands
    │   └─ docker-compose commands
    │   ↓
    ├─ Access filesystem
    │   ├─ Read stack directories
    │   └─ Access backup files
    │   ↓
    └─ Return results
```

## Security Layers

### Layer 1: Network Security

```
┌─────────────────────────────────────┐
│         Internet Traffic            │
│  Only HTTPS (443) exposed           │
│  Agent ports NEVER exposed          │
└─────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│         Firewall (UFW)              │
│  Allow: 80, 443                     │
│  Deny: 8000, 9100                   │
└─────────────────────────────────────┘
```

### Layer 2: Application Security

```
┌──────────────────────────────────────┐
│         Nginx                        │
│  • SSL/TLS                           │
│  • Security Headers                  │
│  • Rate Limiting                     │
└──────────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────┐
│         Dashboard                    │
│  • Session Auth                      │
│  • Input Validation                  │
│  • CSRF Protection                   │
└──────────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────┐
│         Agent                        │
│  • Token Auth                        │
│  • Action Whitelist                  │
│  • No shell=True                     │
└──────────────────────────────────────┘
```

### Layer 3: System Security

```
┌──────────────────────────────────────┐
│    Process Isolation                 │
│  • Non-root user                     │
│  • Docker group only                 │
│  • NoNewPrivileges                   │
│  • PrivateTmp                        │
└──────────────────────────────────────┘
```

## Data Flow

### Viewing Stacks

```
1. User → Browser: Navigate to /dashboard
2. Browser → Nginx: GET /dashboard
3. Nginx → Dashboard: GET /dashboard (localhost:8000)
4. Dashboard → Check Session: Valid?
5. Dashboard → Agent: GET /stacks (with token)
6. Agent → System: Execute `fm status` for each stack
7. Agent → Dashboard: Return JSON with stack info
8. Dashboard → Browser: Render dashboard.html with data
9. Browser → User: Display stacks
```

### Creating Backup

```
1. User → Browser: Click "Backup Now"
2. Browser → Dashboard: POST /site/{stack}/{site}/backup (HTMX)
3. Dashboard → Agent: POST /action
   {
     "action": "backup_site",
     "stack": "prod",
     "site": "site1.local"
   }
4. Agent → System: docker exec backend bench --site site1.local backup
5. Agent → Filesystem: Copy backup to /backups/prod/site1/
6. Agent → Dashboard: Return success
7. Dashboard → Browser: JSON {success: true, message: "Backup created"}
8. Browser → User: Show notification
```

### Downloading Backup

```
1. User → Browser: Click "Download"
2. Browser → Dashboard: GET /download/{stack}/{site}/{filename}
3. Dashboard → Agent: GET /backups/{stack}/{site}/{filename}
4. Agent → Filesystem: Read backup file
5. Agent → Dashboard: Stream file
6. Dashboard → Browser: Stream file with proper headers
7. Browser → User: Save file
```

### Scheduled Backup

```
Scheduler (APScheduler)
    │
    ├─ Trigger: Daily 2:00 AM
    │   ↓
    ├─ Execute: scheduled_backup_job()
    │   ↓
    ├─ Dashboard → Agent: POST /action {backup_site}
    │   ↓
    ├─ Agent → System: Execute backup
    │   ↓
    └─ Log result
```

## File Structure

### Configuration Files

```
config.yaml
    ├─ agent:
    │   └─ listen, port
    ├─ security:
    │   └─ token, allowed_actions
    ├─ stacks:
    │   └─ {name}: {path, type}
    ├─ backups:
    │   └─ base_path, retention
    └─ dashboard:
        └─ listen, port, secret_key, credentials
```

### Backup Directory Structure

```
/backups/
├── prod/
│   ├── site1.local/
│   │   ├── 2026-01-13_02-00-00.sql.gz
│   │   ├── 2026-01-12_02-00-00.sql.gz
│   │   └── 2026-01-11_02-00-00.sql.gz
│   └── site2.local/
│       └── 2026-01-13_02-00-00.sql.gz
└── dev/
    └── dev.local/
        └── 2026-01-13_14-30-00.sql.gz
```

## Process Management

### Systemd Services

```
systemd
    │
    ├─ fm-agent.service
    │   ├─ User: manager-pc
    │   ├─ Group: docker
    │   ├─ WorkingDirectory: /home/manager-pc/Desktop/dash
    │   ├─ ExecStart: uvicorn agent.main:app
    │   └─ Restart: always
    │
    └─ fm-dashboard.service
        ├─ User: manager-pc
        ├─ Group: manager-pc
        ├─ WorkingDirectory: /home/manager-pc/Desktop/dash
        ├─ ExecStart: uvicorn dashboard.main:app
        ├─ Restart: always
        └─ After: fm-agent.service
```

### Service Dependencies

```
docker.service
    ↓
fm-agent.service
    ↓
fm-dashboard.service
    ↓
nginx.service
```

## API Endpoints

### Agent Service (Port 9100)

```
GET  /                              # Health check
GET  /stacks                        # List all stacks
GET  /stacks/{stack_name}           # Get stack details
GET  /stacks/{stack_name}/sites     # List sites
POST /action                        # Execute action
GET  /backups/{stack}/{site}        # List backups
GET  /backups/{stack}/{site}/{file} # Download backup
```

### Dashboard Service (Port 8000)

```
GET  /                              # Redirect to /dashboard
GET  /login                         # Login page
POST /login                         # Handle login
GET  /logout                        # Logout
GET  /dashboard                     # Main dashboard
GET  /stack/{name}                  # Stack detail
POST /stack/{name}/restart          # Restart stack
POST /stack/{name}/update           # Update stack
POST /site/{stack}/{site}/restart   # Restart site
POST /site/{stack}/{site}/migrate   # Migrate site
POST /site/{stack}/{site}/backup    # Backup site
GET  /backups/{stack}/{site}        # Backups page
GET  /download/{stack}/{site}/{file}# Download backup
GET  /scheduler                     # Scheduler page
POST /scheduler/add                 # Add schedule
POST /scheduler/remove/{id}         # Remove schedule
```

## Authentication Flow

```
┌──────────┐
│  Login   │
│   Page   │
└────┬─────┘
     │
     ▼
┌──────────────────┐
│ POST /login      │
│ {username, pass} │
└────┬─────────────┘
     │
     ▼
┌─────────────────────┐
│ Verify Credentials  │
│ (from config.yaml)  │
└────┬────────────────┘
     │
     ├─ Valid
     │   ↓
     │  ┌───────────────────┐
     │  │ Create Session    │
     │  │ Set cookie        │
     │  └───────┬───────────┘
     │          │
     │          ▼
     │  ┌───────────────────┐
     │  │ Redirect to       │
     │  │ /dashboard        │
     │  └───────────────────┘
     │
     └─ Invalid
         ↓
        ┌───────────────────┐
        │ Show error        │
        │ Stay on /login    │
        └───────────────────┘

Protected Routes:
    ├─ Check session
    │   ├─ Valid → Allow
    │   └─ Invalid → Redirect to /login
```

## Scheduler Architecture

```
Dashboard Service
    │
    ├─ APScheduler
    │   │
    │   ├─ JobStore (Memory)
    │   │   └─ Stores job definitions
    │   │
    │   ├─ Triggers (Cron)
    │   │   ├─ Daily: hour=2, minute=0
    │   │   ├─ Weekly: day_of_week=0, hour=2
    │   │   └─ Monthly: day=1, hour=2
    │   │
    │   └─ Executor
    │       └─ Runs: scheduled_backup_job()
    │
    └─ scheduled_backup_job()
        │
        ├─ Call Agent: POST /action
        │   {
        │     "action": "backup_site",
        │     "stack": "prod",
        │     "site": "site1"
        │   }
        │
        └─ Log result
```

## Error Handling

```
User Action
    │
    ▼
Dashboard
    │
    ├─ Try: Execute action
    │   │
    │   ├─ Call Agent
    │   │   │
    │   │   ├─ Success
    │   │   │   └─ Return: {success: true, message: "..."}
    │   │   │
    │   │   └─ Failure
    │   │       ├─ 401: Authentication failed
    │   │       ├─ 404: Not found
    │   │       ├─ 500: Server error
    │   │       └─ Return: {success: false, message: "..."}
    │   │
    │   └─ Handle Response
    │       ├─ Show notification (success/error)
    │       ├─ Log to console
    │       └─ Update UI
    │
    └─ Catch: Network/Timeout errors
        └─ Show error notification
```

## Performance Considerations

### Caching

- Session data cached in memory (FastAPI SessionMiddleware)
- No database required for simple deployments
- Scheduler jobs stored in memory (can be persisted to DB if needed)

### Concurrency

- Uvicorn handles concurrent requests
- APScheduler runs backup jobs in background
- File downloads streamed (not loaded into memory)

### Resource Usage

```
Agent Service:
  - Memory: ~50-100 MB
  - CPU: Minimal (except during backup operations)
  
Dashboard Service:
  - Memory: ~100-150 MB
  - CPU: Minimal (UI rendering)
  
Nginx:
  - Memory: ~10-20 MB
  - CPU: Minimal
```

## Monitoring Points

```
1. Service Health
   └─ systemctl status fm-agent fm-dashboard

2. Service Logs
   ├─ journalctl -u fm-agent -f
   └─ journalctl -u fm-dashboard -f

3. Nginx Logs
   ├─ /var/log/nginx/fm-dashboard-access.log
   └─ /var/log/nginx/fm-dashboard-error.log

4. Application Metrics
   ├─ GET /stacks (check response time)
   ├─ Backup sizes and counts
   └─ Scheduled job execution times

5. System Resources
   ├─ htop / top (CPU, RAM)
   └─ df -h (disk space)
```

## Scalability

### Current Limitations

- Single server only
- In-memory scheduler (jobs lost on restart)
- No database (config-file based)
- Limited to configured stacks

### Future Scalability Options

1. **Database Backend**
   - Store users, stacks, jobs in database
   - Persistent scheduler
   - Multi-user support

2. **Multi-Server**
   - Agent on each server
   - Dashboard coordinates multiple agents
   - Centralized management

3. **Load Balancing**
   - Multiple dashboard instances
   - Session affinity or shared sessions
   - Distributed scheduler

4. **Microservices**
   - Separate backup service
   - Separate scheduler service
   - Message queue for async tasks

---

This architecture provides a solid foundation for secure, reliable FM stack management while maintaining simplicity and ease of deployment.

