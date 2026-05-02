#!/bin/bash
# D435 + IMU 融合定位（原脚本）
set -u

echo "=================================================="
echo "  D435 + IMU 融合定位（原脚本）"
echo "=================================================="
echo "  - launch: d435_imu.launch"
echo "  - IMU/STM32: 自动检测 (115200 找 coor 标签, 460800 找连续二进制)"
echo "  - 发送频率: 50Hz (0.02s)"
echo "=================================================="

cd ~/d435/catkin_ws
source devel/setup.bash

# ---------- 1. 自动检测 IMU / STM32 端口 ----------
echo ""
echo "=================================================="
echo "  扫描串口..."
echo "=================================================="
PORT_VARS=$(rosrun d435_h30_localization detect_serial.py)
eval "$PORT_VARS"

IMU_PORT=${IMU_PORT:-}
STM32_PORT=${STM32_PORT:-}

if [ -z "$IMU_PORT" ]; then
  echo "!! 未检测到 IMU 端口，将退回 launch 默认 /dev/ttyACM0"
  IMU_PORT=/dev/ttyACM0
fi
if [ -z "$STM32_PORT" ]; then
  echo "!! 未检测到 STM32 端口，将让 launch 内部再做一次自动检测"
fi

echo ""
echo "=================================================="
echo "  最终端口分配:"
echo "    IMU   = $IMU_PORT"
echo "    STM32 = ${STM32_PORT:-(launch 内自动检测)}"
echo "=================================================="

# ---------- 2. 启动定位系统 ----------
roslaunch d435_h30_localization d435_imu.launch \
  send_to_stm32:=true \
  imu_port:="$IMU_PORT" \
  stm32_port:="$STM32_PORT" &
LAUNCH_PID=$!

sleep 4

# ---------- 3. 串口助手 ----------
echo ""
echo "=================================================="
echo "  正在启动串口助手（发送 / 接收）"
echo "=================================================="
gnome-terminal --title="串口助手（发送）" --geometry=80x20+100+100 -- bash -c "cd ~/d435/catkin_ws && source devel/setup.bash && sleep 1 && rosrun d435_h30_localization serial_monitor.py --mode tx; exec bash"
gnome-terminal --title="串口助手（接收）" --geometry=80x20+800+100 -- bash -c "cd ~/d435/catkin_ws && source devel/setup.bash && sleep 1 && rosrun d435_h30_localization serial_monitor.py --mode rx; exec bash"

echo ""
echo "=================================================="
echo "  系统启动完成!"
echo "  - 主终端: 定位系统"
echo "  - 串口助手（发送）: TX 数据"
echo "  - 串口助手（接收）: RX 数据"
echo "  按 Ctrl+C 退出"
echo "=================================================="
echo ""

wait $LAUNCH_PID
