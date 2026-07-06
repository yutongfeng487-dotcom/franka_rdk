#!/usr/bin/env bash
set -e

echo "== Disable RDK Franka bridge autostart services =="

systemctl --user stop rdk-command-executor.service 2>/dev/null || true
systemctl --user stop rdk-command-server.service 2>/dev/null || true
systemctl --user disable rdk-command-executor.service 2>/dev/null || true
systemctl --user disable rdk-command-server.service 2>/dev/null || true

rm -f "$HOME/.config/systemd/user/rdk-command-executor.service"
rm -f "$HOME/.config/systemd/user/rdk-command-server.service"

systemctl --user daemon-reload

echo "Autostart disabled."
echo "Runtime config is kept at:"
echo "  $HOME/.config/rdk_franka_bridge.env"

