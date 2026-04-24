#!/bin/bash
# 方案三：D435 + IMU + CAD 建模融合定位

echo "=================================================="
echo "      方案三：D435 + IMU + CAD 建模融合定位"
echo "=================================================="
cd ~/d435/catkin_ws
source devel/setup.bash

# 启动定位系统
roslaunch d435_h30_localization d435_imu_cad.launch send_to_stm32:=true serial_assistant:=false &
LAUNCH_PID=$!

# 等待一下
sleep 3

echo ""
echo "=================================================="
echo "      正在启动串口助手"
echo "=================================================="
gnome-terminal --title="串口助手" --geometry=80x20+100+100 -- bash -c "cd ~/d435/catkin_ws && source devel/setup.bash && rosrun d435_h30_localization serial_assistant.py; exec bash"

echo ""
echo "=================================================="
echo "      系统启动完成！"
echo "      按 Ctrl+C 退出定位系统"
echo "=================================================="
echo ""

# 保持运行
wait $LAUNCH_PID
