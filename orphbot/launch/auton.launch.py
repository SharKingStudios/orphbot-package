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
    max_pwm = LaunchConfiguration('max_pwm')

    return LaunchDescription([
        DeclareLaunchArgument('max_pwm', default_value='0.35'),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(bringup_launch),
            launch_arguments={'max_pwm': max_pwm}.items(),
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
