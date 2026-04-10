from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare

def generate_launch_description():
    # 参数声明
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

    # 获取参数
    imu_port = LaunchConfiguration('imu_port')
    imu_baud = LaunchConfiguration('imu_baud')

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
        }]
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

    # 4. 启动 RTAB-Map
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
            'approx_sync_max_interval': '0.05',
            'visual_odometry': 'true',
            'odom_topic': 'odom',
            'rviz': 'true',
            'rtabmap_viz': 'false',
            'queue_size': '20',
            'args': '--delete_db_on_start'
        }.items()
    )

    return LaunchDescription([
        imu_port_arg,
        imu_baud_arg,
        realsense_launch,
        h30_imu_driver_node,
        base_link_to_camera_tf,
        camera_to_imu_tf,
        rtabmap_launch
    ])
