#!/usr/bin/env bash
set -e

IFACE="${1:-}"

echo "== Configure one network card with two IP addresses =="

if [ -z "${IFACE}" ]; then
  echo "Available network interfaces:"
  ip -br link
  echo
  echo "Usage:"
  echo "  ./05_config_network_two_ips.sh <interface>"
  echo
  echo "Example:"
  echo "  ./05_config_network_two_ips.sh enp3s0"
  echo "  ./05_config_network_two_ips.sh ens33"
  exit 1
fi

echo "interface: ${IFACE}"
echo "Add IPs:"
echo "  192.168.0.100/24  for X5/Robot network"
echo "  172.16.0.100/24   for C2/Shop Floor network"

sudo ip addr flush dev "${IFACE}"
sudo ip addr add 192.168.0.100/24 dev "${IFACE}"
sudo ip addr add 172.16.0.100/24 dev "${IFACE}"
sudo ip link set "${IFACE}" up

echo
ip addr show "${IFACE}"

echo
echo "Done. Now test with:"
echo "  ./06_test_franka_network.sh"

