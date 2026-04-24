#!/bin/bash
# 一键启动定位系统（带CAD模型）

echo "=== 启动定位系统（带CAD模型） ==="
cd ~/d435/catkin_ws
source devel/setup.bash

# 启动定位系统
roslaunch d435_h30_localization d435_imu_cad.launch send_to_stm32:=true
