#!/usr/bin/env bash
set -e

IFACE="${1:-}"
MODE="${2:-dual}"

if [ -z "${IFACE}" ]; then
  echo "Usage:"
  echo "  ./10_switch_network_ip.sh <interface> dual"
  echo "  ./10_switch_network_ip.sh <interface> x5"
  echo "  ./10_switch_network_ip.sh <interface> c2"
  echo "  ./10_switch_network_ip.sh <interface> dhcp"
  echo
  echo "Examples:"
  echo "  ./10_switch_network_ip.sh enp3s0 dual"
  echo "  ./10_switch_network_ip.sh ens33 dual"
  echo
  echo "Available interfaces:"
  ip -br link
  exit 1
fi

echo "interface: ${IFACE}"
echo "mode:      ${MODE}"

case "${MODE}" in
  dual)
    echo "Set two static IPs for Franka C2 and X5."
    sudo ip addr flush dev "${IFACE}"
    sudo ip addr add 192.168.0.100/24 dev "${IFACE}"
    sudo ip addr add 172.16.0.100/24 dev "${IFACE}"
    sudo ip link set "${IFACE}" up
    ;;

  x5)
    echo "Set only X5/Robot network IP."
    sudo ip addr flush dev "${IFACE}"
    sudo ip addr add 192.168.0.100/24 dev "${IFACE}"
    sudo ip link set "${IFACE}" up
    ;;

  c2)
    echo "Set only C2/Shop Floor network IP."
    sudo ip addr flush dev "${IFACE}"
    sudo ip addr add 172.16.0.100/24 dev "${IFACE}"
    sudo ip link set "${IFACE}" up
    ;;

  dhcp)
    echo "Restore DHCP using NetworkManager if available."
    sudo ip addr flush dev "${IFACE}"
    sudo ip link set "${IFACE}" up
    if command -v nmcli >/dev/null 2>&1; then
      CONN="$(nmcli -t -f NAME,DEVICE connection show --active | awk -F: -v dev="${IFACE}" '$2 == dev {print $1; exit}')"
      if [ -n "${CONN}" ]; then
        sudo nmcli connection modify "${CONN}" ipv4.method auto
        sudo nmcli connection down "${CONN}" || true
        sudo nmcli connection up "${CONN}" || true
      else
        sudo dhclient "${IFACE}" || true
      fi
    else
      sudo dhclient "${IFACE}" || true
    fi
    ;;

  *)
    echo "ERROR: unknown mode: ${MODE}"
    echo "Use: dual, x5, c2, or dhcp"
    exit 1
    ;;
esac

echo
echo "Current IP:"
ip addr show "${IFACE}"

echo
echo "Useful tests:"
echo "  ping -c 4 192.168.0.1"
echo "  ping -c 4 172.16.0.2"
echo "  nc -vz -w 3 172.16.0.2 1337"
