from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    package_share = get_package_share_directory('orphbot')
    urdf_path = f'{package_share}/urdf/robot.urdf.xacro'
    rviz_path = f'{package_share}/rviz/orphbot.rviz'
    use_description_publisher = LaunchConfiguration('use_description_publisher')
    robot_description = ParameterValue(
        Command(['xacro ', urdf_path]),
        value_type=str,
    )

    return LaunchDescription([
        DeclareLaunchArgument('use_description_publisher', default_value='false'),
        Node(
            package='orphbot',
            executable='robot_description_publisher',
            name='laptop_robot_description_publisher',
            output='screen',
            parameters=[{'robot_description': robot_description}],
            condition=IfCondition(use_description_publisher),
        ),
        Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            arguments=['-d', rviz_path],
            output='screen',
        ),
    ])
