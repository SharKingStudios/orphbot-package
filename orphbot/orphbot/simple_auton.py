from geometry_msgs.msg import Twist
import rclpy
from rclpy.node import Node


class SimpleAuton(Node):
    def __init__(self):
        super().__init__('simple_auton')
        self.declare_parameter('forward_speed', 0.12)
        self.declare_parameter('turn_speed', 0.45)
        self.declare_parameter('first_forward_duration', 1.2)
        self.declare_parameter('turn_duration', 0.9)
        self.declare_parameter('second_forward_duration', 1.0)
        self.declare_parameter('stop_duration', 0.6)
        self.declare_parameter('start_delay', 1.0)

        forward = float(self.get_parameter('forward_speed').value)
        turn = float(self.get_parameter('turn_speed').value)
        first = float(self.get_parameter('first_forward_duration').value)
        turn_time = float(self.get_parameter('turn_duration').value)
        second = float(self.get_parameter('second_forward_duration').value)
        stop = float(self.get_parameter('stop_duration').value)
        delay = float(self.get_parameter('start_delay').value)

        self.steps = [
            (delay, 0.0, 0.0),
            (first, forward, 0.0),
            (stop, 0.0, 0.0),
            (turn_time, 0.0, turn),
            (stop, 0.0, 0.0),
            (second, forward, 0.0),
            (stop, 0.0, 0.0),
        ]
        self.step_index = 0
        self.step_start = self.get_clock().now()
        self.publisher = self.create_publisher(Twist, 'cmd_vel', 10)
        self.timer = self.create_timer(0.05, self.tick)
        self.get_logger().info('Simple autonomous routine armed with conservative speeds')

    def tick(self):
        if self.step_index >= len(self.steps):
            self.publish(0.0, 0.0)
            self.timer.cancel()
            self.get_logger().info('Simple autonomous routine complete')
            return

        duration, linear, angular = self.steps[self.step_index]
        elapsed = (self.get_clock().now() - self.step_start).nanoseconds / 1e9
        if elapsed >= duration:
            self.step_index += 1
            self.step_start = self.get_clock().now()
            self.publish(0.0, 0.0)
            return

        self.publish(linear, angular)

    def publish(self, linear, angular):
        msg = Twist()
        msg.linear.x = linear
        msg.angular.z = angular
        self.publisher.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = SimpleAuton()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.publish(0.0, 0.0)
    finally:
        node.publish(0.0, 0.0)
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
