#!/usr/bin/env bash
set -e

RUNNER="${HOME}/franka_direct_control/build/franka_read_joints"
CONFIG="${FRANKA_ACTION_CONFIG:-${HOME}/franka_direct_control/config/actions.conf}"

if [ ! -x "$RUNNER" ]; then
  echo "ERROR: 找不到关节读取程序："
  echo "  $RUNNER"
  echo "请先运行："
  echo "  ./08_build_franka_direct_control.sh"
  exit 1
fi

if [ -z "$FRANKA_ROBOT_IP" ]; then
  echo "ERROR: 请先设置 Franka 控制箱 IP，例如："
  echo "  export FRANKA_ROBOT_IP=172.16.0.2"
  exit 1
fi

echo "== Franka 关节角标定工具 =="
echo
echo "使用方法："
echo "1. 在 Desk/手动引导模式下，把机械臂移动到要保存的位置。"
echo "2. 保持机械臂静止。"
echo "3. 输入点位名，例如 home / pick_above / pick / box_left。"
echo

read -r -p "请输入点位名: " POSE_NAME
if [ -z "$POSE_NAME" ]; then
  echo "点位名不能为空。"
  exit 1
fi

read -r -p "运动时长秒数，建议 5.0: " DURATION
if [ -z "$DURATION" ]; then
  DURATION="5.0"
fi

echo "读取当前关节角..."
OUTPUT="$("$RUNNER" --robot-ip "$FRANKA_ROBOT_IP")"
echo "$OUTPUT"

Q_VALUES="$(echo "$OUTPUT" | awk '/^q / {for (i=2; i<=8; i++) printf "%s%s", $i, (i<8 ? " " : "")}')"

if [ -z "$Q_VALUES" ]; then
  echo "ERROR: 未能解析关节角。"
  exit 1
fi

mkdir -p "$(dirname "$CONFIG")"
touch "$CONFIG"

NEW_LINE="${POSE_NAME} ${Q_VALUES} ${DURATION}"

echo
echo "将写入："
echo "$NEW_LINE"
echo
read -r -p "确认保存到 ${CONFIG} ? [y/N] " CONFIRM
case "$CONFIRM" in
  y|Y|yes|YES) ;;
  *) echo "已取消。"; exit 0 ;;
esac

TMP_FILE="$(mktemp)"
if grep -q "^${POSE_NAME}[[:space:]]" "$CONFIG"; then
  awk -v name="$POSE_NAME" -v newline="$NEW_LINE" '
    $1 == name { print newline; done=1; next }
    { print }
    END { if (!done) print newline }
  ' "$CONFIG" > "$TMP_FILE"
else
  cat "$CONFIG" > "$TMP_FILE"
  echo "$NEW_LINE" >> "$TMP_FILE"
fi

cp "$CONFIG" "${CONFIG}.backup.$(date +%Y%m%d_%H%M%S)"
mv "$TMP_FILE" "$CONFIG"

echo "保存成功。"
echo "配置文件：$CONFIG"
echo
echo "建议下一步 dry-run 测试："
echo "  ${HOME}/franka_direct_control/build/franka_action_runner --command home"

