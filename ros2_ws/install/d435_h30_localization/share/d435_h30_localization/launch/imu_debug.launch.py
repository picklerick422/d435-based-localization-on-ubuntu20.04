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

    # 启动 H30 IMU 调试驱动
    h30_imu_driver_node = Node(
        package='d435_h30_localization',
        executable='h30_imu_driver_debug.py',
        name='h30_imu_driver_debug',
        output='screen',
        parameters=[{
            'serial_port': imu_port,
            'baud_rate': imu_baud
        }],
        arguments=['--ros-args', '--log-level', 'info']
    )

    return LaunchDescription([
        imu_port_arg,
        imu_baud_arg,
        h30_imu_driver_node
    ])
