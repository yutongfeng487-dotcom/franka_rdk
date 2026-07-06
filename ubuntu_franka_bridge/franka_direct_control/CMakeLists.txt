cmake_minimum_required(VERSION 3.16)
project(franka_direct_control)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(Franka REQUIRED)

add_executable(franka_action_runner src/franka_action_runner.cpp)
target_link_libraries(franka_action_runner Franka::Franka)

add_executable(franka_read_joints src/franka_read_joints.cpp)
target_link_libraries(franka_read_joints Franka::Franka)

install(TARGETS franka_action_runner
  franka_read_joints
  RUNTIME DESTINATION bin
)
