# Source this after /opt/ros/jazzy/setup.bash and the OrphBot workspace setup.
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export ROS_DOMAIN_ID=17
export ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET
export CYCLONEDDS_URI="file://${SCRIPT_DIR}/cyclonedds_wsl.xml"
unset ROS_LOCALHOST_ONLY
