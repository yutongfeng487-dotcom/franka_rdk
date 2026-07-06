#!/usr/bin/env bash
set -e

ROBOT_FCI_IP="${ROBOT_FCI_IP:-172.16.0.2}"
ROBOT_X5_IP="${ROBOT_X5_IP:-192.168.0.1}"

echo "== Test Franka network =="
echo "C2/FCI candidate: ${ROBOT_FCI_IP}"
echo "X5 candidate:     ${ROBOT_X5_IP}"

echo
echo "Ping ${ROBOT_X5_IP}:"
ping -c 4 "${ROBOT_X5_IP}" || true

echo
echo "Ping ${ROBOT_FCI_IP}:"
ping -c 4 "${ROBOT_FCI_IP}" || true

echo
echo "Test FCI/libfranka port on ${ROBOT_FCI_IP}:1337"
nc -vz -w 3 "${ROBOT_FCI_IP}" 1337 || true

echo
echo "Test FCI/libfranka port on ${ROBOT_X5_IP}:1337"
nc -vz -w 3 "${ROBOT_X5_IP}" 1337 || true

echo
echo "Expected from yesterday:"
echo "  ${ROBOT_FCI_IP}:1337 should succeed."

