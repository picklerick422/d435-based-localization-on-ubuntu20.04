from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
import os

def generate_launch_description():
    # 参数声明
    enable_imu_arg = DeclareLaunchArgument(
        'enable_imu',
        default_value='true',
        description='Whether to enable IMU'
    )
    use_wit_node_arg = DeclareLaunchArgument(
        'use_wit_node',
        default_value='false',
        description='Whether to use wit_node'
    )
    imu_port_arg = DeclareLaunchArgument(
        'imu_port',
        default_value='/dev/ttyACM0',
        description='IMU serial port'
    )
    imu_baud_arg = DeclareLaunchArgument(
        'imu_baud',
        default_value='460800',
        description='IMU baud rate'
    )
    enable_rtabmap_arg = DeclareLaunchArgument(
        'enable_rtabmap',
        default_value='false',
        description='Whether to enable RTAB-Map'
    )

    # 获取参数
    enable_imu = LaunchConfiguration('enable_imu')
    use_wit_node = LaunchConfiguration('use_wit_node')
    imu_port = LaunchConfiguration('imu_port')
    imu_baud = LaunchConfiguration('imu_baud')
    enable_rtabmap = LaunchConfiguration('enable_rtabmap')

    # 1. 启动 D435 相机
    realsense_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([
                FindPackageShare('realsense2_camera'),
                'launch',
                'rs_launch.py'
            ])
        ]),
        launch_arguments={
            'align_depth.enable': 'true',
            'enable_sync': 'true'
        }.items()
    )

    # 2. 启动 H30 IMU 驱动
    h30_imu_driver_node = Node(
        package='d435_h30_localization',
        executable='h30_imu_driver.py',
        name='h30_imu_driver',
        output='screen',
        parameters=[{
            'serial_port': imu_port,
            'baud_rate': imu_baud
        }],
        condition=IfCondition(enable_imu)
    )

    # 3. 静态 TF 变换
    base_link_to_camera_tf = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='base_link_to_camera',
        arguments=['0', '0', '0', '0', '0', '0', 'base_link', 'camera_link']
    )

    camera_to_imu_tf = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='camera_to_imu',
        arguments=['0', '0', '0', '0', '0', '0', 'camera_link', 'imu_link']
    )

    # 4. RTAB-Map (可选)
    rtabmap_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([
                FindPackageShare('rtabmap_launch'),
                'launch',
                'rtabmap.launch.py'
            ])
        ]),
        launch_arguments={
            'rgb_topic': '/camera/color/image_raw',
            'depth_topic': '/camera/aligned_depth_to_color/image_raw',
            'camera_info_topic': '/camera/color/camera_info',
            'imu_topic': '/imu/data',
            'frame_id': 'camera_link',
            'odom_frame_id': 'odom',
            'map_frame_id': 'map',
            'approx_sync': 'true',
            'approx_sync_max_interval': '0.5',
            'visual_odometry': 'true',
            'odom_topic': 'odom',
            'rtabmap_viz': 'true',
            'rviz': 'true',
            'queue_size': '20',
            'args': '--delete_db_on_start '
                    '--Odom/Strategy 1 '
                    '--Odom/IMUEnabled true '
                    '--Odom/IMUWeight 0.7 '
                    '--Optimizer/GravitySigma 0.01 '
                    '--Odom/ResetOnGap false '
                    '--Odom/ResetOnLowInliers false '
                    '--Odom/FillInfoData true '
                    '--Odom/MinInliers 10 '
                    '--Odom/InlierDistance 0.1 '
                    '--Odom/RansacIterations 100 '
                    '--Odom/IMUBufferSize 2000 '
                    '--Odom/IMUMaxSpinUpWait 2.0 '
                    '--Odom/IMUAngleThreshold 5.0 '
                    '--Odom/IMUGravityVelocityThreshold 5.0 '
                    '--Mem/IncrementalMemory true '
                    '--Mem/BadSignaturesIgnored true '
                    '--Rtabmap/DetectionRate 1 '
                    '--Rtabmap/StartNewMapOnLoopClosure false'
        }.items(),
        condition=IfCondition(enable_rtabmap)
    )

    return LaunchDescription([
        enable_imu_arg,
        use_wit_node_arg,
        imu_port_arg,
        imu_baud_arg,
        enable_rtabmap_arg,
        realsense_launch,
        h30_imu_driver_node,
        base_link_to_camera_tf,
        camera_to_imu_tf,
        rtabmap_launch
    ])
