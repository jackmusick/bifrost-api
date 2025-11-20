#!/bin/bash
# Script to recover the corrupted Git repository in the workspace

set -e

echo "Recovering Git repository in workspace..."
cd /Users/jack/Sync/Bifrost/workspace

echo "1. Backing up current state..."
cp -r .git .git.backup.$(date +%s)

echo "2. Removing corrupted index..."
rm -f .git/index

echo "3. Resetting to origin/main..."
git reset --hard origin/main

echo "4. Verifying repository status..."
git status

echo ""
echo "Recovery complete! Repository is now at origin/main."
echo "Backup saved in .git.backup.* (you can delete it once confirmed working)"
