#!/bin/bash
# 一键启动定位系统（带CAD模型，带串口监控 + 自动串口检测）

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== 串口自动检测 ==="
cd "$SCRIPT_DIR"

# 运行串口检测（source 让变量传回当前 shell）
source "$SCRIPT_DIR/detect_serials.sh"

echo ""
echo "最终使用:"
echo "  IMU 端口:    $IMU_PORT"
echo "  STM32 端口:  $STM32_PORT"
echo ""

cd "$SCRIPT_DIR/catkin_ws"
source devel/setup.bash

echo "=== 启动定位系统（带CAD模型） ==="
echo ""

roslaunch d435_h30_localization d435_imu_cad.launch \
    send_to_stm32:=true \
    imu_port:="$IMU_PORT" \
    stm32_port:="$STM32_PORT" &
LAUNCH_PID=$!

echo "主系统已启动 (PID: $LAUNCH_PID)"
echo ""

sleep 3

gnome-terminal --title="STM32 TX 监控" --geometry=100x25+0+0 -- bash -c "
    source '$SCRIPT_DIR/catkin_ws/devel/setup.bash'
    echo '📤 TX 监控 - 显示发送到 STM32 的原始数据'
    echo '============================================================'
    echo ''
    rosrun d435_h30_localization serial_monitor.py --mode tx
" &

gnome-terminal --title="STM32 RX 监控" --geometry=100x25+520+0 -- bash -c "
    source '$SCRIPT_DIR/catkin_ws/devel/setup.bash'
    echo '📥 RX 监控 - 显示从 STM32 接收的数据'
    echo '============================================================'
    echo ''
    rosrun d435_h30_localization serial_monitor.py --mode rx
" &

echo "✓ 已启动两个监控终端！"
echo "  - 左侧窗口: TX (发送) 监控"
echo "  - 右侧窗口: RX (接收) 监控"
echo ""
echo "按 Ctrl+C 停止所有进程"

wait $LAUNCH_PID
