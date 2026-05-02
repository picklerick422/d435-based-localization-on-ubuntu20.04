#!/bin/bash
# D435 + IMU 融合定位（推荐 + 可视化）

echo "=================================================="
echo "  D435 + IMU 融合定位（推荐 + 可视化）"
echo "=================================================="
echo "  - launch: d435_h30_rviz.launch"
echo "  - 优化版: 640x480@30, queue_size=5, base_link"
echo "  - 启动 RViz + RTAB-MapViz 双可视化"
echo "  - 注意: 此模式仅用于调试，不发送 STM32"
echo "=================================================="
cd ~/d435/catkin_ws
source devel/setup.bash

# 启动定位系统（带可视化，无 STM32 发送）
roslaunch d435_h30_localization d435_h30_rviz.launch
