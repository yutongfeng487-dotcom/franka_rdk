#include <cstdlib>
#include <exception>
#include <iomanip>
#include <iostream>
#include <string>

#include <franka/exception.h>
#include <franka/robot.h>

namespace {

std::string arg_value(int argc, char** argv, const std::string& key) {
  for (int i = 1; i + 1 < argc; ++i) {
    if (argv[i] == key) {
      return argv[i + 1];
    }
  }
  return "";
}

void print_usage() {
  std::cout << "Usage:\n"
            << "  franka_read_joints --robot-ip 172.16.0.2\n"
            << "or:\n"
            << "  export FRANKA_ROBOT_IP=172.16.0.2\n"
            << "  franka_read_joints\n";
}

}  // namespace

int main(int argc, char** argv) {
  std::string robot_ip = arg_value(argc, argv, "--robot-ip");
  if (robot_ip.empty()) {
    const char* env_ip = std::getenv("FRANKA_ROBOT_IP");
    if (env_ip != nullptr) {
      robot_ip = env_ip;
    }
  }

  if (robot_ip.empty()) {
    print_usage();
    return 2;
  }

  try {
    franka::Robot robot(robot_ip);
    const auto state = robot.readOnce();
    std::cout << std::fixed << std::setprecision(6);
    std::cout << "q";
    for (double value : state.q) {
      std::cout << " " << value;
    }
    std::cout << "\n";
  } catch (const franka::Exception& exc) {
    std::cerr << "Franka error: " << exc.what() << "\n";
    return 1;
  } catch (const std::exception& exc) {
    std::cerr << "Error: " << exc.what() << "\n";
    return 1;
  }

  return 0;
}
