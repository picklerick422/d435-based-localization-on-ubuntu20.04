#!/bin/bash
# D435 相机定位（纯视觉，无 IMU；640x480@30fps + 默认滤波，稳定基线）
set -u

HEADLESS="${HEADLESS:-false}"

echo "=================================================="
echo "  D435 相机定位（纯视觉，无 IMU）"
echo "=================================================="
echo "  - launch:  camera_only.launch"
echo "  - 流式:    848x480 @ 60fps RGB+Depth (需 USB3 + D435 固件 5.15+)"
echo "  - 滤波:    decimation,spatial,temporal (D435 后处理)"
echo "  - STM32:   自动检测 (115200, coor 标签)"
echo "  - 发送频率: 50Hz"
echo "  - HEADLESS: ${HEADLESS} (true=关闭 rtabmap_viz 省 CPU)"
echo "=================================================="

cd ~/d435/catkin_ws
source devel/setup.bash

# ---------- 1. 自动检测 STM32 端口 ----------
echo ""
echo "=================================================="
echo "  扫描串口..."
echo "=================================================="
PORT_VARS=$(rosrun d435_h30_localization detect_serial.py)
eval "$PORT_VARS"

STM32_PORT=${STM32_PORT:-}
if [ -z "$STM32_PORT" ]; then
  echo "!! 未检测到 STM32 端口，将让 launch 内部再做一次自动检测"
fi

echo ""
echo "=================================================="
echo "  最终端口分配:"
echo "    STM32 = ${STM32_PORT:-(launch 内自动检测)}"
echo "=================================================="

# ---------- 2. 检测已有地图 ----------
MAP_PATH="$HOME/d435/maps/rtabmap.db"
if [ -f "$MAP_PATH" ]; then
  echo ""
  echo "检测到已有地图: $MAP_PATH"
  echo "将加载该地图进行定位..."
  USE_MAP=true
else
  echo ""
  echo "未检测到已有地图，将以全新地图模式运行"
  echo "提示: 如需预先建立地图，请运行 ./mapping.sh"
  USE_MAP=false
fi

# ---------- 3. 启动定位系统 ----------
if [ "$HEADLESS" = "true" ]; then
  RTABMAP_VIZ=false
else
  RTABMAP_VIZ=true
fi

if [ "$USE_MAP" = "true" ]; then
  echo ""
  echo "加载已有地图: $MAP_PATH"
  echo "运行 localization 模式（只读定位，不追加地图）"

  # 关键：拷贝到 /tmp，让 RTAB 写它的副本，保护原始 db 不被 shutdown 时的 WM 写回覆盖
  TMP_DB="/tmp/rtabmap_loc_$$.db"
  cp "$MAP_PATH" "$TMP_DB"
  echo "地图副本: $TMP_DB（原文件 $MAP_PATH 只读保护）"
  trap 'rm -f "$TMP_DB" 2>/dev/null' EXIT INT TERM

  roslaunch d435_h30_localization camera_only.launch \
    send_to_stm32:=true \
    stm32_port:="$STM32_PORT" \
    rtabmap_viz:="$RTABMAP_VIZ" \
    localization:=true \
    db_path:="$TMP_DB" &
else
  echo ""
  echo "未检测到已有地图，将以全新地图模式运行"
  echo "提示: 如需预先建立地图，请运行 ./mapping.sh"

  roslaunch d435_h30_localization camera_only.launch \
    send_to_stm32:=true \
    stm32_port:="$STM32_PORT" \
    rtabmap_viz:="$RTABMAP_VIZ" \
    db_arg:=--delete_db_on_start &
fi
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
