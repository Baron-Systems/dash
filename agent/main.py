"""
Bench/FM Agent Service
Executes allowed actions on FM/Docker stacks
"""
import os
import subprocess
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import yaml
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.responses import FileResponse
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load configuration
CONFIG_PATH = os.getenv("CONFIG_PATH", "/home/manager-pc/Desktop/dash/config.yaml")
with open(CONFIG_PATH, "r") as f:
    config = yaml.safe_load(f)

AGENT_CONFIG = config["agent"]
SECURITY_CONFIG = config["security"]
STACKS_CONFIG = config["stacks"]
BACKUPS_CONFIG = config["backups"]

# Initialize FastAPI
app = FastAPI(title="FM Agent Service", version="1.0.0")


# Security
def verify_token(authorization: str = Header(None)):
    """Verify Bearer token"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="Invalid authentication scheme")
        
        if token != SECURITY_CONFIG["token"]:
            raise HTTPException(status_code=401, detail="Invalid token")
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid authorization header")


# Models
class ActionRequest(BaseModel):
    action: str
    stack: str
    site: Optional[str] = None
    params: Optional[Dict] = {}


class ActionResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict] = None


class StackInfo(BaseModel):
    name: str
    path: str
    type: str
    status: str
    containers: List[Dict] = []


# Helper Functions
def run_command(cmd: List[str], cwd: Optional[str] = None) -> tuple:
    """
    Execute command safely without shell=True
    Returns (success, output, error)
    """
    try:
        logger.info(f"Executing command: {' '.join(cmd)} in {cwd or 'current dir'}")
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=300
        )
        success = result.returncode == 0
        return success, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Command timed out"
    except Exception as e:
        return False, "", str(e)


def get_stack_path(stack_name: str) -> Path:
    """Get and validate stack path"""
    if stack_name not in STACKS_CONFIG:
        raise HTTPException(status_code=404, detail=f"Stack '{stack_name}' not found")
    
    stack_path = Path(STACKS_CONFIG[stack_name]["path"])
    if not stack_path.exists():
        raise HTTPException(status_code=404, detail=f"Stack path does not exist: {stack_path}")
    
    return stack_path


def get_backup_path(stack_name: str, site_name: str) -> Path:
    """Get backup directory path for a site"""
    backup_base = Path(BACKUPS_CONFIG["base_path"])
    backup_dir = backup_base / stack_name / site_name
    backup_dir.mkdir(parents=True, exist_ok=True)
    return backup_dir


# Agent Actions
def list_sites(stack_name: str) -> List[str]:
    """List all sites in a stack"""
    stack_path = get_stack_path(stack_name)
    
    # Try using fm command
    success, output, error = run_command(["fm", "list"], cwd=stack_path)
    
    if success:
        # Parse fm list output
        sites = []
        for line in output.strip().split("\n"):
            if line.strip() and not line.startswith("─") and not line.startswith("Site"):
                parts = line.split()
                if parts:
                    sites.append(parts[0])
        return sites
    
    # Fallback: check sites directory
    sites_dir = stack_path / "workspace" / "frappe-bench" / "sites"
    if sites_dir.exists():
        sites = [d.name for d in sites_dir.iterdir() 
                if d.is_dir() and d.name not in ["assets", "common_site_config.json"]]
        return sites
    
    return []


def get_stack_status(stack_name: str) -> Dict:
    """Get status of a stack and its containers"""
    stack_path = get_stack_path(stack_name)
    
    # Get fm status
    success, output, error = run_command(["fm", "status"], cwd=stack_path)
    
    status_info = {
        "name": stack_name,
        "path": str(stack_path),
        "type": STACKS_CONFIG[stack_name]["type"],
        "status": "running" if success else "stopped",
        "containers": []
    }
    
    # Get docker containers
    compose_file = stack_path / "docker-compose.yml"
    if compose_file.exists():
        success, output, error = run_command(
            ["docker-compose", "ps", "--format", "json"],
            cwd=stack_path
        )
        if success and output:
            try:
                import json
                containers = [json.loads(line) for line in output.strip().split("\n") if line]
                status_info["containers"] = containers
            except:
                pass
    
    return status_info


def restart_stack(stack_name: str) -> tuple:
    """Restart an FM stack"""
    stack_path = get_stack_path(stack_name)
    
    # Stop
    success, output, error = run_command(["fm", "stop"], cwd=stack_path)
    if not success:
        return False, f"Failed to stop stack: {error}"
    
    # Start
    success, output, error = run_command(["fm", "start"], cwd=stack_path)
    if not success:
        return False, f"Failed to start stack: {error}"
    
    return True, "Stack restarted successfully"


def restart_site(stack_name: str, site_name: str) -> tuple:
    """Restart a specific site"""
    stack_path = get_stack_path(stack_name)
    
    # Restart using docker-compose
    success, output, error = run_command(
        ["docker-compose", "restart", "backend"],
        cwd=stack_path
    )
    
    if not success:
        return False, f"Failed to restart site: {error}"
    
    return True, f"Site '{site_name}' restarted successfully"


def migrate_site(stack_name: str, site_name: str) -> tuple:
    """Run migrate on a site"""
    stack_path = get_stack_path(stack_name)
    
    # Execute migrate command
    success, output, error = run_command(
        ["docker", "exec", "-it", "backend", "bench", "--site", site_name, "migrate"],
        cwd=stack_path
    )
    
    if not success:
        # Try without -it flag
        success, output, error = run_command(
            ["docker", "exec", "backend", "bench", "--site", site_name, "migrate"],
            cwd=stack_path
        )
    
    if not success:
        return False, f"Failed to migrate site: {error}"
    
    return True, f"Site '{site_name}' migrated successfully"


def backup_site(stack_name: str, site_name: str) -> tuple:
    """Backup a site"""
    stack_path = get_stack_path(stack_name)
    backup_dir = get_backup_path(stack_name, site_name)
    
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    
    # Execute backup command
    success, output, error = run_command(
        ["docker", "exec", "backend", "bench", "--site", site_name, "backup"],
        cwd=stack_path
    )
    
    if not success:
        return False, f"Failed to backup site: {error}"
    
    # Find the backup files (they're created in sites/<site>/private/backups/)
    source_backup_dir = stack_path / "workspace" / "frappe-bench" / "sites" / site_name / "private" / "backups"
    
    if source_backup_dir.exists():
        # Find the latest backup files
        backup_files = sorted(source_backup_dir.glob("*.sql.gz"), key=lambda x: x.stat().st_mtime, reverse=True)
        
        if backup_files:
            latest_backup = backup_files[0]
            # Copy to our backup directory
            import shutil
            dest_file = backup_dir / f"{timestamp}.sql.gz"
            shutil.copy2(latest_backup, dest_file)
            
            return True, f"Site '{site_name}' backed up successfully to {dest_file}"
    
    return True, "Backup command executed, but backup file location unknown"


def update_stack(stack_name: str) -> tuple:
    """Update an FM stack"""
    stack_path = get_stack_path(stack_name)
    
    # Pull latest images
    success, output, error = run_command(
        ["docker-compose", "pull"],
        cwd=stack_path
    )
    
    if not success:
        return False, f"Failed to pull images: {error}"
    
    # Restart with new images
    success, output, error = run_command(
        ["docker-compose", "up", "-d"],
        cwd=stack_path
    )
    
    if not success:
        return False, f"Failed to restart with new images: {error}"
    
    return True, "Stack updated successfully"


# API Endpoints
@app.get("/")
def root():
    """Health check"""
    return {"status": "healthy", "service": "FM Agent", "version": "1.0.0"}


@app.get("/stacks", dependencies=[Depends(verify_token)])
def get_stacks():
    """Get all configured stacks"""
    stacks = []
    for name, config in STACKS_CONFIG.items():
        try:
            status_info = get_stack_status(name)
            stacks.append(status_info)
        except Exception as e:
            logger.error(f"Error getting status for {name}: {e}")
            stacks.append({
                "name": name,
                "path": config["path"],
                "type": config["type"],
                "status": "error",
                "error": str(e)
            })
    
    return {"stacks": stacks}


@app.get("/stacks/{stack_name}", dependencies=[Depends(verify_token)])
def get_stack(stack_name: str):
    """Get detailed status of a specific stack"""
    try:
        status_info = get_stack_status(stack_name)
        sites = list_sites(stack_name)
        status_info["sites"] = sites
        return status_info
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stacks/{stack_name}/sites", dependencies=[Depends(verify_token)])
def get_sites(stack_name: str):
    """Get all sites in a stack"""
    try:
        sites = list_sites(stack_name)
        return {"stack": stack_name, "sites": sites}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/action", dependencies=[Depends(verify_token)])
def execute_action(request: ActionRequest):
    """Execute an allowed action"""
    action = request.action
    stack = request.stack
    site = request.site
    
    # Validate action
    if action not in SECURITY_CONFIG["allowed_actions"]:
        raise HTTPException(status_code=403, detail=f"Action '{action}' not allowed")
    
    try:
        # Execute action
        if action == "restart_stack":
            success, message = restart_stack(stack)
        
        elif action == "restart_site":
            if not site:
                raise HTTPException(status_code=400, detail="Site name required")
            success, message = restart_site(stack, site)
        
        elif action == "migrate_site":
            if not site:
                raise HTTPException(status_code=400, detail="Site name required")
            success, message = migrate_site(stack, site)
        
        elif action == "backup_site":
            if not site:
                raise HTTPException(status_code=400, detail="Site name required")
            success, message = backup_site(stack, site)
        
        elif action == "update_stack":
            success, message = update_stack(stack)
        
        elif action == "list_sites":
            sites = list_sites(stack)
            return ActionResponse(success=True, message="Sites retrieved", data={"sites": sites})
        
        elif action == "get_stack_status":
            status = get_stack_status(stack)
            return ActionResponse(success=True, message="Status retrieved", data=status)
        
        else:
            raise HTTPException(status_code=400, detail=f"Unknown action: {action}")
        
        return ActionResponse(success=success, message=message)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing action {action}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/backups/{stack_name}/{site_name}", dependencies=[Depends(verify_token)])
def list_backups(stack_name: str, site_name: str):
    """List all backups for a site"""
    try:
        backup_dir = get_backup_path(stack_name, site_name)
        
        backups = []
        for backup_file in sorted(backup_dir.glob("*.sql.gz"), key=lambda x: x.stat().st_mtime, reverse=True):
            backups.append({
                "filename": backup_file.name,
                "size": backup_file.stat().st_size,
                "created": datetime.fromtimestamp(backup_file.stat().st_mtime).isoformat()
            })
        
        return {"stack": stack_name, "site": site_name, "backups": backups}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/backups/{stack_name}/{site_name}/{filename}", dependencies=[Depends(verify_token)])
def download_backup(stack_name: str, site_name: str, filename: str):
    """Download a backup file"""
    try:
        backup_dir = get_backup_path(stack_name, site_name)
        backup_file = backup_dir / filename
        
        if not backup_file.exists():
            raise HTTPException(status_code=404, detail="Backup file not found")
        
        # Security: ensure filename doesn't contain path traversal
        if ".." in filename or "/" in filename:
            raise HTTPException(status_code=400, detail="Invalid filename")
        
        return FileResponse(
            path=str(backup_file),
            filename=filename,
            media_type="application/gzip"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=AGENT_CONFIG["listen"],
        port=AGENT_CONFIG["port"],
        log_level="info"
    )

