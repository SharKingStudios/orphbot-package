import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from std_msgs.msg import String


class RobotDescriptionPublisher(Node):
    def __init__(self):
        super().__init__('robot_description_publisher')
        self.declare_parameter('robot_description', '')
        self.robot_description = self.get_parameter('robot_description').value
        if not self.robot_description:
            raise RuntimeError('robot_description parameter is empty')

        qos = QoSProfile(depth=1)
        qos.durability = DurabilityPolicy.TRANSIENT_LOCAL
        qos.reliability = ReliabilityPolicy.RELIABLE
        self.publisher = self.create_publisher(String, 'robot_description', qos)
        self.create_timer(2.0, self.publish_description)
        self.publish_description()
        self.get_logger().info('Publishing STL robot description for RViz')

    def publish_description(self):
        msg = String()
        msg.data = self.robot_description
        self.publisher.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = None
    try:
        node = RobotDescriptionPublisher()
        rclpy.spin(node)
    except RuntimeError as exc:
        temp_node = node
        if temp_node is None:
            temp_node = rclpy.create_node('robot_description_startup_error')
        temp_node.get_logger().error(str(exc))
    except KeyboardInterrupt:
        pass
    finally:
        if node is not None:
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
