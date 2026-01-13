# Update GitHub Repository

## New Files Added

The following improvements have been made:

### 1. **One-Command Installation** (`install.sh`)
- Auto-discovers everything
- Only asks for username/password
- Complete automated setup

### 2. **Auto-Starting Scripts**
- `start-all.sh` - Start all services
- `start-agent.sh` - Start agent only
- `start-dashboard.sh` - Start dashboard only

### 3. **Arabic Documentation** (`README.ar.md`)
- Complete guide in Arabic
- Quick reference
- Troubleshooting

### 4. **Flexible Path Detection**
- Both `agent/main.py` and `dashboard/main.py` updated
- Auto-detect config.yaml location
- Auto-detect templates directory

## Push to GitHub

```bash
cd /home/manager-pc/Desktop/dash

# Add all changes
git add .

# Commit
git commit -m "feat: Add one-command installation with auto-discovery

- Add install.sh for automated setup
- Auto-discover FM stacks
- Auto-generate secure tokens
- Add startup scripts (start-all.sh, start-agent.sh, start-dashboard.sh)
- Add Arabic documentation (README.ar.md)
- Fix hardcoded paths in agent and dashboard
- Auto-detect config.yaml and templates locations
- Update README with quick install instructions"

# Push to GitHub
git push origin main
```

## What Changed

### Modified Files
- ✅ `agent/main.py` - Flexible config path detection
- ✅ `dashboard/main.py` - Flexible config and templates path
- ✅ `README.md` - Added quick install section

### New Files
- ✅ `install.sh` - One-command installation
- ✅ `README.ar.md` - Arabic documentation
- ✅ `scripts/sync-to-opt.sh` - Sync helper script
- ✅ `UPDATE_REPO.md` - This file

### Auto-Generated (Not in repo)
- `start-all.sh` - Created by install.sh
- `start-agent.sh` - Created by install.sh
- `start-dashboard.sh` - Created by install.sh

## For Users

After pushing, users can simply:

```bash
git clone https://github.com/Baron-Systems/dash.git
cd dash
bash install.sh
```

That's it! Everything else is automatic.

## Testing

Before pushing, test the installation:

```bash
# In a temporary directory
cd /tmp
git clone /home/manager-pc/Desktop/dash test-dash
cd test-dash
bash install.sh
# Follow prompts, then test
```

