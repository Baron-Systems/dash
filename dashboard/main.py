"""
Web Dashboard for FM/Bench Management
Provides UI for managing stacks, sites, backups, and scheduling
"""
import os
import yaml
import httpx
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
CONFIG_PATH = os.getenv("CONFIG_PATH", "/home/manager-pc/Desktop/dash/config.yaml")
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

# Templates
templates = Jinja2Templates(directory="/home/manager-pc/Desktop/dash/dashboard/templates")

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
                "stack": stack_data
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

