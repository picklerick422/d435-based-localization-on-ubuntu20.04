# D435+H30 IMU 融合定位包

本 ROS 包实现了 Intel RealSense D435 深度相机与 H30 IMU 的融合定位功能，支持结合 SolidWorks CAD 模型进行高精度定位。

## 目录结构

```
d435_h30_localization/
├── CMakeLists.txt
├── package.xml
├── README.md
├── launch/
│   ├── d435_h30.launch          # 基本融合定位启动文件
│   └── d435_h30_cad.launch      # 结合CAD模型的定位启动文件
├── scripts/
│   └── h30_imu_driver.py        # 简单的H30 IMU驱动节点
├── calib/
│   ├── aprilgrid_6x8_20mm.yaml  # AprilTag标定板配置
│   ├── imu_calib_example.yaml    # IMU内参示例配置
│   └── camchain_example.yaml     # 相机链示例配置
└── config/                        # 配置文件目录
```

## 前置条件

确保已安装以下软件包：
- ROS Noetic (Ubuntu 20.04)
- Librealsense SDK
- realsense-ros
- pyserial (用于IMU驱动)

可选安装：
- wit_node (H30 IMU官方驱动)
- rtabmap_ros (用于融合定位)
- imu_tools (用于IMU标定)
- kalibr (用于相机-IMU外参标定)

## 快速开始

### 1. 安装包

将本包复制到 catkin 工作空间：

```bash
cp -r d435_h30_localization ~/catkin_ws/src/
cd ~/catkin_ws
catkin_make
source devel/setup.bash
```

### 2. 安装 Python 依赖

```bash
pip3 install pyserial
```

### 3. 基本使用

#### 启动 D435 相机 (仅相机)

```bash
roslaunch d435_h30_localization d435_h30.launch enable_imu:=false
```

#### 启动 D435 + 内置 H30 IMU 驱动

```bash
# 确保串口权限
sudo chmod 777 /dev/ttyUSB0

# 启动系统（默认使用内置IMU驱动）
roslaunch d435_h30_localization d435_h30.launch
```

#### 使用 wit_node (如果已安装)

```bash
roslaunch d435_h30_localization d435_h30.launch use_wit_node:=true
```

#### 启动 RTAB-Map 融合定位 (需要先安装 rtabmap_ros)

```bash
sudo apt install ros-noetic-rtabmap-ros
roslaunch d435_h30_localization d435_h30.launch enable_rtabmap:=true
```

### 4. 传感器标定（关键步骤）

#### 4.1 IMU 内参标定

```bash
# 启动IMU节点（使用内置驱动）
roslaunch d435_h30_localization d435_h30.launch enable_imu:=true

# 在新终端中启动标定工具，保持IMU静止5分钟
rosrun imu_tools imu_calib --imu_topic /imu/data --imu_rate 100

# 标定完成后将生成的 imu_calib.yaml 保存到 calib/ 目录
```

#### 4.2 相机-IMU 外参标定

```bash
# 同时启动D435和H30 IMU
roslaunch d435_h30_localization d435_h30.launch enable_imu:=true

# 录制标定数据包
rosbag record -O cam_imu_calib.bag /camera/color/image_raw /camera/color/camera_info /imu/data

# 运行标定程序
kalibr_calibrate_imu_camera \
  --bag cam_imu_calib.bag \
  --cam calib/camchain.yaml \
  --imu calib/imu_calib.yaml \
  --target calib/aprilgrid_6x8_20mm.yaml
```

### 5. 结合 CAD 模型的定位

1. 将 SolidWorks 导出的 CAD 模型（PLY/STL格式）放置到 `~/race_track/cad_map.ply`
2. 修改参数或通过命令行传递：

```bash
roslaunch d435_h30_localization d435_h30_cad.launch \
  cad_map_path:=/path/to/your/cad_map.ply \
  database_path:=/path/to/your/database.db
```

### 6. 设置初始位姿（开机秒定位）

```bash
rostopic pub /initialpose geometry_msgs/PoseStamped \
"{header: {frame_id: map}, pose: {position: {x:0,y:0,z:0}, orientation: {z:0,w:1}}}" --once
```

## 参数说明

### Launch 文件参数

#### d435_h30.launch
- `enable_imu`: 是否启用 IMU (默认: true)
- `use_wit_node`: 是否使用 wit_node 官方驱动 (默认: false)
- `imu_port`: IMU 串口设备 (默认: /dev/ttyUSB0)
- `imu_baud`: IMU 波特率 (默认: 115200)
- `enable_rtabmap`: 是否启用 RTAB-Map (默认: false)

#### d435_h30_cad.launch
- 包含上述所有参数
- `cad_map_path`: CAD 模型文件路径 (默认: /home/picklerick/race_track/cad_map.ply)
- `database_path`: RTAB-Map 数据库路径 (默认: ~/race_track/race_track_map.db)

## 参数调优

### IMU 权重调整

在 launch 文件中修改 `Odom/IMUWeight` 参数：
- 高纹理场地：0.3
- 低纹理/纯白场地：0.7

### CAD 模型匹配参数

- `Localization/RoiRadius`: 局部匹配半径（默认1.0米）
- `Localization/MinInliers`: 最小匹配内点数（默认15）

## 关于 H30 IMU 驱动

本包提供了一个简单的 H30 IMU 驱动节点 (`scripts/h30_imu_driver.py`)：

- 支持串口通信
- 如果无法连接串口，会自动切换到模拟模式发布测试数据
- 完整的协议解析需要根据 H30 的具体协议文档实现

如需使用 wit_node 官方驱动，请先安装：

```bash
cd ~/catkin_ws/src
git clone https://github.com/yowlings/wit_node.git
cd ~/catkin_ws
catkin_make
```

## 常见问题

1. **串口权限问题**
```bash
sudo chmod 777 /dev/ttyUSB0
```

2. **时间同步问题**
```bash
sudo apt install ntpdate
sudo ntpdate time.nist.gov
```

3. **USB供电问题**
   - 确保使用 USB 3.0 接口
   - 使用原装数据线

4. **找不到 rtabmap_ros**
```bash
sudo apt install ros-noetic-rtabmap-ros
```

5. **Python 依赖问题**
```bash
pip3 install pyserial
```

## 参考资料

- [Intel RealSense 官方文档](https://dev.intelrealsense.com/)
- [RTAB-Map 官方文档](https://introlab.github.io/rtabmap/)
- [Kalibr 标定工具](https://github.com/ethz-asl/kalibr)
- [维特智能 H30 IMU 文档](https://witmotion-sensor.com/)
