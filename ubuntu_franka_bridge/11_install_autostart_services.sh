#!/usr/bin/env bash
set -e

echo "== Install RDK Franka bridge autostart services =="
echo
echo "This will create two user-level systemd services:"
echo "  1. rdk-command-server.service"
echo "  2. rdk-command-executor.service"
echo
echo "Default mode is SAFE DRY-RUN."
echo "It will not move the real robot unless FRANKA_EXECUTE_REAL=1 is set in:"
echo "  ~/.config/rdk_franka_bridge.env"
echo

if [ ! -f /opt/ros/humble/setup.bash ]; then
  echo "ERROR: ROS 2 Humble is missing: /opt/ros/humble/setup.bash"
  echo "Run ./01_install_everything.sh first."
  exit 1
fi

if [ ! -f "$HOME/rdk_franka_ws/install/setup.bash" ]; then
  echo "ERROR: RDK bridge workspace is not built:"
  echo "  $HOME/rdk_franka_ws/install/setup.bash"
  echo "Run ./02_build_workspace.sh first."
  exit 1
fi

mkdir -p "$HOME/.config/systemd/user"
mkdir -p "$HOME/.config"

ENV_FILE="$HOME/.config/rdk_franka_bridge.env"

if [ ! -f "$ENV_FILE" ]; then
  cat > "$ENV_FILE" <<'EOF'
# RDK Franka bridge runtime config
#
# Keep FRANKA_EXECUTE_REAL=0 while testing.
# Set to 1 only after robot safety, workspace, and action code are verified.
FRANKA_EXECUTE_REAL=0

# Change this to your real Franka control box IP when testing connection.
FRANKA_ROBOT_IP=172.16.0.2

# Usually no need to change this.
FRANKA_ACTION_RUNNER=/home/wuqr/franka_direct_control/build/franka_action_runner
FRANKA_ACTION_CONFIG=/home/wuqr/franka_direct_control/config/actions.conf
EOF

  # Replace hard-coded sample home path with current user home.
  sed -i "s#/home/wuqr#${HOME}#g" "$ENV_FILE"
fi

cat > "$HOME/.config/systemd/user/rdk-command-server.service" <<EOF
[Unit]
Description=RDK Franka HTTP Command Server
After=default.target

[Service]
Type=simple
WorkingDirectory=${HOME}/rdk_franka_ws
ExecStart=/bin/bash -lc 'source /opt/ros/humble/setup.bash && source ${HOME}/rdk_franka_ws/install/setup.bash && ros2 run rdk_franka_bridge command_server'
Restart=always
RestartSec=3

[Install]
WantedBy=default.target
EOF

cat > "$HOME/.config/systemd/user/rdk-command-executor.service" <<EOF
[Unit]
Description=RDK Franka Command Executor
After=rdk-command-server.service

[Service]
Type=simple
WorkingDirectory=${HOME}/rdk_franka_ws
EnvironmentFile=${ENV_FILE}
ExecStart=/bin/bash -lc 'source /opt/ros/humble/setup.bash && source ${HOME}/rdk_franka_ws/install/setup.bash && ros2 run rdk_franka_bridge command_executor'
Restart=always
RestartSec=3

[Install]
WantedBy=default.target
EOF

systemctl --user daemon-reload
systemctl --user enable rdk-command-server.service
systemctl --user enable rdk-command-executor.service

echo
echo "Enable user services to run after boot without manually logging in."
echo "This may ask for your Ubuntu password."
sudo loginctl enable-linger "$USER"

systemctl --user restart rdk-command-server.service
systemctl --user restart rdk-command-executor.service

echo
echo "Autostart installed and services started."
echo
echo "Check status:"
echo "  systemctl --user status rdk-command-server.service"
echo "  systemctl --user status rdk-command-executor.service"
echo
echo "Watch logs:"
echo "  journalctl --user -u rdk-command-server.service -f"
echo "  journalctl --user -u rdk-command-executor.service -f"
echo
echo "Runtime config:"
echo "  $ENV_FILE"
echo
echo "Current safety mode:"
grep -E 'FRANKA_EXECUTE_REAL|FRANKA_ROBOT_IP' "$ENV_FILE" || true
