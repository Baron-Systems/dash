"""
Web Dashboard for FM/Bench Management
Provides UI for managing stacks, sites, backups, and scheduling
"""
import os
import yaml
import httpx
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional
from fastapi import FastAPI, Request, Depends, HTTPException, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from passlib.context import CryptContext
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.triggers.cron import CronTrigger
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load configuration
# Try multiple possible config locations
CONFIG_PATH = os.getenv("CONFIG_PATH")
if not CONFIG_PATH:
    # Try common locations
    script_dir = os.path.dirname(os.path.abspath(__file__))
    possible_paths = [
        os.path.join(script_dir, "..", "config.yaml"),
        "/opt/dash/config.yaml",
        "/etc/dash/config.yaml",
        "/home/manager-pc/Desktop/dash/config.yaml"
    ]
    for path in possible_paths:
        if os.path.exists(path):
            CONFIG_PATH = path
            break
    
    if not CONFIG_PATH or not os.path.exists(CONFIG_PATH):
        raise FileNotFoundError(
            "config.yaml not found. Please set CONFIG_PATH environment variable or "
            "place config.yaml in one of: " + ", ".join(possible_paths)
        )

logger.info(f"Using config file: {CONFIG_PATH}")
with open(CONFIG_PATH, "r") as f:
    config = yaml.safe_load(f)

AGENT_CONFIG = config["agent"]
SECURITY_CONFIG = config["security"]
DASHBOARD_CONFIG = config["dashboard"]

# Initialize FastAPI
app = FastAPI(title="FM Dashboard", version="1.0.0")

# Add session middleware
app.add_middleware(
    SessionMiddleware,
    secret_key=DASHBOARD_CONFIG["secret_key"]
)

# Templates - use relative path
script_dir = os.path.dirname(os.path.abspath(__file__))
templates_dir = os.path.join(script_dir, "templates")
if not os.path.exists(templates_dir):
    raise FileNotFoundError(f"Templates directory not found at: {templates_dir}")
logger.info(f"Using templates directory: {templates_dir}")
templates = Jinja2Templates(directory=templates_dir)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Agent client configuration
AGENT_URL = f"http://{AGENT_CONFIG['listen']}:{AGENT_CONFIG['port']}"
AGENT_HEADERS = {"Authorization": f"Bearer {SECURITY_CONFIG['token']}"}

# Scheduler
jobstores = {'default': MemoryJobStore()}
scheduler = BackgroundScheduler(jobstores=jobstores)
scheduler.start()


# Helper Functions
async def call_agent(method: str, endpoint: str, **kwargs):
    """Make HTTP call to agent service"""
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.request(
                method,
                f"{AGENT_URL}{endpoint}",
                headers=AGENT_HEADERS,
                **kwargs
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        logger.error(f"Agent call failed: {e}")
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash password"""
    return pwd_context.hash(password)


def get_current_user(request: Request) -> Optional[str]:
    """Get current logged-in user from session"""
    return request.session.get("user")


def require_auth(request: Request):
    """Require authentication"""
    user = get_current_user(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_302_FOUND,
            detail="Not authenticated",
            headers={"Location": "/login"}
        )
    return user


# Scheduled backup job
async def scheduled_backup_job(stack_name: str, site_name: str):
    """Background job for scheduled backups"""
    try:
        logger.info(f"Running scheduled backup for {stack_name}/{site_name}")
        
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                f"{AGENT_URL}/action",
                headers=AGENT_HEADERS,
                json={
                    "action": "backup_site",
                    "stack": stack_name,
                    "site": site_name
                }
            )
            
            if response.status_code == 200:
                logger.info(f"Scheduled backup completed for {stack_name}/{site_name}")
            else:
                logger.error(f"Scheduled backup failed: {response.text}")
    
    except Exception as e:
        logger.error(f"Scheduled backup error: {e}")


# Routes
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page"""
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    
    return RedirectResponse(url="/dashboard", status_code=302)


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Login page"""
    user = get_current_user(request)
    if user:
        return RedirectResponse(url="/dashboard", status_code=302)
    
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    """Handle login"""
    # Simple authentication (in production, use database)
    admin_username = DASHBOARD_CONFIG["admin_username"]
    admin_password = DASHBOARD_CONFIG["admin_password"]
    
    if username == admin_username and password == admin_password:
        request.session["user"] = username
        return RedirectResponse(url="/dashboard", status_code=302)
    
    return templates.TemplateResponse(
        "login.html",
        {"request": request, "error": "Invalid credentials"}
    )


@app.get("/logout")
async def logout(request: Request):
    """Logout"""
    request.session.clear()
    return RedirectResponse(url="/login", status_code=302)


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, user: str = Depends(require_auth)):
    """Main dashboard"""
    try:
        # Get all stacks from agent
        stacks_data = await call_agent("GET", "/stacks")
        
        return templates.TemplateResponse(
            "dashboard.html",
            {
                "request": request,
                "user": user,
                "stacks": stacks_data.get("stacks", [])
            }
        )
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        return templates.TemplateResponse(
            "dashboard.html",
            {
                "request": request,
                "user": user,
                "stacks": [],
                "error": str(e)
            }
        )


@app.get("/stack/{stack_name}", response_class=HTMLResponse)
async def stack_detail(request: Request, stack_name: str, user: str = Depends(require_auth)):
    """Stack detail page"""
    try:
        # Get stack details
        stack_data = await call_agent("GET", f"/stacks/{stack_name}")
        
        return templates.TemplateResponse(
            "stack_detail.html",
            {
                "request": request,
                "user": user,
                "stack": stack_data,
                "sites": stack_data.get("sites", []),
                "stack_name": stack_name
            }
        )
    except Exception as e:
        logger.error(f"Stack detail error: {e}")
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "user": user,
                "error": f"Failed to load stack: {str(e)}"
            }
        )


@app.get("/stack/{stack_name}/refresh-sites", response_class=HTMLResponse)
async def refresh_sites(request: Request, stack_name: str, user: str = Depends(require_auth)):
    """Refresh sites list for a stack"""
    try:
        # Get updated sites list from agent
        stack_data = await call_agent("GET", f"/stacks/{stack_name}")
        sites = stack_data.get("sites", [])
        
        return templates.TemplateResponse(
            "sites_list_partial.html",
            {
                "request": request,
                "sites": sites,
                "stack_name": stack_name
            }
        )
    except Exception as e:
        logger.error(f"Refresh sites error: {e}")
        return f'<div class="text-red-600 p-4"><i class="fas fa-exclamation-triangle mr-2"></i>Failed to refresh sites: {str(e)}</div>'


@app.post("/stack/{stack_name}/restart")
async def restart_stack(request: Request, stack_name: str, user: str = Depends(require_auth)):
    """Restart a stack"""
    try:
        result = await call_agent(
            "POST",
            "/action",
            json={
                "action": "restart_stack",
                "stack": stack_name
            }
        )
        
        return {"success": True, "message": result.get("message", "Stack restarted")}
    except Exception as e:
        return {"success": False, "message": str(e)}


@app.post("/stack/{stack_name}/update")
async def update_stack(request: Request, stack_name: str, user: str = Depends(require_auth)):
    """Update a stack"""
    try:
        result = await call_agent(
            "POST",
            "/action",
            json={
                "action": "update_stack",
                "stack": stack_name
            }
        )
        
        return {"success": True, "message": result.get("message", "Stack updated")}
    except Exception as e:
        return {"success": False, "message": str(e)}


@app.post("/site/{stack_name}/{site_name}/restart")
async def restart_site(
    request: Request,
    stack_name: str,
    site_name: str,
    user: str = Depends(require_auth)
):
    """Restart a site"""
    try:
        result = await call_agent(
            "POST",
            "/action",
            json={
                "action": "restart_site",
                "stack": stack_name,
                "site": site_name
            }
        )
        
        return {"success": True, "message": result.get("message", "Site restarted")}
    except Exception as e:
        return {"success": False, "message": str(e)}


@app.post("/site/{stack_name}/{site_name}/migrate")
async def migrate_site(
    request: Request,
    stack_name: str,
    site_name: str,
    user: str = Depends(require_auth)
):
    """Migrate a site"""
    try:
        result = await call_agent(
            "POST",
            "/action",
            json={
                "action": "migrate_site",
                "stack": stack_name,
                "site": site_name
            }
        )
        
        return {"success": True, "message": result.get("message", "Site migrated")}
    except Exception as e:
        return {"success": False, "message": str(e)}


@app.post("/site/{stack_name}/{site_name}/backup")
async def backup_site(
    request: Request,
    stack_name: str,
    site_name: str,
    user: str = Depends(require_auth)
):
    """Backup a site"""
    try:
        result = await call_agent(
            "POST",
            "/action",
            json={
                "action": "backup_site",
                "stack": stack_name,
                "site": site_name
            }
        )
        
        return {"success": True, "message": result.get("message", "Backup completed")}
    except Exception as e:
        return {"success": False, "message": str(e)}


@app.get("/backups/{stack_name}/{site_name}", response_class=HTMLResponse)
async def backups_page(
    request: Request,
    stack_name: str,
    site_name: str,
    user: str = Depends(require_auth)
):
    """Backups page for a site"""
    try:
        # Get backups list
        backups_data = await call_agent("GET", f"/backups/{stack_name}/{site_name}")
        
        return templates.TemplateResponse(
            "backups.html",
            {
                "request": request,
                "user": user,
                "stack_name": stack_name,
                "site_name": site_name,
                "backups": backups_data.get("backups", [])
            }
        )
    except Exception as e:
        logger.error(f"Backups page error: {e}")
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "user": user,
                "error": f"Failed to load backups: {str(e)}"
            }
        )


@app.get("/download/{stack_name}/{site_name}/{filename}")
async def download_backup(
    stack_name: str,
    site_name: str,
    filename: str,
    user: str = Depends(require_auth)
):
    """Download a backup file"""
    try:
        # Stream the file from agent
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.get(
                f"{AGENT_URL}/backups/{stack_name}/{site_name}/{filename}",
                headers=AGENT_HEADERS
            )
            response.raise_for_status()
            
            return StreamingResponse(
                iter([response.content]),
                media_type="application/gzip",
                headers={
                    "Content-Disposition": f"attachment; filename={filename}"
                }
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/site/{stack_name}/{site_name}/logs", response_class=HTMLResponse)
async def site_logs(
    request: Request,
    stack_name: str,
    site_name: str,
    user: str = Depends(require_auth)
):
    """Site logs page"""
    try:
        # Get logs from agent
        result = await call_agent("GET", f"/site/{stack_name}/{site_name}/logs")
        
        return templates.TemplateResponse(
            "site_logs.html",
            {
                "request": request,
                "user": user,
                "stack_name": stack_name,
                "site_name": site_name,
                "logs": result.get("data", {}).get("logs", "No logs available")
            }
        )
    except Exception as e:
        logger.error(f"Site logs error: {e}")
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "user": user,
                "error": f"Failed to load logs: {str(e)}"
            }
        )


@app.get("/site/{stack_name}/{site_name}/files", response_class=HTMLResponse)
async def site_files(
    request: Request,
    stack_name: str,
    site_name: str,
    path: str = "",
    user: str = Depends(require_auth)
):
    """Site files browser page"""
    try:
        # Get files from agent
        result = await call_agent("GET", f"/site/{stack_name}/{site_name}/files?path={path}")
        
        return templates.TemplateResponse(
            "site_files.html",
            {
                "request": request,
                "user": user,
                "stack_name": stack_name,
                "site_name": site_name,
                "current_path": path,
                "files_data": result.get("data", {})
            }
        )
    except Exception as e:
        logger.error(f"Site files error: {e}")
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "user": user,
                "error": f"Failed to load files: {str(e)}"
            }
        )


@app.get("/site/{stack_name}/{site_name}/console", response_class=HTMLResponse)
async def site_console(
    request: Request,
    stack_name: str,
    site_name: str,
    user: str = Depends(require_auth)
):
    """Site console page"""
    try:
        # Get console command from agent
        result = await call_agent("GET", f"/site/{stack_name}/{site_name}/console")
        
        return templates.TemplateResponse(
            "site_console.html",
            {
                "request": request,
                "user": user,
                "stack_name": stack_name,
                "site_name": site_name,
                "console_command": result.get("message", "")
            }
        )
    except Exception as e:
        logger.error(f"Site console error: {e}")
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "user": user,
                "error": f"Failed to load console: {str(e)}"
            }
        )


@app.get("/logs-viewer", response_class=HTMLResponse)
async def logs_viewer_page(
    request: Request,
    stack: str = None,
    site: str = None,
    lines: int = 100,
    user: str = Depends(require_auth)
):
    """Logs viewer page for FM sites"""
    try:
        from datetime import datetime
        
        # Get all stacks
        stacks_data = await call_agent("GET", "/stacks")
        stacks = stacks_data.get("stacks", [])
        
        # Get sites for selected stack
        sites = []
        if stack:
            try:
                stack_data = await call_agent("GET", f"/stacks/{stack}")
                sites_data = stack_data.get("sites", [])
                # Handle both dict and string formats
                if sites_data and isinstance(sites_data[0], dict):
                    sites = [s["name"] for s in sites_data]
                else:
                    sites = sites_data
            except:
                sites = []
        
        # Get logs if both stack and site are selected
        logs = None
        if stack and site:
            try:
                result = await call_agent("GET", f"/site/{stack}/{site}/logs?lines={lines}")
                if result.get("success"):
                    logs = result.get("data", {}).get("logs", "")
            except Exception as e:
                logger.error(f"Error getting logs: {e}")
                logs = None
        
        return templates.TemplateResponse(
            "logs_viewer.html",
            {
                "request": request,
                "user": user,
                "stacks": stacks,
                "sites": sites,
                "selected_stack": stack,
                "selected_site": site,
                "lines": lines,
                "logs": logs,
                "current_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        )
    except Exception as e:
        logger.error(f"Logs viewer page error: {e}")
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "user": user,
                "error": f"Failed to load logs viewer: {str(e)}"
            }
        )


@app.get("/system-logs", response_class=HTMLResponse)
async def system_logs_page(
    request: Request,
    service: str = "dashboard",
    lines: int = 100,
    user: str = Depends(require_auth)
):
    """System logs page for Dashboard and Agent services"""
    try:
        from datetime import datetime
        import subprocess
        
        logs = None
        source = "none"
        
        if service == "dashboard":
            # Get dashboard logs from journalctl
            try:
                result = subprocess.run(
                    ["journalctl", "-u", "fm-dashboard", "-n", str(lines), "--no-pager"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    logs = result.stdout
                    source = "journalctl"
            except Exception as e:
                logger.error(f"Error getting dashboard logs: {e}")
                # Fallback to log file
                log_file = Path("/var/log/fm-dashboard.log")
                if not log_file.exists():
                    log_file = Path("/tmp/fm-dashboard.log")
                if log_file.exists():
                    with open(log_file, 'r') as f:
                        all_lines = f.readlines()
                        logs = ''.join(all_lines[-lines:])
                        source = "log_file"
        
        elif service == "agent":
            # Get agent logs via API
            try:
                result = await call_agent("GET", f"/system/logs?lines={lines}")
                if result.get("success"):
                    logs = result.get("data", {}).get("logs", "")
                    source = result.get("data", {}).get("source", "unknown")
            except Exception as e:
                logger.error(f"Error getting agent logs: {e}")
        
        return templates.TemplateResponse(
            "system_logs.html",
            {
                "request": request,
                "user": user,
                "service": service,
                "lines": lines,
                "logs": logs,
                "source": source,
                "current_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        )
    except Exception as e:
        logger.error(f"System logs page error: {e}")
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "user": user,
                "error": f"Failed to load system logs: {str(e)}"
            }
        )


@app.get("/scheduler", response_class=HTMLResponse)
async def scheduler_page(request: Request, user: str = Depends(require_auth)):
    """Scheduler management page"""
    try:
        # Get all scheduled jobs
        jobs = []
        for job in scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger)
            })
        
        # Get stacks for dropdown
        stacks_data = await call_agent("GET", "/stacks")
        
        return templates.TemplateResponse(
            "scheduler.html",
            {
                "request": request,
                "user": user,
                "jobs": jobs,
                "stacks": stacks_data.get("stacks", [])
            }
        )
    except Exception as e:
        logger.error(f"Scheduler page error: {e}")
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "user": user,
                "error": f"Failed to load scheduler: {str(e)}"
            }
        )


@app.post("/scheduler/add")
async def add_scheduled_backup(
    request: Request,
    stack_name: str = Form(...),
    site_name: str = Form(...),
    schedule_type: str = Form(...),
    hour: int = Form(...),
    minute: int = Form(0),
    day_of_week: str = Form("*"),
    user: str = Depends(require_auth)
):
    """Add a scheduled backup job"""
    try:
        job_id = f"backup_{stack_name}_{site_name}_{datetime.now().timestamp()}"
        
        # Create cron trigger based on schedule type
        if schedule_type == "daily":
            trigger = CronTrigger(hour=hour, minute=minute)
        elif schedule_type == "weekly":
            trigger = CronTrigger(day_of_week=day_of_week, hour=hour, minute=minute)
        elif schedule_type == "monthly":
            trigger = CronTrigger(day=1, hour=hour, minute=minute)
        else:
            return {"success": False, "message": "Invalid schedule type"}
        
        # Add job
        scheduler.add_job(
            scheduled_backup_job,
            trigger=trigger,
            args=[stack_name, site_name],
            id=job_id,
            name=f"Backup {stack_name}/{site_name}",
            replace_existing=True
        )
        
        return {"success": True, "message": "Scheduled backup added"}
    except Exception as e:
        logger.error(f"Add schedule error: {e}")
        return {"success": False, "message": str(e)}


@app.post("/scheduler/remove/{job_id}")
async def remove_scheduled_backup(
    request: Request,
    job_id: str,
    user: str = Depends(require_auth)
):
    """Remove a scheduled backup job"""
    try:
        scheduler.remove_job(job_id)
        return {"success": True, "message": "Scheduled backup removed"}
    except Exception as e:
        logger.error(f"Remove schedule error: {e}")
        return {"success": False, "message": str(e)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=DASHBOARD_CONFIG["listen"],
        port=DASHBOARD_CONFIG["port"],
        log_level="info"
    )

