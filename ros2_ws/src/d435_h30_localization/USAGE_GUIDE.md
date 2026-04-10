# D435 + H30 IMU 融合定位系统 - 使用手册

## 一、开机启动流程

### 1.1 系统上电与连接检查

```bash
# 1. 连接 D435 相机到 USB3.0 接口
# 2. 连接 H30 IMU 到 USB 接口（会显示为 /dev/ttyACM0）

# 检查设备是否识别
ls /dev/ttyACM*
lsusb | grep RealSense
```

**预期输出：**
- `/dev/ttyACM0` (H30 IMU)
- `Intel Corp. Intel(R) RealSense(TM) Depth Camera 435` (D435)

### 1.2 设置串口权限

```bash
sudo chmod 777 /dev/ttyACM0
```

### 1.3 启动 ROS 环境

```bash
# 终端 1：启动融合定位系统
cd ~/catkin_ws
source devel/setup.bash
roslaunch d435_h30_localization d435_h30_rviz.launch
```

**系统将自动启动：**
- ✅ D435 深度相机
- ✅ H30 IMU 驱动
- ✅ RTAB-Map 融合定位算法
- ✅ RViz 可视化界面

---

## 二、日常使用操作

### 2.1 启动后快速验证

**打开新终端，运行：**

```bash
# 检查所有核心话题是否正常发布
rostopic list | grep -E "(imu|odom|rtabmap)"
```

**必须看到以下话题：**
- `/imu/data` - IMU 数据
- `/rtabmap/odom` - 里程计数据

```bash
# 查看相机帧率（应约 30Hz）
rostopic hz /camera/color/image_raw

# 查看 IMU 数据（晃动 IMU 应有变化）
rostopic echo /imu/data --noarr

# 查看里程计（移动小车应有变化）
rostopic echo /rtabmap/odom --noarr
```

### 2.2 RViz 可视化操作

RViz 自动打开后：

1. **Global Status 应显示 OK**（不是 Error）

2. **添加可视化显示项**（如果未自动显示）：
   - 点击左下角 **"Add"** 按钮
   - 选择 **By topic**
   - 勾选：
     - `PointCloud2` → `/rtabmap/cloud_map` （点云地图）
     - `Path` → `/rtabmap/global_path` （运动轨迹）
     - `Pose` → `/rtabmap/global_pose` （当前位姿）

3. **固定坐标系设置**：
   - 左侧面板找到 **"Fixed Frame"**
   - 设置为 `map`

---

## 三、定位数据查看

### 3.1 实时位姿查看

```bash
# 查看当前位置和姿态（x, y, z 坐标 + 四元数方向）
rostopic echo /rtabmap/global_pose --noarr
```

**输出示例：**
```
header:
  seq: 1234
  stamp:
    secs: 1704321000
    nsecs: 123456789
  frame_id: map
pose:
  pose:
    position:
      x: 1.234        # X 坐标（米）
      y: 5.678        # Y 坐标（米）
      z: 0.000        # Z 坐标（通常为 0）
    orientation:
      x: 0.001         # 四元数 X
      y: 0.002         # 四元数 Y
      z: 0.707         # 四元数 Z
      w: 0.707         # 四元数 W
```

### 3.2 里程计数据查看

```bash
# 查看里程计（包含速度信息）
rostopic echo /rtabmap/odom --noarr
```

### 3.3 IMU 数据查看

```bash
# 查看加速度和角速度
rostopic echo /imu/data --noarr
```

---

## 四、常见问题处理

### 4.1 启动失败：找不到串口设备

**症状：**
```
[ERROR] Failed to open serial port /dev/ttyACM0
```

**解决：**
```bash
# 1. 检查 IMU 是否连接
ls /dev/ttyACM*

# 2. 如果没有设备，重新插拔 IMU 的 USB 线

# 3. 设置权限
sudo chmod 777 /dev/ttyACM0

# 4. 重新启动
roslaunch d435_h30_localization d435_h30_rviz.launch
```

### 4.2 启动失败：D435 相机无法加载

**症状：**
```
[FATAL] Failed to load nodelet realsense2_camera
```

**解决：**
```bash
# 1. 检查 USB 连接（必须使用 USB3.0）
lsusb | grep RealSense

# 2. 如果未检测到，重新插拔相机到 USB3.0 接口

# 3. 重启系统后再次尝试
sudo reboot
```

### 4.3 RViz 显示 Global Status: Error

**原因：** TF 树不完整或缺少数据

**解决：**
```bash
# 在新终端中检查 TF 树
rosrun tf view_frames

# 等待 5-10 秒让系统初始化完成
# RViz 中的 Error 通常会在几秒后自动变为 OK
```

### 4.4 定位漂移严重

**可能原因及解决：**

1. **IMU 未正确校准**
   ```bash
   # 使用官方上位机进行陀螺零偏校准
   # 参考 H30 用户手册 3.1 节
   ```

2. **IMU 权重参数调整**
   
   编辑 launch 文件中的 IMU 权重：
   ```xml
   <!-- 在 rtabmap 配置中 -->
   <param name="Odom/IMUWeight" value="0.5" />
   ```
   
   - 高纹理环境：调小到 `0.3`
   - 低纹理/纯白场地：调大到 `0.7`

3. **时间同步问题**
   ```bash
   # 同步系统时间
   sudo apt install ntpdate
   sudo ntpdate time.nist.gov
   ```

### 4.5 话题频率异常

**检查各传感器频率：**

```bash
# 相机应约 30Hz
rostopic hz /camera/color/image_raw

# IMU 应 > 50Hz（通常 100-200Hz）
rostopic hz /imu/data

# 里程计应 > 10Hz
rostopic hz /rtabmap/odom
```

**如果频率过低或为 0：**
- 检查硬件连接
- 重新启动系统
- 检查 CPU/GPU 占用率（`htop` 或 `top`）

---

## 五、数据录制与回放

### 5.1 录制定位数据

```bash
# 录制所有相关话题
rosbag record -O localization_data.bag \
  /imu/data \
  /camera/color/image_raw \
  /camera/aligned_depth_to_color/image_raw \
  /camera/color/camera_info \
  /rtabmap/odom \
  /rtabmap/mapData \
  /rtabmap/global_pose \
  /tf

# 按 Ctrl+C 停止录制
```

### 5.2 回放录制的数据

```bash
# 回放数据包
rosbag play localization_data.bag
```

---

## 六、性能优化建议

### 6.1 提高 RTAB-Map 性能

编辑配置文件或在 launch 中添加参数：

```xml
<!-- 降低地图分辨率以提高性能 -->
<param name="Rtabmap/DetectionRate" value="2" />

<!-- 减少点云密度 -->
<arg name="gen_cloud_decimation" value="4" />

<!-- 限制地图大小 -->
<param name="RGBD/OptimizeMaxError" value="3.0" />
```

### 6.2 降低 CPU 占用

```bash
# 降低相机分辨率（在 rs_camera.launch 中）
<arg name="color_width" value="640" />
<arg name="color_height" value="480" />
<arg name="depth_width" value="640" />
<arg name="depth_height" value="480" />
```

---

## 七、关机流程

### 7.1 正常关闭系统

```bash
# 1. 在运行 roslaunch 的终端按 Ctrl+C 停止所有节点

# 2. 等待所有节点完全关闭（约 5-10 秒）

# 3. 可以安全关闭电源或重启系统
sudo reboot  # 或 shutdown -h now
```

### 7.2 强制关闭（仅在无响应时）

```bash
# 如果 Ctrl+C 无法停止，在新终端中执行：
rosnode kill -a

# 如果仍无法关闭：
killall -9 roslaunch roscore rviz
```

---

## 八、快速参考卡

### 每次开机必做清单 ☑️

- [ ] 连接 D435 到 USB3.0
- [ ] 连接 H30 IMU 到 USB
- [ ] 运行 `sudo chmod 777 /dev/ttyACM0`
- [ ] 执行 `roslaunch d435_h30_localization d435_h30_rviz.launch`
- [ ] 确认 RViz Global Status 为 OK
- [ ] 开始使用！

### 常用命令速查

| 操作 | 命令 |
|------|------|
| 启动系统 | `roslaunch d435_h30_localization d435_h30_rviz.launch` |
| 仅启动 IMU | `roslaunch d435_h30_localization imu_only_official.launch` |
| 查看话题列表 | `rostopic list \| grep -E "(imu\|odom\|rtabmap)"` |
| 查看位姿 | `rostopic echo /rtabmap/global_pose --noarr` |
| 查看里程计 | `rostopic echo /rtabmap/odom --noarr` |
| 查看相机频率 | `rostopic hz /camera/color/image_raw` |
| 录制数据 | `rosbag record -O test.bag /imu/data /rtabmap/odom` |

---

## 九、技术支持

### 关键文件位置

- **Launch 文件目录**: `~/catkin_ws/src/d435_h30_localization/launch/`
- **主 Launch 文件**: `d435_h30_rviz.launch`（带可视化）, `d435_h30_full.launch`（无可视化）
- **IMU 驱动**: `~/catkin_ws/src/yesense_imu/`
- **RTAB-Map 配置**: `/opt/ros/noetic/share/rtabmap_launch/launch/rtabmap.launch`

### 相关文档

- D435 技术文档: `/home/picklerick/d435/Intel D435 Ubuntu20.04 全流程配置与高精度定位技术文档.md`
- H30 用户手册: `/home/picklerick/d435/1.WHEELTEC_H30惯导模块用户手册.md`

---

**版本**: v1.0  
**最后更新**: 2026-04-04  
**适用环境**: Ubuntu 20.04 + ROS Noetic + D435 + H30 IMU
