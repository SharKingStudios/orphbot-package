from glob import glob
import os

from setuptools import find_packages, setup

package_name = 'orphbot'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
        (os.path.join('share', package_name, 'urdf'), glob('urdf/*')),
        (os.path.join('share', package_name, 'meshes'), glob('meshes/*')),
        (os.path.join('share', package_name, 'cad'), glob('cad/*')),
        (os.path.join('share', package_name, 'rviz'), glob('rviz/*')),
        (os.path.join('share', package_name, 'config'), glob('config/*')),
        (os.path.join('share', package_name, 'docs'), glob('../docs/*')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='logan',
    maintainer_email='brushfire257@gmail.com',
    description='ROS 2 nodes and guide assets for the OrphBot waypoint tutorial robot.',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'keyboard_teleop = orphbot.keyboard_teleop:main',
            'motor_driver = orphbot.motor_driver:main',
            'motor_test = orphbot.motor_test:main',
            'mpu6050_node = orphbot.mpu6050_node:main',
            'odom_publisher = orphbot.odom_publisher:main',
            'simple_auton = orphbot.simple_auton:main',
        ],
    },
)
