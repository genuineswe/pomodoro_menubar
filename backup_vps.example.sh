#!/bin/bash

# ==============================================================================
# Pomodoro Menu Bar App VPS Backup Script (Example)
# ==============================================================================
# How to use:
# 1. Copy this file to `backup_vps.sh` (remove .example)
#    Command: cp backup_vps.example.sh backup_vps.sh
# 2. Edit the configuration variables below according to your VPS server.
# 3. Give execution permission: chmod +x backup_vps.sh
# 4. Run: ./backup_vps.sh
#
# Automation (Optional):
# You can add this script to crontab for automatic backups.
# ==============================================================================

# ------------------------------------------------------------------------------
# 1. VPS Connection Configuration
# ------------------------------------------------------------------------------
VPS_USER="your_vps_username"          # Replace with your VPS SSH username (e.g. root, ubuntu)
VPS_IP="192.168.1.100"                # Replace with your VPS IP Address
VPS_PORT="22"                         # Replace with your VPS SSH port (default 22)

# ------------------------------------------------------------------------------
# 2. Directory Configuration
# ------------------------------------------------------------------------------
# Local directory where the Pomodoro app is located (usually auto-detected)
LOCAL_DIR=$(dirname "$0")             
# If auto-detect doesn't work, use absolute path (remove the # sign):
# LOCAL_DIR="/Users/your_username/pomodoro_menubar"

# Get current date and time (format: YYYY-MM-DD_HH-MM-SS)
DATETIME_NOW=$(date +"%Y-%m-%d_%H:%M:%S")

# Main backup folder on VPS. This directory will be created if it does not exist.
VPS_BASE_DIR="/var/www/backup_pomodoro"      # Replace with your path backup
VPS_TARGET_DIR="${VPS_BASE_DIR}/${DATETIME_NOW}"

# ------------------------------------------------------------------------------
# 3. Backup Execution Process (Do not change unless you understand what you are doing)
# ------------------------------------------------------------------------------
echo "====================================================="
echo "Select backup mode:"
echo "1) All files (tasks, history, backups, daily log)"
echo "2) Daily log only (session_logs_today.json)"
echo "====================================================="
read -p "Enter your choice (1 or 2): " BACKUP_CHOICE

if [ "$BACKUP_CHOICE" == "2" ]; then
    echo "Mode selected: Daily log only."
    FILES_TO_BACKUP="$LOCAL_DIR/session_logs_today.json"
else
    echo "Mode selected: All files."
    FILES_TO_BACKUP="$LOCAL_DIR/session_logs_history.json $LOCAL_DIR/session_logs_today.json $LOCAL_DIR/tasks.json"
fi

echo "====================================================="
echo "Starting backup process to VPS for $DATETIME_NOW..."
echo "Local location: $LOCAL_DIR"
echo "VPS target    : $VPS_USER@$VPS_IP:$VPS_TARGET_DIR"
echo "====================================================="

# Create directory based on date on VPS
ssh -p "$VPS_PORT" "$VPS_USER@$VPS_IP" "mkdir -p $VPS_TARGET_DIR"

if [ $? -ne 0 ]; then
    echo "❌ Failed to create directory $VPS_TARGET_DIR on VPS."
    echo "Troubleshooting:"
    echo "1. Make sure IP and Port are correct."
    echo "2. Make sure internet connection is active."
    echo "3. Try manual SSH login first to verify key/password."
    exit 1
fi

echo "🔄 Transferring files..."
# Use rsync with --inplace to securely transfer files without mkstemp errors
rsync -avz --inplace -e "ssh -p $VPS_PORT" $FILES_TO_BACKUP "$VPS_USER@$VPS_IP:$VPS_TARGET_DIR/"

if [ $? -eq 0 ]; then
    echo "====================================================="
    echo "✅ Backup successfully performed to $VPS_TARGET_DIR!"
    echo "====================================================="
else
    echo "====================================================="
    echo "❌ A failure occurred during the rsync process."
    echo "Make sure the JSON files to be backed up are available in the local directory."
    echo "====================================================="
fi
