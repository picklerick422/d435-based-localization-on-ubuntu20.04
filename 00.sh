#!/bin/bash
# 一键启动定位系统和串口助手（在新窗口

echo "=== 启动定位系统 ==="
cd ~/d435/catkin_ws
source devel/setup.bash

# 在后台启动定位系统
roslaunch d435_h30_localization d435_imu.launch send_to_stm32:=true serial_assistant:=false &
LAUNCH_PID=$!

# 等待一下
sleep 3

echo ""
echo "=== 启动串口助手 ==="
echo "打开新终端..."
gnome-terminal --title="串口助手" --geometry=80x20+100+100 -- bash -c "cd ~/d435/catkin_ws && source devel/setup.bash && rosrun d435_h30_localization serial_assistant.py; exec bash"

echo ""
echo "=== 系统启动完成！"
echo "按 Ctrl+C 退出定位系统"
echo ""

# 保持运行
wait $LAUNCH_PID