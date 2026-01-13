"""
Bench/FM Agent Service
Executes allowed actions on FM/Docker stacks
"""
import os
import re
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
def find_site_bench(stack_name: str, site_name: str) -> Path:
    """Find the bench directory that contains a specific site
    
    Returns the bench container path (e.g., /stack/sites/devsite.mby-solution.vip)
    where the site's workspace/frappe-bench/sites/{site_name} exists
    """
    stack_path = get_stack_path(stack_name)
    sites_dir = stack_path / "sites"
    
    if sites_dir.exists() and sites_dir.is_dir():
        for bench_dir in sites_dir.iterdir():
            if not bench_dir.is_dir():
                continue
            
            # Check if site exists in this bench
            site_path = bench_dir / "workspace" / "frappe-bench" / "sites" / site_name
            if site_path.exists() and site_path.is_dir():
                logger.info(f"Found site '{site_name}' in bench '{bench_dir.name}'")
                return bench_dir
    
    # If not found in FM structure, assume site name is also bench name (fallback)
    fallback = sites_dir / site_name
    if fallback.exists():
        return fallback
    
    raise FileNotFoundError(f"Site '{site_name}' not found in stack '{stack_name}'")


def list_sites(stack_name: str) -> List[str]:
    """List all sites in a stack - FM structure aware"""
    stack_path = get_stack_path(stack_name)
    
    # FM Structure: stack/sites/{bench-name}/workspace/frappe-bench/sites/{actual-sites}
    # We need to find all actual Frappe sites across all benches
    
    all_sites = set()  # Use set to avoid duplicates
    
    # Method 1: Scan FM structure (sites/{bench}/workspace/frappe-bench/sites/)
    sites_dir = stack_path / "sites"
    if sites_dir.exists() and sites_dir.is_dir():
        # Iterate through each bench container
        for bench_dir in sites_dir.iterdir():
            if not bench_dir.is_dir():
                continue
            
            # Check for workspace/frappe-bench/sites inside each bench
            frappe_sites_dir = bench_dir / "workspace" / "frappe-bench" / "sites"
            if frappe_sites_dir.exists() and frappe_sites_dir.is_dir():
                # List actual sites in this bench
                for site_dir in frappe_sites_dir.iterdir():
                    if site_dir.is_dir() and site_dir.name not in ["assets", "common_site_config.json", "apps"]:
                        all_sites.add(site_dir.name)
                        logger.info(f"Found site in bench '{bench_dir.name}': {site_dir.name}")
    
    if all_sites:
        return sorted(list(all_sites))
    
    # Method 2: Try using fm command as fallback
    success, output, error = run_command(["fm", "list"], cwd=stack_path)
    
    if success and output:
        sites = []
        for line in output.strip().split("\n"):
            # Look for lines containing /sites/ in path
            if '/sites/' in line:
                try:
                    # Extract site name from path
                    # Example: /home/baron/frappe/sites/devsite.mby-solution.vip
                    parts = line.split('/sites/')
                    if len(parts) > 1:
                        site_part = parts[-1].strip()
                        # Get the last component (actual site name)
                        site_name = site_part.split('/')[-1].split()[0].rstrip('│').rstrip()
                        if site_name and '.' in site_name:
                            sites.append(site_name)
                            logger.info(f"Found site from fm list: {site_name}")
                except Exception as e:
                    logger.debug(f"Error parsing fm list line: {e}")
                    continue
        
        if sites:
            return sorted(list(set(sites)))  # Remove duplicates
    
    # Method 3: Fallback to old structure (for compatibility)
    workspace_sites = stack_path / "workspace" / "frappe-bench" / "sites"
    if workspace_sites.exists() and workspace_sites.is_dir():
        sites = [d.name for d in workspace_sites.iterdir() 
                if d.is_dir() and d.name not in ["assets", "common_site_config.json", "apps"]]
        if sites:
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
    """Restart an FM stack (all benches)"""
    stack_path = get_stack_path(stack_name)
    
    # For FM, we restart all benches in the stack
    sites_dir = stack_path / "sites"
    if not sites_dir.exists():
        return False, "No benches found in stack"
    
    benches = [d for d in sites_dir.iterdir() if d.is_dir()]
    if not benches:
        return False, "No benches found in stack"
    
    failed = []
    for bench_dir in benches:
        bench_name = bench_dir.name
        
        # Stop bench using docker-compose
        success, output, error = run_command(
            ["docker-compose", "down"],
            cwd=bench_dir
        )
        if not success:
            failed.append(f"{bench_name} (stop failed)")
            continue
        
        # Start bench using docker-compose
        success, output, error = run_command(
            ["docker-compose", "up", "-d"],
            cwd=bench_dir
        )
        if not success:
            failed.append(f"{bench_name} (start failed)")
    
    if failed:
        return False, f"Failed to restart benches: {', '.join(failed)}"
    
    return True, f"Stack restarted successfully ({len(benches)} benches)"


def restart_site(stack_name: str, site_name: str) -> tuple:
    """Restart a specific site"""
    try:
        # Find the bench that contains this site
        bench_path = find_site_bench(stack_name, site_name)
        
        # Restart using docker-compose in the bench directory
        success, output, error = run_command(
            ["docker-compose", "restart", "backend"],
            cwd=bench_path
        )
        
        if not success:
            return False, f"Failed to restart site: {error}"
        
        return True, f"Site '{site_name}' restarted successfully"
    except FileNotFoundError as e:
        return False, str(e)


def migrate_site(stack_name: str, site_name: str) -> tuple:
    """Run migrate on a site"""
    try:
        # Find the bench that contains this site
        bench_path = find_site_bench(stack_name, site_name)
        
        # Execute migrate command in the bench directory
        success, output, error = run_command(
            ["docker", "exec", "-it", "backend", "bench", "--site", site_name, "migrate"],
            cwd=bench_path
        )
        
        if not success:
            # Try without -it flag
            success, output, error = run_command(
                ["docker", "exec", "backend", "bench", "--site", site_name, "migrate"],
                cwd=bench_path
            )
        
        if not success:
            return False, f"Failed to migrate site: {error}"
        
        return True, f"Site '{site_name}' migrated successfully"
    except FileNotFoundError as e:
        return False, str(e)


def backup_site(stack_name: str, site_name: str) -> tuple:
    """Backup a site"""
    try:
        # Find the bench that contains this site
        bench_path = find_site_bench(stack_name, site_name)
        backup_dir = get_backup_path(stack_name, site_name)
        
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        
        # Execute backup command in the bench directory
        success, output, error = run_command(
            ["docker", "exec", "backend", "bench", "--site", site_name, "backup"],
            cwd=bench_path
        )
        
        if not success:
            return False, f"Failed to backup site: {error}"
        
        # Find the backup files in the correct bench workspace
        source_backup_dir = bench_path / "workspace" / "frappe-bench" / "sites" / site_name / "private" / "backups"
        
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
    except FileNotFoundError as e:
        return False, str(e)


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


def get_site_logs(stack_name: str, site_name: str, lines: int = 100) -> tuple:
    """Get logs for a site"""
    try:
        # Find the bench that contains this site
        bench_path = find_site_bench(stack_name, site_name)
        
        # Get docker logs from backend container in the bench directory
        success, output, error = run_command(
            ["docker", "logs", "--tail", str(lines), "backend"],
            cwd=bench_path
        )
        
        if not success:
            return False, f"Failed to get logs: {error}"
        
        return True, output
    except FileNotFoundError as e:
        return False, str(e)


def list_site_files(stack_name: str, site_name: str, subpath: str = "") -> tuple:
    """List files in a site directory"""
    try:
        # Find the bench that contains this site
        bench_path = find_site_bench(stack_name, site_name)
        
        # Build the site directory path in the correct bench
        site_dir = bench_path / "workspace" / "frappe-bench" / "sites" / site_name
        
        if not site_dir.exists():
            return False, f"Site directory not found at {site_dir}"
        
        # If subpath provided, append it
        if subpath:
            site_dir = site_dir / subpath
            if not site_dir.exists():
                return False, f"Path not found: {subpath}"
        
        # List files and directories
        try:
            items = []
            for item in sorted(site_dir.iterdir()):
                items.append({
                    "name": item.name,
                    "type": "dir" if item.is_dir() else "file",
                    "size": item.stat().st_size if item.is_file() else 0,
                    "modified": datetime.fromtimestamp(item.stat().st_mtime).isoformat()
                })
            
            return True, {"path": str(site_dir), "items": items}
        except Exception as e:
            return False, f"Failed to list files: {str(e)}"
    except FileNotFoundError as e:
        return False, str(e)


def open_site_console(stack_name: str, site_name: str) -> tuple:
    """Get command to open console for a site"""
    stack_path = get_stack_path(stack_name)
    
    # Return the command that user can execute
    command = f"docker exec -it backend bench --site {site_name} console"
    
    return True, f"Run this command: cd {stack_path} && {command}"


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


@app.get("/site/{stack_name}/{site_name}/logs", dependencies=[Depends(verify_token)])
def get_logs(stack_name: str, site_name: str, lines: int = 100):
    """Get site logs"""
    try:
        success, message = get_site_logs(stack_name, site_name, lines)
        return ActionResponse(success=success, message=message if not success else "", data={"logs": message if success else ""})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/site/{stack_name}/{site_name}/files", dependencies=[Depends(verify_token)])
def list_files(stack_name: str, site_name: str, path: str = ""):
    """List files in site directory"""
    try:
        success, result = list_site_files(stack_name, site_name, path)
        if success:
            return ActionResponse(success=True, message="Files retrieved", data=result)
        else:
            return ActionResponse(success=False, message=result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/site/{stack_name}/{site_name}/console", dependencies=[Depends(verify_token)])
def get_console_command(stack_name: str, site_name: str):
    """Get console command for site"""
    try:
        success, command = open_site_console(stack_name, site_name)
        return ActionResponse(success=success, message=command)
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

