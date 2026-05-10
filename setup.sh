#!/bin/bash
set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
PLIST="$HOME/Library/LaunchAgents/com.user.iphone-import.plist"

echo "==> Creating Python virtual environment..."
python3 -m venv "$DIR/venv"

echo "==> Installing pymobiledevice3..."
"$DIR/venv/bin/pip" install --upgrade pip --quiet
"$DIR/venv/bin/pip" install pymobiledevice3 --quiet

echo "==> Stopping any existing daemon..."
launchctl unload "$PLIST" 2>/dev/null || true

echo "==> Starting daemon via launchd..."
launchctl load "$PLIST"

echo ""
echo "Done! The daemon is now running in the background."
echo ""
echo "Logs:  tail -f $DIR/iphone_import.log"
echo "Stop:  launchctl unload $PLIST"
echo "Start: launchctl load $PLIST"
echo ""
echo "IMPORTANT: On the first connection, tap 'Trust' on your iPhone"
echo "when prompted. Photos.app will open automatically during import."
