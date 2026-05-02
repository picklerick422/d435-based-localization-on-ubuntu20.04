cmake_minimum_required(VERSION 3.0.2)
project(d435_h30_localization)

find_package(catkin REQUIRED COMPONENTS
  roscpp
  rospy
  std_msgs
  sensor_msgs
  nav_msgs
  geometry_msgs
)

catkin_package(
  CATKIN_DEPENDS roscpp rospy std_msgs sensor_msgs nav_msgs geometry_msgs
)

include_directories(
  ${catkin_INCLUDE_DIRS}
)

catkin_install_python(PROGRAMS
  scripts/h30_imu_driver.py
  scripts/rtabmap_odom_handler.py
  scripts/serial_monitor.py
  scripts/cad_icp_localizer.py
  scripts/detect_serial.py
  DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
)
