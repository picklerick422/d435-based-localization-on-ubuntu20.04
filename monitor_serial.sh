#!/bin/bash
# 串口监控工具 - 在两个独立终端中显示发送和接收数据

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/catkin_ws/devel/setup.bash"

echo "=== 串口监控工具 ==="
echo ""

# 启动 TX 监控终端 (通过ROS话题，不占用串口)
gnome-terminal --title="STM32 TX 监控" --geometry=100x25+0+0 -- bash -c "
    source '$SCRIPT_DIR/catkin_ws/devel/setup.bash'
    echo '📤 TX 监控 - 显示发送到 STM32 的原始数据'
    echo '============================================================'
    echo ''
    rosrun d435_h30_localization serial_monitor.py --mode tx
    echo ''
    echo 'TX 监控已停止'
    read -p '按回车键关闭...'
" &

sleep 1

# 启动 RX 监控终端 (直接读串口，自动检测)
gnome-terminal --title="STM32 RX 监控" --geometry=100x25+520+0 -- bash -c "
    source '$SCRIPT_DIR/catkin_ws/devel/setup.bash'
    echo '📥 RX 监控 - 显示从 STM32 接收的数据'
    echo '============================================================'
    echo ''
    rosrun d435_h30_localization serial_monitor.py --mode rx
    echo ''
    echo 'RX 监控已停止'
    read -p '按回车键关闭...'
" &

echo "✓ 已启动两个监控终端！"
echo "  - 左侧窗口: TX (发送) 监控 - 显示原始 coor:x,y,r 格式"
echo "  - 右侧窗口: RX (接收) 监控 - 自动检测 STM32 串口"
