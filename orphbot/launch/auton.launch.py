from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    package_share = get_package_share_directory('orphbot')
    bringup_launch = f'{package_share}/launch/bringup.launch.py'

    mock_hardware = LaunchConfiguration('mock_hardware')
    max_pwm = LaunchConfiguration('max_pwm')
    use_imu = LaunchConfiguration('use_imu')

    return LaunchDescription([
        DeclareLaunchArgument('mock_hardware', default_value='false'),
        DeclareLaunchArgument('max_pwm', default_value='0.35'),
        DeclareLaunchArgument('use_imu', default_value='true'),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(bringup_launch),
            launch_arguments={
                'mock_hardware': mock_hardware,
                'max_pwm': max_pwm,
                'use_imu': use_imu,
            }.items(),
        ),
        Node(
            package='orphbot',
            executable='simple_auton',
            name='simple_auton',
            output='screen',
            parameters=[{
                'forward_speed': ParameterValue('0.12', value_type=float),
                'turn_speed': ParameterValue('0.45', value_type=float),
            }],
        ),
    ])
