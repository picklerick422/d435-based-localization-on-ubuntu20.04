#!/bin/bash
# 在 D435 运行后, 通过 dynamic_reconfigure 应用赛道场景调优参数
#
# 用法:
#   ./d435_apply_params.sh                 # 全部应用
#   ./d435_apply_params.sh rgb             # 只应用 RGB
#   ./d435_apply_params.sh depth           # 只应用 深度
#
# 注意: 必须在 rs_camera.launch 启动后再调用本脚本

set -e

CAM_NS="${CAM_NS:-/camera}"
TARGET="${1:-all}"

apply_rgb() {
  echo "  [RGB] 关闭 auto exposure, 固定 78x100us, gain=64"
  rosrun dynamic_reconfigure dynparam set ${CAM_NS}/rgb_camera enable_auto_exposure false
  rosrun dynamic_reconfigure dynparam set ${CAM_NS}/rgb_camera exposure 78
  rosrun dynamic_reconfigure dynparam set ${CAM_NS}/rgb_camera gain 64
  rosrun dynamic_reconfigure dynparam set ${CAM_NS}/rgb_camera frames_queue_size 1
  rosrun dynamic_reconfigure dynparam set ${CAM_NS}/rgb_camera enable_auto_white_balance true
  rosrun dynamic_reconfigure dynparam set ${CAM_NS}/rgb_camera power_line_frequency 1
}

apply_depth() {
  echo "  [Depth] 关闭 auto exposure, 5ms, laser_power=240, preset=HighAccuracy"
  rosrun dynamic_reconfigure dynparam set ${CAM_NS}/stereo_module enable_auto_exposure false
  rosrun dynamic_reconfigure dynparam set ${CAM_NS}/stereo_module exposure 5000
  rosrun dynamic_reconfigure dynparam set ${CAM_NS}/stereo_module gain 16
  rosrun dynamic_reconfigure dynparam set ${CAM_NS}/stereo_module laser_power 240
  rosrun dynamic_reconfigure dynparam set ${CAM_NS}/stereo_module emitter_enabled 1
  rosrun dynamic_reconfigure dynparam set ${CAM_NS}/stereo_module visual_preset 3
  rosrun dynamic_reconfigure dynparam set ${CAM_NS}/stereo_module frames_queue_size 1
  rosrun dynamic_reconfigure dynparam set ${CAM_NS}/stereo_module global_time_enabled true
}

case "$TARGET" in
  rgb)   apply_rgb ;;
  depth) apply_depth ;;
  all)   apply_rgb; apply_depth ;;
  *)     echo "用法: $0 [rgb|depth|all]"; exit 1 ;;
esac

echo "  [完成] D435 调优参数已应用"
