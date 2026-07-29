import math

from geometry_msgs.msg import PoseStamped, TransformStamped, Twist
from nav_msgs.msg import Odometry, Path
import rclpy
from rclpy.node import Node
from tf2_ros import TransformBroadcaster


def yaw_to_quaternion(yaw):
    half = yaw * 0.5
    return 0.0, 0.0, math.sin(half), math.cos(half)


class OdomPublisher(Node):
    def __init__(self):
        super().__init__('odom_publisher')
        self.declare_parameter('odom_frame', 'odom')
        self.declare_parameter('base_frame', 'base_link')
        self.declare_parameter('publish_rate', 30.0)
        self.declare_parameter('linear_scale', 1.0)
        self.declare_parameter('angular_scale', 1.0)
        self.declare_parameter('path_max_poses', 500)

        self.odom_frame = self.get_parameter('odom_frame').value
        self.base_frame = self.get_parameter('base_frame').value
        rate = float(self.get_parameter('publish_rate').value)
        self.linear_scale = float(self.get_parameter('linear_scale').value)
        self.angular_scale = float(self.get_parameter('angular_scale').value)
        self.path_max_poses = int(self.get_parameter('path_max_poses').value)

        self.x = 0.0
        self.y = 0.0
        self.yaw = 0.0
        self.linear = 0.0
        self.angular = 0.0
        self.last_time = self.get_clock().now()
        self.path = Path()
        self.path.header.frame_id = self.odom_frame

        self.odom_pub = self.create_publisher(Odometry, 'odom', 10)
        self.path_pub = self.create_publisher(Path, 'path', 10)
        self.tf_broadcaster = TransformBroadcaster(self)
        self.create_subscription(Twist, 'cmd_vel', self.cmd_vel_callback, 10)
        self.create_timer(1.0 / rate, self.tick)
        self.get_logger().info('Command-based odometry publisher ready')

    def cmd_vel_callback(self, msg):
        self.linear = msg.linear.x * self.linear_scale
        self.angular = msg.angular.z * self.angular_scale

    def tick(self):
        now = self.get_clock().now()
        dt = (now - self.last_time).nanoseconds / 1e9
        self.last_time = now
        if dt < 0.0 or dt > 1.0:
            dt = 0.0

        self.x += self.linear * math.cos(self.yaw) * dt
        self.y += self.linear * math.sin(self.yaw) * dt
        self.yaw += self.angular * dt
        self.yaw = math.atan2(math.sin(self.yaw), math.cos(self.yaw))

        qx, qy, qz, qw = yaw_to_quaternion(self.yaw)
        stamp = now.to_msg()

        transform = TransformStamped()
        transform.header.stamp = stamp
        transform.header.frame_id = self.odom_frame
        transform.child_frame_id = self.base_frame
        transform.transform.translation.x = self.x
        transform.transform.translation.y = self.y
        transform.transform.translation.z = 0.0
        transform.transform.rotation.x = qx
        transform.transform.rotation.y = qy
        transform.transform.rotation.z = qz
        transform.transform.rotation.w = qw
        self.tf_broadcaster.sendTransform(transform)

        odom = Odometry()
        odom.header.stamp = stamp
        odom.header.frame_id = self.odom_frame
        odom.child_frame_id = self.base_frame
        odom.pose.pose.position.x = self.x
        odom.pose.pose.position.y = self.y
        odom.pose.pose.orientation.x = qx
        odom.pose.pose.orientation.y = qy
        odom.pose.pose.orientation.z = qz
        odom.pose.pose.orientation.w = qw
        odom.twist.twist.linear.x = self.linear
        odom.twist.twist.angular.z = self.angular
        odom.pose.covariance[0] = 0.08
        odom.pose.covariance[7] = 0.08
        odom.pose.covariance[35] = 0.25
        odom.twist.covariance[0] = 0.12
        odom.twist.covariance[35] = 0.35
        self.odom_pub.publish(odom)

        pose = PoseStamped()
        pose.header = odom.header
        pose.pose = odom.pose.pose
        self.path.header.stamp = stamp
        self.path.poses.append(pose)
        if len(self.path.poses) > self.path_max_poses:
            self.path.poses = self.path.poses[-self.path_max_poses:]
        self.path_pub.publish(self.path)


def main(args=None):
    rclpy.init(args=args)
    node = OdomPublisher()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        try:
            node.destroy_node()
        except KeyboardInterrupt:
            pass
        try:
            if rclpy.ok():
                rclpy.shutdown()
        except Exception:
            pass


if __name__ == '__main__':
    main()
