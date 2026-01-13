#!/bin/bash

# Sync updated files to /opt/dash

echo "======================================="
echo "FM Dashboard - Sync Script"
echo "======================================="
echo ""

SOURCE_DIR="/home/manager-pc/Desktop/dash"
TARGET_DIR="/opt/dash"

if [ ! -d "$SOURCE_DIR" ]; then
    echo "❌ Source directory not found: $SOURCE_DIR"
    exit 1
fi

if [ ! -d "$TARGET_DIR" ]; then
    echo "❌ Target directory not found: $TARGET_DIR"
    exit 1
fi

echo "Syncing files from $SOURCE_DIR to $TARGET_DIR"
echo ""

# Copy updated Python files
echo "📋 Copying agent/main.py..."
sudo cp -f "$SOURCE_DIR/agent/main.py" "$TARGET_DIR/agent/main.py"

echo "📋 Copying dashboard/main.py..."
sudo cp -f "$SOURCE_DIR/dashboard/main.py" "$TARGET_DIR/dashboard/main.py"

# Copy all templates
echo "📋 Copying templates..."
sudo cp -rf "$SOURCE_DIR/dashboard/templates" "$TARGET_DIR/dashboard/"

# Fix ownership
echo "🔐 Fixing ownership..."
sudo chown -R baron:baron "$TARGET_DIR"

echo ""
echo "✅ Sync complete!"
echo ""
echo "Now you can run:"
echo "  cd /opt/dash"
echo "  source venv/bin/activate"
echo "  python dashboard/main.py"
echo ""

