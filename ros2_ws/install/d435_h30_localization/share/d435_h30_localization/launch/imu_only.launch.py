from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

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

    # 启动 H30 IMU 驱动
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

    # 静态 TF 变换
    camera_to_imu_tf = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='camera_to_imu',
        arguments=['0', '0', '0', '0', '0', '0', 'camera_link', 'imu_link']
    )

    return LaunchDescription([
        imu_port_arg,
        imu_baud_arg,
        h30_imu_driver_node,
        camera_to_imu_tf
    ])
