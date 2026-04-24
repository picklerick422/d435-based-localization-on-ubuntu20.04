#!/bin/bash
# 一键启动相机定位（只用相机）

echo "=== 启动相机定位系统 ==="
cd ~/d435/catkin_ws
source devel/setup.bash

# 启动定位系统
roslaunch d435_h30_localization camera_only.launch send_to_stm32:=true
