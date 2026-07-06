#!/usr/bin/env bash
set -e

echo "== Realtime notes for Franka =="
echo
echo "Check current kernel:"
uname -a
echo
echo "If libfranka reports:"
echo "  Running kernel does not have realtime capabilities."
echo
echo "Then this Ubuntu needs a PREEMPT_RT realtime kernel before safe real motion control."
echo "Do not do real robot motion until realtime kernel and safety checks are ready."
echo
echo "Current user:"
id
echo
echo "Useful checks:"
echo "  ulimit -r"
echo "  groups"
echo
echo "Ask Codex for the next step with the output of:"
echo "  uname -a"
echo "  lsb_release -a"

