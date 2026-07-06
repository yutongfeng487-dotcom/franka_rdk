#!/usr/bin/env bash
set -e

ROBOT_IP="${ROBOT_IP:-172.16.0.2}"
SRC="/tmp/read_franka_joints.cpp"
BIN="/tmp/read_franka_joints"

echo "== Create read joints test program =="
echo "robot ip: ${ROBOT_IP}"

cat > "${SRC}" <<CPP
#include <iostream>
#include <franka/exception.h>
#include <franka/robot.h>

int main() {
  try {
    franka::Robot robot("${ROBOT_IP}");
    auto state = robot.readOnce();

    std::cout << "q = ";
    for (double v : state.q) {
      std::cout << v << " ";
    }
    std::cout << std::endl;

    std::cout << "q_deg = ";
    for (double v : state.q) {
      std::cout << v * 180.0 / 3.14159265358979323846 << " ";
    }
    std::cout << std::endl;

    return 0;
  } catch (const franka::Exception& e) {
    std::cerr << "Franka error: " << e.what() << std::endl;
    return 1;
  }
}
CPP

g++ "${SRC}" -o "${BIN}" -lfranka -pthread

echo
echo "Created:"
echo "  ${SRC}"
echo "  ${BIN}"
echo
echo "Run:"
echo "  ./08_run_read_joints.sh"

