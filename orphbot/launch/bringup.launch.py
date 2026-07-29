from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    package_share = get_package_share_directory('orphbot')
    urdf_path = f'{package_share}/urdf/robot.urdf.xacro'
    config_path = f'{package_share}/config/orphbot.yaml'
    max_pwm = LaunchConfiguration('max_pwm')
    robot_description = ParameterValue(
        Command(['xacro ', urdf_path]),
        value_type=str,
    )

    return LaunchDescription([
        DeclareLaunchArgument('max_pwm', default_value='0.35'),
        Node(
            package='tf2_ros',
            executable='static_transform_publisher',
            name='map_to_odom_publisher',
            arguments=[
                '--x', '0', '--y', '0', '--z', '0',
                '--roll', '0', '--pitch', '0', '--yaw', '0',
                '--frame-id', 'map', '--child-frame-id', 'odom',
            ],
        ),
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            name='robot_state_publisher',
            parameters=[{'robot_description': robot_description}],
        ),
        Node(
            package='orphbot',
            executable='odom_publisher',
            name='odom_publisher',
            output='screen',
            parameters=[config_path],
        ),
        Node(
            package='orphbot',
            executable='mpu6050_node',
            name='mpu6050_node',
            output='screen',
            parameters=[config_path],
        ),
        Node(
            package='orphbot',
            executable='motor_driver',
            name='motor_driver',
            output='screen',
            parameters=[
                config_path,
                {'max_pwm': ParameterValue(max_pwm, value_type=float)},
            ],
        ),
    ])
