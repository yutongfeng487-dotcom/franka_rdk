#include <array>
#include <cmath>
#include <cstdlib>
#include <exception>
#include <fstream>
#include <iostream>
#include <map>
#include <sstream>
#include <stdexcept>
#include <string>
#include <thread>
#include <vector>

#include <franka/control_types.h>
#include <franka/duration.h>
#include <franka/exception.h>
#include <franka/robot.h>
#include <franka/robot_state.h>

namespace {

constexpr double kPi = 3.14159265358979323846;

struct Pose {
  std::array<double, 7> q{};
  double duration{5.0};
};

struct Options {
  std::string robot_ip;
  std::string command;
  std::string item;
  std::string target;
  std::string config_path;
  bool execute{false};
  bool connect_only{false};
};

std::string arg_value(int argc, char** argv, const std::string& key) {
  for (int i = 1; i + 1 < argc; ++i) {
    if (argv[i] == key) {
      return argv[i + 1];
    }
  }
  return "";
}

bool has_flag(int argc, char** argv, const std::string& flag) {
  for (int i = 1; i < argc; ++i) {
    if (argv[i] == flag) {
      return true;
    }
  }
  return false;
}

std::string home_dir() {
  const char* home = std::getenv("HOME");
  return home == nullptr ? "." : std::string(home);
}

Options parse_options(int argc, char** argv) {
  Options options;
  options.robot_ip = arg_value(argc, argv, "--robot-ip");
  options.command = arg_value(argc, argv, "--command");
  options.item = arg_value(argc, argv, "--item");
  options.target = arg_value(argc, argv, "--target");
  options.config_path = arg_value(argc, argv, "--config");
  options.execute = has_flag(argc, argv, "--execute");
  options.connect_only = has_flag(argc, argv, "--connect-only");

  if (options.robot_ip.empty()) {
    const char* env_ip = std::getenv("FRANKA_ROBOT_IP");
    if (env_ip != nullptr) {
      options.robot_ip = env_ip;
    }
  }

  if (options.config_path.empty()) {
    const char* env_config = std::getenv("FRANKA_ACTION_CONFIG");
    if (env_config != nullptr) {
      options.config_path = env_config;
    } else {
      options.config_path = home_dir() + "/franka_direct_control/config/actions.conf";
    }
  }

  return options;
}

void print_usage() {
  std::cout
      << "Usage:\n"
      << "  franka_action_runner --command flip_package\n"
      << "  franka_action_runner --command sort_box --target left\n"
      << "  franka_action_runner --robot-ip 172.16.0.2 --connect-only --execute\n"
      << "  franka_action_runner --robot-ip 172.16.0.2 --command home --execute\n\n"
      << "Default mode is dry-run. Add --execute only after safety checks.\n";
}

std::map<std::string, Pose> load_config(const std::string& path) {
  std::ifstream input(path);
  if (!input) {
    throw std::runtime_error("Cannot open action config: " + path);
  }

  std::map<std::string, Pose> poses;
  std::string line;
  int line_no = 0;
  while (std::getline(input, line)) {
    ++line_no;
    const auto comment = line.find('#');
    if (comment != std::string::npos) {
      line = line.substr(0, comment);
    }
    std::istringstream iss(line);
    std::string name;
    Pose pose;
    if (!(iss >> name)) {
      continue;
    }
    for (double& value : pose.q) {
      if (!(iss >> value)) {
        throw std::runtime_error("Bad config line " + std::to_string(line_no) +
                                 ": expected pose name + 7 joints + duration");
      }
    }
    if (!(iss >> pose.duration)) {
      throw std::runtime_error("Bad config line " + std::to_string(line_no) +
                               ": missing duration");
    }
    if (pose.duration < 2.0) {
      throw std::runtime_error("Bad config line " + std::to_string(line_no) +
                               ": duration must be >= 2.0 seconds");
    }
    poses[name] = pose;
  }

  return poses;
}

std::vector<std::string> action_sequence(const std::string& command, const std::string& target) {
  if (command == "home") {
    return {"home"};
  }
  if (command == "flip_package") {
    return {"home", "pick_above", "pick", "pick_above", "flip_prepare", "flip_place",
            "pick_above", "home"};
  }
  if (command == "sort_box") {
    if (target.find("右") != std::string::npos || target == "right") {
      return {"home", "pick_above", "pick", "pick_above", "box_right", "home"};
    }
    if (target.find("前") != std::string::npos || target == "front") {
      return {"home", "pick_above", "pick", "pick_above", "box_front", "home"};
    }
    if (target.find("后") != std::string::npos || target == "back") {
      return {"home", "pick_above", "pick", "pick_above", "box_back", "home"};
    }
    return {"home", "pick_above", "pick", "pick_above", "box_left", "home"};
  }
  if (command == "sort_bag") {
    if (target.find("左") != std::string::npos || target == "left") {
      return {"home", "pick_above", "pick", "pick_above", "bag_left", "home"};
    }
    if (target.find("前") != std::string::npos || target == "front") {
      return {"home", "pick_above", "pick", "pick_above", "bag_front", "home"};
    }
    if (target.find("后") != std::string::npos || target == "back") {
      return {"home", "pick_above", "pick", "pick_above", "bag_back", "home"};
    }
    return {"home", "pick_above", "pick", "pick_above", "bag_right", "home"};
  }
  if (command == "stop") {
    return {};
  }
  throw std::runtime_error("Unknown command: " + command);
}

void print_sequence(const std::vector<std::string>& sequence) {
  if (sequence.empty()) {
    std::cout << "Action sequence: <none>\n";
    return;
  }
  std::cout << "Action sequence:";
  for (const auto& name : sequence) {
    std::cout << " " << name;
  }
  std::cout << "\n";
}

void move_to_joint_pose(franka::Robot& robot, const Pose& target) {
  std::array<double, 7> initial_q{};
  double elapsed = 0.0;
  bool initialized = false;

  robot.control([&](const franka::RobotState& state, franka::Duration period)
                    -> franka::JointPositions {
    if (!initialized) {
      initial_q = state.q;
      initialized = true;
    }

    elapsed += period.toSec();
    const double progress = std::min(elapsed / target.duration, 1.0);
    const double smooth = 0.5 - 0.5 * std::cos(kPi * progress);

    std::array<double, 7> command_q{};
    for (size_t i = 0; i < command_q.size(); ++i) {
      command_q[i] = initial_q[i] + smooth * (target.q[i] - initial_q[i]);
    }

    franka::JointPositions output(command_q);
    if (progress >= 1.0) {
      return franka::MotionFinished(output);
    }
    return output;
  });
}

void execute_sequence(franka::Robot& robot,
                      const std::map<std::string, Pose>& poses,
                      const std::vector<std::string>& sequence) {
  robot.setCollisionBehavior(
      {{20.0, 20.0, 18.0, 18.0, 16.0, 14.0, 12.0}},
      {{20.0, 20.0, 18.0, 18.0, 16.0, 14.0, 12.0}},
      {{20.0, 20.0, 18.0, 18.0, 16.0, 14.0, 12.0}},
      {{20.0, 20.0, 18.0, 18.0, 16.0, 14.0, 12.0}},
      {{20.0, 20.0, 20.0, 25.0, 25.0, 25.0}},
      {{20.0, 20.0, 20.0, 25.0, 25.0, 25.0}},
      {{20.0, 20.0, 20.0, 25.0, 25.0, 25.0}},
      {{20.0, 20.0, 20.0, 25.0, 25.0, 25.0}});

  for (const auto& name : sequence) {
    const auto it = poses.find(name);
    if (it == poses.end()) {
      throw std::runtime_error("Pose not found in config: " + name);
    }
    std::cout << "Moving to pose: " << name << " duration=" << it->second.duration << "s\n";
    move_to_joint_pose(robot, it->second);
    std::this_thread::sleep_for(std::chrono::milliseconds(300));
  }
}

}  // namespace

int main(int argc, char** argv) {
  const Options options = parse_options(argc, argv);
  if (options.command.empty() && !options.connect_only) {
    print_usage();
    return 2;
  }

  try {
    if (options.robot_ip.empty() && options.execute) {
      throw std::runtime_error("Robot IP is empty. Use --robot-ip or FRANKA_ROBOT_IP.");
    }

    std::vector<std::string> sequence;
    if (!options.connect_only) {
      sequence = action_sequence(options.command, options.target);
      print_sequence(sequence);
    }

    if (!options.execute) {
      std::cout << "[DRY-RUN] command=" << options.command << " item=" << options.item
                << " target=" << options.target << "\n";
      std::cout << "[DRY-RUN] config=" << options.config_path << "\n";
      return 0;
    }

    std::cout << "Connecting to Franka at " << options.robot_ip << "...\n";
    franka::Robot robot(options.robot_ip);
    const auto state = robot.readOnce();
    std::cout << "Connected. Robot mode: " << static_cast<int>(state.robot_mode) << "\n";

    if (options.connect_only) {
      std::cout << "Connection test only. No motion executed.\n";
      return 0;
    }

    const auto poses = load_config(options.config_path);
    execute_sequence(robot, poses, sequence);
    std::cout << "Action finished.\n";
  } catch (const franka::Exception& exc) {
    std::cerr << "Franka error: " << exc.what() << "\n";
    return 1;
  } catch (const std::exception& exc) {
    std::cerr << "Error: " << exc.what() << "\n";
    return 1;
  }

  return 0;
}
