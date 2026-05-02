#!/bin/bash
# D435 纯视觉建图（预先建立地图，供 01.sh 后续加载定位）
set -u

MAP_DIR="$HOME/d435/maps"
MAP_PATH="$MAP_DIR/rtabmap.db"

echo "=================================================="
echo "  D435 纯视觉建图模式"
echo "=================================================="
echo "  - launch:   mapping.launch"
echo "  - 分辨率:   848x480 @ 30fps RGB+Depth"
echo "  - JSON:     d435_race_track_fast_motion.json (RGB 1.5ms)"
echo "  - 保存路径: $MAP_PATH"
echo "  - 操作:     手持/驱动设备遍历赛道以建立地图"
echo "  - 退出:     按 Ctrl+C 保存并退出"
echo "=================================================="

# 确保地图目录存在
mkdir -p "$MAP_DIR"

if [ -f "$MAP_PATH" ]; then
    echo ""
    echo "注意: 检测到已有地图文件，本次建图将在该数据库上继续追加"
    echo "      如需全新建图，请先删除: $MAP_PATH"
    echo ""
fi

cd ~/d435/catkin_ws
source devel/setup.bash

# 启动建图系统
roslaunch d435_h30_localization mapping.launch \
  database_path:="$MAP_PATH" &
LAUNCH_PID=$!

# 捕获 Ctrl+C / SIGTERM，优雅关闭并提示保存
trap 'echo ""; echo "正在保存地图..."; kill -INT $LAUNCH_PID 2>/dev/null; wait $LAUNCH_PID; echo "地图已保存到: $MAP_PATH"; exit 0' INT TERM

echo ""
echo "=================================================="
echo "  建图系统已启动!"
echo "  - RTAB-Map Viz 已启用（观察建图效果）"
echo "  - 请手持或驱动设备遍历赛道"
echo "  - 按 Ctrl+C 保存地图并退出"
echo "=================================================="
echo ""

wait $LAUNCH_PID
