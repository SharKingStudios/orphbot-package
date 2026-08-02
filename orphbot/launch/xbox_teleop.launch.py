from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    joy_dev = LaunchConfiguration('joy_dev')
    deadzone = LaunchConfiguration('deadzone')

    return LaunchDescription([
        DeclareLaunchArgument('joy_dev', default_value='/dev/input/js0'),
        DeclareLaunchArgument('deadzone', default_value='0.12'),
        Node(
            package='joy',
            executable='joy_node',
            name='joy_node',
            output='screen',
            parameters=[{
                'dev': joy_dev,
                'deadzone': ParameterValue(deadzone, value_type=float),
                'autorepeat_rate': 20.0,
            }],
        ),
        Node(
            package='teleop_twist_joy',
            executable='teleop_node',
            name='teleop_twist_joy_node',
            output='screen',
            parameters=[{
                'require_enable_button': True,
                'enable_button': 2,
                'enable_turbo_button': 5,
                'axis_linear.x': 1,
                'scale_linear.x': 0.16,
                'scale_linear_turbo.x': 0.28,
                'axis_angular.yaw': 0,
                'scale_angular.yaw': 0.65,
                'scale_angular_turbo.yaw': 1.0,
                'inverted_reverse': False,
                'publish_stamped_twist': False,
            }],
        ),
    ])
