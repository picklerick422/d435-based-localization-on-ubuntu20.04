#!/bin/bash
# D435 + IMU + CAD 地图融合
set -u

echo "=================================================="
echo "  D435 + IMU + CAD 地图融合"
echo "=================================================="
echo "  - launch: d435_imu_cad.launch"
echo "  - IMU/STM32: 自动检测 (115200 找 coor 标签, 460800 找连续二进制)"
echo "  - 发送频率: 50Hz (0.02s)"
echo "  - 需要预先有 CAD 地图: ~/race_track/cad_map.ply"
echo "=================================================="

cd ~/d435/catkin_ws
source devel/setup.bash

# ---------- 0. 依赖检查 ----------
if ! python3 -c "import open3d" >/dev/null 2>&1; then
  echo ""
  echo "!! 致命: 未安装 open3d (cad_icp_localizer 依赖)"
  echo "   请先执行: pip install open3d"
  echo "   按 Ctrl+C 退出，或继续等待 (会启动失败)"
  echo ""
  sleep 3
fi

CAD_PATH="${CAD_PATH:-$HOME/race_track/cad_map.ply}"
if [ ! -f "$CAD_PATH" ]; then
  # 找不到精确路径时, 同目录大小写不敏感地找一个 .ply/.PLY
  CAD_DIR=$(dirname "$CAD_PATH")
  CAD_BASE=$(basename "$CAD_PATH")
  CAD_ALT=$(find "$CAD_DIR" -maxdepth 1 -iname "$CAD_BASE" 2>/dev/null | head -1)
  if [ -n "$CAD_ALT" ]; then
    echo "  (CAD 大小写不匹配, 实际使用: $CAD_ALT)"
    CAD_PATH="$CAD_ALT"
  else
    echo ""
    echo "!! 警告: CAD 文件不存在 -> $CAD_PATH"
    echo "   cad_icp_localizer 会以"空转"模式运行 (不发 /cad_pose)"
    echo "   STM32 通信仍正常启动，可用于测试串口链路"
    echo "   要换路径: 设置环境变量 CAD_PATH=/path/to/cad.ply"
    echo ""
    sleep 1
  fi
fi

# ---------- 1. 自动检测 IMU / STM32 端口 ----------
echo ""
echo "=================================================="
echo "  扫描串口..."
echo "=================================================="
# detect_serial.py 把日志写到 stderr (直接打到终端)
# 把 IMU_PORT/STM32_PORT 写到 stdout (被 $() 捕获)
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
# CAD 默认按 mm 单位 (0.001 缩放) + Y-up 轴重排到 Z-up (xzy)
# 如果 CAD 已经是 m + Z-up, 设 CAD_SCALE=1.0 CAD_AXIS_REMAP=xyz
CAD_SCALE="${CAD_SCALE:-0.001}"
CAD_AXIS_REMAP="${CAD_AXIS_REMAP:-xzy}"
echo ""
echo "  CAD 缩放: x $CAD_SCALE   轴重排: $CAD_AXIS_REMAP"
echo ""

roslaunch d435_h30_localization d435_imu_cad.launch \
  send_to_stm32:=true \
  imu_port:="$IMU_PORT" \
  stm32_port:="$STM32_PORT" \
  cad_path:="$CAD_PATH" \
  cad_scale:="$CAD_SCALE" \
  cad_axis_remap:="$CAD_AXIS_REMAP" &
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
