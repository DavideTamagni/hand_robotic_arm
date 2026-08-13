cmake_minimum_required(VERSION 3.8)
project(hand_robotic_arm)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)

install(DIRECTORY 
  config 
  launch 
  meshes 
  urdf
  worlds
  DESTINATION share/${PROJECT_NAME}
)

install(PROGRAMS
  scripts/pick_can_sequence.py
  scripts/precise_pick_can.py
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()
